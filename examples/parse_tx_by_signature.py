#!/usr/bin/env python3
"""
Parse a Transaction from RPC by Signature

Fetches a specific transaction from Solana RPC and parses DEX events.

Usage:
  TX_SIGNATURE=<sig> python examples/parse_tx_by_signature.py
  RPC_URL=https://api.mainnet-beta.solana.com TX_SIGNATURE=<sig> python examples/parse_tx_by_signature.py
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import parse_logs_only

DEFAULT_SIGNATURE = "3zsihbygW7hoKGtduAyDDFzp4E1eis8gaBzEzzNKr8ma39baffpFcphok9wHFgR3EauDe9vYYsVf4Puh5pZ6UJiS"
RPC_URL = os.environ.get("RPC_URL", "https://api.mainnet-beta.solana.com")


def fetch_transaction(signature: str) -> dict | None:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
        ],
    }).encode()
    req = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"RPC error: {result['error']['message']}")
    return result.get("result")


def main():
    sig = os.environ.get("TX_SIGNATURE", DEFAULT_SIGNATURE)

    print("=== Transaction Parser ===\n")
    print(f"Signature: {sig}")
    print(f"RPC URL  : {RPC_URL}\n")

    print("Fetching transaction from RPC...")
    try:
        tx = fetch_transaction(sig)
    except Exception as e:
        print(f"Failed to fetch: {e}", file=sys.stderr)
        sys.exit(1)

    if not tx or not tx.get("meta"):
        print("Transaction not found. It may be too old or pruned.", file=sys.stderr)
        print("Use an archive RPC (e.g. Helius, QuickNode) or set RPC_URL.", file=sys.stderr)
        sys.exit(1)

    logs = tx["meta"].get("logMessages", [])
    slot = tx.get("slot", 0)
    print(f"Log messages: {len(logs)}\n")

    events = parse_logs_only(logs, sig, slot, None)

    if not events:
        print("No DEX events found in this transaction.")
        print("Try a PumpFun/PumpSwap/Raydium/Orca transaction signature.")
        return

    print(f"✅ Found {len(events)} DEX event(s):\n")
    for i, ev in enumerate(events, 1):
        key = next(iter(ev))
        print(f"Event #{i}: [{key}]")
        print(json.dumps(ev, indent=2, default=str))
        print()

    print("=== Summary ===")
    print("✅ sol-parser-sdk successfully parsed the transaction!")
    print("   - Direct parsing from RPC (no gRPC streaming needed)")
    print("   - All 10 DEX protocols supported")


if __name__ == "__main__":
    main()
