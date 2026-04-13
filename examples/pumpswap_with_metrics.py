#!/usr/bin/env python3
"""
PumpSwap Event Parsing with Detailed Performance Metrics

Demonstrates how to:
- Subscribe to PumpSwap protocol events
- Measure end-to-end latency per event
- Display periodic 10s summaries (total count, rate, avg/min/max latency)

Run: python examples/pumpswap_with_metrics.py  (``GRPC_URL`` / ``GRPC_TOKEN`` or ``.env``)
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import parse_logs_only
from sol_parser.env_config import parse_grpc_credentials
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import TransactionFilter, SubscribeCallbacks

PROGRAM_IDS = ["pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ"]  # PumpSwap

event_count = 0
total_latency = 0
min_latency = float("inf")
max_latency = 0
last_count = 0


def now_us() -> int:
    return int(time.time() * 1_000_000)


async def stats_reporter():
    global last_count
    while True:
        await asyncio.sleep(10)
        if event_count == 0:
            continue
        avg = total_latency // event_count if event_count > 0 else 0
        rate = (event_count - last_count) / 10.0
        min_us = 0 if min_latency == float("inf") else min_latency
        print("\n╔════════════════════════════════════════════════════╗")
        print("║      PumpSwap Performance Stats (10s window)       ║")
        print("╠════════════════════════════════════════════════════╣")
        print(f"║  Total Events : {event_count:>10}                              ║")
        print(f"║  Events/sec   : {rate:>10.1f}                              ║")
        print(f"║  Avg Latency  : {avg:>10} μs                           ║")
        print(f"║  Min Latency  : {min_us:>10} μs                           ║")
        print(f"║  Max Latency  : {max_latency:>10} μs                           ║")
        print("╚════════════════════════════════════════════════════╝\n")
        last_count = event_count


async def main():
    global event_count, total_latency, min_latency, max_latency

    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )
    print("PumpSwap event parsing with detailed performance metrics")
    print("🚀 Subscribing to Yellowstone gRPC (PumpSwap)...")
    print(f"📡 Endpoint: {endpoint}\n")

    client = YellowstoneGrpc(endpoint)
    if token:
        client.set_x_token(token)
    await client.connect()

    asyncio.create_task(stats_reporter())

    def on_update(update):
        global event_count, total_latency, min_latency, max_latency

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig = tx_info.signature.hex()
        queue_recv_us = now_us()
        events = parse_logs_only(logs, sig, slot, None)

        for ev in events:
            key = next(iter(ev))
            if not key.startswith("PumpSwap"):
                continue
            data = ev[key] or {}
            metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
            grpc_recv_us = metadata.get("grpc_recv_us", 0)
            latency_us = queue_recv_us - grpc_recv_us if grpc_recv_us > 0 else 0

            event_count += 1
            total_latency += latency_us
            if latency_us < min_latency:
                min_latency = latency_us
            if latency_us > max_latency:
                max_latency = latency_us

            print(f"\n================================================")
            print(f"gRPC recv time : {grpc_recv_us} μs")
            print(f"Queue recv time: {queue_recv_us} μs")
            print(f"Latency        : {latency_us} μs")
            print(f"================================================")
            print(f"Event: {key}")
            if isinstance(data, dict):
                for field in ("pool", "user", "base_mint", "quote_mint",
                              "base_amount_out", "quote_amount_in",
                              "base_amount_in", "quote_amount_out"):
                    if field in data:
                        print(f"  {field}: {data[field]}")
            print()

    def on_error(err):
        print(f"Stream error: {err}", file=sys.stderr)

    def on_end():
        print("Stream ended")

    tx_filter = TransactionFilter(
        account_include=PROGRAM_IDS,
        account_exclude=[],
        account_required=[],
        vote=False,
        failed=False,
    )
    callbacks = SubscribeCallbacks(on_update=on_update, on_error=on_error, on_end=on_end)

    sub = await client.subscribe_transactions(tx_filter, callbacks)
    print("✅ gRPC client created successfully")
    print("📋 Event Filter: Buy, Sell, CreatePool, LiquidityAdded, LiquidityRemoved")
    print(f"✅ Subscribed (id={sub.id})")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        print("\n👋 Shutting down gracefully...")


if __name__ == "__main__":
    asyncio.run(main())
