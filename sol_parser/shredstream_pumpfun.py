"""ShredStream 路径下的 PumpFun 外层指令：静态账户 best-effort 解析（对齐 Rust ``shredstream``）。"""

from __future__ import annotations

import struct
from typing import List, Set, Tuple

from .dex_parsers import Z, normalize_pumpfun_ix_name
from .event_types import DexEvent, PumpFunTradeEvent
from .grpc_types import EventMetadata, EventType
from .instructions import PUMPFUN_PROGRAM_ID, parse_pumpfun_instruction

_DISC_CREATE = bytes([24, 30, 200, 40, 5, 28, 7, 119])
_DISC_CREATE_V2 = bytes([214, 144, 76, 236, 95, 139, 49, 180])
_DISC_BUY_V2 = bytes([184, 23, 238, 97, 103, 197, 211, 61])
_DISC_SELL_V2 = bytes([93, 246, 130, 60, 231, 233, 64, 178])
_DISC_BUY_EXACT_QUOTE_IN_V2 = bytes([194, 171, 28, 70, 104, 77, 91, 47])


def _get_acct(accounts: List[str], ix_accounts: bytes, idx: int) -> str:
    if idx >= len(ix_accounts):
        return ""
    ai = ix_accounts[idx]
    if ai >= len(accounts):
        return Z
    return accounts[ai]


def _ordered_ix_accounts(accounts: List[str], ix_accounts: bytes) -> List[str]:
    return [_get_acct(accounts, ix_accounts, i) for i in range(len(ix_accounts))]


def _parse_create_v2_mayhem(data_after_disc: bytes) -> bool:
    o = 0
    for _ in range(3):
        if len(data_after_disc) < o + 4:
            return False
        (ln,) = struct.unpack_from("<I", data_after_disc, o)
        o += 4 + int(ln)
    if len(data_after_disc) < o + 32 + 1:
        return False
    o += 32
    return data_after_disc[o] != 0


def detect_pumpfun_create_mints(
    program_id: str,
    data: bytes,
    ix_accounts: bytes,
    accounts: List[str],
) -> Tuple[Set[str], Set[str]]:
    """返回 ``(created_mints, mayhem_mints)``。"""
    created: Set[str] = set()
    mayhem: Set[str] = set()
    if program_id != PUMPFUN_PROGRAM_ID or len(data) < 8:
        return created, mayhem
    disc = data[:8]
    if disc == _DISC_CREATE or disc == _DISC_CREATE_V2:
        if not ix_accounts:
            return created, mayhem
        mint = _get_acct(accounts, ix_accounts, 0)
        if mint and mint != Z:
            created.add(mint)
        if disc == _DISC_CREATE_V2:
            if _parse_create_v2_mayhem(data[8:]):
                mayhem.add(mint)
    return created, mayhem


def _meta(sig: str, slot: int, tx_index: int, recv_us: int) -> EventMetadata:
    return EventMetadata(
        signature=sig,
        slot=slot,
        tx_index=tx_index,
        block_time_us=0,
        grpc_recv_us=recv_us,
    )


def _token_program_default(tp: str) -> str:
    if not tp or tp == "11111111111111111111111111111111":
        return "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
    return tp


def _pumpfun_trade_event_type(ix_name: str) -> EventType:
    normalized = normalize_pumpfun_ix_name(ix_name)
    if normalized == "buy":
        return EventType.PUMP_FUN_BUY
    if normalized == "sell":
        return EventType.PUMP_FUN_SELL
    if normalized == "buy_exact_sol_in":
        return EventType.PUMP_FUN_BUY_EXACT_SOL_IN
    if normalized == "buy_exact_quote_in":
        return EventType.PUMP_FUN_BUY
    return EventType.PUMP_FUN_TRADE


