<div align="center">
    <h1>⚡ Sol Parser SDK - Python</h1>
    <h3><em>高性能 Solana DEX 事件解析器，专为 Python 设计</em></h3>
</div>

<p align="center">
    <strong>通过 Yellowstone gRPC 实时解析 Solana DEX 事件的 Python 库</strong>
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
    <a href="https://fnzero.dev/">官网</a> |
    <a href="https://t.me/fnzero_group">Telegram</a> |
    <a href="https://discord.gg/vuazbGkqQE">Discord</a>
</p>

---

## 📊 性能亮点

### ⚡ 实时解析
- **零延迟** 基于日志的事件解析
- **gRPC 流式传输** 支持 Yellowstone/Geyser 协议
- **原生 async/await** 支持 asyncio 异步编程
- **多协议** 单次订阅同时监听多个 DEX

### 🏗️ 支持的协议
- ✅ **PumpFun** - Meme 代币交易
- ✅ **PumpSwap** - PumpFun 交换协议
- ✅ **Raydium AMM V4** - 自动做市商
- ✅ **Raydium CLMM** - 集中流动性
- ✅ **Raydium CPMM** - 集中池
- ✅ **Orca Whirlpool** - 集中流动性 AMM
- ✅ **Meteora DAMM V2** - 动态 AMM
- ✅ **Meteora DLMM** - 动态流动性做市商
- ✅ **Bonk Launchpad** - 代币发射平台

---

## 🔥 快速开始

### 安装

```bash
git clone https://github.com/0xfnzero/sol-parser-sdk-python
cd sol-parser-sdk-python
pip install -e .
pip install grpcio grpcio-tools protobuf base58
```

### 运行示例

```bash
# PumpFun 交易过滤（Buy/Sell/BuyExactSolIn/Create）
GEYSER_API_TOKEN=your_token python examples/pumpfun_trade_filter.py

# PumpSwap 超低延迟，附带性能指标
GEYSER_API_TOKEN=your_token python examples/pumpswap_low_latency.py

# 同时订阅所有协议
GEYSER_API_TOKEN=your_token python examples/multi_protocol_grpc.py
```

### 示例列表

| 示例 | 描述 | 命令 |
|------|------|------|
| **PumpFun** | | |
| `pumpfun_trade_filter` | PumpFun 交易过滤（Buy/Sell/BuyExactSolIn/Create），附带延迟指标 | `python examples/pumpfun_trade_filter.py` |
| **PumpSwap** | | |
| `pumpswap_low_latency` | PumpSwap 超低延迟，含每笔交易 + 10 秒汇总统计 | `python examples/pumpswap_low_latency.py` |
| **多协议** | | |
| `multi_protocol_grpc` | 同时订阅所有 DEX 协议 | `python examples/multi_protocol_grpc.py` |

### 基本用法

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

## 🏗️ 支持的协议与事件

### 事件类型
每个协议均支持：
- 📈 **交易/兑换事件** - 买入/卖出交易
- 💧 **流动性事件** - 存入/提取
- 🏊 **池子事件** - 池子创建/初始化
- 🎯 **仓位事件** - 开仓/平仓（CLMM）

### PumpFun 事件
- `PumpFunBuy` - 买入代币
- `PumpFunSell` - 卖出代币
- `PumpFunBuyExactSolIn` - 指定 SOL 数量买入
- `PumpFunCreate` - 创建新代币
- `PumpFunTrade` - 通用交易（兜底）

### PumpSwap 事件
- `PumpSwapBuy` - 通过池子买入代币
- `PumpSwapSell` - 通过池子卖出代币
- `PumpSwapCreatePool` - 创建流动性池
- `PumpSwapLiquidityAdded` - 添加流动性
- `PumpSwapLiquidityRemoved` - 移除流动性

### Raydium 事件
- `RaydiumAmmV4Swap` - AMM V4 兑换
- `RaydiumClmmSwap` - CLMM 兑换
- `RaydiumCpmmSwap` - CPMM 兑换

### Orca 事件
- `OrcaWhirlpoolSwap` - Whirlpool 兑换

### Meteora 事件
- `MeteoraDammV2Swap` - DAMM V2 兑换
- `MeteoraDammV2AddLiquidity` - 添加流动性
- `MeteoraDammV2RemoveLiquidity` - 移除流动性
- `MeteoraDammV2CreatePosition` - 创建仓位
- `MeteoraDammV2ClosePosition` - 关闭仓位

### Bonk 事件
- `BonkTrade` - Bonk Launchpad 交易

---

## 📁 项目结构

```
sol-parser-sdk-python/
├── sol_parser/
│   ├── grpc_client.py          # GrpcClient（异步连接与订阅）
│   ├── grpc_types.py           # TransactionFilter、TransactionUpdate 等
│   ├── unified_parser.py       # parse_logs_only、parse_transaction_events
│   ├── optimized_matcher.py    # 日志解析（所有协议）
│   ├── geyser_pb2.py           # 生成的 proto（Yellowstone）
│   ├── geyser_pb2_grpc.py      # 生成的 gRPC 存根
│   ├── solana_storage_pb2.py   # 生成的 proto（Solana 存储）
│   └── ...
├── examples/
│   ├── pumpfun_trade_filter.py
│   ├── pumpswap_low_latency.py
│   └── multi_protocol_grpc.py
└── pyproject.toml
```

---

## 🔧 高级用法

### 自定义 gRPC 端点

```python
import os

endpoint = os.environ.get("GEYSER_ENDPOINT", "https://solana-yellowstone-grpc.publicnode.com:443")
token = os.environ.get("GEYSER_API_TOKEN", "")
client = GrpcClient(endpoint, token)
```

### 异步定时统计

```python
import asyncio

total_events = 0

async def stats_reporter():
    while True:
        await asyncio.sleep(10)
        print(f"过去 10 秒总事件数: {total_events}")

asyncio.create_task(stats_reporter())
```

---

## 📄 许可证

MIT License

## 📞 联系我们

- **仓库**: https://github.com/0xfnzero/sol-parser-sdk-python
- **官网**: https://fnzero.dev/
- **Telegram**: https://t.me/fnzero_group
- **Discord**: https://discord.gg/vuazbGkqQE
