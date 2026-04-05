<div align="center">
    <h1>⚡ Sol Parser SDK - Python</h1>
    <h3><em>High-performance Solana DEX event parser for Python</em></h3>
</div>

<p align="center">
    <strong>High-performance Python library for parsing Solana DEX events in real-time via Yellowstone gRPC</strong>
</p>

<p align="center">
    <a href="https://pypi.org/project/sol-parser-sdk-python/">
        <img src="https://img.shields.io/pypi/v/sol-parser-sdk-python.svg" alt="PyPI">
    </a>
    <a href="https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/LICENSE">
        <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
    </a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Solana-9945FF?style=for-the-badge&logo=solana&logoColor=white" alt="Solana">
    <img src="https://img.shields.io/badge/gRPC-4285F4?style=for-the-badge&logo=grpc&logoColor=white" alt="gRPC">
</p>

<p align="center">
    <a href="./README_CN.md">中文</a> |
    <a href="./README.md">English</a> |
    <a href="https://fnzero.dev/">Website</a> |
    <a href="https://t.me/fnzero_group">Telegram</a> |
    <a href="https://discord.gg/vuazbGkqQE">Discord</a>
</p>

<p align="center">
    <a href="https://github.com/0xfnzero/sol-parser-sdk">Rust</a> |
    <a href="https://github.com/0xfnzero/sol-parser-sdk-nodejs">Node.js</a> |
    <a href="https://github.com/0xfnzero/sol-parser-sdk-python"><strong>Python</strong></a> |
    <a href="https://github.com/0xfnzero/sol-parser-sdk-golang">Go</a>
</p>

---

## 📦 SDK Versions

This SDK is available in multiple languages:

| Language | Repository | Description |
|----------|------------|-------------|
| **Rust** | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) | Ultra-low latency with SIMD optimization |
| **Node.js** | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) | TypeScript/JavaScript for Node.js |
| **Python** | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) | Async/await native support |
| **Go** | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) | Concurrent-safe with goroutine support |

---

## 📊 Performance Highlights

### ⚡ Real-Time Parsing
- **Sub-millisecond** log-based event parsing
- **gRPC streaming** with Yellowstone/Geyser protocol
- **Async/await** native support with asyncio
- **Event type filtering** for targeted parsing
- **Minimal allocations** on hot paths

### 🎚️ Flexible Order Modes
| Mode | Latency | Description |
|------|---------|-------------|
| **Unordered** | <1ms | Immediate output, ultra-low latency |
| **MicroBatch** | 1-5ms | Micro-batch ordering with time window |
| **StreamingOrdered** | 5-20ms | Stream ordering with continuous sequence release |
| **Ordered** | 10-100ms | Full slot ordering, wait for complete slot |

### 🚀 Optimization Highlights
- ✅ **Async/await native** with asyncio for efficient I/O
- ✅ **Optimized pattern matching** for protocol detection
- ✅ **Event type filtering** for targeted parsing
- ✅ **Conditional Create detection** (only when needed)
- ✅ **Multiple order modes** for latency vs ordering trade-off
- ✅ **Type-safe event classes** for better IDE support

---

## 🔥 Quick Start

### Installation

```bash
git clone https://github.com/0xfnzero/sol-parser-sdk-python
cd sol-parser-sdk-python
pip install -e .
pip install grpcio grpcio-tools protobuf base58
```

### Use PyPI

```bash
pip install sol-parser-sdk-python
```

### Performance Testing

Test parsing with the optimized examples:

```bash
# PumpFun trade filter (Buy/Sell/BuyExactSolIn/Create)
GEYSER_API_TOKEN=your_token python examples/pumpfun_trade_filter.py

# PumpSwap low-latency with performance metrics
GEYSER_API_TOKEN=your_token python examples/pumpswap_low_latency.py

# All protocols simultaneously
GEYSER_API_TOKEN=your_token python examples/multi_protocol_grpc.py

# Expected output:
# gRPC接收时间: 1234567890 μs
# 事件接收时间: 1234567900 μs
# 延迟时间: 10 μs  <-- Ultra-low latency!
```

