import json
from pathlib import Path
from sol_parser.pump_upgrade import (
    parse_pump_upgrade_event,
    decode_pump_multi_hop_intent,
)
from sol_parser.inner_instruction_parser import parse_inner_instruction


def test_official_event_and_cpi_layouts():
    f = json.loads(
        (Path(__file__).parent / "fixtures/pump_upgrade/events.json").read_text()
    )
    for e in f:
        raw = bytes.fromhex(e["body"])
        n = e["disc"]
        meta = {}
        parsed = parse_pump_upgrade_event(n, raw, meta, e["program"])
        assert parsed is not None
        for k, v in e["values"].items():
            assert getattr(parsed.data, k) == v
        assert parse_pump_upgrade_event(n, raw[:-1], meta, e["program"]) is None
        assert parse_pump_upgrade_event(n, raw, meta, "bad") is None
        cpi = (
            bytes([228, 69, 165, 46, 81, 203, 154, 29]) + n.to_bytes(8, "little") + raw
        )
        assert parse_inner_instruction(cpi, e["program"], meta, None, False) is not None
    assert (
        parse_pump_upgrade_event(619296439455019615, bytes(104), {}).data.quote_mint
        == "So11111111111111111111111111111111111111112"
    )


def test_distinct_route_venues_are_retained():
    from sol_parser.event_types import DexEvent, PumpSwapSellEvent
    from sol_parser.grpc_types import EventType
    from sol_parser.merger import try_merge_dex_events

    a = DexEvent(EventType.PUMP_SWAP_SELL, PumpSwapSellEvent(pool="a"))
    b = DexEvent(EventType.PUMP_SWAP_SELL, PumpSwapSellEvent(pool="b"))
    assert not try_merge_dex_events(a, b)
