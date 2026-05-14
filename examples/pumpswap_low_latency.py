#!/usr/bin/env python3
"""PumpSwap 最低延迟测试 — 对齐 ``sol-parser-sdk/examples/pumpswap_low_latency.rs``。

Run: ``python examples/pumpswap_low_latency.py``
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
    account_filter_for_protocols,
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
        total = total_latency
        min_l = min_latency if min_latency < 2**62 else 0
        max_l = max_latency
        queue_len = queue.qsize()
        avg = total // count if count else 0
        events_per_sec = (count - last_count) / 10.0

        print("\n╔════════════════════════════════════════════════════╗")
        print("║          性能统计 (10秒间隔)                       ║")
        print("╠════════════════════════════════════════════════════╣")
        print(f"║  事件总数: {count:>10}                              ║")
        print(f"║  事件速率: {events_per_sec:>10.1f} events/sec                  ║")
        print(f"║  队列长度: {queue_len:>10}                              ║")
        print(f"║  平均延迟: {avg:>10} μs                           ║")
        print(f"║  最小延迟: {min_l:>10} μs                           ║")
        print(f"║  最大延迟: {max_l:>10} μs                           ║")
        print("╚════════════════════════════════════════════════════╝\n")

        if queue_len > 1000:
            print(f"⚠️  警告: 队列堆积 ({queue_len}), 消费速度 < 生产速度")

        last_count = count


def _grpc_recv_us(ev: DexEvent) -> int | None:
    d = ev.data
    if d is None:
        return None
    meta = getattr(d, "metadata", None)
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

    print("🚀 PumpSwap Low-Latency Test (No Ordering)")
    print("============================================\n")

    config = ClientConfig.default()
    config.enable_metrics = True
    config.connection_timeout_ms = 10000
    config.request_timeout_ms = 30000
    config.enable_tls = True
    config.order_mode = OrderMode.UNORDERED

    print("📋 Configuration:")
    print(f"   Order Mode: {config.order_mode} (零延迟，无排序开销)")
    print("   Clock Source: now_micros() (10-50ns, 比 clock_gettime 快 20-100 倍)")
    print()

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)
    print("✅ gRPC client created (parser pre-warmed)")

    protocols = [Protocol.PUMP_SWAP]
    print(f"📊 Protocols: {[p.value for p in protocols]}")

    tx_filter = transaction_filter_for_protocols(protocols)
    tx_filter.vote = False
    tx_filter.failed = False
    account_filter = account_filter_for_protocols(protocols)

    event_filter = event_type_filter_include_only(
        [
            EventType.PUMP_SWAP_BUY,
            EventType.PUMP_SWAP_SELL,
            EventType.PUMP_SWAP_CREATE_POOL,
        ]
    )

    print("🎧 Starting low-latency subscription...\n")

    queue: asyncio.Queue[DexEvent] = await client.subscribe_dex_events(
        [tx_filter],
        [account_filter],
        event_filter,
    )
    asyncio.create_task(stats_reporter(queue))

    async def consume_events() -> None:
        global event_count, total_latency, min_latency, max_latency

        while True:
            ev = await queue.get()
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue

            grpc_recv_us_opt = _grpc_recv_us(ev)
            if grpc_recv_us_opt is None:
                continue

            queue_recv_us = now_micros()
            latency_us = max(0, queue_recv_us - grpc_recv_us_opt)

            event_count += 1
            total_latency += latency_us
            min_latency = min(min_latency, latency_us)
            max_latency = max(max_latency, latency_us)

            print("\n================================================")
            print(f"gRPC接收时间: {grpc_recv_us_opt} μs")
            print(f"事件接收时间: {queue_recv_us} μs")
            print(f"延迟时间: {latency_us} μs")
            print(f"队列长度: {queue.qsize()}")
            print("================================================")
            print(format_dex_event_json(ev))
            print()

    async def auto_stop():
        await asyncio.sleep(600)
        print("⏰ Auto-stopping after 10 minutes...")
        await client.disconnect()

    asyncio.create_task(auto_stop())

    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await consume_events()
    finally:
        await client.disconnect()
        print("\n👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
