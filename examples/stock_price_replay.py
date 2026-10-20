"""Replay saved stock trades; --fixture FILE replaces the bundled capture."""

import json
from dataclasses import asdict
from pathlib import Path
from sol_parser import StockPriceTracker, screened_stock_catalog
from replay_input import load_cases, replay_events


def main():
    tracker = StockPriceTracker(screened_stock_catalog())
    for case in load_cases(
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/stock_price_replay_20261020.json"
    ):
        tracker.reset()
        prices = [
            asdict(price)
            for event in replay_events(case["rpc"])
            if (price := tracker.process(event, 1_000_000)) is not None
        ]
        print(
            json.dumps(
                dict(
                    name=case.get("name"),
                    signature=case.get("signature"),
                    replay=True,
                    prices=prices,
                )
            )
        )


if __name__ == "__main__":
    main()
