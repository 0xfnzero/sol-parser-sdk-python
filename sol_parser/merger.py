"""Instruction + inner instruction 事件合并（对齐 Rust ``core/merger``）。"""

from __future__ import annotations

import dataclasses
from typing import Any

from .event_types import (
    DexEvent,
    PumpFunCreateEvent,
    PumpFunCreateV2TokenEvent,
    PumpFunMigrateEvent,
    PumpFunTradeEvent,
    PumpSwapBuyEvent,
    PumpSwapCreatePoolEvent,
    PumpSwapLiquidityAddedEvent,
    PumpSwapLiquidityRemovedEvent,
    PumpSwapSellEvent,
    RaydiumAmmV4DepositEvent,
    RaydiumAmmV4SwapEvent,
    RaydiumAmmV4WithdrawEvent,
    RaydiumClmmCollectFeeEvent,
    RaydiumClmmCreatePoolEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmIncreaseLiquidityEvent,
    RaydiumClmmSwapEvent,
    RaydiumCpmmDepositEvent,
    RaydiumCpmmSwapEvent,
    RaydiumCpmmWithdrawEvent,
    MeteoraDammV2AddLiquidityEvent,
    MeteoraDammV2ClosePositionEvent,
    MeteoraDammV2CreatePositionEvent,
    MeteoraDammV2RemoveLiquidityEvent,
    MeteoraDammV2SwapEvent,
    MeteoraDlmmAddLiquidityEvent,
    MeteoraDlmmClaimFeeEvent,
    MeteoraDlmmClosePositionEvent,
    MeteoraDlmmCreatePositionEvent,
    MeteoraDlmmInitializeBinArrayEvent,
    MeteoraDlmmInitializePoolEvent,
    MeteoraDlmmRemoveLiquidityEvent,
    MeteoraDlmmSwapEvent,
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsSwapEvent,
    OrcaWhirlpoolLiquidityDecreasedEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolSwapEvent,
    RaydiumLaunchlabTradeEvent,
)
from .grpc_types import EventType

ZERO = "11111111111111111111111111111111"

GENERIC_MERGE_TYPES = (
    PumpSwapCreatePoolEvent,
    PumpSwapLiquidityAddedEvent,
    PumpSwapLiquidityRemovedEvent,
    RaydiumClmmSwapEvent,
    RaydiumClmmIncreaseLiquidityEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmCreatePoolEvent,
    RaydiumClmmCollectFeeEvent,
    RaydiumCpmmSwapEvent,
    RaydiumCpmmDepositEvent,
    RaydiumCpmmWithdrawEvent,
    RaydiumAmmV4SwapEvent,
    RaydiumAmmV4DepositEvent,
    RaydiumAmmV4WithdrawEvent,
    OrcaWhirlpoolSwapEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolLiquidityDecreasedEvent,
    MeteoraPoolsSwapEvent,
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraDammV2SwapEvent,
    MeteoraDammV2AddLiquidityEvent,
    MeteoraDammV2RemoveLiquidityEvent,
    MeteoraDammV2CreatePositionEvent,
    MeteoraDammV2ClosePositionEvent,
    MeteoraDlmmSwapEvent,
    MeteoraDlmmAddLiquidityEvent,
    MeteoraDlmmRemoveLiquidityEvent,
    MeteoraDlmmInitializeBinArrayEvent,
    MeteoraDlmmClaimFeeEvent,
    RaydiumLaunchlabTradeEvent,
)


def _merge_generic(base: Any, inner: Any) -> None:
    for f in dataclasses.fields(type(base)):
        setattr(base, f.name, getattr(inner, f.name))


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == ZERO


def _fill_attr_if_empty(base: Any, attr: str, source: Any) -> None:
    value = getattr(source, attr, None)
    if _empty(getattr(base, attr, None)) and not _empty(value):
        setattr(base, attr, value)


def _put_attr_if_set(base: Any, attr: str, source: Any) -> None:
    value = getattr(source, attr, None)
    if not _empty(value):
        setattr(base, attr, value)


def _put_num_if_nonzero(base: Any, attr: str, source: Any) -> None:
    value = getattr(source, attr, 0)
    if value:
        setattr(base, attr, value)


