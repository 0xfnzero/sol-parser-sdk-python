"""对齐 Rust ``accounts/rpc_wallet.rs``：RPC getAccountInfo + ``user_wallet_pubkey_for_onchain_account``。"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, Optional

from .utils import user_wallet_pubkey_for_onchain_account


def _get_account_info(rpc_url: str, address_bs58: str, timeout_s: float = 15.0) -> Optional[Dict[str, Any]]:
    import base64

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [address_bs58, {"encoding": "base64"}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    err = raw.get("error")
    if err:
        return None
    val = (raw.get("result") or {}).get("value")
    if not val:
        return None
    data_b64 = val.get("data")
    if isinstance(data_b64, list) and data_b64:
        data_b64 = data_b64[0]
    if not isinstance(data_b64, str):
        return None
    try:
        data = base64.b64decode(data_b64)
    except Exception:
        return None
    owner = val.get("owner") or ""
    exe = bool(val.get("executable", False))
    return {"data": data, "owner": owner, "executable": exe}


def rpc_resolve_user_wallet_pubkey(rpc_url: str, address_bs58: str) -> Optional[str]:
    """同步 JSON-RPC：``getAccountInfo`` → 用户钱包公钥 base58（与 Rust 语义一致）。"""
    info = _get_account_info(rpc_url, address_bs58)
    if not info:
        return None
    return user_wallet_pubkey_for_onchain_account(
        address_bs58,
        info["owner"],
        info["data"],
        info["executable"],
    )
