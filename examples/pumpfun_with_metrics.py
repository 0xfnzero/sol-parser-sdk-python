#!/usr/bin/env python3
"""PumpFun + performance metrics — latest ``subscribe_dex_events`` API.

Run: ``python examples/pumpfun_with_metrics.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import format_dex_event_json, now_micros
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
total_latency = 0
min_latency = 2**62
max_latency = 0
last_count = 0


async def stats_reporter(queue: asyncio.Queue[DexEvent]):
    global last_count
    while True:
        await asyncio.sleep(10)
        if event_count == 0:
            continue
        count = event_count
        avg = total_latency // count if count else 0
        events_per_sec = (count - last_count) / 10.0
        min_l = min_latency if min_latency < 2**62 else 0
        print("\n╔════════════════════════════════════════════════════╗")
        print("║          性能统计 (10秒间隔)                       ║")
        print("╠════════════════════════════════════════════════════╣")
        print(f"║  事件总数: {count:>10}                              ║")
        print(f"║  事件速率: {events_per_sec:>10.1f} events/sec                  ║")
        print(f"║  队列长度: {queue.qsize():>10}                              ║")
        print(f"║  平均延迟: {avg:>10} μs                           ║")
        print(f"║  最小延迟: {min_l:>10} μs                           ║")
        print(f"║  最大延迟: {max_latency:>10} μs                           ║")
        print("╚════════════════════════════════════════════════════╝\n")
        last_count = count


def _grpc_recv_us(ev: DexEvent) -> int | None:
    meta = getattr(ev.data, "metadata", None) if ev.data is not None else None
    if meta is None:
        return None
    v = int(getattr(meta, "grpc_recv_us", 0) or 0)
    return v if v > 0 else None


async def main() -> None:
    global event_count, total_latency, min_latency, max_latency

    load_dotenv_silent()
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )

    print("Starting Sol Parser SDK Example with Metrics...")
    print("🚀 Subscribing to Yellowstone gRPC events...")

    config = ClientConfig.default()
    config.enable_metrics = True
    config.connection_timeout_ms = 10000
    config.request_timeout_ms = 30000
    config.enable_tls = True
    config.order_mode = OrderMode.UNORDERED

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)

    protocols = [Protocol.PUMP_FUN]
    print(f"📊 Protocols to monitor: {[p.value for p in protocols]}")

    tx_filter = transaction_filter_for_protocols(protocols)
    tx_filter.vote = False
    tx_filter.failed = False
    event_filter = event_type_filter_include_only(
        [
            EventType.PUMP_FUN_BUY,
            EventType.PUMP_FUN_SELL,
            EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
            EventType.PUMP_FUN_CREATE,
            EventType.PUMP_FUN_CREATE_V2,
        ]
    )

    queue: asyncio.Queue[DexEvent] = await client.subscribe_dex_events(
        [tx_filter],
        [],
        event_filter,
    )
    asyncio.create_task(stats_reporter(queue))

    print("📋 Event Filter: Buy, Sell, BuyExactSolIn, Create")
    print("🛑 Press Ctrl+C to stop...")

    try:
        while True:
            ev = await queue.get()
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue
            grpc_recv_us = _grpc_recv_us(ev)
            if grpc_recv_us is None:
                continue
            queue_recv_us = now_micros()
            latency_us = max(0, queue_recv_us - grpc_recv_us)

            event_count += 1
            total_latency += latency_us
            min_latency = min(min_latency, latency_us)
            max_latency = max(max_latency, latency_us)

            print("\n================================================")
            print(f"gRPC接收时间: {grpc_recv_us} μs")
            print(f"事件接收时间: {queue_recv_us} μs")
            print(f"延迟时间: {latency_us} μs")
            print(f"队列长度: {queue.qsize()}")
            print("================================================")
            print(format_dex_event_json(ev))
            print()
    finally:
        await client.disconnect()
        print("👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
