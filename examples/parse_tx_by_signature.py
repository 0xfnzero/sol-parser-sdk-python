#!/usr/bin/env python3
"""按签名从 RPC 拉取并解析 — 对齐 ``sol-parser-sdk/examples/parse_pump_tx.rs``。

Usage:
  TX_SIGNATURE=<sig> python examples/parse_tx_by_signature.py
  SOLANA_RPC_URL=https://api.mainnet-beta.solana.com TX_SIGNATURE=<sig> python examples/parse_tx_by_signature.py
  python examples/parse_tx_by_signature.py --rpc=https://api.mainnet-beta.solana.com --sig=<sig>

``.env``: ``RPC_URL`` / ``SOLANA_RPC_URL``、``TX_SIGNATURE``。CLI 覆盖环境变量。

使用 ``encoding: json``（或 ``jsonParsed``）以便从结构化 ``transaction`` 构建账户表并做与 gRPC 一致的账户补全；
若 RPC 仅返回 base64 交易数组则回退为仅日志解析（无补全）。
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import format_dex_event_json, parse_logs_only
from sol_parser.env_config import load_dotenv_silent, parse_rpc_and_tx_signature
from sol_parser.rpc_parser import (
    parse_rpc_transaction,
    rpc_get_transaction_result_dict_to_response,
)

DEFAULT_SIGNATURE = (
    "64srGF8CnTz9zPbdayWYmzs5aVRFBcfjDcidFVvBgAD25VMh52wr88vma7ytSbAZT3C5Giu5BPyGfNfLexLSrKhP"
)


def fetch_transaction(signature: str, rpc_url: str) -> dict | None:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "json", "maxSupportedTransactionVersion": 0},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"RPC error: {result['error']['message']}")
    return result.get("result")


def main() -> None:
    load_dotenv_silent()
    rpc_url, sig = parse_rpc_and_tx_signature(
        sys.argv[1:],
        default_signature=DEFAULT_SIGNATURE,
    )

    print("=== PumpFun Transaction Parser ===\n")
    print(f"Transaction Signature: {sig}\n")

    print(f"Connecting to: {rpc_url}")
    print("\n=== Parsing with sol-parser-sdk ===")
    print("Fetching and parsing transaction...\n")

    try:
        tx = fetch_transaction(sig, rpc_url)
    except Exception as e:
        print(f"✗ Failed to parse transaction: {e}", file=sys.stderr)
        print(
            "\nNote: If the error says 'Transaction not found (RPC returned null)', the tx may be pruned.",
            file=sys.stderr,
        )
        print(
            "Use an archive RPC (e.g. Helius, QuickNode) or set SOLANA_RPC_URL.",
            file=sys.stderr,
        )
        print(
            "Example: export SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY",
            file=sys.stderr,
        )
        sys.exit(1)

    if not tx or not tx.get("meta"):
        print("✗ Failed to parse transaction: Transaction not found", file=sys.stderr)
        print(
            "\nNote: If the error says 'Transaction not found (RPC returned null)', the tx may be pruned.",
            file=sys.stderr,
        )
        print(
            "Use an archive RPC (e.g. Helius, QuickNode) or set SOLANA_RPC_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    slot = tx.get("slot", 0)
    grpc_recv_us = int(time.time() * 1_000_000)

    rpc_resp = rpc_get_transaction_result_dict_to_response(tx)
    if rpc_resp is not None:
        events, err = parse_rpc_transaction(rpc_resp, sig, None, grpc_recv_us)
        if err:
            print(f"parse_rpc_transaction: {err}", file=sys.stderr)
            events = []
    else:
        logs = tx["meta"].get("logMessages", [])
        txi = tx.get("transactionIndex", tx.get("transaction_index"))
        tx_index = int(txi) if txi is not None else 0
        events = parse_logs_only(logs, sig, slot, None, tx_index=tx_index)

    print("✓ Parsing completed!")
    print(f"  Found {len(events)} DEX events\n")

    if not events:
        print("⚠ No DEX events found in this transaction.")
    else:
        print("=== Parsed Events (SDK Format) ===\n")
        for i, event in enumerate(events, 1):
            print(f"Event #{i}:")
            print(format_dex_event_json(event))
            print()

    print("\n=== Summary ===")
    print("✓ sol-parser-sdk successfully parsed the transaction!")
    print("  The new RPC parsing API supports:")
    print("  - Direct parsing from RPC (no gRPC streaming needed)")
    print("  - Inner instruction parsing (16-byte discriminators)")
    print("  - Account fill from transaction + meta when using structured JSON encoding")
    print("  - All 10 DEX protocols (including PumpFun)")
    print("  - Perfect for testing and validation")


if __name__ == "__main__":
    main()
