#!/usr/bin/env python3
"""
PumpSwap Low-Latency Example

Demonstrates:
- Subscribe to PumpSwap protocol events
- Measure end-to-end latency
- Per-event and periodic performance statistics

Run: python examples/pumpswap_low_latency.py
Config: ``GRPC_URL`` / ``GRPC_TOKEN``, ``.env``, or CLI flags (see ``parse_grpc_credentials``).
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
total_latency_us = 0
min_latency_us = float("inf")
max_latency_us = 0
last_report_count = 0


def now_us() -> int:
    return int(time.time() * 1_000_000)


async def stats_reporter():
    global last_report_count
    while True:
        await asyncio.sleep(10)
        if event_count == 0:
            continue
        events_in_window = event_count - last_report_count
        avg_us = int(total_latency_us / event_count) if event_count else 0
        min_l = int(min_latency_us) if min_latency_us != float("inf") else 0

        print("\n╔════════════════════════════════════════════════════╗")
        print("║          Performance Stats (10s window)            ║")
        print("╠════════════════════════════════════════════════════╣")
        print(f"║  Total Events : {event_count:>10}                              ║")
        print(f"║  Events/sec   : {events_in_window / 10:>10.1f}                              ║")
        print(f"║  Avg Latency  : {avg_us:>10} μs                           ║")
        print(f"║  Min Latency  : {min_l:>10} μs                           ║")
        print(f"║  Max Latency  : {int(max_latency_us):>10} μs                           ║")
        print("╚════════════════════════════════════════════════════╝\n")
        last_report_count = event_count


async def main():
    global event_count, total_latency_us, min_latency_us, max_latency_us

    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )
    print("🚀 PumpSwap Low-Latency Test")
    print("============================\n")
    print(f"📡 Endpoint: {endpoint}\n")

    client = YellowstoneGrpc(endpoint)
    if token:
        client.set_x_token(token)

    await client.connect()
    asyncio.create_task(stats_reporter())

    def on_update(update):
        global event_count, total_latency_us, min_latency_us, max_latency_us

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
            grpc_recv_us = metadata.get("grpc_recv_us", queue_recv_us)
            latency_us = queue_recv_us - grpc_recv_us

            event_count += 1
            total_latency_us += latency_us
            if latency_us < min_latency_us:
                min_latency_us = latency_us
            if latency_us > max_latency_us:
                max_latency_us = latency_us

            print(f"\n================================================")
            print(f"gRPC recv time : {grpc_recv_us} μs")
            print(f"Queue recv time: {queue_recv_us} μs")
            print(f"Latency        : {latency_us} μs")
            print(f"================================================")
            print(f"Event: {key}")
            if isinstance(data, dict):
                if data.get("pool"):
                    print(f"  pool : {data['pool']}")
                if data.get("user"):
                    print(f"  user : {data['user']}")
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


if __name__ == "__main__":
    asyncio.run(main())
