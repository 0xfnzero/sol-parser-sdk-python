#!/usr/bin/env python3
"""
Multi-Protocol gRPC Example

Subscribe to multiple DEX protocols simultaneously:
PumpFun, PumpSwap, Raydium, Orca, Meteora, Bonk

Run: python examples/multi_protocol_grpc.py
Config: ``GRPC_URL`` / ``GRPC_TOKEN``, ``.env``, or CLI ``--grpc-url`` / ``--grpc-token``.
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import parse_logs_only
from sol_parser.env_config import parse_grpc_credentials
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import TransactionFilter, SubscribeCallbacks

PROGRAM_IDS = [
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # PumpFun
    "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ",  # PumpSwap
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM V4
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CLMM
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",  # Raydium CPMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",   # Orca Whirlpool
    "Eo7WjKq67rjJQDd1d4dSYkT7LeHVAaFL1K7dajEgrpwz",  # Meteora DAMM V2
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",   # Meteora DLMM
]

stats: dict[str, int] = {}


async def stats_reporter():
    while True:
        await asyncio.sleep(30)
        if not stats:
            continue
        print("\n📊 Event Statistics:")
        for k, v in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {k:<35}: {v}")
        print()


async def main():
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )
    print("🚀 Multi-Protocol gRPC Example")
    print("================================\n")
    print(f"📡 Endpoint: {endpoint}")
    print(f"📊 Protocols: PumpFun, PumpSwap, Raydium, Orca, Meteora\n")

    client = YellowstoneGrpc(endpoint)
    if token:
        client.set_x_token(token)

    await client.connect()
    asyncio.create_task(stats_reporter())

    def on_update(update):
        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig = tx_info.signature.hex()[:16] + "..."
        events = parse_logs_only(logs, sig, slot, None)

        for ev in events:
            key = next(iter(ev))
            stats[key] = stats.get(key, 0) + 1
            data = ev[key]
            s = json.dumps({key: data}, default=str)
            if len(s) > 200:
                s = s[:200] + "..."
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] {key}")
            print(f"  sig={sig} slot={slot}")
            if isinstance(data, dict):
                if data.get("mint"):
                    print(f"  mint : {data['mint']}")
                if data.get("pool"):
                    print(f"  pool : {data['pool']}")
                if data.get("user"):
                    print(f"  user : {data['user']}")
                if data.get("sol_amount") is not None:
                    print(f"  sol  : {data['sol_amount']} lamports")
            print()

    tx_filter = TransactionFilter(
        account_include=PROGRAM_IDS,
        account_exclude=[],
        account_required=[],
        vote=False,
        failed=False,
    )
    callbacks = SubscribeCallbacks(
        on_update=on_update,
        on_error=lambda e: print(f"Stream error: {e}", file=sys.stderr),
        on_end=lambda: print("Stream ended"),
    )

    sub = await client.subscribe_transactions(tx_filter, callbacks)
    print(f"✅ Subscribed (id={sub.id})")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        print("\n📊 Final Event Statistics:")
        for k, v in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {k:<35}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
