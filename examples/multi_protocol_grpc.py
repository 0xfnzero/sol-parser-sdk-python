#!/usr/bin/env python3
"""多协议 gRPC — Program ID 与 ``sol-parser-sdk/src/grpc/program_ids.rs`` / ``Protocol`` 枚举对齐。

Run: ``python examples/multi_protocol_grpc.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

import base58

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import format_dex_event_json, parse_logs_only
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    ClientConfig,
    Protocol,
    SubscribeCallbacks,
    transaction_filter_for_protocols,
)

# 与 Rust ``PROTOCOL_PROGRAM_IDS`` 覆盖范围一致（不含 Orca 等未在 Protocol 中的程序）
PROTOCOLS = [
    Protocol.PUMP_FUN,
    Protocol.PUMP_SWAP,
    Protocol.BONK,
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
    client = YellowstoneGrpc.new_with_config(endpoint, token or None, cfg)

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

        sb = bytes(tx_info.signature) if tx_info.signature else b""
        sig_b58 = base58.b58encode(sb).decode("ascii") if len(sb) == 64 else ""

        for ev in parse_logs_only(
            logs, sig_b58, slot, None, subscribe_tx_info=tx_info
        ):
            if not isinstance(ev, DexEvent):
                continue
            key = str(ev.type.value)
            stats[key] = stats.get(key, 0) + 1
            print(format_dex_event_json(ev))

    tx_filter = transaction_filter_for_protocols(PROTOCOLS)
    tx_filter.vote = False
    tx_filter.failed = False

    await client.subscribe_transactions(
        tx_filter,
        SubscribeCallbacks(
            on_update=on_update,
            on_error=lambda e: print(f"Stream error: {e}", file=sys.stderr),
            on_end=lambda: print("Stream ended"),
        ),
    )

    print(f"✅ Subscribed")
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