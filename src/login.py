"""登录助手：短信验证码登录并把凭据写入 GitHub Secrets / 本地状态文件。

用法（本地）::

    python login_helper.py --phone 13800000000 --send-only
    python login_helper.py --phone 13800000000 --code 123456 --write-state

在 GitHub Actions 中使用时，配合环境变量 ``GIVEFUN_PHONE`` ``GIVEFUN_CODE``
``GH_PAT`` ``GIVEFUN_SYNC_SECRETS=1``，脚本会把拿到的令牌自动写回仓库 Secret。

注意：真实参数名为 ``veriStr``（就是短信验证码本身），已由线上实测确认。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .client import GiveFunClient, GiveFunError, extract_token
from .config import Config, mask, mask_phone

STATE_FILE = Path(__file__).resolve().parent.parent / "state.json"

SECRET_PAYLOAD_KEYS = ("GIVEFUN_TOKEN", "GIVEFUN_DEVICE_ID", "GIVEFUN_USER_ID")


def load_state() -> Dict[str, str]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: Dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[状态] 已写入 {STATE_FILE.name}（已在 .gitignore 中，请勿提交）")


def _client(phone: str = "") -> GiveFunClient:
    config = Config.from_env()
    if phone:
        config.phone = phone
    return GiveFunClient(config)


def phone_status(phone: str) -> Dict[str, Any]:
    return _client(phone).phone_status(phone)


def send_code(phone: str, code_type: int = 1) -> Any:
    return _client(phone).send_sms_code(phone, code_type=code_type)


def login(phone: str, code: str) -> Dict[str, Any]:
    data = _client(phone).login(phone, code)
    token, device_id, user_id = extract_token(data)
    return {"raw": data, "token": token, "device_id": device_id, "user_id": user_id}


def register(phone: str, code: str) -> Dict[str, Any]:
    data = _client(phone).register(phone, code)
    token, device_id, user_id = extract_token(data)
    return {"raw": data, "token": token, "device_id": device_id, "user_id": user_id}


def push_secrets_to_github(payload: Dict[str, str]) -> bool:
    """使用 PyNaCl + GitHub API 把凭据写回仓库 Secrets（需要 GH_PAT）。"""
    pat = os.environ.get("GH_PAT", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not (pat and repo):
        print("[GitHub] 未配置 GH_PAT / GITHUB_REPOSITORY，跳过自动回写 Secret")
        return False
    try:
        import base64

        import requests  # type: ignore
        from nacl import encoding, public  # type: ignore
    except ImportError as exc:
        print(f"[GitHub] 缺少依赖 {exc}，请先 pip install requests pynacl")
        return False

    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    key_resp = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers, timeout=20,
    )
    if key_resp.status_code != 200:
        print(f"[GitHub] 获取公钥失败：{key_resp.status_code} {key_resp.text[:200]}")
        return False

    key_data = key_resp.json()
    public_key = public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder())

    ok = True
    for name, value in payload.items():
        if not value:
            continue
        sealed = base64.b64encode(
            public.SealedBox(public_key).encrypt(value.encode("utf-8"))
        ).decode("utf-8")
        resp = requests.put(
            f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
            headers=headers, timeout=20,
            json={"encrypted_value": sealed, "key_id": key_data["key_id"]},
        )
        status = "✅" if resp.status_code in (201, 204) else "❌"
        print(f"[GitHub] {status} {name} -> {resp.status_code}")
        ok = ok and resp.status_code in (201, 204)
    return ok


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="疾风加速器登录助手")
    parser.add_argument("--phone", default=os.environ.get("GIVEFUN_PHONE", ""),
                        help="手机号，默认取 GIVEFUN_PHONE")
    parser.add_argument("--code", default=os.environ.get("GIVEFUN_CODE", ""),
                        help="短信验证码；不传则只发送验证码")
    parser.add_argument("--send-only", action="store_true", help="只发送验证码")
    parser.add_argument("--register", action="store_true",
                        help="走注册流程（仅在从未注册过时才需要；默认永远是登录）")
    parser.add_argument("--status", action="store_true", help="只查询手机号注册状态")
    parser.add_argument("--write-state", action="store_true",
                        help="把凭据写入本地 state.json")
    parser.add_argument("--sync-secrets", action="store_true",
                        help="把凭据回写到 GitHub 仓库 Secrets（需 GH_PAT）")
    args = parser.parse_args(list(argv) if argv is not None else None)

    phone = args.phone.strip()
    if not phone:
        print("错误：请提供 --phone 或设置 GIVEFUN_PHONE")
        return 2

    # 0) 注册状态：仅作信息展示，不改变默认行为（默认永远走登录）
    try:
        status = phone_status(phone)
        is_register = int(status.get("isRegister") or 0)
        print(f"[0/3] {mask_phone(phone)} 注册状态："
              f"{'已注册' if is_register else '未注册'}"
              f"（isSetPwd={status.get('isSetPwd')}）")
    except GiveFunError as exc:
        print(f"[0/3] 注册状态查询失败：{exc}")
        is_register = 1

    if args.status:
        return 0

    # 只有显式指定 --register 才走注册；其余一律登录
    action = "注册" if args.register else "登录"
    code_type = 2 if args.register else 1
    if not is_register and not args.register:
        print("      注意：服务端标记该手机号未注册。若你确实在用这个号登录，"
              "请忽略此提示；若从未注册过，需先加 --register 完成注册。")

    # 1) 发送验证码
    if args.send_only or not args.code:
        print(f"[1/3] 正在向 {mask_phone(phone)} 发送{action}验证码（type={code_type}）…")
        try:
            result = send_code(phone, code_type=code_type)
        except GiveFunError as exc:
            print(f"[1/3] 发送失败：{exc}")
            print("      若是频率限制，请等待 60 秒后重试；若提示需要图形验证码，"
                  "请改用官方 App 获取验证码后手动填入 --code。")
            return 1
        print(f"[1/3] 接口返回：{json.dumps(result, ensure_ascii=False)[:300]}")
        if not args.code:
            print("      请把收到的验证码通过 --code 传入（或设置 GIVEFUN_CODE）后再次运行。")
            return 0

    # 2) 登录 / 注册
    code = args.code.strip()
    print(f"[2/3] 使用验证码{action} {mask_phone(phone)} …")
    try:
        result = register(phone, code) if args.register else login(phone, code)
    except GiveFunError as exc:
        print(f"[2/3] {action}失败：{exc}")
        if "veriStr" in str(exc):
            print("      验证码不正确或已过期，请重新发送并尽快使用。")
        return 1

    token = result["token"]
    if not token:
        print("[2/3] 响应中未找到令牌字段，原始返回如下（请据此调整 extract_token）：")
        print(json.dumps(result["raw"], ensure_ascii=False, indent=2)[:2000])
        return 1

    print("[2/3] 成功")
    print(f"      token      = {mask(token)}")
    print(f"      device_id  = {mask(result['device_id']) if result['device_id'] else '(未返回)'}")
    print(f"      user_id    = {mask(result['user_id']) if result['user_id'] else '(未返回)'}")

    payload = {
        "GIVEFUN_TOKEN": token,
        "GIVEFUN_DEVICE_ID": result["device_id"],
        "GIVEFUN_USER_ID": result["user_id"],
    }

    # 3) 持久化
    if args.write_state:
        state = load_state()
        state.update({k: v for k, v in payload.items() if v})
        state["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        save_state(state)

    if args.sync_secrets or os.environ.get("GIVEFUN_SYNC_SECRETS") == "1":
        push_secrets_to_github(payload)

    print("\n[3/3] 请把下面的值填入仓库 Settings → Secrets and variables → Actions：")
    for key in SECRET_PAYLOAD_KEYS:
        if payload.get(key):
            print(f"  {key} = {payload[key]}")
    if not payload.get("GIVEFUN_DEVICE_ID"):
        print("  提示：服务端未返回 device_id，仅配置 GIVEFUN_TOKEN 即可。")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
