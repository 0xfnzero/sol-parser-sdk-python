"""将 Rust ``serde_json`` 输出的 DexEvent 列表规范化为 Python ``legacy_dict_to_dex_event`` 可消费的 dict。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import base58

from .event_types import DexEvent, legacy_dict_to_dex_event


def normalize_rust_json_value(v: Any) -> Any:
    """递归：Solana pubkey/signature 的 byte 数组 → base58 字符串。"""
    if isinstance(v, list) and v and all(isinstance(x, int) for x in v):
        if len(v) in (32, 64):
            try:
                return base58.b58encode(bytes(v)).decode("ascii")
            except Exception:
                return v
    if isinstance(v, dict):
        return {k: normalize_rust_json_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [normalize_rust_json_value(x) for x in v]
    return v


def dex_events_from_rust_json_str(s: str) -> List[DexEvent]:
    """解析 native 扩展返回的 JSON 数组为 ``List[DexEvent]``。"""
    raw = json.loads(s)
    if not isinstance(raw, list):
        return []
    out: List[DexEvent] = []
    for item in raw:
        if not isinstance(item, dict) or len(item) != 1:
            continue
        norm = normalize_rust_json_value(item)
        ev = legacy_dict_to_dex_event(norm)
        if ev is not None:
            out.append(ev)
    return out


def dex_event_from_log_rust_json_str(s: str) -> Optional[DexEvent]:
    """单条日志事件 JSON → ``DexEvent``。"""
    d = json.loads(s)
    if not isinstance(d, dict):
        return None
    norm = normalize_rust_json_value(d)
    return legacy_dict_to_dex_event(norm)
