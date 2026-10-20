import json
from sol_parser.trade_source import (
    log_outer_indices,
    RawInstructionPayload,
    TradeParseStatus,
)
from sol_parser.event_types import PumpFunTradeEvent, to_typed_event, DexEvent
from sol_parser.grpc_types import EventType
from sol_parser.json_util import dex_event_json_dumps


def test_truncated_log_mapping_is_not_shifted():
    assert log_outer_indices(
        ["Program router invoke [1]", "Program data: x"], ["router", "router"]
    ) == [-1, -1]
    assert log_outer_indices(
        ["Program router invoke [1]", "Program data: x", "Program other invoke [1]"],
        ["router", "other"],
    ) == [0, 0, 1]


def test_source_json_roundtrip_preserves_unknown_accounts_and_status():
    raw = RawInstructionPayload(
        "router", 3, ["account", "account", None], [1, 1, 250], [255, 0, 3]
    )
    trade = PumpFunTradeEvent(
        third_program=raw, parse_status=TradeParseStatus.UNRESOLVED
    )
    encoded = json.loads(
        dex_event_json_dumps(DexEvent(EventType.PUMP_FUN_TRADE, trade))
    )
    restored = to_typed_event({encoded["type"]: encoded["data"]})
    assert restored.third_program == raw
    assert restored.parse_status is TradeParseStatus.UNRESOLVED


def test_other_dex_occurrence_mismatches_remain_unpaired():
    from sol_parser import event_types as events
    from sol_parser.log_instr_dedup import dedupe_log_instruction_events

    for name, field in (
        ("RaydiumClmmSwap", "pool_state"),
        ("RaydiumCpmmSwap", "pool_id"),
        ("OrcaWhirlpoolSwap", "whirlpool"),
        ("MeteoraDlmmSwap", "pool"),
        ("RaydiumLaunchlabTrade", "pool_state"),
    ):
        cls = getattr(events, name + "Event")
        for left, right in ((1, 2), (2, 1)):
            make = lambda: DexEvent(EventType(name), cls(**{field: "pool"}))
            result = dedupe_log_instruction_events(
                [make() for _ in range(left)], [make() for _ in range(right)]
            )
            assert len(result) == left + right, name