### Examples

| Description | Run Command | Source Code |
|-------------|-------------|-------------|
| **PumpFun** | | |
| PumpFun trade filtering (Buy/Sell/BuyExactSolIn/Create) with latency metrics | `python examples/pumpfun_trade_filter.py` | [examples/pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) |
| Quick PumpFun connection test (first 10 events) | `python examples/pumpfun_quick_test.py` | [examples/pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) |
| **PumpSwap** | | |
| PumpSwap ultra-low latency with per-event + 10s stats | `python examples/pumpswap_low_latency.py` | [examples/pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) |
| PumpSwap events with performance metrics | `python examples/pumpswap_with_metrics.py` | [examples/pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) |
| **Meteora DAMM** | | |
| Meteora DAMM V2 (Swap/AddLiquidity/RemoveLiquidity/CreatePosition/ClosePosition) | `python examples/meteora_damm_grpc.py` | [examples/meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) |
| **Multi-Protocol** | | |
| Subscribe to all DEX protocols simultaneously | `python examples/multi_protocol_grpc.py` | [examples/multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) |

### Basic Usage

```python
import asyncio
import os
import base58

from sol_parser.grpc_client import GrpcClient
from sol_parser.grpc_types import TransactionFilter
from sol_parser.unified_parser import parse_logs_only

ENDPOINT = "https://solana-yellowstone-grpc.publicnode.com:443"
X_TOKEN = os.environ.get("GEYSER_API_TOKEN", "")

async def main():
    client = GrpcClient(ENDPOINT, X_TOKEN)

    filter_ = TransactionFilter(
        account_include=[
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # PumpFun
            "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ",  # PumpSwap
        ],
        vote=False,
        failed=False,
    )

    async def on_update(update):
        tx = update.transaction
        if tx is None or tx.transaction is None:
            return

        tx_info = tx.transaction
        logs = tx_info.log_messages
        if not logs:
            return

        sig = base58.b58encode(tx_info.signature).decode()
        events = parse_logs_only(logs, sig, tx.slot, None)

        for ev in events:
            ev_type = type(ev).__name__
            print(f"[{ev_type}] {ev}")

    await client.subscribe_transactions(filter_, on_update)

asyncio.run(main())
```

---

## 🏗️ Supported Protocols

### DEX Protocols
- ✅ **PumpFun** - Meme coin trading
- ✅ **PumpSwap** - PumpFun swap protocol
- ✅ **Raydium AMM V4** - Automated Market Maker
- ✅ **Raydium CLMM** - Concentrated Liquidity
- ✅ **Raydium CPMM** - Concentrated Pool
- ✅ **Orca Whirlpool** - Concentrated liquidity AMM
- ✅ **Meteora DAMM V2** - Dynamic AMM
- ✅ **Meteora DLMM** - Dynamic Liquidity Market Maker
- ✅ **Bonk Launchpad** - Token launch platform

### Event Types
Each protocol supports:
- 📈 **Trade/Swap Events** - Buy/sell transactions
- 💧 **Liquidity Events** - Deposits/withdrawals
- 🏊 **Pool Events** - Pool creation/initialization
- 🎯 **Position Events** - Open/close positions (CLMM)

---

## ⚡ Performance Features

### Optimized Pattern Matching
```python
import re

# Pre-compiled regex patterns for fast protocol detection
PUMPFUN_PATTERN = re.compile(r"Program 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")

# Fast check before full parsing
if PUMPFUN_PATTERN.search(log_string):
    return parse_pumpfun_event(logs, signature, slot)
```

### Event Type Filtering
```python
# Filter specific event types for targeted parsing
from sol_parser.types import EventType

event_filter = {
    "include_only": [EventType.PumpFunTrade, EventType.PumpSwapBuy]
}
```

### Async Stats Reporter
```python
import asyncio

total_events = 0

async def stats_reporter():
    while True:
        await asyncio.sleep(10)
        print(f"Total events in last 10s: {total_events}")

asyncio.create_task(stats_reporter())
```

---

## 🎯 Event Filtering

Reduce processing overhead by filtering specific events:

