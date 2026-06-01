import struct

from sol_parser.dex_parsers import Z
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.shredstream_client import (
    _filter_parsed_event,
    _should_parse_shred_instructions,
    _static_ix_account_strings,
)
from sol_parser.shredstream_pumpfun import parse_pumpfun_shred_ix


PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
BUY_DISC = bytes([102, 6, 61, 18, 1, 218, 235, 234])
SELL_DISC = bytes([51, 230, 133, 164, 1, 127, 131, 173])
BUY_EXACT_SOL_IN_DISC = bytes([56, 252, 116, 8, 158, 223, 205, 95])
BUY_V2_DISC = bytes([184, 23, 238, 97, 103, 197, 211, 61])
SELL_V2_DISC = bytes([93, 246, 130, 60, 231, 233, 64, 178])
BUY_EXACT_QUOTE_IN_V2_DISC = bytes([194, 171, 28, 70, 104, 77, 91, 47])


def _push_string(out: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    out.extend(struct.pack("<I", len(encoded)))
    out.extend(encoded)


def _create_data() -> bytes:
    out = bytearray(bytes([24, 30, 200, 40, 5, 28, 7, 119]))
    _push_string(out, "Alt Coin")
    _push_string(out, "ALT")
    _push_string(out, "https://example.invalid/alt.json")
    out.extend(bytes(range(32)))
    return bytes(out)


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _ix_data(disc: bytes, first: int = 111, second: int = 222) -> bytes:
    return disc + struct.pack("<QQ", first, second)


def _parse(disc: bytes, ix_account_count: int):
    return parse_pumpfun_shred_ix(
        _ix_data(disc),
        _accounts(32),
        bytes(range(ix_account_count)),
        PUMPFUN_PROGRAM_ID,
        "sig",
        1,
        0,
        10,
        set(),
        set(),
    )


def test_pumpfun_shred_legacy_trade_event_types_match_rust() -> None:
    assert _parse(BUY_DISC, 16).type == EventType.PUMP_FUN_BUY
    assert _parse(SELL_DISC, 14).type == EventType.PUMP_FUN_SELL
    assert _parse(BUY_EXACT_SOL_IN_DISC, 16).type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN


def test_pumpfun_shred_v2_short_accounts_best_effort() -> None:
    buy = _parse(BUY_V2_DISC, 2)
    assert buy is not None
    assert buy.type == EventType.PUMP_FUN_BUY
    assert buy.data.mint == "account_1"

    exact_quote = _parse(BUY_EXACT_QUOTE_IN_V2_DISC, 2)
    assert exact_quote is not None
    assert exact_quote.type == EventType.PUMP_FUN_BUY
    assert exact_quote.data.spendable_quote_in == 111
    assert exact_quote.data.min_tokens_out == 222

    sell = _parse(SELL_V2_DISC, 2)
    assert sell is not None
    assert sell.type == EventType.PUMP_FUN_SELL
    assert sell.data.mint == "account_1"


def test_shredstream_static_account_mapping_defaults_alt_loaded_accounts() -> None:
    assert _static_ix_account_strings(["a", "b"], bytes([0, 1])) == ["a", "b"]
    assert _static_ix_account_strings(["a", "b"], bytes([0, 2])) == ["a", Z]


def test_pumpfun_shred_create_uses_instruction_order_accounts() -> None:
    ev = parse_pumpfun_shred_ix(
        _create_data(),
        _accounts(12),
        bytes([5, 1, 3, 2, 6, 7, 8, 11, 10, 4]),
        PUMPFUN_PROGRAM_ID,
        "sig",
        1,
        0,
        10,
        set(),
        set(),
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_CREATE
    assert ev.data.mint == "account_5"
    assert ev.data.bonding_curve == "account_3"
    assert ev.data.user == "account_11"


def test_shredstream_filter_applies_to_pumpfun_fast_path() -> None:
    ev = _parse(BUY_DISC, 16)
    assert ev is not None
    assert _filter_parsed_event(ev, IncludeOnlyFilter([EventType.PUMP_FUN_SELL])) is None
    assert _filter_parsed_event(ev, IncludeOnlyFilter([EventType.PUMP_FUN_TRADE])) is ev
    assert not _should_parse_shred_instructions(
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_GLOBAL])
    )
    assert not _should_parse_shred_instructions(IncludeOnlyFilter([]))
