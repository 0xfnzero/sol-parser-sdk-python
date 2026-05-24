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
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsSwapEvent,
    OrcaWhirlpoolLiquidityDecreasedEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolSwapEvent,
    BonkTradeEvent,
)
from .grpc_types import EventType

ZERO = "11111111111111111111111111111111"


def _merge_generic(base: Any, inner: Any) -> None:
    for f in dataclasses.fields(type(base)):
        setattr(base, f.name, getattr(inner, f.name))


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == ZERO


def _fill_attr_if_empty(base: Any, attr: str, source: Any) -> None:
    value = getattr(source, attr, None)
    if _empty(getattr(base, attr, None)) and not _empty(value):
        setattr(base, attr, value)


def merge_pumpfun_trade(base: PumpFunTradeEvent, inner: PumpFunTradeEvent) -> None:
    base.mint = inner.mint
    base.sol_amount = inner.sol_amount
    base.token_amount = inner.token_amount
    base.is_buy = inner.is_buy
    base.user = inner.user
    base.timestamp = inner.timestamp
    base.virtual_sol_reserves = inner.virtual_sol_reserves
    base.virtual_token_reserves = inner.virtual_token_reserves
    base.real_sol_reserves = inner.real_sol_reserves
    base.real_token_reserves = inner.real_token_reserves
    base.fee_recipient = inner.fee_recipient
    base.fee_basis_points = inner.fee_basis_points
    base.fee = inner.fee
    base.creator = inner.creator
    base.creator_fee_basis_points = inner.creator_fee_basis_points
    base.creator_fee = inner.creator_fee
    base.track_volume = inner.track_volume
    base.total_unclaimed_tokens = inner.total_unclaimed_tokens
    base.total_claimed_tokens = inner.total_claimed_tokens
    base.current_sol_volume = inner.current_sol_volume
    base.last_update_timestamp = inner.last_update_timestamp
    base.ix_name = inner.ix_name
    base.is_created_buy = inner.is_created_buy
    base.mayhem_mode = inner.mayhem_mode
    base.cashback_fee_basis_points = inner.cashback_fee_basis_points
    base.cashback = inner.cashback
    if inner.buyback_fee_basis_points != 0:
        base.buyback_fee_basis_points = inner.buyback_fee_basis_points
    if inner.buyback_fee != 0:
        base.buyback_fee = inner.buyback_fee
    if inner.shareholders:
        base.shareholders = inner.shareholders
    if not _empty(inner.quote_mint):
        base.quote_mint = inner.quote_mint
    if inner.quote_amount != 0:
        base.quote_amount = inner.quote_amount
    if inner.virtual_quote_reserves != 0:
        base.virtual_quote_reserves = inner.virtual_quote_reserves
    if inner.real_quote_reserves != 0:
        base.real_quote_reserves = inner.real_quote_reserves
    base.is_cashback_coin = inner.is_cashback_coin


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
            base.type = inner.type
        return

    if isinstance(bd, PumpFunCreateEvent) and isinstance(ind, PumpFunCreateEvent):
        merge_pumpfun_create(bd, ind)
        return

    if isinstance(bd, PumpFunCreateV2TokenEvent) and isinstance(ind, PumpFunCreateV2TokenEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, PumpFunMigrateEvent) and isinstance(ind, PumpFunMigrateEvent):
        merge_pumpfun_migrate(bd, ind)
        return

    if isinstance(bd, PumpSwapBuyEvent) and isinstance(ind, PumpSwapBuyEvent):
        merge_pumpswap_buy(bd, ind)
        return
    if isinstance(bd, PumpSwapSellEvent) and isinstance(ind, PumpSwapSellEvent):
        merge_pumpswap_sell(bd, ind)
        return
    if isinstance(bd, PumpSwapCreatePoolEvent) and isinstance(ind, PumpSwapCreatePoolEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, PumpSwapLiquidityAddedEvent) and isinstance(ind, PumpSwapLiquidityAddedEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, PumpSwapLiquidityRemovedEvent) and isinstance(ind, PumpSwapLiquidityRemovedEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, RaydiumClmmSwapEvent) and isinstance(ind, RaydiumClmmSwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumClmmIncreaseLiquidityEvent) and isinstance(ind, RaydiumClmmIncreaseLiquidityEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumClmmDecreaseLiquidityEvent) and isinstance(ind, RaydiumClmmDecreaseLiquidityEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumClmmCreatePoolEvent) and isinstance(ind, RaydiumClmmCreatePoolEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumClmmCollectFeeEvent) and isinstance(ind, RaydiumClmmCollectFeeEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, RaydiumCpmmSwapEvent) and isinstance(ind, RaydiumCpmmSwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumCpmmDepositEvent) and isinstance(ind, RaydiumCpmmDepositEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumCpmmWithdrawEvent) and isinstance(ind, RaydiumCpmmWithdrawEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, RaydiumAmmV4SwapEvent) and isinstance(ind, RaydiumAmmV4SwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumAmmV4DepositEvent) and isinstance(ind, RaydiumAmmV4DepositEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, RaydiumAmmV4WithdrawEvent) and isinstance(ind, RaydiumAmmV4WithdrawEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, OrcaWhirlpoolSwapEvent) and isinstance(ind, OrcaWhirlpoolSwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, OrcaWhirlpoolLiquidityIncreasedEvent) and isinstance(ind, OrcaWhirlpoolLiquidityIncreasedEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, OrcaWhirlpoolLiquidityDecreasedEvent) and isinstance(ind, OrcaWhirlpoolLiquidityDecreasedEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, MeteoraPoolsSwapEvent) and isinstance(ind, MeteoraPoolsSwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraPoolsAddLiquidityEvent) and isinstance(ind, MeteoraPoolsAddLiquidityEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraPoolsRemoveLiquidityEvent) and isinstance(ind, MeteoraPoolsRemoveLiquidityEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, MeteoraDammV2SwapEvent) and isinstance(ind, MeteoraDammV2SwapEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraDammV2AddLiquidityEvent) and isinstance(ind, MeteoraDammV2AddLiquidityEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraDammV2RemoveLiquidityEvent) and isinstance(ind, MeteoraDammV2RemoveLiquidityEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraDammV2CreatePositionEvent) and isinstance(ind, MeteoraDammV2CreatePositionEvent):
        _merge_generic(bd, ind)
        return
    if isinstance(bd, MeteoraDammV2ClosePositionEvent) and isinstance(ind, MeteoraDammV2ClosePositionEvent):
        _merge_generic(bd, ind)
        return

    if isinstance(bd, BonkTradeEvent) and isinstance(ind, BonkTradeEvent):
        _merge_generic(bd, ind)
        return