### Example: Trading Bot
```python
from sol_parser.types import EventType

event_filter = {
    "include_only": [
        EventType.PumpFunTrade,
        EventType.RaydiumAmmV4Swap,
        EventType.RaydiumClmmSwap,
        EventType.OrcaWhirlpoolSwap,
    ]
}
```

### Example: Pool Monitor
```python
from sol_parser.types import EventType

event_filter = {
    "include_only": [
        EventType.PumpFunCreate,
        EventType.PumpSwapCreatePool,
    ]
}
```

**Performance Impact:**
- 60-80% reduction in processing
- Lower memory usage
- Reduced network bandwidth

---

## 🔧 Advanced Features

### Create+Buy Detection
Automatically detects when a token is created and immediately bought in the same transaction:

```python
from sol_parser.unified_parser import parse_logs_only

# Automatically detects "Program data: GB7IKAUcB3c..." pattern
events = parse_logs_only(logs, signature, slot, None)

# Sets is_created_buy flag on Trade events
for ev in events:
    if hasattr(ev, 'is_created_buy') and ev.is_created_buy:
        print("Create+Buy detected!")
```

### Custom gRPC Endpoint

```python
import os

endpoint = os.environ.get("GEYSER_ENDPOINT", "https://solana-yellowstone-grpc.publicnode.com:443")
token = os.environ.get("GEYSER_API_TOKEN", "")
client = GrpcClient(endpoint, token)
```

### Unsubscribe

```python
# Async context manager for automatic cleanup
async with GrpcClient(ENDPOINT, TOKEN) as client:
    await client.subscribe_transactions(filter_, on_update)
```

---

## 📁 Project Structure

```
sol-parser-sdk-python/
├── sol_parser/
│   ├── grpc_client.py          # GrpcClient (async, connect, subscribe)
│   ├── grpc_types.py           # TransactionFilter, TransactionUpdate, etc.
│   ├── unified_parser.py       # parse_logs_only, parse_transaction_events
│   ├── optimized_matcher.py    # Log parsing (all protocols)
│   ├── geyser_pb2.py           # Generated proto (Yellowstone)
│   ├── geyser_pb2_grpc.py      # Generated gRPC stubs
│   ├── solana_storage_pb2.py   # Generated proto (Solana storage)
│   └── ...
├── examples/
│   ├── pumpfun_trade_filter.py
│   ├── pumpfun_quick_test.py
│   ├── pumpswap_low_latency.py
│   ├── pumpswap_with_metrics.py
│   ├── meteora_damm_grpc.py
│   └── multi_protocol_grpc.py
└── pyproject.toml
```

---

## 🚀 Optimization Techniques

### 1. **Async/Await Native**
- Full asyncio support for non-blocking I/O
- Efficient event loop integration
- Concurrent connection handling

### 2. **Optimized Pattern Matching**
- Pre-compiled regex patterns for protocol detection
- Fast path for single-protocol filtering
- Minimal string operations

### 3. **Event Type Filtering**
- Early filtering at protocol level
- Conditional Create detection
- Single-type ultra-fast path

### 4. **Type-Safe Events**
- Strongly typed event classes
- Better IDE autocomplete and type hints
- Runtime type checking where needed

### 5. **Efficient Memory Usage**
- Reusable buffers where possible
- Generator-based event streaming
- Minimal object allocation on hot path

---

## 📄 License

MIT License

## 📞 Contact

- **Repository**: https://github.com/0xfnzero/sol-parser-sdk-python
- **Website**: https://fnzero.dev/
- **Telegram**: https://t.me/fnzero_group
- **Discord**: https://discord.gg/vuazbGkqQE

---

## ⚠️ Performance Tips

1. **Use Event Filtering** — Filter by program ID for 60-80% performance gain
2. **Use async/await** — Leverage asyncio for non-blocking I/O
3. **Use latest Python** — Python 3.10+ has better async performance
4. **Monitor latency** — Check gRPC receive timestamps in production
5. **Avoid blocking calls** — Keep event processing async

## 🔬 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black sol_parser/
isort sol_parser/

# Type check
mypy sol_parser/
```
