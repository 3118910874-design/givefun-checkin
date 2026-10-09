"""AES 工具，对上官方 App 的 ``AES128Encode`` / ``AES128Decode``。

官方客户端对部分接口参数（如 ``jifeng/device/info``）使用对称加密，
服务端解密失败时会返回 ``400 illegal base64 data``。该接口的具体密钥与
IV 未能通过静态分析确认，因此本模块作为可选能力提供：

* 如果你通过抓包/自建环境拿到了 ``key`` / ``iv``，可直接调用本模块复现。
* 未配置时，脚本会跳过相关接口，不影响「查进度 + 领取」主流程。

默认算法：``AES/CBC/PKCS7Padding``，密文 Base64 编码（与原实现一致）。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Optional

BLOCK_SIZE = 16


def _pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    padding = block_size - (len(data) % block_size)
    return data + bytes([padding]) * padding


def _unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    if not data:
        return data
    padding = data[-1]
    if padding < 1 or padding > block_size or data[-padding:] != bytes([padding]) * padding:
        return data.rstrip(b"\x00")
    return data[:-padding]


def _normalize_key(key: str | bytes) -> bytes:
    raw = key.encode("utf-8") if isinstance(key, str) else key
    if len(raw) == 16:
        return raw
    if len(raw) == 24 or len(raw) == 32:
        return raw
    # 官方类名标明 128 位，非 16 字节时用 MD5 补齐
    return hashlib.md5(raw).digest()


def aes_encrypt(plaintext: str, key: str | bytes, iv: Optional[str | bytes] = None) -> str:
    """AES-CBC 加密并做 Base64（无 iv 时退化为 ECB）。"""
    from Crypto.Cipher import AES as _AES  # type: ignore # pragma: no cover

    raw_key = _normalize_key(key)
    data = _pad(plaintext.encode("utf-8"))
    if iv:
        raw_iv = iv.encode("utf-8") if isinstance(iv, str) else iv
        cipher = _AES.new(raw_key[:16], _AES.MODE_CBC, raw_iv[:16])
    else:
        cipher = _AES.new(raw_key[:16], _AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(data)).decode("ascii")


def aes_decrypt(ciphertext: str, key: str | bytes, iv: Optional[str | bytes] = None) -> str:
    from Crypto.Cipher import AES as _AES  # type: ignore # pragma: no cover

    raw_key = _normalize_key(key)
    data = base64.b64decode(ciphertext)
    if iv:
        raw_iv = iv.encode("utf-8") if isinstance(iv, str) else iv
        cipher = _AES.new(raw_key[:16], _AES.MODE_CBC, raw_iv[:16])
    else:
        cipher = _AES.new(raw_key[:16], _AES.MODE_ECB)
    return _unpad(cipher.decrypt(data)).decode("utf-8", "replace")


def sign(params: dict, secret: str) -> str:
    """按 ``k=v&k=v`` 升序拼接后取 MD5，常见于国内 App 的 ``appsign``。"""
    items = sorted((str(k), str(v)) for k, v in params.items() if v not in (None, ""))
    raw = "&".join(f"{k}={v}" for k, v in items)
    return hashlib.md5(f"{raw}{secret}".encode("utf-8")).hexdigest()


def hmac_sha256(message: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
