#!/usr/bin/env python
"""接口连通性自检：不依赖账号，验证网关、信封格式与网络可达性。

在 GitHub Actions 里建议先跑一次本脚本，用来确认：
1. runner 能否直连 ``api.geifun.com.cn``；
2. 免登录接口是否返回 ``code: 1``；
3. 需要登录的接口是否按预期返回 HTTP 401。

如果第 2 步就失败（超时 / 403），说明当前出口 IP 被网关限制，
需要自建国内 runner 或在 workflow 中配置代理。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import AuthError, GiveFunClient, GiveFunError  # noqa: E402
from src.config import Config  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="疾风加速器接口连通性自检")
    parser.add_argument("--token", default="", help="临时用这个令牌做登录态检查")
    parser.add_argument("--debug", action="store_true", help="打印请求明细")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.token:
        config.token = args.token
    if args.debug:
        config.debug = True

    client = GiveFunClient(config)
    failures = 0

    print("网关: https://api.geifun.com.cn/")
    print(f"出口: {os.environ.get('RUNNER_NAME', 'local')}")
    print(f"令牌: {'已配置' if config.token else '未配置'}\n")

    # 1) 免登录、应当成功
    try:
        data = client.request("jifeng/game/category/list", params={})
        count = len((data or {}).get("list") or [])
        print(f"[OK] 网关连通，游戏分类 {count} 条")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"[!!] 网关不可用: {exc}")

    # 2) 免登录、应当成功
    try:
        ban = client.get_ban_status()
        print(f"[OK] 封禁状态查询: {json.dumps(ban, ensure_ascii=False)}")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"[!!] 封禁状态查询失败: {exc}")

    # 3) 需登录接口：无令牌应 401；有令牌应能通过
    try:
        info = client.check_info()
        print(f"[OK] 登录态有效: {json.dumps(info, ensure_ascii=False)[:160]}")
    except GiveFunError as exc:
        if config.token:
            failures += 1
            print(f"[!!] 已配置令牌但校验失败（令牌过期？）: {exc}")
        elif getattr(exc, "status", None) == 401:
            print("[OK] 鉴权生效（未登录按预期返回 401）")
        else:
            print(f"[??] checkinfo 返回非 401 错误: {exc}")

    # 4) 需登录的只读接口：无令牌时应表现为「未登录」，有令牌时应返回数据
    try:
        progress = client.video_progress()
        print(f"[OK] 任务进度接口可达: {json.dumps(progress, ensure_ascii=False)[:200]}")
    except AuthError as exc:
        if config.token:
            failures += 1
            print(f"[!!] 已配置令牌但仍提示未登录: {exc}")
        else:
            print("[OK] 任务进度接口可达（当前未配置令牌，返回未登录属预期）")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"[!!] 任务进度接口失败: {exc}")

    print()
    if failures:
        print(f"自检未全部通过（{failures} 项失败）")
    else:
        print("自检通过 ✅")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
