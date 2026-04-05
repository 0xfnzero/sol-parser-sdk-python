<div align="center">
    <h1>⚡ Sol Parser SDK - Python</h1>
    <h3><em>High-performance Solana DEX event parser for Python</em></h3>
</div>

<p align="center">
    <strong>Python library for parsing Solana DEX events in real-time via Yellowstone gRPC</strong>
</p>

<p align="center">
    <a href="https://github.com/0xfnzero/sol-parser-sdk-python">
        <img src="https://img.shields.io/badge/pypi-sol--parser--sdk--python-3776AB.svg" alt="PyPI">
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

---

## 📊 Performance Highlights

### ⚡ Real-Time Parsing
- **Zero-latency** log-based event parsing
- **gRPC streaming** with Yellowstone/Geyser protocol
- **Async/await** native support with asyncio
- **Multi-protocol** support in a single subscription

### 🏗️ Supported Protocols
- ✅ **PumpFun** - Meme coin trading
- ✅ **PumpSwap** - PumpFun swap protocol
- ✅ **Raydium AMM V4** - Automated Market Maker
- ✅ **Raydium CLMM** - Concentrated Liquidity
- ✅ **Raydium CPMM** - Concentrated Pool
- ✅ **Orca Whirlpool** - Concentrated liquidity AMM
- ✅ **Meteora DAMM V2** - Dynamic AMM
- ✅ **Meteora DLMM** - Dynamic Liquidity Market Maker
- ✅ **Bonk Launchpad** - Token launch platform

---

## 🔥 Quick Start

### Installation

```bash
git clone https://github.com/0xfnzero/sol-parser-sdk-python
cd sol-parser-sdk-python
pip install -e .
pip install grpcio grpcio-tools protobuf base58
```

### Run Examples

```bash
# PumpFun trade filter (Buy/Sell/BuyExactSolIn/Create)
GEYSER_API_TOKEN=your_token python examples/pumpfun_trade_filter.py

# PumpSwap low-latency with performance metrics
GEYSER_API_TOKEN=your_token python examples/pumpswap_low_latency.py

# All protocols simultaneously
GEYSER_API_TOKEN=your_token python examples/multi_protocol_grpc.py
```

### Examples

| Example | Description | Command |
|---------|-------------|---------|
| **PumpFun** | | |
| `pumpfun_trade_filter` | PumpFun trade filtering (Buy/Sell/BuyExactSolIn/Create) with latency metrics | `python examples/pumpfun_trade_filter.py` |
| **PumpSwap** | | |
| `pumpswap_low_latency` | PumpSwap ultra-low latency with per-event + 10s stats | `python examples/pumpswap_low_latency.py` |
| **Multi-Protocol** | | |
| `multi_protocol_grpc` | Subscribe to all DEX protocols simultaneously | `python examples/multi_protocol_grpc.py` |

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

### Parse Logs Only (No gRPC)

```python
from sol_parser.unified_parser import parse_logs_only

logs = [
    "Program 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P invoke [1]",
    "Program data: vdt/pQ8AAA...",  # base64 encoded event
    "Program 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P success",
]

events = parse_logs_only(logs, "tx_signature", 123456789, None)
for ev in events:
    print(type(ev).__name__, ev)
```

---

## 🏗️ Supported Protocols & Events

### Event Types
Each protocol supports:
- 📈 **Trade/Swap Events** - Buy/sell transactions
- 💧 **Liquidity Events** - Deposits/withdrawals
- 🏊 **Pool Events** - Pool creation/initialization
- 🎯 **Position Events** - Open/close positions (CLMM)

### PumpFun Events
- `PumpFunBuy` - Buy token
- `PumpFunSell` - Sell token
- `PumpFunBuyExactSolIn` - Buy with exact SOL amount
- `PumpFunCreate` - Create new token
- `PumpFunTrade` - Generic trade (fallback)

### PumpSwap Events
- `PumpSwapBuy` - Buy token via pool
- `PumpSwapSell` - Sell token via pool
- `PumpSwapCreatePool` - Create liquidity pool
- `PumpSwapLiquidityAdded` - Add liquidity
- `PumpSwapLiquidityRemoved` - Remove liquidity

### Raydium Events
- `RaydiumAmmV4Swap` - AMM V4 swap
- `RaydiumClmmSwap` - CLMM swap
- `RaydiumCpmmSwap` - CPMM swap

### Orca Events
- `OrcaWhirlpoolSwap` - Whirlpool swap

### Meteora Events
- `MeteoraDammV2Swap` - DAMM V2 swap
- `MeteoraDammV2AddLiquidity` - Add liquidity
- `MeteoraDammV2RemoveLiquidity` - Remove liquidity
- `MeteoraDammV2CreatePosition` - Create position
- `MeteoraDammV2ClosePosition` - Close position

### Bonk Events
- `BonkTrade` - Bonk Launchpad trade

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
│   ├── pumpswap_low_latency.py
│   └── multi_protocol_grpc.py
└── pyproject.toml
```

---

## 🔧 Advanced Usage

### Custom gRPC Endpoint

```python
import os

endpoint = os.environ.get("GEYSER_ENDPOINT", "https://solana-yellowstone-grpc.publicnode.com:443")
token = os.environ.get("GEYSER_API_TOKEN", "")
client = GrpcClient(endpoint, token)
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

## 📄 License

MIT License

## 📞 Contact

- **Repository**: https://github.com/0xfnzero/sol-parser-sdk-python
- **Website**: https://fnzero.dev/
- **Telegram**: https://t.me/fnzero_group
- **Discord**: https://discord.gg/vuazbGkqQE
