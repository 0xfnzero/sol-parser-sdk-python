#!/usr/bin/env python3
"""
Meteora DAMM V2 gRPC Streaming Example

Demonstrates how to:
- Subscribe to Meteora DAMM V2 protocol events via gRPC
- Filter specific event types: Swap, AddLiquidity, RemoveLiquidity, CreatePosition, ClosePosition
- Display event details with latency metrics

Run: GEYSER_API_TOKEN=your_token python examples/meteora_damm_grpc.py
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

# Meteora DAMM V2 program ID
PROGRAM_IDS = ["cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"]

event_count = 0
swap_count = 0
add_liquidity_count = 0
remove_liquidity_count = 0


def now_us() -> int:
    return int(time.time() * 1_000_000)


async def main():
    global event_count, swap_count, add_liquidity_count, remove_liquidity_count

    print("🚀 Meteora DAMM gRPC Streaming Example")
    print("========================================\n")
    print(f"📡 Endpoint: {ENDPOINT}")
    print(f"🎯 Program: {PROGRAM_IDS[0]}\n")

    client = YellowstoneGrpc(ENDPOINT)
    if TOKEN:
        client.set_x_token(TOKEN)
    await client.connect()

    def on_update(update):
        global event_count, swap_count, add_liquidity_count, remove_liquidity_count

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig = tx_info.signature.hex()
        now = now_us()
        events = parse_logs_only(logs, sig, slot, None)

        for ev in events:
            key = next(iter(ev))
            if not key.startswith("MeteoraDamm"):
                continue
            data = ev[key] or {}
            metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
            grpc_recv_us = metadata.get("grpc_recv_us", now)
            latency_us = now - grpc_recv_us
            event_count += 1

            if key == "MeteoraDammV2Swap":
                swap_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🔄 Meteora DAMM SWAP (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                if isinstance(data, dict):
                    for field, label in [
                        ("pool", "Pool"), ("amount_in", "Amount In"),
                        ("minimum_amount_out", "Min Out"), ("output_amount", "Actual Out"),
                        ("actual_amount_in", "Actual In"), ("lp_fee", "LP Fee"),
                        ("protocol_fee", "Protocol"), ("trade_direction", "Direction"),
                    ]:
                        if field in data:
                            print(f"│ {label:<11}: {data[field]}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Stats   : Swap={swap_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}")
                print("└─────────────────────────────────────────────────────────────\n")

            elif key == "MeteoraDammV2AddLiquidity":
                add_liquidity_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ ➕ Meteora DAMM ADD LIQUIDITY (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                if isinstance(data, dict):
                    for field, label in [
                        ("pool", "Pool"), ("position", "Position"),
                        ("token_a_amount", "Token A In"), ("token_b_amount", "Token B In"),
                    ]:
                        if field in data:
                            print(f"│ {label:<11}: {data[field]}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Stats   : Swap={swap_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}")
                print("└─────────────────────────────────────────────────────────────\n")

            elif key == "MeteoraDammV2RemoveLiquidity":
                remove_liquidity_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ ➖ Meteora DAMM REMOVE LIQUIDITY (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                if isinstance(data, dict):
                    for field, label in [
                        ("pool", "Pool"), ("position", "Position"),
                        ("token_a_amount", "Token A Out"), ("token_b_amount", "Token B Out"),
                    ]:
                        if field in data:
                            print(f"│ {label:<11}: {data[field]}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Stats   : Swap={swap_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}")
                print("└─────────────────────────────────────────────────────────────\n")

            else:
                # CreatePosition / ClosePosition
                print(f"[{key}] slot={slot} latency={latency_us}μs")
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k != "metadata":
                            print(f"  {k}: {v}")
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
    print(f"✅ gRPC client created (parser pre-warmed)")
    print(f"🎯 Event Filter: Swap, AddLiquidity, RemoveLiquidity, CreatePosition, ClosePosition")
    print(f"✅ Subscribed (id={sub.id})")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        print(f"\n👋 Total: {event_count} events (Swap={swap_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count})")


if __name__ == "__main__":
    asyncio.run(main())
