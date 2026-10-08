"""Real mainnet wire, execution amounts and compact/legacy account regressions."""

import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import (
    rpc_get_transaction_result_dict_to_response,
    parse_rpc_transaction,
)

CASES = json.loads(
    (Path(__file__).parent / "fixtures/pump_upgrade/mainnet.json").read_text()
)["cases"]

CASES += json.loads(
    (Path(__file__).parent / "fixtures/pump_upgrade/simulation_events.json").read_text()
)["cases"]


@pytest.mark.parametrize(
    "case", CASES, ids=lambda c: c.get("name", c["signature"][:12])
)
def test_mainnet_matches_official_idl_and_wire(case):
    raw = case["raw"]
    events, error = parse_rpc_transaction(
        rpc_get_transaction_result_dict_to_response(raw), case["signature"], None, 0
    )
    assert error is None
    if raw["meta"]["err"] is not None:
        assert events == []
        return
    for expected in case["expected"]:
        d = expected["data"]
        identity = "mint" if expected["name"] == "TradeEvent" else "pool"
        matches = [
            e.data
            for e in events
            if getattr(e.data, identity, None) == d[identity]
            and getattr(e.data, "user", None) == d["user"]
            and ("is_buy" not in d or getattr(e.data, "is_buy", None) == d["is_buy"])
            and (expected["name"] != "BuyEvent" or hasattr(e.data, "base_amount_out"))
            and (expected["name"] != "SellEvent" or hasattr(e.data, "base_amount_in"))
        ]
        assert len(matches) == 1
        actual = matches[0]
        for field, value in d.items():
            if field == "shareholders":
                continue
            got = getattr(actual, field)
            if field == "quote_mint" and value == "11111111111111111111111111111111":
                assert got in [
                    value,
                    "So11111111111111111111111111111111111111111",
                    "So11111111111111111111111111111111111111112",
                ]
            else:
                assert str(got) == str(value), field
