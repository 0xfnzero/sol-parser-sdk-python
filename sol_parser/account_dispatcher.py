"""账户上下文填充（对齐 Rust ``account_dispatcher`` / ``common_filler``）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import base58

from .account_fillers import pumpfun, pumpswap
from .event_types import DexEvent
from .grpc_types import EventType
from .instr_account_utils import get_instruction_account_getter
from .instructions import (
    PUMPFUN_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    PUMPSWAP_FEES_PROGRAM_ID,
)


def find_instruction_invoke(
    invokes: List[Tuple[int, int]],
    meta_pb: Any,
    transaction_pb: Any,
) -> Optional[Tuple[int, int]]:
    """账户数最多的 invoke（与 Rust ``find_instruction_invoke`` 一致）。"""
    best: Optional[Tuple[int, int]] = None
    best_len = -1
    for outer_idx, inner_idx in invokes:
        n = 0
        if inner_idx >= 0:
            for inn in meta_pb.inner_instructions:
                if int(inn.index) == int(outer_idx):
                    if inner_idx < len(inn.instructions):
                        n = len(inn.instructions[inner_idx].accounts)
                    break
        else:
            msg = transaction_pb.message
            if outer_idx < len(msg.instructions):
                n = len(msg.instructions[outer_idx].accounts)
        if n > best_len:
            best_len = n
            best = (outer_idx, inner_idx)
    return best


def get_instruction_data(
    meta_pb: Any,
    transaction_pb: Any,
    index: Tuple[int, int],
) -> Optional[bytes]:
    oi, ii = index
    if ii >= 0:
        for inn in meta_pb.inner_instructions:
            if int(inn.index) == int(oi):
                if ii < len(inn.instructions):
                    return bytes(inn.instructions[ii].data)
                return None
        return None
    msg = transaction_pb.message
    if oi < len(msg.instructions):
        return bytes(msg.instructions[oi].data)
    return None


def fill_accounts_with_owned_keys(
    event: DexEvent,
    meta_pb: Any,
    transaction_pb: Any,
    invokes: Dict[bytes, List[Tuple[int, int]]],
) -> None:
    if transaction_pb is None:
        return
    static_keys = [bytes(x) for x in transaction_pb.message.account_keys]
    w = [bytes(x) for x in meta_pb.loaded_writable_addresses]
    r = [bytes(x) for x in meta_pb.loaded_readonly_addresses]

    def run(program_b58: str, filler) -> None:
        pid = base58.b58decode(program_b58)
        inv = invokes.get(pid)
        if not inv:
            return
        ix = find_instruction_invoke(inv, meta_pb, transaction_pb)
        if ix is None:
            return
        get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, ix)
        if get is None:
            return
        filler(get)

    et = event.type
    data = event.data

    if et in (
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
    ):
        run(PUMPFUN_PROGRAM_ID, lambda g: pumpfun.fill_trade_accounts(data, g))
    elif et == EventType.PUMP_FUN_CREATE:
        run(PUMPFUN_PROGRAM_ID, lambda g: pumpfun.fill_create_accounts(data, g))
    elif et == EventType.PUMP_FUN_CREATE_V2:
        run(PUMPFUN_PROGRAM_ID, lambda g: pumpfun.fill_create_v2_accounts(data, g))
    elif et == EventType.PUMP_SWAP_BUY:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_buy_accounts(data, g))
    elif et == EventType.PUMP_SWAP_SELL:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_sell_accounts(data, g))
    elif et == EventType.PUMP_SWAP_CREATE_POOL:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_create_pool_accounts(data, g))
    elif et == EventType.PUMP_SWAP_LIQUIDITY_ADDED:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_liquidity_added_accounts(data, g))
    elif et == EventType.PUMP_SWAP_LIQUIDITY_REMOVED:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_liquidity_removed_accounts(data, g))


def fill_data(
    event: DexEvent,
    meta_pb: Any,
    transaction_pb: Any,
    invokes_str: Dict[str, List[Tuple[int, int]]],
) -> None:
    """对齐 Rust ``common_filler::fill_data``（PumpSwap Buy/Sell ``is_pump_pool``）。"""
    if transaction_pb is None:
        return
    et = event.type
    data = event.data
    if et not in (EventType.PUMP_SWAP_BUY, EventType.PUMP_SWAP_SELL):
        return
    inv = invokes_str.get(PUMPSWAP_FEES_PROGRAM_ID)
    if not inv:
        return
    ix = inv[-1]
    raw = get_instruction_data(meta_pb, transaction_pb, ix)
    if raw is None or len(raw) <= 9:
        return
    is_pump = raw[9] != 0
    setattr(data, "is_pump_pool", is_pump)
