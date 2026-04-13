#!/usr/bin/env python3
"""Meteora DAMM gRPC — 对齐 ``sol-parser-sdk/examples/meteora_damm_grpc.rs``。

Run: ``python examples/meteora_damm_grpc.py``

环境: ``GRPC_ENDPOINT`` / ``GRPC_URL``、``GRPC_AUTH_TOKEN`` 等（与 Rust 一致）。
"""

from __future__ import annotations

import asyncio
import os
import sys

import base58

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sol_parser import now_micros, parse_logs_only
from sol_parser.env_config import load_dotenv_silent, parse_grpc_credentials
from sol_parser.event_types import DexEvent
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    ClientConfig,
    EventType,
    OrderMode,
    Protocol,
    SubscribeCallbacks,
    event_type_filter_include_only,
    transaction_filter_for_protocols,
)

event_count = 0
swap_count = 0
swap2_count = 0
add_liquidity_count = 0
remove_liquidity_count = 0


async def main() -> None:
    global event_count, swap_count, add_liquidity_count, remove_liquidity_count

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

    print("📋 Configuration:")
    print(f"   Order Mode: {config.order_mode} (ultra-low latency)")
    print()

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)

    print("✅ gRPC client created (parser pre-warmed)")
    print(f"📡 Endpoint: {endpoint}")

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

    print("🎯 Event Filter: Swap, Swap2, AddLiquidity, RemoveLiquidity")
    print("🎧 Starting subscription...\n")

    await client.connect()

    def on_update(update):
        global event_count, swap_count, add_liquidity_count, remove_liquidity_count

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
            t = ev.type
            if not event_filter.should_include(t):
                continue
            if t in (
                EventType.METEORA_DAMM_V2_CREATE_POSITION,
                EventType.METEORA_DAMM_V2_CLOSE_POSITION,
            ):
                continue

            d = ev.data
            meta = getattr(d, "metadata", None)
            grpc_recv_us = int(getattr(meta, "grpc_recv_us", 0) or 0) if meta else 0
            now_us = now_micros()
            latency_us = now_us - grpc_recv_us if grpc_recv_us else 0

            sig_s = (
                ((getattr(meta, "signature", None) or "").strip() or sig)
                if meta
                else sig
            )
            slot_u = int(getattr(meta, "slot", slot) or slot)
            tx_ix = int(
                getattr(meta, "tx_index", getattr(tx_info, "index", 0)) or 0
            )

            event_count += 1

            if t == EventType.METEORA_DAMM_V2_SWAP:
                swap_count += 1
                direction = "A→B" if getattr(d, "trade_direction", 0) == 0 else "B→A"
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🔄 Meteora DAMM SWAP (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Pool       : {getattr(d, 'pool', '')}")
                print(f"│ Direction  : {direction}")
                print(f"│ Amount In  : {getattr(d, 'amount_in', 0)}")
                print(f"│ Min Out    : {getattr(d, 'minimum_amount_out', 0)}")
                print(f"│ Actual Out : {getattr(d, 'output_amount', 0)}")
                print(f"│ Actual In  : {getattr(d, 'actual_amount_in', 0)}")
                print(f"│ LP Fee     : {getattr(d, 'lp_fee', 0)}")
                print(f"│ Protocol   : {getattr(d, 'protocol_fee', 0)}")
                print(
                    f"│ Referral   : {getattr(d, 'referral_fee', 0)} (has_referral: {getattr(d, 'has_referral', False)})"
                )
                print(f"│ Sqrt Price : {getattr(d, 'next_sqrt_price', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Swap={swap_count} Swap2={swap2_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t == EventType.METEORA_DAMM_V2_ADD_LIQUIDITY:
                add_liquidity_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ ➕ Meteora DAMM ADD LIQUIDITY (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Pool       : {getattr(d, 'pool', '')}")
                print(f"│ Position   : {getattr(d, 'position', '')}")
                print(f"│ Token A In : {getattr(d, 'token_a_amount', 0)}")
                print(f"│ Token B In : {getattr(d, 'token_b_amount', 0)}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Swap={swap_count} Swap2={swap2_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t == EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY:
                remove_liquidity_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ ➖ Meteora DAMM REMOVE LIQUIDITY (V2) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Pool       : {getattr(d, 'pool', '')}")
                print(f"│ Position   : {getattr(d, 'position', '')}")
                print(f"│ Token A Out: {getattr(d, 'token_a_amount', 0)}")
                print(f"│ Token B Out: {getattr(d, 'token_b_amount', 0)}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Swap={swap_count} Swap2={swap2_count} AddLiq={add_liquidity_count} RemLiq={remove_liquidity_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

    await client.subscribe_transactions(
        tx_filter,
        SubscribeCallbacks(
            on_update=on_update,
            on_error=lambda e: print(f"Stream error: {e}", file=sys.stderr),
            on_end=lambda: None,
        ),
    )

    async def auto_stop():
        await asyncio.sleep(600)
        print("⏰ Auto-stopping after 10 minutes...")
        await client.disconnect()

    asyncio.create_task(auto_stop())

    print("🛑 Press Ctrl+C to stop...\n")

    try:
        await asyncio.Event().wait()
    finally:
        await client.disconnect()
        print("\n👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
