#!/usr/bin/env python3
"""PumpSwap + 性能指标 — 对齐 ``sol-parser-sdk/examples/pumpswap_with_metrics.rs``。

Run: ``python examples/pumpswap_with_metrics.py``
"""

from __future__ import annotations

import asyncio
import os
import sys

import base58

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import format_dex_event_json, now_micros, parse_logs_only
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    ClientConfig,
    EventType,
    Protocol,
    SubscribeCallbacks,
    event_type_filter_include_only,
    transaction_filter_for_protocols,
)

event_count = 0
total_latency = 0
min_latency = 2**62
max_latency = 0
last_count = 0


async def stats_reporter():
    global last_count
    while True:
        await asyncio.sleep(10)
        if event_count == 0:
            continue
        count = event_count
        total = total_latency
        min_l = min_latency if min_latency < 2**62 else 0
        max_l = max_latency
        queue_len = 0
        avg = total // count if count else 0
        events_per_sec = (count - last_count) / 10.0

        print("\n╔════════════════════════════════════════════════════╗")
        print("║      PumpSwap 性能统计 (10秒间隔)                  ║")
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

    print("PumpSwap event parsing with detailed performance metrics")
    print("🚀 Subscribing to Yellowstone gRPC (PumpSwap)...")

    config = ClientConfig.default()
    config.enable_metrics = True
    config.connection_timeout_ms = 10000
    config.request_timeout_ms = 30000
    config.enable_tls = True

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)
    print("✅ gRPC client created successfully")

    protocols = [Protocol.PUMP_SWAP]
    print(f"📊 Protocols to monitor: {[p.value for p in protocols]}")

    tx_filter = transaction_filter_for_protocols(protocols)
    tx_filter.vote = False
    tx_filter.failed = False

    print("🎧 Starting subscription...")
    print("🔍 Monitoring PumpSwap programs for DEX events...")

    event_filter = event_type_filter_include_only(
        [
            EventType.PUMP_SWAP_BUY,
            EventType.PUMP_SWAP_SELL,
            EventType.PUMP_SWAP_CREATE_POOL,
            EventType.PUMP_SWAP_LIQUIDITY_ADDED,
            EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
        ]
    )

    print("📋 Event Filter: Buy, Sell, CreatePool, LiquidityAdded, LiquidityRemoved")

    await client.connect()
    asyncio.create_task(stats_reporter())

    def on_update(update):
        global event_count, total_latency, min_latency, max_latency

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
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue
            if not event_filter.should_include(ev.type):
                continue

            grpc_recv_us_opt = _grpc_recv_us(ev)
            if grpc_recv_us_opt is None:
                continue

            queue_recv_us = now_micros()
            latency_us = queue_recv_us - grpc_recv_us_opt
            if latency_us < 0:
                latency_us = 0

            event_count += 1
            total_latency += latency_us
            min_latency = min(min_latency, latency_us)
            max_latency = max(max_latency, latency_us)

            queue_len = 0

            print("\n================================================")
            print(f"gRPC接收时间: {grpc_recv_us_opt} μs")
            print(f"事件接收时间: {queue_recv_us} μs")
            print(f"延迟时间: {latency_us} μs")
            print(f"队列长度: {queue_len}")
            print("================================================")
            print(format_dex_event_json(ev))
            print()

    await client.subscribe_transactions(
        tx_filter,
        SubscribeCallbacks(
            on_update=on_update,
            on_error=lambda e: print(f"Stream error: {e}", file=sys.stderr),
            on_end=lambda: None,
        ),
    )

    print("🛑 Press Ctrl+C to stop...")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()
        print("👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
