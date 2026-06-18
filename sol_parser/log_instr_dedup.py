"""Rust-style log/instruction dedupe for Yellowstone transaction parsing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .event_types import DexEvent
from .grpc_types import EventType

ZERO = "11111111111111111111111111111111"

PUMPFUN_TRADE_TYPES = {
    EventType.PUMP_FUN_TRADE,
    EventType.PUMP_FUN_BUY,
    EventType.PUMP_FUN_SELL,
    EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
}


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == ZERO


def _fill_attr(log: Any, attr: str, ix: Any, ix_attr: Optional[str] = None) -> None:
    src_attr = ix_attr or attr
    value = getattr(ix, src_attr, None)
    if _empty(getattr(log, attr, None)) and not _empty(value):
        setattr(log, attr, value)


def _fill_raydium_launchlab_mint_param(log: Any, ix: Any, key: str) -> None:
    src = getattr(ix, "base_mint_param", None)
    if not isinstance(src, dict):
        return
    dst = getattr(log, "base_mint_param", None)
    if not isinstance(dst, dict):
        dst = {}
        setattr(log, "base_mint_param", dst)
    value = src.get(key)
    if _empty(dst.get(key)) and not _empty(value):
        dst[key] = value


def _ix_lane(ix_name: Any) -> int:
    if ix_name in ("sell", "sell_v2"):
        return 1
    if ix_name in ("buy_exact_sol_in", "buy_exact_quote_in", "buy_exact_quote_in_v2"):
        return 2
    return 0


PumpfunLaneBase = Tuple[str, str, bool, int]


def _next_occurrence(base: PumpfunLaneBase, counts: Dict[PumpfunLaneBase, int]) -> int:
    current = counts.get(base, 0)
    counts[base] = current + 1
    return current


def _dedupe_key(ev: DexEvent, pumpfun_lane_counts: Dict[PumpfunLaneBase, int]) -> Optional[str]:
    data = ev.data
    if data is None:
        return None

    if ev.type in PUMPFUN_TRADE_TYPES:
        lane = _ix_lane(getattr(data, "ix_name", ""))
        base = (
            getattr(data, "mint", ""),
            getattr(data, "user", ""),
            bool(getattr(data, "is_buy", False)),
            lane,
        )
        occ = _next_occurrence(base, pumpfun_lane_counts)
        return f"PumpFunTrade|{base[0]}|{base[1]}|{base[2]}|{base[3]}|{occ}"

    t = ev.type
    if t == EventType.PUMP_FUN_CREATE:
        return f"PumpFunCreate|{getattr(data, 'mint', '')}"
    if t == EventType.PUMP_FUN_CREATE_V2:
        return f"PumpFunCreate|{getattr(data, 'mint', '')}"
    if t == EventType.PUMP_FUN_MIGRATE:
        return (
            f"PumpFunMigrate|{getattr(data, 'mint', '')}|"
            f"{getattr(data, 'pool', '')}|{getattr(data, 'user', '')}"
        )
    if t == EventType.RAYDIUM_LAUNCHLAB_TRADE:
        return (
            f"RaydiumLaunchlabTrade|{getattr(data, 'pool_state', '')}|"
            f"{getattr(data, 'user', '')}|{bool(getattr(data, 'is_buy', False))}"
        )
    if t == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE:
        return f"RaydiumLaunchlabPoolCreate|{getattr(data, 'pool_state', '')}"
    if t == EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM:
        return (
            f"RaydiumLaunchlabMigrateAmm|{getattr(data, 'old_pool', '')}|"
            f"{getattr(data, 'new_pool', '')}|{getattr(data, 'user', '')}"
        )
    if t == EventType.PUMP_SWAP_BUY:
        return f"PumpSwapBuy|{getattr(data, 'pool', '')}|{getattr(data, 'user', '')}"
    if t == EventType.PUMP_SWAP_SELL:
        return f"PumpSwapSell|{getattr(data, 'pool', '')}|{getattr(data, 'user', '')}"
    if t == EventType.PUMP_SWAP_CREATE_POOL:
        return (
            f"PumpSwapCreatePool|{getattr(data, 'pool', '')}|"
            f"{getattr(data, 'base_mint', '')}|{getattr(data, 'quote_mint', '')}"
        )
    if t == EventType.PUMP_SWAP_LIQUIDITY_ADDED:
        return f"PumpSwapLiquidityAdded|{getattr(data, 'pool', '')}|{getattr(data, 'user', '')}"
    if t == EventType.PUMP_SWAP_LIQUIDITY_REMOVED:
        return f"PumpSwapLiquidityRemoved|{getattr(data, 'pool', '')}|{getattr(data, 'user', '')}"
    if t == EventType.RAYDIUM_CLMM_SWAP:
        return f"RaydiumClmmSwap|{getattr(data, 'pool_state', '')}|{bool(getattr(data, 'zero_for_one', False))}"
    if t == EventType.RAYDIUM_AMM_V4_SWAP:
        return f"RaydiumAmmV4Swap|{getattr(data, 'amm', '')}"
    if t == EventType.METEORA_DLMM_SWAP:
        return (
            f"MeteoraDlmmSwap|{getattr(data, 'pool', '')}|"
            f"{getattr(data, 'from_addr', '')}|{bool(getattr(data, 'swap_for_y', False))}"
        )
    return None


def _merge_pumpfun_trade(log: Any, ix: Any) -> None:
    for attr in (
        "global_account",
        "bonding_curve",
        "bonding_curve_v2",
        "associated_bonding_curve",
        "associated_user",
        "system_program",
        "token_program",
        "quote_token_program",
        "associated_token_program",
        "creator_vault",
        "fee_recipient",
        "associated_quote_fee_recipient",
        "buyback_fee_recipient",
        "associated_quote_buyback_fee_recipient",
        "associated_quote_bonding_curve",
        "associated_quote_user",
        "associated_creator_vault",
        "sharing_config",
        "event_authority",
        "program",
        "global_volume_accumulator",
        "user_volume_accumulator",
        "associated_user_volume_accumulator",
        "fee_config",
        "fee_program",
        "quote_mint",
        "creator",
        "extra_instruction_account",
    ):
        _fill_attr(log, attr, ix)
    for attr in (
        "amount",
        "max_sol_cost",
        "min_sol_output",
        "spendable_sol_in",
        "spendable_quote_in",
        "min_tokens_out",
        "quote_amount",
        "virtual_quote_reserves",
        "real_quote_reserves",
    ):
        if getattr(log, attr, 0) == 0 and getattr(ix, attr, 0) != 0:
            setattr(log, attr, getattr(ix, attr))
    if getattr(log, "ix_name", "") == "" and getattr(ix, "ix_name", "") != "":
        log.ix_name = ix.ix_name
    log.is_created_buy = bool(getattr(log, "is_created_buy", False)) or bool(
        getattr(ix, "is_created_buy", False)
    )


def _merge_pumpfun_create(log: Any, ix: Any) -> None:
    for attr in (
        "name",
        "symbol",
        "uri",
        "mint",
        "bonding_curve",
        "user",
        "creator",
        "token_program",
        "quote_mint",
        "quote_vault",
        "quote_token_program",
    ):
        _fill_attr(log, attr, ix)
    for attr in (
        "timestamp",
        "virtual_token_reserves",
        "virtual_sol_reserves",
        "real_token_reserves",
        "token_total_supply",
        "virtual_quote_reserves",
    ):
        if getattr(log, attr, 0) == 0 and getattr(ix, attr, 0) != 0:
            setattr(log, attr, getattr(ix, attr))
    log.is_mayhem_mode = bool(getattr(log, "is_mayhem_mode", False)) or bool(
        getattr(ix, "is_mayhem_mode", False)
    )
    log.is_cashback_enabled = bool(getattr(log, "is_cashback_enabled", False)) or bool(
        getattr(ix, "is_cashback_enabled", False)
    )


def _merge_pumpfun_create_v2(log: Any, ix: Any) -> None:
    _merge_pumpfun_create(log, ix)
    for attr in (
        "mint_authority",
        "associated_bonding_curve",
        "global_account",
        "system_program",
        "associated_token_program",
        "mayhem_program_id",
        "global_params",
        "sol_vault",
        "mayhem_state",
        "mayhem_token_vault",
        "event_authority",
        "program",
        "observed_fee_recipient",
    ):
        _fill_attr(log, attr, ix)


def _merge_pumpswap_buy_sell(log: Any, ix: Any, include_ix_name: bool) -> None:
    for attr in (
        "user_base_token_account",
        "user_quote_token_account",
        "protocol_fee_recipient",
        "protocol_fee_recipient_token_account",
        "coin_creator",
        "base_mint",
        "quote_mint",
        "pool_base_token_account",
        "pool_quote_token_account",
        "coin_creator_vault_ata",
        "coin_creator_vault_authority",
        "base_token_program",
        "quote_token_program",
        "pool_v2",
        "fee_recipient",
        "fee_recipient_quote_token_account",
    ):
        _fill_attr(log, attr, ix)
    if include_ix_name and getattr(log, "ix_name", "") == "" and getattr(ix, "ix_name", "") != "":
        log.ix_name = ix.ix_name


def _merge_grpc_instruction_into_log(log_ev: DexEvent, ix_ev: DexEvent) -> None:
    log = log_ev.data
    ix = ix_ev.data
    if log is None or ix is None:
        return

    if log_ev.type in PUMPFUN_TRADE_TYPES and ix_ev.type in PUMPFUN_TRADE_TYPES:
        _merge_pumpfun_trade(log, ix)
    elif log_ev.type == EventType.PUMP_FUN_CREATE and ix_ev.type == EventType.PUMP_FUN_CREATE_V2:
        _merge_pumpfun_create(log, ix)
    elif log_ev.type == EventType.PUMP_FUN_CREATE_V2 and ix_ev.type == EventType.PUMP_FUN_CREATE:
        _merge_pumpfun_create_v2(log, ix)
    elif log_ev.type == EventType.PUMP_FUN_CREATE and ix_ev.type == EventType.PUMP_FUN_CREATE:
        _merge_pumpfun_create(log, ix)
    elif log_ev.type == EventType.PUMP_FUN_CREATE_V2 and ix_ev.type == EventType.PUMP_FUN_CREATE_V2:
        _merge_pumpfun_create_v2(log, ix)
    elif log_ev.type == EventType.PUMP_FUN_MIGRATE and ix_ev.type == EventType.PUMP_FUN_MIGRATE:
        for attr in ("bonding_curve", "pool", "user"):
            _fill_attr(log, attr, ix)
    elif log_ev.type == EventType.PUMP_SWAP_BUY and ix_ev.type == EventType.PUMP_SWAP_BUY:
        _merge_pumpswap_buy_sell(log, ix, True)
    elif log_ev.type == EventType.PUMP_SWAP_SELL and ix_ev.type == EventType.PUMP_SWAP_SELL:
        _merge_pumpswap_buy_sell(log, ix, False)
    elif log_ev.type == EventType.PUMP_SWAP_CREATE_POOL and ix_ev.type == EventType.PUMP_SWAP_CREATE_POOL:
        for attr in (
            "creator",
            "pool",
            "lp_mint",
            "user_base_token_account",
            "user_quote_token_account",
            "coin_creator",
        ):
            _fill_attr(log, attr, ix)
    elif (
        log_ev.type == EventType.PUMP_SWAP_LIQUIDITY_ADDED
        and ix_ev.type == EventType.PUMP_SWAP_LIQUIDITY_ADDED
    ) or (
        log_ev.type == EventType.PUMP_SWAP_LIQUIDITY_REMOVED
        and ix_ev.type == EventType.PUMP_SWAP_LIQUIDITY_REMOVED
    ):
        for attr in ("user_base_token_account", "user_quote_token_account", "user_pool_token_account"):
            _fill_attr(log, attr, ix)
    elif log_ev.type == EventType.RAYDIUM_CLMM_SWAP and ix_ev.type == EventType.RAYDIUM_CLMM_SWAP:
        for attr in ("token_account_0", "token_account_1", "sender"):
            _fill_attr(log, attr, ix)
    elif log_ev.type == EventType.RAYDIUM_AMM_V4_SWAP and ix_ev.type == EventType.RAYDIUM_AMM_V4_SWAP:
        for attr in (
            "token_program",
            "amm_authority",
            "amm_open_orders",
            "pool_coin_token_account",
            "pool_pc_token_account",
            "serum_program",
            "serum_market",
            "serum_bids",
            "serum_asks",
            "serum_event_queue",
            "serum_coin_vault_account",
            "serum_pc_vault_account",
            "serum_vault_signer",
            "user_source_token_account",
            "user_destination_token_account",
        ):
            _fill_attr(log, attr, ix)
    elif log_ev.type == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE and ix_ev.type == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE:
        _fill_attr(log, "creator", ix)
        for key in ("name", "symbol", "uri"):
            _fill_raydium_launchlab_mint_param(log, ix, key)
    elif log_ev.type == EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM and ix_ev.type == EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM:
        for attr in ("old_pool", "new_pool", "user"):
            _fill_attr(log, attr, ix)


def dedupe_log_instruction_events(
    log_events: List[DexEvent],
    instruction_events: List[DexEvent],
) -> List[DexEvent]:
    out: List[DexEvent] = []
    index_by_key: Dict[str, int] = {}
    log_pumpfun_counts: Dict[PumpfunLaneBase, int] = {}
    ix_pumpfun_counts: Dict[PumpfunLaneBase, int] = {}

    for ev in log_events:
        key = _dedupe_key(ev, log_pumpfun_counts)
        if key is not None:
            index_by_key[key] = len(out)
        out.append(ev)

    for ev in instruction_events:
        key = _dedupe_key(ev, ix_pumpfun_counts)
        if key is None:
            out.append(ev)
            continue
        idx = index_by_key.get(key)
        if idx is None:
            index_by_key[key] = len(out)
            out.append(ev)
            continue
        _merge_grpc_instruction_into_log(out[idx], ev)

    return out
