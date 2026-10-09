"""疾风加速器接口客户端。

协议要点（对线上网关实测 + 官方安卓客户端 com.gameaccel.rapid 逆向得出）：

* 网关：``https://api.geifun.com.cn/``，路径形如 ``jifeng/<module>/<action>``
  （**没有** 前导斜杠，也没有 ``/api`` 前缀）。
* **参数位置：查询字符串（query string）**。这是本项目踩过的最大一个坑——
  服务端不解析 JSON 请求体，把参数放进 body 只会得到
  ``field "xxx" is not set``。少数接口（如 ``user/heartbeat``）两种都认，
  但 query 是通用做法。
* 统一响应信封::

      {"code": 1, "msg": "success", "data": {...}}

  ``code == 1`` 成功；``code == 3`` 参数/业务错误（``msg`` 给出原因）；
  HTTP 401 表示未登录。
* 鉴权：登录或注册后服务端下发令牌，随请求头回传（``GIVEFUN_TOKEN``）。
  官方客户端同时携带 ``x-device-id`` 等设备头。
* 部分只读接口（``videoads/get/progress``、``videoads/history/list``）即使未登录
  也返回 HTTP 200，只在信封里给出 ``code=3, msg=用户信息错误``，
  本模块会把它规范化成 :class:`AuthError`。

本模块只使用标准库，便于在 GitHub Actions 的裸 Python 环境里直接跑。
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from .config import (
    API_BASE,
    APP_VERSION_CODE,
    APP_VERSION_NAME,
    MAIN_CHANNEL,
    PACKAGE_NAME,
    PLATFORM,
    SUB_CHANNEL,
    Config,
)


class GiveFunError(RuntimeError):
    """接口层面的业务错误。"""

    def __init__(self, message: str, code: Any = None, status: Optional[int] = None,
                 payload: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.payload = payload


class AuthError(GiveFunError):
    """未登录 / 令牌失效。"""


# 服务端把「未登录」也表达成业务错误时的提示语
_AUTH_MESSAGES = ("用户信息错误", "未登录", "token 过期", "token失效", "登录已过期")


class GiveFunClient:
    """极简 HTTP 客户端。"""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._ssl_ctx = ssl.create_default_context()
        self.last_response: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 基础请求
    # ------------------------------------------------------------------
    def _base_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "okhttp/4.9.0",
            "App-Id": PACKAGE_NAME,
            "App-Ver": APP_VERSION_NAME,
            "app-version": APP_VERSION_NAME,
            "appVersion": APP_VERSION_NAME,
            "version": APP_VERSION_NAME,
            "platform": PLATFORM,
            "os": PLATFORM,
            "channel": MAIN_CHANNEL,
            "subch": SUB_CHANNEL,
            "packageName": PACKAGE_NAME,
            "vc": APP_VERSION_CODE,
        }

        token = self.config.token
        if token:
            # 官方客户端使用 accessToken/token 语义的鉴权头；这里同时带上几种常见
            # 名称，服务端只会识别其中一种，多带不会产生副作用。
            headers["Token"] = token
            headers["token"] = token
            headers["Authorization"] = token
            headers["accessToken"] = token
        if self.config.device_id:
            headers["x-device-id"] = self.config.device_id
            headers["deviceId"] = self.config.device_id
            headers["device_id"] = self.config.device_id
        if self.config.user_id:
            headers["userId"] = self.config.user_id
            headers["UID"] = self.config.user_id

        headers.update(self.config.extra_headers)
        return headers

    def request(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        json_body: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        """发起一次请求并返回 ``data`` 字段（``raw=True`` 时返回完整响应体）。

        :param params:    查询字符串参数（**推荐使用**，服务端主要读这里）
        :param json_body: 可选的 JSON 请求体（少数接口需要）
        """
        url = API_BASE + path.lstrip("/")
        if params:
            clean = {k: v for k, v in params.items() if v is not None and v != ""}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"

        body: Optional[bytes] = None
        headers = self._base_headers()
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        if self.config.debug:
            print(f"[debug] {method.upper()} {url}")
            if body:
                print(f"[debug]   body={body.decode('utf-8')[:300]}")

        last_error: Optional[Exception] = None
        for attempt in range(self.config.retries + 1):
            request = urllib.request.Request(url, data=body, method=method.upper())
            for key, value in headers.items():
                request.add_header(key, value)

            try:
                with urllib.request.urlopen(
                    request, timeout=self.config.timeout, context=self._ssl_ctx
                ) as response:
                    text = response.read().decode("utf-8", "replace")
                    status = response.status
            except urllib.error.HTTPError as exc:
                text = exc.read().decode("utf-8", "replace")
                status = exc.code
            except Exception as exc:  # 网络层错误：重试
                last_error = exc
                if attempt < self.config.retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise GiveFunError(f"网络请求失败: {exc}") from exc

            if self.config.debug and text:
                print(f"[debug]   <- {status} {text[:400]}")

            parsed: Any
            try:
                parsed = json.loads(text) if text.strip() else {}
            except json.JSONDecodeError:
                parsed = {"code": status, "msg": text.strip()[:200], "data": None}

            if status == 401:
                raise AuthError("未登录或登录已过期（HTTP 401）", code=401, status=status,
                                payload=parsed)

            if raw:
                return parsed

            if not isinstance(parsed, dict):
                return parsed

            code = parsed.get("code")
            if code is not None and int(code) != 1:
                message = str(parsed.get("msg") or f"接口返回 code={code}")
                error = GiveFunError(message, code=code, status=status, payload=parsed)
                if int(code) == 3 and any(word in message for word in _AUTH_MESSAGES):
                    raise AuthError(message, code=code, status=status, payload=parsed)
                raise error

            return parsed.get("data")

        raise GiveFunError(f"网络请求失败: {last_error}")

    # ------------------------------------------------------------------
    # 业务接口
    # ------------------------------------------------------------------
    def send_sms_code(self, phone: str, code_type: int = 1) -> Any:
        """发送短信验证码。

        :param code_type: 1=登录，2=注册（服务端必填 ``type``）
        """
        return self.request("jifeng/sms/sendcode",
                            params={"phoneNumber": phone, "type": code_type})

    def phone_status(self, phone: str) -> Dict[str, Any]:
        """查询手机号是否已注册。返回 ``{"isRegister": 0/1, "isSetPwd": 0/1}``。"""
        data = self.request("jifeng/user/phonestatus", params={"phoneNumber": phone})
        return data if isinstance(data, dict) else {}

    def login(self, phone: str, code: str) -> Dict[str, Any]:
        """短信验证码登录（真实参数名是 ``veriStr``，即短信验证码本身）。"""
        data = self.request("jifeng/user/login",
                            params={"phoneNumber": phone, "veriStr": code})
        return data if isinstance(data, dict) else {}

    def register(self, phone: str, code: str, password: str = "", **extra: Any) -> Dict[str, Any]:
        """短信验证码注册（参数名为 ``verifyCode``）。"""
        params: Dict[str, Any] = {"phoneNumber": phone, "verifyCode": code}
        if password:
            params["password"] = password
        params.update(extra)
        data = self.request("jifeng/user/register", params=params)
        return data if isinstance(data, dict) else {}

    def check_info(self) -> Any:
        """校验当前令牌并返回用户信息（未登录返回 HTTP 401）。"""
        return self.request("jifeng/user/checkinfo", params={})

    def heartbeat(self) -> Any:
        """客户端心跳，保持会话活跃。注意 ``operateClient`` 为必填。"""
        return self.request(
            "jifeng/user/heartbeat",
            params={
                "operateClient": 1,
                "deviceId": self.config.device_id,
                "version": APP_VERSION_NAME,
            },
        )

    def get_ban_status(self) -> Any:
        """账号封禁状态（免登录接口）。"""
        return self.request("jifeng/device/getban", method="GET")

    def video_progress(self) -> Dict[str, Any]:
        """查询「看视频领加速时长」任务的当前进度。

        字段：``watch_video_progress`` / ``new_watch_video_progress`` / ``popup_copy``
        / ``speed_end_time`` / ``now_time`` / ``watch_num``。
        """
        data = self.request("jifeng/videoads/get/progress", params={}, method="GET")
        return data if isinstance(data, dict) else {}

    def report_progress(self, watch_ad_key: str, **extra: Any) -> Dict[str, Any]:
        """上报/领取一条视频广告任务。

        返回 ``{"watch_ad_key_status": int, "watch_num": int}``。
        """
        params: Dict[str, Any] = {"watch_ad_key": watch_ad_key}
        params.update({k: v for k, v in extra.items() if v is not None})
        data = self.request("jifeng/videoads/report/progress", params=params)
        return data if isinstance(data, dict) else {}

    def video_history(self) -> Dict[str, Any]:
        """任务历史与加速时长余额（``speed_time_task`` / ``speed_end_time``）。"""
        data = self.request("jifeng/videoads/history/list", params={}, method="GET")
        return data if isinstance(data, dict) else {}

    def video_history_list(self, page: int = 1, page_size: int = 20) -> Any:
        return self.request("jifeng/videoads/history/list",
                            params={"page": page, "pageSize": page_size}, method="GET")

    def refresh_token(self) -> Any:
        return self.request("jifeng/token/refresh", params={})

    def speed_switch(self, enable: bool = True) -> Any:
        return self.request("jifeng/user/speed/switch",
                            params={"switch": 1 if enable else 0})


def extract_token(data: Dict[str, Any]) -> Tuple[str, str, str]:
    """从登录/注册响应中提取 ``(token, device_id, user_id)``。

    字段名做了兼容处理，因为不同客户端版本的命名略有差异。
    """
    if not isinstance(data, dict):
        return "", "", ""

    def pick(*names: str) -> str:
        containers = [data, data.get("userInfo"), data.get("user"), data.get("data"),
                      data.get("result")]
        for name in names:
            for container in containers:
                if isinstance(container, dict):
                    value = container.get(name)
                    if value not in (None, ""):
                        return str(value)
        return ""

    token = pick("token", "accessToken", "access_token", "Token", "deviceToken",
                 "jifengToken", "authToken")
    device_id = pick("deviceId", "device_id", "deviceid", "deviceNo", "deviceToken")
    user_id = pick("userId", "user_id", "userid", "uid", "UID", "id")
    return token, device_id, user_id
