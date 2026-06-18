from __future__ import annotations

import base58
import struct

from sol_parser.event_types import (
    EventType,
    PumpFeesResetFeeSharingConfigEvent,
    PumpFeesUpdateFeeSharesEvent,
)
from sol_parser.instructions import parse_pump_fees_instruction


UPDATE_FEE_SHARES_IX = bytes([189, 13, 136, 99, 187, 164, 237, 35])
UPDATE_FEE_SHARES_V2_IX = bytes([111, 251, 49, 6, 78, 78, 106, 18])
RESET_FEE_SHARING_IX = bytes([10, 2, 182, 95, 16, 127, 129, 186])
RESET_FEE_SHARING_V2_IX = bytes([169, 245, 17, 209, 94, 91, 248, 128])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _update_fee_shares_data(disc: bytes) -> bytes:
    return disc + struct.pack("<I", 1) + bytes([42]) * 32 + struct.pack("<H", 2500)


def test_parse_pump_fees_update_fee_shares_v1_v2_instruction_layout() -> None:
    for disc in (UPDATE_FEE_SHARES_IX, UPDATE_FEE_SHARES_V2_IX):
        ev = parse_pump_fees_instruction(_update_fee_shares_data(disc), _accounts(8), "sig", 1, 0, None, 10)
        assert ev is not None
        assert ev.type == EventType.PUMP_FEES_UPDATE_FEE_SHARES
        assert isinstance(ev.data, PumpFeesUpdateFeeSharesEvent)
        assert ev.data.mint == "account_4"
        assert ev.data.sharing_config == "account_5"
        assert ev.data.admin == "account_2"
        assert ev.data.bonding_curve == "account_6"
        assert ev.data.pump_creator_vault == "account_7"
        assert ev.data.new_shareholders[0].address == base58.b58encode(bytes([42]) * 32).decode("ascii")
        assert ev.data.new_shareholders[0].share_bps == 2500


def test_parse_pump_fees_reset_fee_sharing_v1_v2_idl_account_order() -> None:
    for disc in (RESET_FEE_SHARING_IX, RESET_FEE_SHARING_V2_IX):
        ev = parse_pump_fees_instruction(disc, _accounts(7), "sig", 1, 0, None, 10)
        assert ev is not None
        assert ev.type == EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG
        assert isinstance(ev.data, PumpFeesResetFeeSharingConfigEvent)
        assert ev.data.new_admin == "account_0"
        assert ev.data.old_admin == "account_3"
        assert ev.data.mint == "account_5"
        assert ev.data.sharing_config == "account_6"
