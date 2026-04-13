"""对齐 Rust ``grpc/transaction_meta.rs``（不依赖 DEX 解析）：账户 key、lamport delta、转账启发式。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import base58


def pubkey_bytes_to_bs58(bs: bytes) -> Optional[str]:
    if len(bs) != 32:
        return None
    return base58.b58encode(bs).decode("ascii")


def collect_account_keys_bs58(tx: Any, meta: Any) -> Optional[List[str]]:
    """对齐 ``collect_account_keys_bs58``：静态 keys + loaded writable/readonly。"""
    msg = getattr(tx, "message", None) or getattr(tx, "Message", None)
    if msg is None:
        return None
    keys: List[str] = []
    for b in getattr(msg, "account_keys", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        k = pubkey_bytes_to_bs58(raw)
        if k:
            keys.append(k)
    for b in getattr(meta, "loaded_writable_addresses", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        k = pubkey_bytes_to_bs58(raw)
        if k:
            keys.append(k)
    for b in getattr(meta, "loaded_readonly_addresses", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        k = pubkey_bytes_to_bs58(raw)
        if k:
            keys.append(k)
    return keys


def lamport_balance_deltas(meta: Any) -> List[int]:
    pre = list(getattr(meta, "pre_balances", []) or [])
    post = list(getattr(meta, "post_balances", []) or [])
    return [int(post[i]) - int(pre[i]) for i in range(min(len(pre), len(post)))]


def heuristic_sol_counterparties_for_watched_keys(
    account_keys_bs58: List[str],
    lamport_deltas: List[int],
    watched_bs58: Set[str],
    min_outflow_lamports: int,
) -> List[Tuple[str, str]]:
    min_l = int(min_outflow_lamports)
    pairs: List[Tuple[str, str]] = []
    for i, key in enumerate(account_keys_bs58):
        if key not in watched_bs58:
            continue
        d = lamport_deltas[i] if i < len(lamport_deltas) else 0
        if d >= -min_l:
            continue
        for j, dj in enumerate(lamport_deltas):
            if i == j or dj <= min_l // 2:
                continue
            pairs.append((key, account_keys_bs58[j]))
    return pairs


def token_balance_raw_amount(t: Any) -> int:
    ui = getattr(t, "ui_token_amount", None)
    if ui is None:
        return 0
    amt = getattr(ui, "amount", None)
    if amt is None:
        return 0
    try:
        return int(str(amt))
    except Exception:
        return 0


def spl_token_counterparty_by_owner(
    meta: Any,
    watch_owner_bs58: str,
    min_watch_decrease_raw: int,
) -> List[Tuple[str, str]]:
    """对齐 ``spl_token_counterparty_by_owner``。"""
    pre = list(getattr(meta, "pre_token_balances", []) or [])
    post = list(getattr(meta, "post_token_balances", []) or [])
    pre_m: Dict[Tuple[str, str], int] = {}
    for b in pre:
        owner = getattr(b, "owner", "") or ""
        if not owner:
            continue
        mint = getattr(b, "mint", "") or ""
        k = (mint, owner)
        pre_m[k] = pre_m.get(k, 0) + token_balance_raw_amount(b)
    post_m: Dict[Tuple[str, str], int] = {}
    for b in post:
        owner = getattr(b, "owner", "") or ""
        if not owner:
            continue
        mint = getattr(b, "mint", "") or ""
        k = (mint, owner)
        post_m[k] = post_m.get(k, 0) + token_balance_raw_amount(b)

    mints: Set[str] = set()
    for (m, o) in list(pre_m.keys()) + list(post_m.keys()):
        if o == watch_owner_bs58:
            mints.add(m)

    out: List[Tuple[str, str]] = []
    min_l = max(int(min_watch_decrease_raw), 1)
    for mint in mints:
        w_pre = pre_m.get((mint, watch_owner_bs58), 0)
        w_post = post_m.get((mint, watch_owner_bs58), 0)
        lost = w_pre - w_post if w_pre >= w_post else 0
        if lost < min_l:
            continue
        for (m, owner), po in post_m.items():
            if m != mint or owner == watch_owner_bs58:
                continue
            pr = pre_m.get((mint, owner), 0)
            if po > pr:
                out.append((watch_owner_bs58, owner))
    out.sort(key=lambda x: x[1])
    seen = set()
    dedup: List[Tuple[str, str]] = []
    for a in out:
        k = (a[0], a[1])
        if k not in seen:
            seen.add(k)
            dedup.append(a)
    return dedup


def collect_watch_transfer_counterparty_pairs(
    tx: Any,
    meta: Any,
    watched_bs58: List[str],
    min_native_outflow_lamports: int,
    spl_min_watch_decrease_raw: int,
) -> Optional[List[Tuple[str, str]]]:
    keys = collect_account_keys_bs58(tx, meta)
    if keys is None:
        return None
    n = len(keys)
    pre = list(getattr(meta, "pre_balances", []) or [])
    post = list(getattr(meta, "post_balances", []) or [])
    if len(pre) != n or len(post) != n:
        return None
    deltas = lamport_balance_deltas(meta)
    watched_h = set(watched_bs58)
    pairs = heuristic_sol_counterparties_for_watched_keys(
        keys, deltas, watched_h, min_native_outflow_lamports
    )
    for w in watched_bs58:
        pairs.extend(spl_token_counterparty_by_owner(meta, w, spl_min_watch_decrease_raw))
    pairs.sort(key=lambda x: x[1])
    seen = set()
    out: List[Tuple[str, str]] = []
    for a in pairs:
        k = (a[0], a[1])
        if k not in seen:
            seen.add(k)
            out.append(a)
    return out


def try_yellowstone_signature(sig: bytes) -> Optional[bytes]:
    if len(sig) != 64:
        return None
    return bytes(sig)


__all__ = [
    "pubkey_bytes_to_bs58",
    "collect_account_keys_bs58",
    "lamport_balance_deltas",
    "heuristic_sol_counterparties_for_watched_keys",
    "token_balance_raw_amount",
    "spl_token_counterparty_by_owner",
    "collect_watch_transfer_counterparty_pairs",
    "try_yellowstone_signature",
]
