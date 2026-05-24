from sol_parser.event_types import DexEvent, PumpFunTradeEvent
from sol_parser.grpc_types import EventType
from sol_parser.log_instr_dedup import dedupe_log_instruction_events


Z = "11111111111111111111111111111111"


def test_dedupe_keeps_log_trade_values_and_fills_instruction_fields():
    log_event = DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            mint="Mint111111111111111111111111111111111111",
            user="User111111111111111111111111111111111111",
            is_buy=True,
            sol_amount=50,
            token_amount=10,
            fee_recipient=Z,
            bonding_curve=Z,
            associated_bonding_curve=Z,
            token_program=Z,
            creator_vault=Z,
            creator=Z,
        ),
    )
    ix_event = DexEvent(
        type=EventType.PUMP_FUN_BUY,
        data=PumpFunTradeEvent(
            mint="Mint111111111111111111111111111111111111",
            user="User111111111111111111111111111111111111",
            is_buy=True,
            sol_amount=999,
            token_amount=999,
            fee_recipient="Fee1111111111111111111111111111111111111",
            bonding_curve="Curve11111111111111111111111111111111111",
            associated_bonding_curve="Assoc11111111111111111111111111111111111",
            token_program="Token11111111111111111111111111111111111",
            creator_vault="Vault11111111111111111111111111111111111",
            is_created_buy=True,
        ),
    )

    out = dedupe_log_instruction_events([log_event], [ix_event])

    assert len(out) == 1
    trade = out[0].data
    assert trade.sol_amount == 50
    assert trade.fee_recipient == "Fee1111111111111111111111111111111111111"
    assert trade.bonding_curve == "Curve11111111111111111111111111111111111"
    assert trade.is_created_buy is True


def test_dedupe_keeps_v2_buy_lanes_distinct_when_occurrence_order_differs():
    base = dict(
        mint="Mint222222222222222222222222222222222222",
        user="User222222222222222222222222222222222222",
        is_buy=True,
        sol_amount=1,
        token_amount=1,
        bonding_curve=Z,
    )
    buy_log = DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(**base, ix_name="buy_v2"),
    )
    exact_log = DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(**base, ix_name="buy_exact_quote_in_v2"),
    )
    exact_ix_data = dict(base)
    exact_ix_data["bonding_curve"] = "ExactCurve2222222222222222222222222222222"
    exact_ix = DexEvent(
        type=EventType.PUMP_FUN_BUY,
        data=PumpFunTradeEvent(
            **exact_ix_data,
            ix_name="buy_exact_quote_in_v2",
        ),
    )
    buy_ix_data = dict(base)
    buy_ix_data["bonding_curve"] = "BuyCurve22222222222222222222222222222222"
    buy_ix = DexEvent(
        type=EventType.PUMP_FUN_BUY,
        data=PumpFunTradeEvent(
            **buy_ix_data,
            ix_name="buy_v2",
        ),
    )

    out = dedupe_log_instruction_events([buy_log, exact_log], [exact_ix, buy_ix])

    assert len(out) == 2
    assert out[0].data.bonding_curve == "BuyCurve22222222222222222222222222222222"
    assert out[1].data.bonding_curve == "ExactCurve2222222222222222222222222222222"
