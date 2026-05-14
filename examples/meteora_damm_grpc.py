#!/usr/bin/env python3
"""Meteora DAMM gRPC — latest ``subscribe_dex_events`` queue API.

Run: ``python examples/meteora_damm_grpc.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import now_micros
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    ClientConfig,
    EventType,
    OrderMode,
    Protocol,
    event_type_filter_include_only,
    transaction_filter_for_protocols,
)

event_count = 0
swap_count = 0
add_liquidity_count = 0
remove_liquidity_count = 0
create_position_count = 0
close_position_count = 0


def _metadata(ev: DexEvent):
    return getattr(ev.data, "metadata", None) if ev.data is not None else None


def _latency_us(ev: DexEvent) -> int:
    meta = _metadata(ev)
    grpc_recv_us = int(getattr(meta, "grpc_recv_us", 0) or 0) if meta else 0
    return max(0, now_micros() - grpc_recv_us) if grpc_recv_us else 0


async def main() -> None:
    global event_count, swap_count, add_liquidity_count, remove_liquidity_count
    global create_position_count, close_position_count

    load_dotenv_silent()
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )

    print("🚀 Meteora DAMM gRPC Streaming Example")
    print("========================================\n")

    config = ClientConfig.default()
    config.enable_metrics = True
    config.connection_timeout_ms = 10000
    config.request_timeout_ms = 30000
    config.enable_tls = True
    config.order_mode = OrderMode.UNORDERED

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)
    protocols = [Protocol.METEORA_DAMM_V2]
    print(f"📊 Protocols: {[p.value for p in protocols]}")

    tx_filter = transaction_filter_for_protocols(protocols)
    tx_filter.vote = False
    tx_filter.failed = False
    event_filter = event_type_filter_include_only(
        [
            EventType.METEORA_DAMM_V2_SWAP,
            EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
            EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
            EventType.METEORA_DAMM_V2_CREATE_POSITION,
            EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        ]
    )

    queue: asyncio.Queue[DexEvent] = await client.subscribe_dex_events(
        [tx_filter],
        [],
        event_filter,
    )

    print("🎯 Event Filter: Swap, AddLiquidity, RemoveLiquidity, CreatePosition, ClosePosition")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        while True:
            ev = await queue.get()
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue
            event_count += 1
            d = ev.data
            meta = _metadata(ev)
            sig = getattr(meta, "signature", "") if meta else ""
            slot = int(getattr(meta, "slot", 0) or 0) if meta else 0
            latency_us = _latency_us(ev)

            if ev.type == EventType.METEORA_DAMM_V2_SWAP:
                swap_count += 1
                direction = "A->B" if getattr(d, "trade_direction", 0) == 0 else "B->A"
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🔄 Meteora DAMM SWAP (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig}")
                print(f"│ Slot       : {slot}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Pool       : {getattr(d, 'pool', '')}")
                print(f"│ Direction  : {direction}")
                print(f"│ Amount In  : {getattr(d, 'amount_in', 0)}")
                print(f"│ Actual Out : {getattr(d, 'output_amount', 0)}")
                print(f"│ Protocol   : {getattr(d, 'protocol_fee', 0)}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Swap={swap_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}"
                )
                print("└─────────────────────────────────────────────────────────────\n")
            elif ev.type == EventType.METEORA_DAMM_V2_ADD_LIQUIDITY:
                add_liquidity_count += 1
                print(f"➕ ADD_LIQUIDITY #{add_liquidity_count} sig={sig} slot={slot} latency={latency_us}μs")
            elif ev.type == EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY:
                remove_liquidity_count += 1
                print(f"➖ REMOVE_LIQUIDITY #{remove_liquidity_count} sig={sig} slot={slot} latency={latency_us}μs")
            elif ev.type == EventType.METEORA_DAMM_V2_CREATE_POSITION:
                create_position_count += 1
                print(f"📌 CREATE_POSITION #{create_position_count} sig={sig} slot={slot} latency={latency_us}μs")
            elif ev.type == EventType.METEORA_DAMM_V2_CLOSE_POSITION:
                close_position_count += 1
                print(f"❌ CLOSE_POSITION #{close_position_count} sig={sig} slot={slot} latency={latency_us}μs")
    finally:
        await client.disconnect()
        print("\n👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
