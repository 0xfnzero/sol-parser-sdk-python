"""ShredStream 路径下的 PumpFun 外层指令：mint 检测与 Buy/Sell/BuyExactSolIn（对齐 Rust ``shredstream/client``）。"""

from __future__ import annotations

import struct
from typing import List, Set, Tuple

from .event_types import DexEvent, PumpFunTradeEvent
from .grpc_types import EventMetadata, EventType
from .instructions import PUMPFUN_PROGRAM_ID, parse_pumpfun_instruction

_DISC_CREATE = bytes([24, 30, 200, 40, 5, 28, 7, 119])
_DISC_CREATE_V2 = bytes([214, 144, 76, 236, 95, 139, 49, 180])
_DISC_BUY = bytes([102, 6, 61, 18, 1, 218, 235, 234])
_DISC_SELL = bytes([51, 230, 133, 164, 1, 127, 131, 173])
_DISC_BUY_EXACT_SOL_IN = bytes([56, 252, 116, 8, 158, 223, 205, 95])


def _get_acct(accounts: List[str], ix_accounts: bytes, idx: int) -> str:
    if idx >= len(ix_accounts):
        return ""
    ai = ix_accounts[idx]
    if ai >= len(accounts):
        return ""
    return accounts[ai]


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
        if mint:
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


def parse_pumpfun_buy(
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
    if len(ix_accounts) < 7 or len(data) < 8:
        return None
    payload = data[8:]
    ta = struct.unpack_from("<Q", payload, 0)[0] if len(payload) >= 8 else 0
    sa = struct.unpack_from("<Q", payload, 8)[0] if len(payload) >= 16 else 0
    mint = _get_acct(accounts, ix_accounts, 2)
    if not mint:
        return None
    m = _meta(sig, slot, tx_index, recv_us)
    return DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            metadata=m,
            mint=mint,
            bonding_curve=_get_acct(accounts, ix_accounts, 3),
            user=_get_acct(accounts, ix_accounts, 6),
            sol_amount=sa,
            token_amount=ta,
            fee_recipient=_get_acct(accounts, ix_accounts, 1),
            is_buy=True,
            is_created_buy=mint in created_mints,
            ix_name="buy",
            mayhem_mode=mint in mayhem_mints,
            associated_bonding_curve=_get_acct(accounts, ix_accounts, 4),
            token_program=_token_program_default(_get_acct(accounts, ix_accounts, 8)),
            creator_vault=_get_acct(accounts, ix_accounts, 9),
        ),
    )


def parse_pumpfun_sell(
    data: bytes,
    accounts: List[str],
    ix_accounts: bytes,
    sig: str,
    slot: int,
    tx_index: int,
    recv_us: int,
) -> DexEvent | None:
    if len(ix_accounts) < 7 or len(data) < 8:
        return None
    payload = data[8:]
    ta = struct.unpack_from("<Q", payload, 0)[0] if len(payload) >= 8 else 0
    sa = struct.unpack_from("<Q", payload, 8)[0] if len(payload) >= 16 else 0
    mint = _get_acct(accounts, ix_accounts, 2)
    if not mint:
        return None
    m = _meta(sig, slot, tx_index, recv_us)
    return DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            metadata=m,
            mint=mint,
            bonding_curve=_get_acct(accounts, ix_accounts, 3),
            user=_get_acct(accounts, ix_accounts, 6),
            sol_amount=sa,
            token_amount=ta,
            fee_recipient=_get_acct(accounts, ix_accounts, 1),
            is_buy=False,
            is_created_buy=False,
            ix_name="sell",
            associated_bonding_curve=_get_acct(accounts, ix_accounts, 4),
            token_program=_token_program_default(_get_acct(accounts, ix_accounts, 9)),
            creator_vault=_get_acct(accounts, ix_accounts, 8),
        ),
    )


def parse_pumpfun_buy_exact_sol_in(
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
    if len(ix_accounts) < 7 or len(data) < 8:
        return None
    payload = data[8:]
    sa = struct.unpack_from("<Q", payload, 0)[0] if len(payload) >= 8 else 0
    ta = struct.unpack_from("<Q", payload, 8)[0] if len(payload) >= 16 else 0
    mint = _get_acct(accounts, ix_accounts, 2)
    if not mint:
        return None
    m = _meta(sig, slot, tx_index, recv_us)
    return DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            metadata=m,
            mint=mint,
            bonding_curve=_get_acct(accounts, ix_accounts, 3),
            user=_get_acct(accounts, ix_accounts, 6),
            sol_amount=sa,
            token_amount=ta,
            fee_recipient=_get_acct(accounts, ix_accounts, 1),
            is_buy=True,
            is_created_buy=mint in created_mints,
            ix_name="buy_exact_sol_in",
            mayhem_mode=mint in mayhem_mints,
            associated_bonding_curve=_get_acct(accounts, ix_accounts, 4),
            token_program=_token_program_default(_get_acct(accounts, ix_accounts, 8)),
            creator_vault=_get_acct(accounts, ix_accounts, 9),
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
    if disc == _DISC_BUY:
        return parse_pumpfun_buy(
            data, accounts, ix_accounts, sig, slot, tx_index, recv_us, created_mints, mayhem_mints
        )
    if disc == _DISC_SELL:
        return parse_pumpfun_sell(data, accounts, ix_accounts, sig, slot, tx_index, recv_us)
    if disc == _DISC_BUY_EXACT_SOL_IN:
        return parse_pumpfun_buy_exact_sol_in(
            data, accounts, ix_accounts, sig, slot, tx_index, recv_us, created_mints, mayhem_mints
        )
    return parse_pumpfun_instruction(data, accounts, sig, slot, tx_index, None, recv_us)
