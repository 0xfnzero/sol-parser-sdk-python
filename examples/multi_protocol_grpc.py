#!/usr/bin/env python3
"""多协议 gRPC — Program ID 与 ``sol-parser-sdk/src/grpc/program_ids.rs`` / ``Protocol`` 枚举对齐。

Run: ``python examples/multi_protocol_grpc.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import format_dex_event_json
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    ClientConfig,
    OrderMode,
    Protocol,
    account_filter_for_protocols,
    transaction_filter_for_protocols,
)

# 与 Rust ``PROTOCOL_PROGRAM_IDS`` 覆盖范围一致（不含 Orca 等未在 Protocol 中的程序）
PROTOCOLS = [
    Protocol.PUMP_FUN,
    Protocol.PUMP_SWAP,
    Protocol.RAYDIUM_LAUNCHLAB,
    Protocol.RAYDIUM_CPMM,
    Protocol.RAYDIUM_CLMM,
    Protocol.RAYDIUM_AMM_V4,
    Protocol.METEORA_DAMM_V2,
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


async def main() -> None:
    load_dotenv_silent()
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )

    print("🚀 Multi-Protocol gRPC Example")
    print("================================\n")
    print(f"📡 Endpoint: {endpoint}")
    print(f"📊 Protocols: {[p.value for p in PROTOCOLS]}\n")

    cfg = ClientConfig.default()
    cfg.enable_metrics = True
    cfg.order_mode = OrderMode.UNORDERED
    client = YellowstoneGrpc.new_with_config(endpoint, token or None, cfg)

    asyncio.create_task(stats_reporter())

    tx_filter = transaction_filter_for_protocols(PROTOCOLS)
    tx_filter.vote = False
    tx_filter.failed = False
    account_filter = account_filter_for_protocols(PROTOCOLS)

    queue: asyncio.Queue[DexEvent] = await client.subscribe_dex_events(
        [tx_filter],
        [account_filter],
    )

    print(f"✅ Subscribed")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        while True:
            ev = await queue.get()
            if not isinstance(ev, DexEvent):
                continue
            key = str(ev.type.value)
            stats[key] = stats.get(key, 0) + 1
            print(format_dex_event_json(ev))
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        print("\n📊 Final Event Statistics:")
        for k, v in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {k:<35}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
