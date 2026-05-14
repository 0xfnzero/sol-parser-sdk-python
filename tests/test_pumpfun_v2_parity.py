from __future__ import annotations

import struct

from sol_parser.event_types import DexEvent, EventMetadata, PumpFunCreateV2TokenEvent, PumpFunTradeEvent
from sol_parser.grpc_types import EventType
from sol_parser.instructions import parse_pumpfun_instruction
from sol_parser.pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge


Z = "11111111111111111111111111111111"
BUY_V2_DISC = bytes([184, 23, 238, 97, 103, 197, 211, 61])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _u64_instruction(disc: bytes, first: int, second: int) -> bytes:
    return disc + struct.pack("<QQ", first, second)


def test_parse_pumpfun_buy_v2_uses_rust_account_indexes() -> None:
    ev = parse_pumpfun_instruction(
        _u64_instruction(BUY_V2_DISC, 123, 456),
        _accounts(27),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_TRADE
    assert isinstance(ev.data, PumpFunTradeEvent)
    t = ev.data
    assert t.ix_name == "buy_v2"
    assert t.mint == "account_1"
    assert t.fee_recipient == "account_6"
    assert t.bonding_curve == "account_10"
    assert t.associated_bonding_curve == "account_11"
    assert t.user == "account_13"
    assert t.token_program == "account_3"
    assert t.creator_vault == "account_16"
    assert t.token_amount == 123
    assert t.sol_amount == 456


def test_pumpfun_post_merge_enriches_create_v2_and_trade_flags() -> None:
    meta = EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=10)
    events = [
        DexEvent(
            type=EventType.PUMP_FUN_CREATE_V2,
            data=PumpFunCreateV2TokenEvent(
                metadata=meta,
                mint="mint",
                observed_fee_recipient="",
                is_cashback_enabled=True,
                is_mayhem_mode=True,
            ),
        ),
        DexEvent(
            type=EventType.PUMP_FUN_BUY,
            data=PumpFunTradeEvent(
                metadata=meta,
                mint="mint",
                fee_recipient="fee",
                is_buy=True,
                ix_name="buy_v2",
            ),
        ),
    ]

    enrich_pumpfun_same_tx_post_merge(events)

    create = events[0].data
    trade = events[1].data
    assert isinstance(create, PumpFunCreateV2TokenEvent)
    assert isinstance(trade, PumpFunTradeEvent)
    assert create.observed_fee_recipient == "fee"
    assert trade.mayhem_mode is True
    assert trade.is_cashback_coin is True
    assert trade.track_volume is True
