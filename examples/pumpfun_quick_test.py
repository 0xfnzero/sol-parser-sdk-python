#!/usr/bin/env python3
"""Quick Test — 对齐最新 ``subscribe_dex_events`` 队列 API。

Run: ``python examples/pumpfun_quick_test.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import ClientConfig, Protocol, transaction_filter_for_protocols


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

    queue: asyncio.Queue[DexEvent] = await client.subscribe_dex_events([tx_filter], [])

    print("✅ Subscribing... (no event filter - will show ALL PumpFun events)")
    print("🎧 Listening for events... (waiting up to 60 seconds)\n")

    event_count = 0
    try:
        while event_count < 10:
            ev = await asyncio.wait_for(queue.get(), timeout=60.0)
            if not isinstance(ev, DexEvent) or not str(ev.type.value).startswith("PumpFun"):
                continue
            event_count += 1
            meta = getattr(ev.data, "metadata", None)
            slot = int(getattr(meta, "slot", 0) or 0) if meta else 0
            print(f"✅ Event #{event_count}: {ev.type.value} (slot={slot})")

        print(f"\n🎉 Received {event_count} events! Test successful!")
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
