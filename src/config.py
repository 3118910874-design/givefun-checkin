"""疾风加速器（givefun.cn）自动领取加速时长 —— 配置模块。

所有配置均通过环境变量注入，方便在 GitHub Actions 中以 Secrets 的方式管理。
本模块只依赖标准库。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量：接口地址（逆向自官方安卓客户端 com.gameaccel.rapid）
# ---------------------------------------------------------------------------

API_BASE = "https://api.geifun.com.cn/"

# 客户端标识，尽量与官方 App 保持一致
APP_VERSION_NAME = "1.2.2.0030"
APP_VERSION_CODE = "1220030"
PACKAGE_NAME = "com.gameaccel.rapid"
MAIN_CHANNEL = "jifeng"
SUB_CHANNEL = "official"
PLATFORM = "android"

DEFAULT_TIMEOUT = 20

# 通知渠道所需的环境变量名（全部可选，可同时配置多个）
NOTIFY_ENV_KEYS = [
    "PUSHPLUS_TOKEN",
    "PUSHPLUS_TOPIC",
    "SERVERCHAN_SENDKEY",
    "WECOM_BOT_KEY",
    "DINGTALK_BOT_KEY",
    "DINGTALK_SECRET",
    "FEISHU_BOT_KEY",
    "BARK_KEY",
    "BARK_GROUP",
    "TG_BOT_TOKEN",
    "TG_CHAT_ID",
]


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return default if value is None else value.strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int = 0) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Config:
    """运行期配置。"""

    # --- 账号 / 鉴权 ---
    phone: str = ""          # 登录手机号（仅登录时使用）
    token: str = ""          # 服务端下发的登录令牌，等价于账号密码
    device_id: str = ""      # 设备号，部分接口要求与登录设备一致
    user_id: str = ""        # 用户 ID（可选）

    # 额外请求头，格式 "K1:V1;K2:V2"，用于站点协议微调时的应急逃生口
    extra_headers: Dict[str, str] = field(default_factory=dict)

    # --- 行为开关 ---
    # 是否在领取前先调用心跳/设备接口（更接近真实客户端行为）
    warmup: bool = True
    # 单次运行最多尝试领取的广告任务数（0 表示不限）
    max_claim: int = 0
    # 网络重试次数
    retries: int = 2

    # --- 输出 ---
    debug: bool = False
    timeout: int = DEFAULT_TIMEOUT

    @classmethod
    def from_env(cls) -> "Config":
        extra: Dict[str, str] = {}
        raw_extra = _env("GIVEFUN_EXTRA_HEADERS")
        for part in raw_extra.replace("\n", ";").split(";"):
            part = part.strip()
            if not part or ":" not in part:
                continue
            key, _, value = part.partition(":")
            extra[key.strip()] = value.strip()

        return cls(
            phone=_env("GIVEFUN_PHONE"),
            token=_env("GIVEFUN_TOKEN"),
            device_id=_env("GIVEFUN_DEVICE_ID"),
            user_id=_env("GIVEFUN_USER_ID"),
            extra_headers=extra,
            warmup=_env_bool("GIVEFUN_WARMUP", True),
            max_claim=_env_int("GIVEFUN_MAX_CLAIM", 0),
            retries=_env_int("GIVEFUN_RETRIES", 2),
            debug=_env_bool("GIVEFUN_DEBUG", False),
            timeout=_env_int("GIVEFUN_TIMEOUT", DEFAULT_TIMEOUT),
        )

    @property
    def has_credentials(self) -> bool:
        """是否具备执行日常任务所需的最小凭据。"""
        return bool(self.token or (self.phone and self.device_id))

    @property
    def notify_env(self) -> Dict[str, str]:
        return {key: _env(key) for key in NOTIFY_ENV_KEYS}


def mask(value: str, keep: int = 4) -> str:
    """日志脱敏：只保留首尾少量字符。"""
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return value[0] + "*" * (len(value) - 1)
    return f"{value[:keep]}{'*' * 6}{value[-keep:]}"


def mask_phone(phone: str) -> str:
    if len(phone) == 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return mask(phone)