def parse_pumpfun_trade_v2(
    ix_name: str,
    data: bytes,
    accounts: List[str],
    ix_accounts: bytes,
    sig: str,
    slot: int,
    tx_index: int,
    recv_us: int,
    created_mints: Set[str],
    mayhem_mints: Set[str],
) -> DexEvent | None:
    if len(data) < 8:
        return None
    payload = data[8:]
    first = struct.unpack_from("<Q", payload, 0)[0] if len(payload) >= 8 else 0
    second = struct.unpack_from("<Q", payload, 8)[0] if len(payload) >= 16 else 0
    if ix_name == "buy_exact_quote_in_v2":
        sol_amount, token_amount = first, second
    else:
        token_amount, sol_amount = first, second
    mint = _get_acct(accounts, ix_accounts, 1)
    if not mint:
        return None
    return DexEvent(
        type=_pumpfun_trade_event_type(ix_name),
        data=PumpFunTradeEvent(
            metadata=_meta(sig, slot, tx_index, recv_us),
            mint=mint,
            bonding_curve=_get_acct(accounts, ix_accounts, 10),
            user=_get_acct(accounts, ix_accounts, 13),
            sol_amount=sol_amount,
            token_amount=token_amount,
            amount=second if ix_name == "buy_exact_quote_in_v2" else first,
            max_sol_cost=(
                0
                if ix_name == "buy_exact_quote_in_v2"
                else (0 if ix_name == "sell_v2" else second)
            ),
            min_sol_output=second if ix_name == "sell_v2" else 0,
            spendable_quote_in=first if ix_name == "buy_exact_quote_in_v2" else 0,
            min_tokens_out=second if ix_name == "buy_exact_quote_in_v2" else 0,
            quote_amount=first if ix_name == "buy_exact_quote_in_v2" else 0,
            fee_recipient=_get_acct(accounts, ix_accounts, 6),
            is_buy=ix_name != "sell_v2",
            is_created_buy=mint in created_mints,
            ix_name=ix_name,
            mayhem_mode=mint in mayhem_mints,
            associated_bonding_curve=_get_acct(accounts, ix_accounts, 11),
            token_program=_token_program_default(_get_acct(accounts, ix_accounts, 3)),
            creator_vault=_get_acct(accounts, ix_accounts, 16),
        ),
    )


def parse_pumpfun_shred_ix(
    data: bytes,
    accounts: List[str],
    ix_accounts: bytes,
    program_id: str,
    sig: str,
    slot: int,
    tx_index: int,
    recv_us: int,
    created_mints: Set[str],
    mayhem_mints: Set[str],
) -> DexEvent | None:
    if program_id != PUMPFUN_PROGRAM_ID or len(data) < 8:
        return None
    disc = data[:8]
    minimum = 26 if disc == _DISC_SELL_V2 else 27
    if (
        disc not in (_DISC_BUY_V2, _DISC_SELL_V2, _DISC_BUY_EXACT_QUOTE_IN_V2)
        or len(ix_accounts) >= minimum
    ):
        event = parse_pumpfun_instruction(
            data,
            _ordered_ix_accounts(accounts, ix_accounts),
            sig,
            slot,
            tx_index,
            None,
            recv_us,
        )
        if event is not None and isinstance(event.data, PumpFunTradeEvent):
            event.data.is_created_buy = event.data.is_buy and event.data.mint in created_mints
            event.data.mayhem_mode = event.data.mint in mayhem_mints
        return event
    # Preserve the explicit legacy best-effort short-V2 compatibility.
    name = {
        _DISC_BUY_V2: "buy_v2",
        _DISC_SELL_V2: "sell_v2",
        _DISC_BUY_EXACT_QUOTE_IN_V2: "buy_exact_quote_in_v2",
    }[disc]
    return parse_pumpfun_trade_v2(
        name,
        data,
        accounts,
        ix_accounts,
        sig,
        slot,
        tx_index,
        recv_us,
        created_mints,
        mayhem_mints,
    )


# Keep the former per-method entry points backed by the shared native decoder.
def parse_pumpfun_buy(
    data,
    accounts,
    ix_accounts,
    sig,
    slot,
    tx_index,
    recv_us,
    created_mints,
    mayhem_mints,
):
    return parse_pumpfun_shred_ix(
        data,
        accounts,
        ix_accounts,
        PUMPFUN_PROGRAM_ID,
        sig,
        slot,
        tx_index,
        recv_us,
        created_mints,
        mayhem_mints,
    )


def parse_pumpfun_sell(data, accounts, ix_accounts, sig, slot, tx_index, recv_us):
    return parse_pumpfun_shred_ix(
        data,
        accounts,
        ix_accounts,
        PUMPFUN_PROGRAM_ID,
        sig,
        slot,
        tx_index,
        recv_us,
        set(),
        set(),
    )


def parse_pumpfun_buy_exact_sol_in(
    data,
    accounts,
    ix_accounts,
    sig,
    slot,
    tx_index,
    recv_us,
    created_mints,
    mayhem_mints,
):
    return parse_pumpfun_shred_ix(
        data,
        accounts,
        ix_accounts,
        PUMPFUN_PROGRAM_ID,
        sig,
        slot,
        tx_index,
        recv_us,
        created_mints,
        mayhem_mints,
    )