def merge_pumpfun_trade(base: PumpFunTradeEvent, inner: PumpFunTradeEvent) -> None:
    leg = inner.sol_amount != 0 or inner.token_amount != 0

    for attr in ("mint", "user", "fee_recipient", "creator"):
        _put_attr_if_set(base, attr, inner)

    if leg:
        for attr in (
            "sol_amount",
            "token_amount",
            "timestamp",
            "virtual_sol_reserves",
            "virtual_token_reserves",
            "real_sol_reserves",
            "real_token_reserves",
            "fee_basis_points",
            "fee",
            "creator_fee_basis_points",
            "creator_fee",
            "total_unclaimed_tokens",
            "total_claimed_tokens",
            "current_sol_volume",
            "last_update_timestamp",
        ):
            setattr(base, attr, getattr(inner, attr))
        base.is_buy = inner.is_buy
        base.track_volume = bool(base.track_volume) or bool(inner.track_volume)
        base.mayhem_mode = bool(base.mayhem_mode) or bool(inner.mayhem_mode)
        if inner.ix_name:
            base.ix_name = inner.ix_name
        base.is_cashback_coin = bool(base.is_cashback_coin) or bool(inner.is_cashback_coin)
    else:
        for attr in (
            "fee",
            "creator_fee",
            "fee_basis_points",
            "creator_fee_basis_points",
            "virtual_sol_reserves",
            "virtual_token_reserves",
            "real_sol_reserves",
            "real_token_reserves",
            "total_unclaimed_tokens",
            "total_claimed_tokens",
            "current_sol_volume",
            "timestamp",
            "last_update_timestamp",
        ):
            _put_num_if_nonzero(base, attr, inner)
        base.track_volume = bool(base.track_volume) or bool(inner.track_volume)
        base.mayhem_mode = bool(base.mayhem_mode) or bool(inner.mayhem_mode)
        if inner.ix_name:
            base.ix_name = inner.ix_name
        base.is_cashback_coin = bool(base.is_cashback_coin) or bool(inner.is_cashback_coin)

    for attr in (
        "cashback_fee_basis_points",
        "cashback",
        "buyback_fee_basis_points",
        "buyback_fee",
        "quote_amount",
        "virtual_quote_reserves",
        "real_quote_reserves",
        "amount",
        "max_sol_cost",
        "min_sol_output",
        "spendable_sol_in",
        "spendable_quote_in",
        "min_tokens_out",
    ):
        _put_num_if_nonzero(base, attr, inner)

    if inner.shareholders and not base.shareholders:
        base.shareholders = inner.shareholders

    for attr in (
        "quote_mint",
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
        "extra_instruction_account",
    ):
        _put_attr_if_set(base, attr, inner)

    base.is_created_buy = bool(base.is_created_buy) or bool(inner.is_created_buy)


def merge_pumpswap_buy(base: PumpSwapBuyEvent, inner: PumpSwapBuyEvent) -> None:
    instruction = dataclasses.replace(base)
    _merge_generic(base, inner)
    for attr in (
        "base_mint",
        "quote_mint",
        "user_base_token_account",
        "user_quote_token_account",
        "pool_base_token_account",
        "pool_quote_token_account",
        "protocol_fee_recipient",
        "protocol_fee_recipient_token_account",
        "coin_creator_vault_ata",
        "coin_creator_vault_authority",
        "base_token_program",
        "quote_token_program",
        "pool_v2",
        "fee_recipient",
        "fee_recipient_quote_token_account",
    ):
        _fill_attr_if_empty(base, attr, instruction)


def merge_pumpswap_sell(base: PumpSwapSellEvent, inner: PumpSwapSellEvent) -> None:
    instruction = dataclasses.replace(base)
    _merge_generic(base, inner)
    for attr in (
        "base_mint",
        "quote_mint",
        "user_base_token_account",
        "user_quote_token_account",
        "pool_base_token_account",
        "pool_quote_token_account",
        "protocol_fee_recipient",
        "protocol_fee_recipient_token_account",
        "coin_creator_vault_ata",
        "coin_creator_vault_authority",
        "base_token_program",
        "quote_token_program",
        "pool_v2",
        "fee_recipient",
        "fee_recipient_quote_token_account",
    ):
        _fill_attr_if_empty(base, attr, instruction)


