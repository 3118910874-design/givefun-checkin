"""每日自动领取加速时长的主流程。

流程（每一步都会记录到通知里）：

1. 校验凭据 → 调用 ``jifeng/user/checkinfo`` 确认令牌有效；
2. 读取进度 → ``GET jifeng/videoads/get/progress`` 拿到今日「看视频领时长」任务；
3. 领取任务 → ``POST jifeng/videoads/report/progress``，参数 ``watch_ad_key``；
4. 复核余额 → ``GET jifeng/videoads/history/list``，确认加速时长是否增加；
5. 汇总结果并推送通知。

设计原则：任何一步失败都不中断整体流程，失败原因会原样体现在通知文本中，
方便你在 Actions 日志/推送里直接定位问题。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import notify
from .client import AuthError, GiveFunClient, GiveFunError
from .config import Config, mask_phone

Step = Tuple[str, bool, str]

# 可能承载「待领取任务凭据」的字段名（大小写不敏感）
KEY_FIELD_HINTS = ("watch_ad_key", "watchadkey", "ad_key", "adkey", "task_key", "taskkey",
                   "key", "watch_key")


def human_time(timestamp: Any) -> str:
    """把秒级时间戳格式化成可读时间；0/空值返回 ``-``。"""
    try:
        value = int(timestamp)
    except (TypeError, ValueError):
        return "-"
    if value <= 0:
        return "-"
    # 兼容毫秒时间戳
    if value > 10_000_000_000:
        value //= 1000
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def collect_keys(node: Any, parent_key: str = "") -> List[str]:
    """递归扫描响应体，收集形如 ``watch_ad_key`` 的字符串值。"""
    found: List[str] = []

    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            if isinstance(value, str) and value and any(hint in lowered for hint in KEY_FIELD_HINTS):
                if len(value) >= 8:  # 过滤掉 "0"/"1" 之类的状态位
                    found.append(value)
            found.extend(collect_keys(value, lowered))
    elif isinstance(node, list):
        for item in node:
            found.extend(collect_keys(item, parent_key))

    # 去重且保序
    seen = set()
    unique: List[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def summarize_progress(progress: Dict[str, Any]) -> str:
    """用一句话描述今日任务进度。"""
    if not progress:
        return "接口未返回数据"
    watch_num = progress.get("watch_num")
    parts: List[str] = []
    if watch_num is not None:
        parts.append(f"今日可看 {watch_num} 次")
    end_time = human_time(progress.get("speed_end_time"))
    if end_time != "-":
        parts.append(f"加速时长到期 {end_time}")
    for field in ("watch_video_progress", "new_watch_video_progress"):
        value = progress.get(field)
        if value not in (None, "", [], {}):
            parts.append(f"{field}={json.dumps(value, ensure_ascii=False)[:160]}")
    keys = collect_keys(progress)
    if keys:
        parts.append(f"发现 {len(keys)} 个可领取凭据")
    popup = progress.get("popup_copy")
    if popup:
        parts.append(f"提示文案：{str(popup)[:40]}")
    return "；".join(parts) if parts else "无可用任务信息"


def run(config: Config) -> int:
    today = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client = GiveFunClient(config)
    steps: List[Step] = []
    balance: Optional[str] = None

    def record(name: str, ok: bool, detail: str) -> None:
        steps.append((name, ok, detail))
        print(f"{'[OK]' if ok else '[!!]'} {name}: {detail}")

    # --- 0. 账号状态（免登录接口，可用于判断是否被封禁） -------------------
    try:
        ban = client.get_ban_status()
        banned_id = (ban or {}).get("banned_id") or ""
        if banned_id:
            record("账号状态", False, f"账号受限：{banned_id} {(ban or {}).get('tips', '')}".strip())
            notify.push(config.notify_env, notify.build_report(today, mask_phone(config.phone), steps))
            return 1
        record("账号状态", True, "正常")
    except Exception as exc:  # noqa: BLE001
        record("账号状态", False, f"查询失败（不影响后续）：{exc}")

    # --- 1. 校验登录态 ----------------------------------------------------
    if not config.has_credentials:
        record("登录校验", False,
               "未配置 GIVEFUN_TOKEN（或 GIVEFUN_PHONE + GIVEFUN_DEVICE_ID），"
               "请先运行「疾风登录」工作流")
        notify.push(config.notify_env, notify.build_report(today, mask_phone(config.phone), steps))
        return 1

    try:
        info = client.check_info()
        nickname = ""
        if isinstance(info, dict):
            nickname = str(info.get("nickName") or info.get("nickname") or info.get("phone") or "")
        record("登录校验", True, f"令牌有效 {nickname}".strip())
    except AuthError as exc:
        record("登录校验", False, f"{exc}，令牌可能已过期，请重新运行「疾风登录」工作流")
        notify.push(config.notify_env, notify.build_report(today, mask_phone(config.phone), steps))
        return 1
    except GiveFunError as exc:
        record("登录校验", False, f"{exc}")

    if config.warmup:
        try:
            client.heartbeat()
            record("客户端心跳", True, "已上报")
        except Exception as exc:  # noqa: BLE001
            record("客户端心跳", False, f"失败（忽略）：{exc}")

    # --- 2. 读取任务进度 --------------------------------------------------
    progress: Dict[str, Any] = {}
    try:
        progress = client.video_progress()
        record("读取任务进度", True, summarize_progress(progress))
        if config.debug:
            print("[debug] get/progress -> " + json.dumps(progress, ensure_ascii=False))
    except AuthError as exc:
        record("读取任务进度", False, f"{exc}；请重新运行「疾风登录」工作流")
    except GiveFunError as exc:
        record("读取任务进度", False, str(exc))

    # --- 3. 领取任务 ------------------------------------------------------
    keys = collect_keys(progress)
    if not keys:
        record("领取任务", True, "今日暂无可领取任务（或任务凭据需在客户端 App 内观看广告后下发）")
    else:
        if config.max_claim:
            keys = keys[: config.max_claim]
        claimed = 0
        failures: List[str] = []
        for index, key in enumerate(keys, 1):
            try:
                result = client.report_progress(key)
                status = (result or {}).get("watch_ad_key_status")
                watch_num = (result or {}).get("watch_num")
                if status in (0, "0"):
                    failures.append(f"#{index} 服务端判定凭据无效（watch_ad_key_status=0）")
                    continue
                claimed += 1
                detail = json.dumps(result, ensure_ascii=False)[:120] if result else "成功"
                print(f"[OK] 领取任务 #{index}: {detail}"
                      + (f"（今日剩余 {watch_num} 次）" if watch_num is not None else ""))
            except AuthError as exc:
                failures.append(f"#{index} {exc}")
                break
            except GiveFunError as exc:
                failures.append(f"#{index} {exc}")
        if claimed:
            record("领取任务", True, f"成功 {claimed}/{len(keys)} 个任务")
        else:
            record("领取任务", False, "；".join(failures) or "全部失败")
        for failure in failures:
            print(f"[!!] 领取失败 {failure}")

    # --- 4. 复核余额 ------------------------------------------------------
    try:
        history = client.video_history()
        end_time = human_time((history or {}).get("speed_end_time"))
        balance = f"到期时间 {end_time}" if end_time != "-" else "接口未返回到期时间"
        record("复核余额", True, json.dumps(history, ensure_ascii=False)[:200])
    except AuthError as exc:
        record("复核余额", False, str(exc))
    except GiveFunError as exc:
        record("复核余额", False, str(exc))

    # --- 5. 汇总 ----------------------------------------------------------
    content = notify.build_report(today, mask_phone(config.phone), steps, balance)
    print("\n" + content)
    notify.push(config.notify_env, content)

    failed = [name for name, ok, _ in steps if not ok]
    return 0 if not failed else 1


def make_client(config: Optional[Config] = None) -> GiveFunClient:
    return GiveFunClient(config or Config.from_env())


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="疾风加速器每日自动领取加速时长")
    parser.add_argument("--debug", action="store_true", help="打印请求/响应明细")
    parser.add_argument("--dry-run", action="store_true", help="只查询，不发起领取")
    args = parser.parse_args(list(argv) if argv is not None else None)

    config = Config.from_env()
    if args.debug:
        config.debug = True

    if args.dry_run:
        config.max_claim = 0
        return _dry_run(config)

    return run(config)


def _dry_run(config: Config) -> int:
    """只读检查：验证凭据与接口连通性，不做任何写操作。"""
    client = GiveFunClient(config)
    print("== dry-run：仅查询，不领取 ==")
    checks = [
        ("免登录接口", lambda: client.get_ban_status()),
        ("登录态", lambda: client.check_info()),
        ("任务进度", lambda: client.video_progress()),
        ("任务历史", lambda: client.video_history()),
    ]
    if config.phone:
        checks.insert(1, ("手机号状态", lambda: client.phone_status(config.phone)))
    failed = 0
    for name, call in checks:
        try:
            data = call()
            print(f"[OK] {name}: {json.dumps(data, ensure_ascii=False)[:300]}")
        except AuthError as exc:
            if config.has_credentials:
                failed += 1
                print(f"[!!] {name}: {exc}")
            else:
                print(f"[--] {name}: 未配置凭据（预期）")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[!!] {name}: {exc}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
