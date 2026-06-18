"""PumpFun 账户填充（对齐 ``account_fillers/pumpfun.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import (
    PumpFunCreateEvent,
    PumpFunCreateV2TokenEvent,
    PumpFunMigrateEvent,
    PumpFunTradeEvent,
)

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_trade_accounts(e: PumpFunTradeEvent, get: AccountGetter) -> None:
    def account_at_matches_mint(idx: int) -> bool:
        return not _empty(e.mint) and get(idx) == e.mint

    def set_attr(name: str, idx: int) -> None:
        if _empty(getattr(e, name)):
            setattr(e, name, get(idx))

    is_v2 = e.ix_name in ("buy_v2", "sell_v2", "buy_exact_quote_in_v2") or account_at_matches_mint(1)
    if is_v2:
        set_attr("global_account", 0)
        set_attr("quote_mint", 2)
        set_attr("fee_recipient", 6)
        set_attr("bonding_curve", 10)
        set_attr("associated_bonding_curve", 11)
        set_attr("associated_quote_bonding_curve", 12)
        set_attr("user", 13)
        set_attr("associated_user", 14)
        set_attr("associated_quote_user", 15)
        set_attr("token_program", 3)
        set_attr("quote_token_program", 4)
        set_attr("associated_token_program", 5)
        set_attr("creator_vault", 16)
        set_attr("associated_quote_fee_recipient", 7)
        set_attr("buyback_fee_recipient", 8)
        set_attr("associated_quote_buyback_fee_recipient", 9)
        set_attr("associated_creator_vault", 17)
        set_attr("sharing_config", 18)
        if e.ix_name == "sell_v2" or (e.ix_name == "sell" and not e.is_buy):
            set_attr("user_volume_accumulator", 19)
            set_attr("associated_user_volume_accumulator", 20)
            set_attr("fee_config", 21)
            set_attr("fee_program", 22)
            set_attr("system_program", 23)
            set_attr("event_authority", 24)
            set_attr("program", 25)
        else:
            set_attr("global_volume_accumulator", 19)
            set_attr("user_volume_accumulator", 20)
            set_attr("associated_user_volume_accumulator", 21)
            set_attr("fee_config", 22)
            set_attr("fee_program", 23)
            set_attr("system_program", 24)
            set_attr("event_authority", 25)
            set_attr("program", 26)
        return
    set_attr("global_account", 0)
    set_attr("fee_recipient", 1)
    set_attr("bonding_curve", 3)
    set_attr("associated_bonding_curve", 4)
    set_attr("associated_user", 5)
    set_attr("user", 6)
    set_attr("system_program", 7)
    if _empty(e.creator_vault):
        e.creator_vault = get(9) if e.is_buy else get(8)
    if _empty(e.token_program):
        e.token_program = get(8) if e.is_buy else get(9)
    set_attr("event_authority", 10)
    set_attr("program", 11)
    if e.is_buy:
        set_attr("global_volume_accumulator", 12)
        set_attr("user_volume_accumulator", 13)
        set_attr("fee_config", 14)
        set_attr("fee_program", 15)
        set_attr("bonding_curve_v2", 16)
        set_attr("buyback_fee_recipient", 17)
        a17 = get(17)
        if not _empty(a17) and _empty(e.extra_instruction_account):
            e.extra_instruction_account = a17
        return
    set_attr("fee_config", 12)
    set_attr("fee_program", 13)
    a16 = get(16)
    if not _empty(a16):
        set_attr("user_volume_accumulator", 14)
        set_attr("bonding_curve_v2", 15)
        set_attr("buyback_fee_recipient", 16)
        if _empty(e.extra_instruction_account):
            e.extra_instruction_account = a16
        return
    if e.is_cashback_coin:
        set_attr("user_volume_accumulator", 14)
        set_attr("bonding_curve_v2", 15)
        return
    set_attr("bonding_curve_v2", 14)
    set_attr("buyback_fee_recipient", 15)
    a15 = get(15)
    if not _empty(a15) and _empty(e.extra_instruction_account):
        e.extra_instruction_account = a15


def fill_create_accounts(e: PumpFunCreateEvent, get: AccountGetter) -> None:
    if get(15) == "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P":
        fill_create_v2_accounts(e, get)  # type: ignore[arg-type]
        return
    if _empty(e.mint):
        e.mint = get(0)
    if _empty(e.bonding_curve):
        e.bonding_curve = get(2)
    if _empty(e.user):
        e.user = get(7)


def fill_create_v2_accounts(e: PumpFunCreateV2TokenEvent, get: AccountGetter) -> None:
    if _empty(e.mint):
        e.mint = get(0)
    if _empty(e.bonding_curve):
        e.bonding_curve = get(2)
    if _empty(e.user):
        e.user = get(5)
    if _empty(e.mint_authority):
        e.mint_authority = get(1)
    if _empty(e.associated_bonding_curve):
        e.associated_bonding_curve = get(3)
    if _empty(e.global_account):
        e.global_account = get(4)
    if _empty(e.system_program):
        e.system_program = get(6)
    if _empty(e.token_program):
        e.token_program = get(7)
    if _empty(e.associated_token_program):
        e.associated_token_program = get(8)
    if _empty(e.mayhem_program_id):
        e.mayhem_program_id = get(9)
    if _empty(e.global_params):
        e.global_params = get(10)
    if _empty(e.sol_vault):
        e.sol_vault = get(11)
    if _empty(e.mayhem_state):
        e.mayhem_state = get(12)
    if _empty(e.mayhem_token_vault):
        e.mayhem_token_vault = get(13)
    if _empty(e.event_authority):
        e.event_authority = get(14)
    if _empty(e.program):
        e.program = get(15)
    if _empty(e.quote_mint) or e.quote_mint == "So11111111111111111111111111111111111111111":
        e.quote_mint = get(16)
    if _empty(e.quote_vault):
        e.quote_vault = get(17)
    if _empty(e.quote_token_program):
        e.quote_token_program = get(18)
    if getattr(e, "ix_name", "") in ("", "create"):
        e.ix_name = "create_v2"


def fill_migrate_accounts(_e: PumpFunMigrateEvent, _get: AccountGetter) -> None:
    pass
