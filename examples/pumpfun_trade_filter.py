#!/usr/bin/env python3
"""PumpFun Trade Event Filter Example — latest ``subscribe_dex_events`` API.

Run: ``python examples/pumpfun_trade_filter.py``
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
buy_count = 0
sell_count = 0
buy_exact_count = 0
create_count = 0


def _metadata(ev: DexEvent):
    return getattr(ev.data, "metadata", None) if ev.data is not None else None


def _latency_us(ev: DexEvent) -> int:
    meta = _metadata(ev)
    grpc_recv_us = int(getattr(meta, "grpc_recv_us", 0) or 0) if meta else 0
    return max(0, now_micros() - grpc_recv_us) if grpc_recv_us else 0


def _print_trade(title: str, ev: DexEvent, latency_us: int) -> None:
    meta = _metadata(ev)
    d = ev.data
    print("┌─────────────────────────────────────────────────────────────")
    print(f"│ {title} #{event_count}")
    print("├─────────────────────────────────────────────────────────────")
    print(f"│ Signature  : {getattr(meta, 'signature', '') if meta else ''}")
    print(f"│ Slot       : {getattr(meta, 'slot', 0) if meta else 0}")
    print("├─────────────────────────────────────────────────────────────")
    print(f"│ Mint       : {getattr(d, 'mint', '')}")
    print(f"│ SOL Amount : {getattr(d, 'sol_amount', 0)} lamports")
    print(f"│ Token Amt  : {getattr(d, 'token_amount', 0)}")
    print(f"│ User       : {getattr(d, 'user', '')}")
    print("├─────────────────────────────────────────────────────────────")
    print(f"│ 📊 Latency : {latency_us} μs")


async def main() -> None:
    global event_count, buy_count, sell_count, buy_exact_count, create_count

    load_dotenv_silent()
    endpoint, token = parse_grpc_credentials(
        sys.argv[1:],
        default_endpoint="solana-yellowstone-grpc.publicnode.com:443",
    )

    print("🚀 PumpFun Trade Event Filter Example")
    print("======================================\n")

    config = ClientConfig.default()
    config.enable_metrics = True
    config.connection_timeout_ms = 10000
    config.request_timeout_ms = 30000
    config.enable_tls = True
    config.order_mode = OrderMode.UNORDERED

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)
    protocols = [Protocol.PUMP_FUN]
    print(f"📊 Protocols: {[p.value for p in protocols]}")

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

    print("🎯 Event Filter: Buy, Sell, BuyExactSolIn, Create")
    print("🛑 Press Ctrl+C to stop...\n")

    try:
        while True:
            ev = await queue.get()
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue
            latency_us = _latency_us(ev)
            event_count += 1

            if ev.type == EventType.PUMP_FUN_BUY:
                buy_count += 1
                _print_trade("🟢 PumpFun BUY", ev, latency_us)
                print(f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}")
                print("└─────────────────────────────────────────────────────────────\n")
            elif ev.type == EventType.PUMP_FUN_SELL:
                sell_count += 1
                _print_trade("🔴 PumpFun SELL", ev, latency_us)
                print(f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}")
                print("└─────────────────────────────────────────────────────────────\n")
            elif ev.type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN:
                buy_exact_count += 1
                _print_trade("🟡 PumpFun BUY_EXACT_SOL_IN", ev, latency_us)
                print(f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}")
                print("└─────────────────────────────────────────────────────────────\n")
            elif ev.type in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
                create_count += 1
                meta = _metadata(ev)
                d = ev.data
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🆕 PumpFun CREATE #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {getattr(meta, 'signature', '') if meta else ''}")
                print(f"│ Slot       : {getattr(meta, 'slot', 0) if meta else 0}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Name       : {getattr(d, 'name', '')}")
                print(f"│ Symbol     : {getattr(d, 'symbol', '')}")
                print(f"│ Mint       : {getattr(d, 'mint', '')}")
                print(f"│ Creator    : {getattr(d, 'creator', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Creates : {create_count}")
                print("└─────────────────────────────────────────────────────────────\n")
    finally:
        await client.disconnect()
        print(
            f"\n👋 Total events: {event_count} "
            f"(Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count} Create={create_count})"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
