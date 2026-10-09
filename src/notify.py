"""多渠道推送通知（仅标准库实现）。

支持渠道（按需在仓库 Secrets 中配置，可同时配置多个，全部都会收到推送）：

======================  ==========================  ==============================
渠道                    Secret 名称                 说明
======================  ==========================  ==============================
PushPlus                ``PUSHPLUS_TOKEN``          可选 ``PUSHPLUS_TOPIC`` 群组
Server 酱               ``SERVERCHAN_SENDKEY``      SendKey
企业微信机器人          ``WECOM_BOT_KEY``           webhook 的 key
钉钉机器人              ``DINGTALK_BOT_KEY``        可选 ``DINGTALK_SECRET`` 加签
飞书机器人              ``FEISHU_BOT_KEY``          webhook 的 key
Bark (iOS)              ``BARK_KEY``                可选 ``BARK_GROUP``
Telegram                ``TG_BOT_TOKEN``            配合 ``TG_CHAT_ID``
======================  ==========================  ==============================
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

TITLE = "疾风加速器每日领取"


def _post_json(url: str, payload: Dict, timeout: int = 15) -> Tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json; charset=utf-8")
    return _send(request, timeout)


def _send(request: urllib.request.Request, timeout: int = 15) -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", "replace")
        if request.full_url.startswith("https://api.telegram.org"):
            ok = '"ok":true' in text.replace(" ", "")
            return ok, text[:200]
        return True, text[:200]
    except Exception as exc:  # noqa: BLE001 - 通知失败不应影响主流程
        return False, str(exc)[:200]


# ----------------------------------------------------------------------
# 各渠道实现
# ----------------------------------------------------------------------

def notify_pushplus(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    token = env.get("PUSHPLUS_TOKEN", "")
    if not token:
        return False, "未配置"
    payload = {"token": token, "title": TITLE, "content": content, "template": "txt"}
    topic = env.get("PUSHPLUS_TOPIC", "")
    if topic:
        payload["topic"] = topic
    return _post_json("https://www.pushplus.plus/send", payload)


def notify_serverchan(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    key = env.get("SERVERCHAN_SENDKEY", "")
    if not key:
        return False, "未配置"
    if key.startswith("sctp"):
        url = f"https://{key}.push.ft07.com/send"
    else:
        url = f"https://sctapi.ftqq.com/{key}.send"
    return _post_json(url, {"title": TITLE, "desp": content})


def notify_wecom(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    key = env.get("WECOM_BOT_KEY", "")
    if not key:
        return False, "未配置"
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    return _post_json(url, {"msgtype": "text", "text": {"content": f"{TITLE}\n{content}"}})


def notify_dingtalk(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    key = env.get("DINGTALK_BOT_KEY", "")
    if not key:
        return False, "未配置"
    url = "https://oapi.dingtalk.com/robot/send?access_token=" + key
    secret = env.get("DINGTALK_SECRET", "")
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(digest).decode("utf-8"))
        url = f"{url}&timestamp={timestamp}&sign={sign}"
    return _post_json(url, {"msgtype": "text", "text": {"content": f"{TITLE}\n{content}"}})


def notify_feishu(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    key = env.get("FEISHU_BOT_KEY", "")
    if not key:
        return False, "未配置"
    url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{key}"
    return _post_json(url, {"msg_type": "text", "content": {"text": f"{TITLE}\n{content}"}})


def notify_bark(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    key = env.get("BARK_KEY", "")
    if not key:
        return False, "未配置"
    if key.startswith("http"):
        base = key.rstrip("/")
    else:
        base = f"https://api.day.app/{key}"
    url = f"{base}/{urllib.parse.quote(TITLE)}/{urllib.parse.quote(content)}"
    group = env.get("BARK_GROUP", "")
    if group:
        url = f"{url}?group={urllib.parse.quote(group)}"
    return _send(urllib.request.Request(url, method="GET"))


def notify_telegram(env: Dict[str, str], content: str) -> Tuple[bool, str]:
    token = env.get("TG_BOT_TOKEN", "")
    chat_id = env.get("TG_CHAT_ID", "")
    if not (token and chat_id):
        return False, "未配置"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return _post_json(url, {"chat_id": chat_id, "text": f"{TITLE}\n{content}"})


CHANNELS = [
    ("PushPlus", notify_pushplus),
    ("Server酱", notify_serverchan),
    ("企业微信", notify_wecom),
    ("钉钉", notify_dingtalk),
    ("飞书", notify_feishu),
    ("Bark", notify_bark),
    ("Telegram", notify_telegram),
]


def push(env: Dict[str, str], content: str) -> List[Tuple[str, bool, str]]:
    """向所有已配置的渠道推送，返回 ``[(渠道, 是否成功, 信息)]``。"""
    results: List[Tuple[str, bool, str]] = []
    for name, handler in CHANNELS:
        try:
            ok, message = handler(env, content)
        except Exception as exc:  # noqa: BLE001
            ok, message = False, str(exc)[:200]
        if message == "未配置":
            continue
        results.append((name, ok, message))
        status = "✅" if ok else "❌"
        print(f"[通知] {status} {name}: {message}")
    if not results:
        print("[通知] 未配置任何推送渠道，跳过")
    return results


def enabled_channels(env: Dict[str, str]) -> List[str]:
    names: List[str] = []
    if env.get("PUSHPLUS_TOKEN"):
        names.append("PushPlus")
    if env.get("SERVERCHAN_SENDKEY"):
        names.append("Server酱")
    if env.get("WECOM_BOT_KEY"):
        names.append("企业微信")
    if env.get("DINGTALK_BOT_KEY"):
        names.append("钉钉")
    if env.get("FEISHU_BOT_KEY"):
        names.append("飞书")
    if env.get("BARK_KEY"):
        names.append("Bark")
    if env.get("TG_BOT_TOKEN") and env.get("TG_CHAT_ID"):
        names.append("Telegram")
    return names


def build_report(
    date_str: str,
    phone: str,
    steps: List[Tuple[str, bool, str]],
    balance: Optional[str] = None,
) -> str:
    """把执行结果拼成一段人类可读的文本。"""
    lines = [f"执行日期：{date_str}", f"账号：{phone or '(未配置)'}", ""]
    success = sum(1 for _, ok, _ in steps if ok)
    lines.append(f"结果：{success}/{len(steps)} 步成功")
    lines.append("")
    for name, ok, detail in steps:
        lines.append(f"{'✅' if ok else '❌'} {name}：{detail}")
    if balance:
        lines.append("")
        lines.append(f"剩余加速时长：{balance}")
    lines.append("")
    lines.append("—— 由 GitHub Actions 自动执行")
    return "\n".join(lines)
