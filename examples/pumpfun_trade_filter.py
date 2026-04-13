#!/usr/bin/env python3
"""PumpFun Trade Event Filter Example — 对齐 ``sol-parser-sdk/examples/pumpfun_trade_filter.rs``。

Run: ``python examples/pumpfun_trade_filter.py``

环境: ``GRPC_URL`` / ``GRPC_ENDPOINT``、``GRPC_AUTH_TOKEN``（或 ``GRPC_TOKEN``）、``.env``，
或 ``--grpc-url`` / ``--grpc-token``。
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
buy_count = 0
sell_count = 0
buy_exact_count = 0
create_count = 0


def _meta_sig_slot_ix(ev: DexEvent, sig_b58: str, slot: int, tx_index: int) -> tuple[str, int, int]:
    d = ev.data
    meta = getattr(d, "metadata", None) if d else None
    sig_s = (getattr(meta, "signature", None) or "").strip() or sig_b58
    slot_u = int(getattr(meta, "slot", slot) or slot)
    tx_ix = int(getattr(meta, "tx_index", tx_index) or tx_index)
    return sig_s, slot_u, tx_ix


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

    print("📋 Configuration:")
    print(f"   Order Mode: {config.order_mode} (ultra-low latency)")
    print()

    client = YellowstoneGrpc.new_with_config(endpoint, token or None, config)

    print("✅ gRPC client created (parser pre-warmed)")

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

    print("🎯 Event Filter: Buy, Sell, BuyExactSolIn, Create")
    print("🎧 Starting subscription...\n")

    await client.connect()

    def on_update(update):
        global event_count, buy_count, sell_count, buy_exact_count, create_count

        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return

        sig_bytes = bytes(tx_info.signature) if tx_info.signature else b""
        sig_b58 = (
            base58.b58encode(sig_bytes).decode("ascii") if len(sig_bytes) == 64 else ""
        )
        tx_index = int(getattr(tx_info, "index", 0) or 0)

        for ev in parse_logs_only(
            logs, sig_b58, slot, None, subscribe_tx_info=tx_info
        ):
            if not isinstance(ev, DexEvent) or ev.data is None:
                continue
            t = ev.type
            if not event_filter.should_include(t):
                continue
            if not str(t.value).startswith("PumpFun"):
                continue

            d = ev.data
            meta = getattr(d, "metadata", None)
            grpc_recv_us = int(getattr(meta, "grpc_recv_us", 0) or 0) if meta else 0
            now_us = now_micros()
            latency_us = now_us - grpc_recv_us if grpc_recv_us else 0
            event_count += 1

            sig_s, slot_u, tx_ix = _meta_sig_slot_ix(ev, sig_b58, slot, tx_index)

            if t == EventType.PUMP_FUN_BUY:
                buy_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🟢 PumpFun BUY #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Mint       : {getattr(d, 'mint', '')}")
                print(f"│ SOL Amount : {getattr(d, 'sol_amount', 0)} lamports")
                print(f"│ Token Amt  : {getattr(d, 'token_amount', 0)}")
                print(f"│ User       : {getattr(d, 'user', '')}")
                print(f"│ ix_name    : {getattr(d, 'ix_name', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t == EventType.PUMP_FUN_SELL:
                sell_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🔴 PumpFun SELL #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Mint       : {getattr(d, 'mint', '')}")
                print(f"│ SOL Amount : {getattr(d, 'sol_amount', 0)} lamports")
                print(f"│ Token Amt  : {getattr(d, 'token_amount', 0)}")
                print(f"│ User       : {getattr(d, 'user', '')}")
                print(f"│ ix_name    : {getattr(d, 'ix_name', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t == EventType.PUMP_FUN_BUY_EXACT_SOL_IN:
                buy_exact_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🟡 PumpFun BUY_EXACT_SOL_IN #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Mint       : {getattr(d, 'mint', '')}")
                print(f"│ SOL Amount : {getattr(d, 'sol_amount', 0)} lamports (exact input)")
                print(f"│ Token Amt  : {getattr(d, 'token_amount', 0)} (min output)")
                print(f"│ User       : {getattr(d, 'user', '')}")
                print(f"│ ix_name    : {getattr(d, 'ix_name', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(
                    f"│ 📊 Stats   : Buy={buy_count} Sell={sell_count} BuyExact={buy_exact_count}"
                )
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t == EventType.PUMP_FUN_TRADE:
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ ⚪ PumpFun TRADE (unknown type) #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(
                    f"│ ix_name    : {getattr(d, 'ix_name', '')} (is_buy={getattr(d, 'is_buy', False)})"
                )
                print(f"│ Signature  : {sig_s}")
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

            elif t in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
                create_count += 1
                print("┌─────────────────────────────────────────────────────────────")
                print(f"│ 🆕 PumpFun CREATE #{event_count}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Signature  : {sig_s}")
                print(f"│ Slot       : {slot_u} | TxIndex: {tx_ix}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ Name       : {getattr(d, 'name', '')}")
                print(f"│ Symbol     : {getattr(d, 'symbol', '')}")
                print(f"│ Mint       : {getattr(d, 'mint', '')}")
                print(f"│ Creator    : {getattr(d, 'creator', '')}")
                print("├─────────────────────────────────────────────────────────────")
                print(f"│ 📊 Latency : {latency_us} μs")
                print(f"│ 📊 Creates : {create_count}")
                print(
                    "└─────────────────────────────────────────────────────────────\n"
                )

    def on_error(err):
        print(f"Stream error: {err}", file=sys.stderr)

    def on_end():
        print("Stream ended")

    callbacks = SubscribeCallbacks(on_update=on_update, on_error=on_error, on_end=on_end)
    await client.subscribe_transactions(tx_filter, callbacks)

    async def auto_stop():
        await asyncio.sleep(600)
        print("⏰ Auto-stopping after 10 minutes...")
        await client.disconnect()

    asyncio.create_task(auto_stop())

    print("🛑 Press Ctrl+C to stop...\n")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await client.disconnect()
        print("\n👋 Shutting down gracefully...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
