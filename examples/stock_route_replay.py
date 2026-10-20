"""Replay real multihop evidence without restricting the conversion DEX by launch platform."""

import json
from pathlib import Path
from sol_parser import (
    analyze_rpc_transaction_routes,
    screened_stock_catalog,
    stock_conversion_legs,
)
from replay_input import load_cases


def main():
    catalog = screened_stock_catalog()
    for case in load_cases(
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/cross_dex_stock_routes_20261020.json"
    ):
        route = analyze_rpc_transaction_routes(case["rpc"]).to_dict()
        print(
            json.dumps(
                dict(
                    name=case.get("name"),
                    signature=case.get("signature"),
                    replay=True,
                    route=route,
                    conversion_legs=stock_conversion_legs(catalog, route),
                )
            )
        )


if __name__ == "__main__":
    main()
