"""PumpFun 账户填充（对齐 ``account_fillers/pumpfun.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import PumpFunCreateEvent, PumpFunCreateV2TokenEvent, PumpFunTradeEvent

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_trade_accounts(e: PumpFunTradeEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(6)
    if _empty(e.bonding_curve):
        e.bonding_curve = get(3)
    if _empty(e.associated_bonding_curve):
        e.associated_bonding_curve = get(4)
    if _empty(e.creator_vault):
        e.creator_vault = get(9) if e.is_buy else get(8)
    if _empty(e.token_program):
        e.token_program = get(8) if e.is_buy else get(9)


def fill_create_accounts(e: PumpFunCreateEvent, get: AccountGetter) -> None:
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
