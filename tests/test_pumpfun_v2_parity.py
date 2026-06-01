from __future__ import annotations

import struct

import base58

from sol_parser.event_types import DexEvent, EventMetadata, PumpFunCreateV2TokenEvent, PumpFunTradeEvent
from sol_parser.grpc_types import EventType
from sol_parser.instructions import parse_pumpfun_instruction
from sol_parser.pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge


Z = "11111111111111111111111111111111"
BUY_DISC = bytes([102, 6, 61, 18, 1, 218, 235, 234])
SELL_DISC = bytes([51, 230, 133, 164, 1, 127, 131, 173])
CREATE_V2_DISC = bytes([214, 144, 76, 236, 95, 139, 49, 180])
BUY_EXACT_SOL_IN_DISC = bytes([56, 252, 116, 8, 158, 223, 205, 95])
BUY_V2_DISC = bytes([184, 23, 238, 97, 103, 197, 211, 61])
BUY_EXACT_QUOTE_IN_V2_DISC = bytes([194, 171, 28, 70, 104, 77, 91, 47])
SELL_V2_DISC = bytes([93, 246, 130, 60, 231, 233, 64, 178])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _u64_instruction(disc: bytes, first: int, second: int) -> bytes:
    return disc + struct.pack("<QQ", first, second)


def _pk(seed: int) -> bytes:
    return bytes((seed + i) & 0xFF for i in range(32))


def _push_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _create_v2_instruction(mayhem: bool, cashback: bool) -> bytes:
    return b"".join(
        [
            CREATE_V2_DISC,
            _push_string("name"),
            _push_string("SYM"),
            _push_string("uri"),
            _pk(120),
            b"\x01" if mayhem else b"\x00",
            b"\x01" if cashback else b"\x00",
        ]
    )


def test_parse_pumpfun_create_v2_reads_official_args_and_accounts() -> None:
    ev = parse_pumpfun_instruction(
        _create_v2_instruction(True, True),
        _accounts(16),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_CREATE_V2
    assert isinstance(ev.data, PumpFunCreateV2TokenEvent)
    create = ev.data
    assert create.mint == "account_0"
    assert create.bonding_curve == "account_2"
    assert create.user == "account_5"
    assert create.creator == base58.b58encode(_pk(120)).decode("ascii")
    assert create.is_mayhem_mode is True
    assert create.is_cashback_enabled is True


def test_parse_pumpfun_legacy_buy_exact_and_sell_instruction_parity() -> None:
    buy = parse_pumpfun_instruction(
        _u64_instruction(BUY_DISC, 111, 222),
        _accounts(18),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert buy is not None
    assert buy.type == EventType.PUMP_FUN_BUY
    assert isinstance(buy.data, PumpFunTradeEvent)
    t = buy.data
    assert t.ix_name == "buy"
    assert t.mint == "account_2"
    assert t.fee_recipient == "account_1"
    assert t.token_program == "account_8"
    assert t.creator_vault == "account_9"
    assert t.bonding_curve_v2 == "account_16"
    assert t.buyback_fee_recipient == "account_17"
    assert t.amount == 111
    assert t.max_sol_cost == 222

    exact = parse_pumpfun_instruction(
        _u64_instruction(BUY_EXACT_SOL_IN_DISC, 333, 444),
        _accounts(16),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert exact is not None
    assert exact.type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN
    assert isinstance(exact.data, PumpFunTradeEvent)
    t = exact.data
    assert t.ix_name == "buy_exact_sol_in"
    assert t.spendable_sol_in == 333
    assert t.min_tokens_out == 444
    assert t.amount == 444

    sell = parse_pumpfun_instruction(
        _u64_instruction(SELL_DISC, 555, 666),
        _accounts(17),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert sell is not None
    assert sell.type == EventType.PUMP_FUN_SELL
    assert isinstance(sell.data, PumpFunTradeEvent)
    t = sell.data
    assert t.ix_name == "sell"
    assert t.mint == "account_2"
    assert t.creator_vault == "account_8"
    assert t.token_program == "account_9"
    assert t.user_volume_accumulator == "account_14"
    assert t.bonding_curve_v2 == "account_15"
    assert t.buyback_fee_recipient == "account_16"
    assert t.amount == 555
    assert t.min_sol_output == 666


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
    assert ev.type == EventType.PUMP_FUN_BUY
    assert isinstance(ev.data, PumpFunTradeEvent)
    t = ev.data
    assert t.ix_name == "buy"
    assert t.mint == "account_1"
    assert t.fee_recipient == "account_6"
    assert t.bonding_curve == "account_10"
    assert t.associated_bonding_curve == "account_11"
    assert t.user == "account_13"
    assert t.token_program == "account_3"
    assert t.creator_vault == "account_16"
    assert t.token_amount == 123
    assert t.sol_amount == 456


def test_parse_pumpfun_buy_exact_quote_in_v2_uses_quote_amount_fields() -> None:
    ev = parse_pumpfun_instruction(
        _u64_instruction(BUY_EXACT_QUOTE_IN_V2_DISC, 777, 888),
        _accounts(27),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_BUY
    assert isinstance(ev.data, PumpFunTradeEvent)
    t = ev.data
    assert t.ix_name == "buy_exact_quote_in"
    assert t.amount == 888
    assert t.max_sol_cost == 0
    assert t.quote_amount == 777
    assert t.spendable_quote_in == 777
    assert t.min_tokens_out == 888
    assert t.quote_mint == "account_2"


def test_parse_pumpfun_sell_v2_returns_sell_event_type() -> None:
    ev = parse_pumpfun_instruction(
        _u64_instruction(SELL_V2_DISC, 333, 444),
        _accounts(26),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_SELL
    assert isinstance(ev.data, PumpFunTradeEvent)
    t = ev.data
    assert t.ix_name == "sell"
    assert t.amount == 333
    assert t.min_sol_output == 444
    assert t.max_sol_cost == 0


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
                ix_name="buy",
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
