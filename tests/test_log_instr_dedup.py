from sol_parser.event_types import (
    DexEvent,
    PumpFunCreateEvent,
    PumpFunCreateV2TokenEvent,
    PumpFunTradeEvent,
)
from sol_parser.grpc_types import EventType
from sol_parser.log_instr_dedup import dedupe_log_instruction_events
from sol_parser.event_types import RaydiumClmmSwapEvent


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


def test_dedupe_collapses_pumpfun_create_and_create_v2_by_mint():
    log_event = DexEvent(
        type=EventType.PUMP_FUN_CREATE,
        data=PumpFunCreateEvent(
            mint="Mint333333333333333333333333333333333333",
            name="Log Name",
            symbol="LOG",
            uri="https://log.example/token.json",
            bonding_curve=Z,
            user=Z,
            creator=Z,
            token_program=Z,
            quote_mint=Z,
            quote_vault=Z,
            quote_token_program=Z,
            virtual_quote_reserves=0,
        ),
    )
    ix_event = DexEvent(
        type=EventType.PUMP_FUN_CREATE_V2,
        data=PumpFunCreateV2TokenEvent(
            mint="Mint333333333333333333333333333333333333",
            name="",
            symbol="",
            uri="",
            bonding_curve="Curve333333333333333333333333333333333333",
            user="User333333333333333333333333333333333333",
            creator="Creator3333333333333333333333333333333333",
            token_program="Token33333333333333333333333333333333333",
            quote_mint="Quote33333333333333333333333333333333333",
            quote_vault="Vault33333333333333333333333333333333333",
            quote_token_program="QToken333333333333333333333333333333333",
            timestamp=456,
            virtual_token_reserves=1,
            virtual_sol_reserves=2,
            real_token_reserves=3,
            token_total_supply=4,
            virtual_quote_reserves=123,
            is_mayhem_mode=True,
            is_cashback_enabled=True,
        ),
    )

    out = dedupe_log_instruction_events([log_event], [ix_event])

    assert len(out) == 1
    assert out[0].type == EventType.PUMP_FUN_CREATE
    create = out[0].data
    assert isinstance(create, PumpFunCreateEvent)
    assert create.name == "Log Name"
    assert create.bonding_curve == "Curve333333333333333333333333333333333333"
    assert create.quote_vault == "Vault33333333333333333333333333333333333"
    assert create.timestamp == 456
    assert create.token_total_supply == 4
    assert create.virtual_quote_reserves == 123
    assert create.is_mayhem_mode is True
    assert create.is_cashback_enabled is True
def _clmm_swap(zero_for_one: bool, amount_0: int) -> DexEvent:
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_SWAP,
        data=RaydiumClmmSwapEvent(
            pool_state="clmm-pool",
            zero_for_one=zero_for_one,
            amount_0=amount_0,
        ),
    )


def test_clmm_dedup_ignores_instruction_placeholder_direction() -> None:
    out = dedupe_log_instruction_events(
        [_clmm_swap(False, 123)],
        [_clmm_swap(True, 0)],
    )

    assert len(out) == 1
    assert out[0].data.amount_0 == 123
    assert out[0].data.zero_for_one is False


def test_clmm_same_pool_occurrences_are_retained() -> None:
    out = dedupe_log_instruction_events(
        [_clmm_swap(False, 1), _clmm_swap(True, 2)],
        [_clmm_swap(True, 0), _clmm_swap(False, 0)],
    )

    assert len(out) == 2