def merge_pumpfun_create(base: PumpFunCreateEvent, inner: PumpFunCreateEvent) -> None:
    base.name = inner.name
    base.symbol = inner.symbol
    base.uri = inner.uri
    base.mint = inner.mint
    base.bonding_curve = inner.bonding_curve
    base.user = inner.user
    base.creator = inner.creator
    base.timestamp = inner.timestamp
    base.virtual_token_reserves = inner.virtual_token_reserves
    base.virtual_sol_reserves = inner.virtual_sol_reserves
    base.real_token_reserves = inner.real_token_reserves
    base.token_total_supply = inner.token_total_supply
    base.token_program = inner.token_program
    base.is_mayhem_mode = inner.is_mayhem_mode
    base.is_cashback_enabled = inner.is_cashback_enabled
    base.quote_mint = inner.quote_mint
    base.virtual_quote_reserves = inner.virtual_quote_reserves


def merge_pumpfun_migrate(base: PumpFunMigrateEvent, inner: PumpFunMigrateEvent) -> None:
    base.user = inner.user
    base.mint = inner.mint
    base.mint_amount = inner.mint_amount
    base.sol_amount = inner.sol_amount
    base.pool_migration_fee = inner.pool_migration_fee
    base.bonding_curve = inner.bonding_curve
    base.timestamp = inner.timestamp
    base.pool = inner.pool


def merge_dex_events(base: DexEvent, inner: DexEvent) -> None:
    """将 ``inner`` 合并进 ``base``（就地修改 ``base.data``）。"""
    try_merge_dex_events(base, inner)


def try_merge_dex_events(base: DexEvent, inner: DexEvent) -> bool:
    """Merge compatible events and report success so unmatched events are retained."""
    bd = base.data
    ind = inner.data

    if isinstance(bd, PumpFunTradeEvent) and isinstance(ind, PumpFunTradeEvent):
        if base.type in (
            EventType.PUMP_FUN_TRADE,
            EventType.PUMP_FUN_BUY,
            EventType.PUMP_FUN_SELL,
            EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        ) and inner.type in (
            EventType.PUMP_FUN_TRADE,
            EventType.PUMP_FUN_BUY,
            EventType.PUMP_FUN_SELL,
            EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        ):
            merge_pumpfun_trade(bd, ind)
            return True
        return False

    if isinstance(bd, PumpFunCreateEvent) and isinstance(ind, PumpFunCreateEvent):
        merge_pumpfun_create(bd, ind)
        return True

    if isinstance(bd, PumpFunCreateV2TokenEvent) and isinstance(ind, PumpFunCreateV2TokenEvent):
        _merge_generic(bd, ind)
        return True

    if isinstance(bd, PumpFunMigrateEvent) and isinstance(ind, PumpFunMigrateEvent):
        merge_pumpfun_migrate(bd, ind)
        return True

    if isinstance(bd, PumpSwapBuyEvent) and isinstance(ind, PumpSwapBuyEvent):
        merge_pumpswap_buy(bd, ind)
        return True
    if isinstance(bd, PumpSwapSellEvent) and isinstance(ind, PumpSwapSellEvent):
        merge_pumpswap_sell(bd, ind)
        return True
    if isinstance(bd, MeteoraDlmmInitializePoolEvent) and isinstance(ind, MeteoraDlmmInitializePoolEvent):
        creator, active_bin_id = bd.creator, bd.active_bin_id
        _merge_generic(bd, ind)
        bd.creator, bd.active_bin_id = creator, active_bin_id
        return True
    if isinstance(bd, MeteoraDlmmCreatePositionEvent) and isinstance(ind, MeteoraDlmmCreatePositionEvent):
        lower_bin_id, width = bd.lower_bin_id, bd.width
        _merge_generic(bd, ind)
        bd.lower_bin_id, bd.width = lower_bin_id, width
        return True
    if isinstance(bd, MeteoraDlmmClosePositionEvent) and isinstance(ind, MeteoraDlmmClosePositionEvent):
        pool = bd.pool
        _merge_generic(bd, ind)
        bd.pool = pool
        return True

    if base.type == inner.type and type(bd) is type(ind) and isinstance(bd, GENERIC_MERGE_TYPES):
        _merge_generic(bd, ind)
        return True

    return False
