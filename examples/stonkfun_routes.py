"""python examples/stonkfun_routes.py <getTransaction-base64.json>"""

import argparse
import json
from pathlib import Path
from sol_parser import analyze_rpc_transaction_routes, StonkFunPoolRegistry


def main():
    parser = argparse.ArgumentParser(
        description="Analyze compiled/base64 transaction execution evidence, without RPC"
    )
    parser.add_argument("transaction", type=Path)
    args = parser.parse_args()
    tx = json.loads(args.transaction.read_text())
    registry = StonkFunPoolRegistry()
    registry.observe_rpc_transaction(tx)
    route = analyze_rpc_transaction_routes(tx, registry.verified_cpmm_pools())
    print(json.dumps(route.to_dict(), indent=2))


if __name__ == "__main__":
    main()
