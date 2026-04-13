<div align="center">
    <h1>⚡ Sol Parser SDK - Python</h1>
    <h3><em>高性能 Solana DEX 事件解析（Python / asyncio）</em></h3>
</div>

<p align="center">
    <strong>通过 Yellowstone gRPC 实时解析 Solana DEX 事件的 Python 库</strong>
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
    <a href="https://fnzero.dev/">官网</a> |
    <a href="https://t.me/fnzero_group">Telegram</a> |
    <a href="https://discord.gg/vuazbGkqQE">Discord</a>
</p>

---

## 其他语言 SDK

| 语言 | 仓库 |
|------|------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) |

---

## 怎么用

### 1. 安装

**PyPI**

```bash
pip install sol-parser-sdk-python
```

**源码**

```bash
git clone https://github.com/0xfnzero/sol-parser-sdk-python
cd sol-parser-sdk-python
pip install -e .
pip install grpcio grpcio-tools protobuf base58 python-dotenv
```

### 2. 环境变量（Yellowstone gRPC 示例）

在**包根目录**（与 `pyproject.toml` 同级）：

```bash
cp .env.example .env
# 填写 GRPC_URL、GRPC_TOKEN
```

在该目录下运行示例，以便加载 `.env`（与 Node 包行为一致）。

**命令行覆盖：** `--grpc-url` / `-g`、`--grpc-token` / `--token`（亦支持 `--grpc-url=https://host:443`）。**旧名：** `GEYSER_ENDPOINT` / `GEYSER_API_TOKEN`。**优先级：** 已在 shell 里 `export` 的变量优先于 `.env`；`python-dotenv` 不会覆盖已有环境变量。

辅助函数：`sol_parser.env_config`（`parse_grpc_credentials`、`require_grpc_env`、`parse_shredstream_url` 等），亦可从 `sol_parser` 直接导入。

### 3. 冒烟

```bash
python examples/pumpfun_quick_test.py
```

需要 `GRPC_URL` 以及多数提供商要求的 `GRPC_TOKEN`（写在 `.env` 或环境中），也可用命令行传入，见步骤 2。

### 4. 最小 gRPC 订阅示例

```python
import asyncio
import os

from sol_parser import parse_logs_only
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import TransactionFilter, SubscribeCallbacks

async def main():
    endpoint = (
        os.environ.get("GRPC_URL", "").strip()
        or os.environ.get("GEYSER_ENDPOINT", "solana-yellowstone-grpc.publicnode.com:443")
    )
    token = os.environ.get("GRPC_TOKEN", "").strip() or os.environ.get("GEYSER_API_TOKEN", "")

    client = YellowstoneGrpc(endpoint)
    if token:
        client.set_x_token(token)
    await client.connect()

    filter_ = TransactionFilter(
        account_include=[
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # PumpFun
            "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ",  # PumpSwap
        ],
        account_exclude=[],
        account_required=[],
        vote=False,
        failed=False,
    )

    def on_update(update):
        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return
        sig = tx_info.signature.hex()
        events = parse_logs_only(logs, sig, slot, None)
        for ev in events:
            print(ev)

    sub = await client.subscribe_transactions(
        filter_,
        SubscribeCallbacks(on_update=on_update, on_error=print, on_end=lambda: None),
    )
    print("subscribed", sub.id)

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    await client.disconnect()

asyncio.run(main())
```

更轻量：仅用日志时用 `parse_logs_only`（无需完整线格式交易）。

### 5. ShredStream（HTTP，不是 Yellowstone gRPC）

Node 版提供 ShredStream HTTP 客户端。**Python** 侧提供与 Node 相同的配置方式（`parse_shredstream_url`：`SHREDSTREAM_URL` / `SHRED_URL`，`--url` / `-u` / `--endpoint=`）；原生 ShredStream 客户端后续可能补充。**不要**用 `GRPC_URL` 配 ShredStream。

---

## 示例列表

在**包根目录**执行，`pip install -e .` 之后。运行：`python examples/<文件>.py`。

| 描述 | 运行命令 | 源码 |
|------|----------|------|
| **PumpFun** | | |
| PumpFun 交易过滤 | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) |
| PumpFun 事件 + 性能指标 | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) |
| PumpFun 快速连接测试 | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) |
| **PumpSwap** | | |
| PumpSwap 超低延迟 | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) |
| PumpSwap 事件 + 性能指标 | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) |
| **Meteora DAMM** | | |
| Meteora DAMM V2 事件 | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) |
| **多协议** | | |
| 同时订阅所有 DEX 协议 | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) |
| **工具** | | |
| 按签名解析交易（HTTP RPC，非 gRPC）。`.env` 或环境中 `TX_SIGNATURE` / `RPC_URL`，或 `--sig` / `--rpc`。 | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) |

**环境变量：** gRPC 示例需要 **`GRPC_URL`**、**`GRPC_TOKEN`**（或旧名 `GEYSER_*`）。详见 **`.env.example`**。

---

## 协议

PumpFun、PumpSwap、Raydium AMM V4 / CLMM / CPMM、Orca Whirlpool、Meteora DAMM V2 / DLMM、Bonk Launchpad（见 `sol_parser/`）。

---

## 常用 API

- `parse_logs_only` — 从 gRPC 日志消息解析 DEX 事件。
- `YellowstoneGrpc` — 异步 Yellowstone 客户端（`connect`、`subscribe_transactions`、`disconnect`）。
- `parse_grpc_credentials` / `require_grpc_env` — 加载 `.env` + 环境变量 + 命令行（与 [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) 的 `grpc_env` 对齐）。

---

## 项目结构

```
sol-parser-sdk-python/
├── sol_parser/
│   ├── grpc_client.py          # YellowstoneGrpc（异步连接 / 订阅）
│   ├── env_config.py           # GRPC_URL、.env、命令行（与 Node 对齐）
│   ├── grpc_types.py           # TransactionFilter、SubscribeCallbacks…
│   ├── parser.py               # parse_logs_only…
│   ├── geyser_pb2.py           # 生成的 proto（Yellowstone）
│   └── …
├── examples/
│   ├── pumpfun_trade_filter.py
│   ├── pumpfun_quick_test.py
│   └── …
├── .env.example
└── pyproject.toml
```

---

## 开发

```bash
pip install -e ".[dev]"
pytest tests/
```

---

## 许可证

MIT — https://github.com/0xfnzero/sol-parser-sdk-python

---

## 联系我们

- **仓库**: https://github.com/0xfnzero/sol-parser-sdk-python  
- **官网**: https://fnzero.dev/  
- **Telegram**: https://t.me/fnzero_group  
- **Discord**: https://discord.gg/vuazbGkqQE  
