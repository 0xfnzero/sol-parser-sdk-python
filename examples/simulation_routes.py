"""python examples/simulation_routes.py saved-evidence.json [case-name]. No RPC.

Accepts {wire:base64,response:simulateTransactionResponse} or {cases:[...]}.
"""

import argparse
import base64
import json
from pathlib import Path
from sol_parser import analyze_simulation_routes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evidence", type=Path)
    ap.add_argument("case", nargs="?")
    args = ap.parse_args()
    data = json.loads(args.evidence.read_text())
    cases = [
        c
        for c in data.get("cases", [data])
        if args.case is None or c.get("name") == args.case
    ]
    if not cases:
        raise ValueError("Simulation case not found")
    for case in cases:
        route = analyze_simulation_routes(
            base64.b64decode(case["wire"], validate=True), case["response"]
        )
        print(json.dumps(dict(name=case.get("name"), route=route.to_dict())))


if __name__ == "__main__":
    main()
