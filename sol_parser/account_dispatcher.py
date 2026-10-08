"""账户上下文填充（对齐 Rust ``account_dispatcher`` / ``common_filler``）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import base58

from .account_fillers import raydium_launchlab, meteora, orca, pumpfun, pumpswap, raydium
from .event_types import DexEvent
from .grpc_types import EventType
from .instr_account_utils import get_instruction_account_getter
from .instructions import (
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    PUMPFUN_PROGRAM_ID,
    PUMPSWAP_FEES_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    RAYDIUM_AMM_V4_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
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

    def run(program_b58: str, filler, anchor=None, unambiguous=False) -> None:
        pid = base58.b58decode(program_b58)
        inv = invokes.get(pid)
        if not inv:
            return
        if anchor is not None or unambiguous:
            pool, index = anchor or (None,1)
            has_anchor=pool and pool != "11111111111111111111111111111111"
            if not has_anchor and not unambiguous:return
            selected = None
            for invocation in inv:
                candidate = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, invocation)
                if candidate is None or (has_anchor and candidate(index) != pool):
                    continue
                if selected is not None and any(selected(i) != candidate(i) for i in range(18)):
                    return  # Same pool, conflicting wallet/account context: do not guess.
                selected = candidate
            if selected is not None:
                filler(selected)
            return
        ix = find_instruction_invoke(inv, meta_pb, transaction_pb)
        if ix is None:
            return
        get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, ix)
        if get is None:
            return
        filler(get)

    def fill_clmm_liquidity(remove=False):
        position_index = 2 if remove else 4
        allowed = (bytes([58,127,188,62,79,82,196,96]), bytes([160,38,208,111,104,91,44,1])) if remove else (bytes([133,29,89,223,69,238,176,10]), bytes([46,156,243,118,13,205,251,178]))
        selected = None
        for invocation in invokes.get(base58.b58decode(RAYDIUM_CLMM_PROGRAM_ID), []):
            raw = get_instruction_data(meta_pb, transaction_pb, invocation)
            if not raw or raw[:8] not in allowed:
                continue
            get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, invocation)
            if get is None or not raydium.clmm_position_matches(data.position_nft_mint, get(position_index)):
                continue
            data.personal_position = get(position_index)
            if selected is not None and any(selected(i) != get(i) for i in range(18)):
                return
            selected = get
        if selected is not None:
            (raydium.fill_clmm_decrease_liquidity_accounts if remove else raydium.fill_clmm_increase_liquidity_accounts)(data, selected)

    def fill_pump_trade():
        if not data.mint or data.mint == "11111111111111111111111111111111":
            return
        layouts = {
            bytes([102,6,61,18,1,218,235,234]): (2,6,True,16),
            bytes([56,252,116,8,158,223,205,95]): (2,6,True,16),
            bytes([51,230,133,164,1,127,131,173]): (2,6,False,14),
            bytes([184,23,238,97,103,197,211,61]): (1,13,True,27),
            bytes([194,171,28,70,104,77,91,47]): (1,13,True,27),
            bytes([93,246,130,60,231,233,64,178]): (1,13,False,26),
            bytes([7,5,29,196,245,23,101,80]): (1,8,True,17),
            bytes([225,247,80,30,213,179,132,136]): (1,8,True,17),
            bytes([28,146,222,119,38,196,105,213]): (1,8,False,17),
        }
        selected = None
        for invocation in invokes.get(base58.b58decode(PUMPFUN_PROGRAM_ID), []):
            raw = get_instruction_data(meta_pb, transaction_pb, invocation)
            layout = layouts.get(raw[:8]) if raw else None
            if layout is None:
                continue
            mint_index, user_index, buy, minimum = layout
            oi, ii = invocation
            instruction = (transaction_pb.message.instructions[oi] if ii < 0 else
                           next(g for g in meta_pb.inner_instructions if g.index == oi).instructions[ii])
            if buy != data.is_buy or len(instruction.accounts) < minimum:
                continue
            get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, invocation)
            if get is None or get(mint_index) != data.mint:
                continue
            if data.user and data.user != "11111111111111111111111111111111" and get(user_index) != data.user:
                continue
            if selected is not None:
                return
            selected = get
        if selected is not None:
            pumpfun.fill_trade_accounts(data, selected)

    def fill_swap(buy):
        # Match the event's own pool, user and direction, not the largest invoke.
        if not data.pool or data.pool == "11111111111111111111111111111111":
            return
        selected = None
        legacy = (bytes([102, 6, 61, 18, 1, 218, 235, 234]),
                  bytes([198, 46, 21, 82, 180, 217, 232, 112])) if buy else (bytes([51, 230, 133, 164, 1, 127, 131, 173]),)
        compact = (bytes([184, 23, 238, 97, 103, 197, 211, 61]),
                   bytes([194, 171, 28, 70, 104, 77, 91, 47])) if buy else (bytes([93, 246, 130, 60, 231, 233, 64, 178]),)
        for invocation in invokes.get(base58.b58decode(PUMPSWAP_PROGRAM_ID), []):
            raw = get_instruction_data(meta_pb, transaction_pb, invocation)
            boost = buy and raw is not None and raw[:8] == bytes([105, 68, 6, 175, 0, 7, 35, 162])
            if raw is None or (not boost and raw[:8] not in legacy + compact):
                continue
            oi, ii = invocation
            instruction = (transaction_pb.message.instructions[oi] if ii < 0 else
                           next(g for g in meta_pb.inner_instructions if g.index == oi).instructions[ii])
            minimum = 13 if boost else (17 if raw[:8] in compact else (23 if buy else 21))
            if len(instruction.accounts) < minimum:
                continue
            get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, invocation)
            if get is None or get(0) != data.pool:
                continue
            if data.user and data.user != "11111111111111111111111111111111" and get(7 if boost else 1) != data.user:
                continue
            if selected is not None:
                return  # Invocation positions are unavailable; ambiguous context stays blank.
            selected = (get, boost)
        if selected is not None:
            get, boost = selected
            filler = pumpswap.fill_boost_buy_accounts if boost else (pumpswap.fill_buy_accounts if buy else pumpswap.fill_sell_accounts)
            filler(data, get)

    def fill_create(v2_only=False):
        selected = None
        for ix in invokes.get(base58.b58decode(PUMPFUN_PROGRAM_ID), []):
            raw = get_instruction_data(meta_pb, transaction_pb, ix)
            if raw is None:
                continue
            v2 = raw[:8] == bytes([214,144,76,236,95,139,49,180])
            legacy = raw[:8] == bytes([24,30,200,40,5,28,7,119])
            if not v2 and (v2_only or not legacy):
                continue
            get = get_instruction_account_getter(meta_pb, transaction_pb, static_keys, w, r, ix)
            oi, ii = ix
            instruction = (transaction_pb.message.instructions[oi] if ii < 0 else
                           next(g for g in meta_pb.inner_instructions if g.index == oi).instructions[ii])
            if len(instruction.accounts) < (16 if v2 else 14) or get is None:
                continue
            if data.mint and data.mint != "11111111111111111111111111111111" and get(0) != data.mint:
                continue
            if selected is not None:
                return  # Multiple matching creates: do not guess.
            selected = (get, v2)
        if selected:
            get, v2 = selected
            (pumpfun.fill_create_v2_accounts if v2 else pumpfun.fill_create_accounts)(data, get)

    et = event.type
    data = event.data

    if et in (
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
    ):
        fill_pump_trade()
    elif et == EventType.PUMP_FUN_CREATE:
        fill_create()
    elif et == EventType.PUMP_FUN_CREATE_V2:
        fill_create(True)
    elif et == EventType.PUMP_FUN_MIGRATE:
        run(PUMPFUN_PROGRAM_ID, lambda g: pumpfun.fill_migrate_accounts(data, g))
    elif et == EventType.PUMP_SWAP_BUY:
        fill_swap(True)
    elif et == EventType.PUMP_SWAP_SELL:
        fill_swap(False)
    elif et == EventType.PUMP_SWAP_TRADE:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_trade_accounts(data, g))
    elif et == EventType.PUMP_SWAP_CREATE_POOL:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_create_pool_accounts(data, g))
    elif et == EventType.PUMP_SWAP_LIQUIDITY_ADDED:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_liquidity_added_accounts(data, g))
    elif et == EventType.PUMP_SWAP_LIQUIDITY_REMOVED:
        run(PUMPSWAP_PROGRAM_ID, lambda g: pumpswap.fill_liquidity_removed_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_SWAP:
        run(RAYDIUM_CLMM_PROGRAM_ID, lambda g: raydium.fill_clmm_swap_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_CREATE_POOL:
        run(RAYDIUM_CLMM_PROGRAM_ID, lambda g: raydium.fill_clmm_create_pool_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_OPEN_POSITION:
        run(RAYDIUM_CLMM_PROGRAM_ID, lambda g: raydium.fill_clmm_open_position_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT:
        run(RAYDIUM_CLMM_PROGRAM_ID, lambda g: raydium.fill_clmm_open_position_with_token_ext_nft_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_CLOSE_POSITION:
        run(RAYDIUM_CLMM_PROGRAM_ID, lambda g: raydium.fill_clmm_close_position_accounts(data, g))
    elif et == EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY:
        fill_clmm_liquidity()
    elif et == EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY:
        fill_clmm_liquidity(True)
    elif et == EventType.RAYDIUM_CPMM_SWAP:
        run(RAYDIUM_CPMM_PROGRAM_ID, lambda g: raydium.fill_cpmm_swap_accounts(data, g))
    elif et == EventType.RAYDIUM_CPMM_DEPOSIT:
        run(RAYDIUM_CPMM_PROGRAM_ID, lambda g: raydium.fill_cpmm_deposit_accounts(data, g))
    elif et == EventType.RAYDIUM_CPMM_WITHDRAW:
        run(RAYDIUM_CPMM_PROGRAM_ID, lambda g: raydium.fill_cpmm_withdraw_accounts(data, g))
    elif et == EventType.RAYDIUM_CPMM_INITIALIZE:
        run(RAYDIUM_CPMM_PROGRAM_ID, lambda g: raydium.fill_cpmm_initialize_accounts(data, g))
    elif et == EventType.RAYDIUM_AMM_V4_SWAP:
        run(RAYDIUM_AMM_V4_PROGRAM_ID, lambda g: raydium.fill_amm_v4_swap_accounts(data, g), (data.amm,1), True)
    elif et == EventType.RAYDIUM_AMM_V4_DEPOSIT:
        run(RAYDIUM_AMM_V4_PROGRAM_ID, lambda g: raydium.fill_amm_v4_deposit_accounts(data, g))
    elif et == EventType.RAYDIUM_AMM_V4_WITHDRAW:
        run(RAYDIUM_AMM_V4_PROGRAM_ID, lambda g: raydium.fill_amm_v4_withdraw_accounts(data, g))
    elif et == EventType.ORCA_WHIRLPOOL_SWAP:
        run(ORCA_WHIRLPOOL_PROGRAM_ID, lambda g: orca.fill_whirlpool_swap_accounts(data, g))
    elif et == EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED:
        run(ORCA_WHIRLPOOL_PROGRAM_ID, lambda g: orca.fill_whirlpool_liquidity_increased_accounts(data, g))
    elif et == EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED:
        run(ORCA_WHIRLPOOL_PROGRAM_ID, lambda g: orca.fill_whirlpool_liquidity_decreased_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_SWAP:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_swap_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_CREATE_POSITION:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_create_position_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_CLOSE_POSITION:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_close_position_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_ADD_LIQUIDITY:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_add_liquidity_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_remove_liquidity_accounts(data, g))
    elif et == EventType.METEORA_DAMM_V2_INITIALIZE_POOL:
        run(METEORA_DAMM_V2_PROGRAM_ID, lambda g: meteora.fill_damm_v2_initialize_pool_accounts(data, g))
    elif et == EventType.METEORA_POOLS_SWAP:
        run(METEORA_POOLS_PROGRAM_ID, lambda g: meteora.fill_pools_swap_accounts(data, g))
    elif et == EventType.METEORA_POOLS_ADD_LIQUIDITY:
        run(METEORA_POOLS_PROGRAM_ID, lambda g: meteora.fill_pools_add_liquidity_accounts(data, g))
    elif et == EventType.METEORA_POOLS_REMOVE_LIQUIDITY:
        run(METEORA_POOLS_PROGRAM_ID, lambda g: meteora.fill_pools_remove_liquidity_accounts(data, g))
    elif et == EventType.METEORA_DLMM_SWAP:
        run(METEORA_DLMM_PROGRAM_ID, lambda g: meteora.fill_dlmm_swap_accounts(data, g))
    elif et == EventType.METEORA_DLMM_ADD_LIQUIDITY:
        run(METEORA_DLMM_PROGRAM_ID, lambda g: meteora.fill_dlmm_add_liquidity_accounts(data, g))
    elif et == EventType.METEORA_DLMM_REMOVE_LIQUIDITY:
        run(METEORA_DLMM_PROGRAM_ID, lambda g: meteora.fill_dlmm_remove_liquidity_accounts(data, g))
    elif et == EventType.RAYDIUM_LAUNCHLAB_TRADE:
        run(RAYDIUM_LAUNCHLAB_PROGRAM_ID, lambda g: raydium_launchlab.fill_trade_accounts(data, g), (data.pool_state,4))
    elif et == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE:
        run(RAYDIUM_LAUNCHLAB_PROGRAM_ID, lambda g: raydium_launchlab.fill_pool_create_accounts(data, g), (data.pool_state,5))


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


def _account_index(transaction_pb: Any, meta_pb: Any, account: str) -> Optional[int]:
    if not account or account == "11111111111111111111111111111111":
        return None
    msg = getattr(transaction_pb, "message", None)
    if msg is None:
        return None
    keys: List[str] = []
    for b in getattr(msg, "account_keys", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        if len(raw) == 32:
            keys.append(base58.b58encode(raw).decode("ascii"))
    for b in getattr(meta_pb, "loaded_writable_addresses", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        if len(raw) == 32:
            keys.append(base58.b58encode(raw).decode("ascii"))
    for b in getattr(meta_pb, "loaded_readonly_addresses", []) or []:
        raw = bytes(b) if not isinstance(b, (bytes, bytearray)) else bytes(b)
        if len(raw) == 32:
            keys.append(base58.b58encode(raw).decode("ascii"))
    try:
        return keys.index(account)
    except ValueError:
        return None


def _token_balance_raw(t: Any) -> int:
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


def fill_token_balances(event: DexEvent, meta_pb: Any, transaction_pb: Any) -> None:
    """对齐 Rust ``common_filler::fill_token_balances``（PumpFun trade 用户余额）。"""
    if meta_pb is None or transaction_pb is None:
        return
    if event.type not in (
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
    ):
        return
    trade = event.data
    user = getattr(trade, "user", "") or ""
    associated_user = getattr(trade, "associated_user", "") or ""
    user_idx = _account_index(transaction_pb, meta_pb, user)
    if user_idx is not None:
        pre_balances = list(getattr(meta_pb, "pre_balances", []) or [])
        post_balances = list(getattr(meta_pb, "post_balances", []) or [])
        if user_idx < len(pre_balances):
            trade.pre_sol_balance = int(pre_balances[user_idx])
        if user_idx < len(post_balances):
            trade.post_sol_balance = int(post_balances[user_idx])
    token_idx = _account_index(transaction_pb, meta_pb, associated_user)
    if token_idx is None:
        return
    token_idx_u32 = token_idx
    pre = None
    post = None
    for bal in getattr(meta_pb, "pre_token_balances", []) or []:
        if int(getattr(bal, "account_index", -1)) == token_idx_u32:
            pre = _token_balance_raw(bal)
            break
    for bal in getattr(meta_pb, "post_token_balances", []) or []:
        if int(getattr(bal, "account_index", -1)) == token_idx_u32:
            post = _token_balance_raw(bal)
            break
    if pre is not None or post is not None:
        trade.pre_token_balance = pre if pre is not None else 0
        trade.post_token_balance = post if post is not None else 0
