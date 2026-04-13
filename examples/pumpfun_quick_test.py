#!/usr/bin/env python3
"""Quick Test — 对齐 ``sol-parser-sdk/examples/pumpfun_quick_test.rs``。

Run: ``python examples/pumpfun_quick_test.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

import base58

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import parse_logs_only
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import ClientConfig, Protocol, SubscribeCallbacks, transaction_filter_for_protocols


def _event_label(ev: DexEvent) -> str:
    t = ev.type.value
    if t.startswith("PumpFun"):
        return t
    return "Other"


async def main() -> None:
    load_dotenv_silent()
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )

    print("🚀 Quick Test - Subscribing to ALL PumpFun events...")

    config = ClientConfig.default()
    config.enable_metrics = True

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)

    protocols = [Protocol.PUMP_FUN]
    tx_filter = transaction_filter_for_protocols(protocols)
    tx_filter.vote = False
    tx_filter.failed = False

    print("✅ Subscribing... (no event filter - will show ALL events)")

    await client.connect()

    event_count = 0
    done = asyncio.Event()

    def on_update(update):
        nonlocal event_count

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sb = bytes(tx_info.signature) if tx_info.signature else b""
        sig = base58.b58encode(sb).decode("ascii") if len(sb) == 64 else ""

        for ev in parse_logs_only(
            logs, sig, slot, None, subscribe_tx_info=tx_info
        ):
            if not isinstance(ev, DexEvent):
                continue
            event_count += 1
            label = _event_label(ev)
            print(f"✅ Event #{event_count}: {label} (Queue: 0)")

            if event_count >= 10:
                print(f"\n🎉 Received {event_count} events! Test successful!")
                done.set()
                return

    await client.subscribe_transactions(
        tx_filter,
        SubscribeCallbacks(
            on_update=on_update,
            on_error=lambda e: print(f"Stream error: {e}", file=sys.stderr),
            on_end=lambda: done.set(),
        ),
    )

    print("🎧 Listening for events... (waiting up to 60 seconds)\n")

    try:
        await asyncio.wait_for(done.wait(), timeout=60.0)
    except asyncio.TimeoutError:
        if event_count == 0:
            print("⏰ Timeout: No events received in 60 seconds.")
            print("   This might indicate:")
            print("   - Network connectivity issues")
            print("   - gRPC endpoint is down")
            print("   - Very low market activity (rare)")
        else:
            print(f"\n✅ Received {event_count} events in 60 seconds")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
