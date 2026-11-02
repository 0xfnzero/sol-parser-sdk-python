import json
import sys
from pathlib import Path
import pytest
from sol_parser import StockPriceTracker, screened_stock_catalog

sys.path.insert(0, str(Path(__file__).parents[1] / "examples"))
from replay_input import replay_events

CASES = json.loads(
    (Path(__file__).parent / "fixtures/stock_price_replay_20261020.json").read_text()
)["cases"]


@pytest.mark.parametrize(
    "case,expected",
    list(zip(CASES, [343.6402644024645, None, 904.3107197730765])),
)
def test_captured_stock_execution(case, expected):
    events = replay_events(case.get("rpc") or case.get("wire_rpc") or case.get("raw"))
    tracker = StockPriceTracker(screened_stock_catalog())
    prices = [p for e in events if (p := tracker.process(e, 1_000_000)) is not None]
    # The historical ABNB pool is excluded from default stock-price monitoring.
    assert len(prices) == (0 if expected is None else 1)
    if expected is None:
        return
    assert prices[0].price_usdc == pytest.approx(expected)
    assert prices[0].liquidity is None
    tracker.reset()
    assert all(tracker.process(e, 100_000_000) is None for e in events)
    for e in events:
        for key in ("input_vault_before", "output_vault_before", "sqrt_price_x64", "post_sqrt_price", "pool_base_token_reserves", "pool_quote_token_reserves"):
            if hasattr(e.data, key):
                setattr(e.data, key, 0)
    for e in events:
        if hasattr(e.data, "event_version"):
            e.data.event_version = 0
    assert all(tracker.process(e, 1_000_000) is None for e in events)


def test_catalog_owned_and_prices_opt_in():
    a, b = screened_stock_catalog(), screened_stock_catalog()
    a["pools"].clear()
    assert b["pools"]
    events = replay_events(
        CASES[0].get("rpc") or CASES[0].get("wire_rpc") or CASES[0].get("raw")
    )
    assert all(StockPriceTracker().process(e, 1_000_000) is None for e in events)
