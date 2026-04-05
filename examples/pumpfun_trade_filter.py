#!/usr/bin/env python3
"""
PumpFun Trade Event Filter Example

Demonstrates how to:
- Subscribe to PumpFun protocol events
- Filter specific trade types: Buy, Sell, BuyExactSolIn, Create
- Display trade details with latency metrics

Run: python examples/pumpfun_trade_filter.py
Or:  GEYSER_ENDPOINT=xxx GEYSER_API_TOKEN=yyy python examples/pumpfun_trade_filter.py
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

event_count = 0
buy_count = 0
sell_count = 0
buy_exact_count = 0
create_count = 0


def now_us() -> int:
    return int(time.time() * 1_000_000)


async def main():
    global event_count, buy_count, sell_count, buy_exact_count, create_count

    print("🚀 PumpFun Trade Event Filter Example")
    print("======================================\n")
    print(f"📡 Endpoint: {ENDPOINT}")
    print(f"🎯 Program: {PROGRAM_IDS[0]}\n")

    client = YellowstoneGrpc(ENDPOINT)
    if TOKEN:
        client.set_x_token(TOKEN)

    await client.connect()

    def on_update(update):
        global event_count, buy_count, sell_count, buy_exact_count, create_count

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig = tx_info.signature.hex()[:16] + "..."
        queue_recv_us = now_us()
        events = parse_logs_only(logs, sig, slot, None)

        for ev in events:
            key = next(iter(ev))
            if not key.startswith("PumpFun"):
                continue
            data = ev[key] or {}
            metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
            grpc_recv_us = metadata.get("grpc_recv_us", queue_recv_us)
            latency_us = queue_recv_us - grpc_recv_us
            event_count += 1

            if key in ("PumpFunBuy", "PumpFunBuyExactSolIn"):
                if key == "PumpFunBuy":
                    buy_count += 1
                    icon = "🟢"
                    label = "BUY"
                else:
                    buy_exact_count += 1
                    icon = "🟡"
                    label = "BUY_EXACT_SOL_IN"
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ {icon} PumpFun {label} #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                print(f"│ Mint       : {data.get('mint', 'N/A')}")
                print(f"│ SOL Amount : {data.get('sol_amount', 0)} lamports")
                print(f"│ Token Amt  : {data.get('token_amount', 0)}")
                print(f"│ User       : {data.get('user', 'N/A')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}")
                print("└─────────────────────────────────────────────────────────────\n")

            elif key == "PumpFunSell":
                sell_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🔴 PumpFun SELL #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                print(f"│ Mint       : {data.get('mint', 'N/A')}")
                print(f"│ SOL Amount : {data.get('sol_amount', 0)} lamports")
                print(f"│ Token Amt  : {data.get('token_amount', 0)}")
                print(f"│ User       : {data.get('user', 'N/A')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}")
                print("└─────────────────────────────────────────────────────────────\n")

            elif key == "PumpFunCreate":
                create_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🆕 PumpFun CREATE #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Slot       : {slot}")
                print(f"│ Name       : {data.get('name', 'N/A')}")
                print(f"│ Symbol     : {data.get('symbol', 'N/A')}")
                print(f"│ Mint       : {data.get('mint', 'N/A')}")
                print(f"│ Creator    : {data.get('creator', 'N/A')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Creates : {create_count}")
                print("└─────────────────────────────────────────────────────────────\n")

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
    print(f"✅ Subscribed (id={sub.id})")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        print(f"\n👋 Total: {event_count} events (Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count} Create={create_count})")


if __name__ == "__main__":
    asyncio.run(main())
