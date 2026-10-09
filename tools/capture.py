#!/usr/bin/env python
"""mitmproxy 抓包脚本：把官方 App 与 api.geifun.com.cn 的交互完整落盘。

用途：官方客户端里「看视频领时长」的领取凭据（``watch_ad_key``）
由服务端在特定时机下发，抓一次真实流量就能确认完整链条，
然后就可以据此校准本项目的领取逻辑。

使用步骤::

    pip install mitmproxy
    # 方式一：脚本模式
    mitmdump -s tools/capture.py -w tools/capture.flow
    # 方式二：只导出 JSON 便于阅读
    mitmdump -s tools/capture.py

随后把手机 Wi-Fi 代理指向电脑的 8080 端口，安装 mitmproxy 证书，
在 App 内点击一次「看视频领时长」，``tools/capture.jsonl`` 里就会出现
完整的请求头、请求体和响应体。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

OUT_FILE = os.environ.get("CAPTURE_OUT", os.path.join(os.path.dirname(__file__), "capture.jsonl"))
TARGET_HOSTS = ("api.geifun.com.cn", "h5.givefun.cn", "log.givefun.cn", "3rd.givefun.cn")


def _append(record: dict) -> None:
    with open(OUT_FILE, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _decode(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, bytes):
        return content.decode("utf-8", "replace")
    return str(content)


def request(flow: Any) -> None:  # noqa: A001 - mitmproxy 约定的钩子名
    host = flow.request.pretty_host
    if not any(host.endswith(target) for target in TARGET_HOSTS):
        return
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "request",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "headers": dict(flow.request.headers),
        "body": _decode(flow.request.get_content()),
    }
    _append(record)
    print(f"[req ] {record['method']} {record['url']}")
    if record["body"]:
        print(f"       body: {record['body'][:300]}")


def response(flow: Any) -> None:
    host = flow.request.pretty_host
    if not any(host.endswith(target) for target in TARGET_HOSTS):
        return
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "response",
        "status": flow.response.status_code,
        "url": flow.request.pretty_url,
        "headers": dict(flow.response.headers),
        "body": _decode(flow.response.get_content()),
    }
    _append(record)
    print(f"[resp] {record['status']} {record['url']}")
    if record["body"]:
        print(f"       body: {record['body'][:300]}")
