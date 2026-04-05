#!/usr/bin/env python3
"""
PumpFun Quick Test

Quick connection test - subscribes to ALL PumpFun events,
prints the first 10, then exits.

Run: GEYSER_API_TOKEN=your_token python examples/pumpfun_quick_test.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import parse_logs_only
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import TransactionFilter, SubscribeCallbacks

ENDPOINT = os.environ.get("GEYSER_ENDPOINT", "solana-yellowstone-grpc.publicnode.com:443")
TOKEN = os.environ.get("GEYSER_API_TOKEN", "")

PROGRAM_IDS = ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]  # PumpFun


async def main():
    print("🚀 Quick Test - Subscribing to ALL PumpFun events...")
    print(f"📡 Endpoint: {ENDPOINT}\n")

    client = YellowstoneGrpc(ENDPOINT)
    if TOKEN:
        client.set_x_token(TOKEN)
    await client.connect()

    event_count = 0
    start_time = time.time()
    stop_event = asyncio.Event()

    def on_update(update):
        nonlocal event_count

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig = tx_info.signature.hex()
        events = parse_logs_only(logs, sig, slot, None)

        for ev in events:
            key = next(iter(ev))
            if not key.startswith("PumpFun"):
                continue
            event_count += 1
            print(f"✅ Event #{event_count}: {key} (slot={slot})")

            if event_count >= 10:
                print(f"\n🎉 Received {event_count} events! Test successful!")
                stop_event.set()
                return

        if time.time() - start_time > 60:
            if event_count == 0:
                print("⏰ Timeout: No events received in 60 seconds.")
                print("   This might indicate:")
                print("   - Network connectivity issues")
                print("   - gRPC endpoint is down")
                print("   - Missing or invalid API token")
            else:
                print(f"\n✅ Received {event_count} events in 60 seconds")
            stop_event.set()

    def on_error(err):
        print(f"Stream error: {err}", file=sys.stderr)
        stop_event.set()

    def on_end():
        print("Stream ended")
        stop_event.set()

    tx_filter = TransactionFilter(
        account_include=PROGRAM_IDS,
        account_exclude=[],
        account_required=[],
        vote=False,
        failed=False,
    )
    callbacks = SubscribeCallbacks(on_update=on_update, on_error=on_error, on_end=on_end)

    print("✅ Subscribing... (no event filter - will show ALL events)")
    print("🎧 Listening for events... (waiting up to 60 seconds)\n")

    sub = await client.subscribe_transactions(tx_filter, callbacks)
    print(f"✅ Connected. Waiting for PumpFun events...\n")

    await stop_event.wait()
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
