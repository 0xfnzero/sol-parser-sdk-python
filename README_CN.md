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
    <a href="#许可证">
        <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
    </a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Solana-9945FF?style=for-the-badge&logo=solana&logoColor=white" alt="Solana">
    <img src="https://img.shields.io/badge/gRPC-4285F4?style=for-the-badge&logo=grpc&logoColor=white" alt="gRPC">
</p>

<p align="center">
    <a href="https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/README_CN.md">中文</a> |
    <a href="https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/README.md">English</a> |
    <a href="https://fnzero.dev/">Website</a> |
    <a href="https://t.me/fnzero_group">Telegram</a> |
    <a href="https://discord.gg/vuazbGkqQE">Discord</a>
</p>

当前版本：**0.10.0**。升级前请阅读 [迁移说明](RELEASE_NOTES.md)；历史变更见 [版本记录](CHANGELOG_CN.md)。

## 目录

- [SDK 版本与相关项目](#sdk-版本与相关项目)
- [怎么用](#怎么用)
- [这个 SDK 适合什么场景](#这个-sdk-适合什么场景)
- [交易来源与解析边界](#交易来源与解析边界)
- [协议](#协议)
- [文档导航](#文档导航)

<a id="sdk-版本与相关项目"></a>

## 📦 SDK 版本与相关项目

各仓库版本独立，依赖兼容要求以对应 SDK 的安装说明为准。

| 语言 | 仓库 | 用途 | 版本 |
|----------|------------|-------------|---------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) | DEX 交易与账户事件解析 | `v0.10.0` |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) | DEX 交易与账户事件解析 | `v0.10.0` |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) | DEX 交易与账户事件解析 | `v0.10.0` |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) | DEX 交易与账户事件解析 | `v0.10.0` |
| Rust | [sol-trade-sdk](https://github.com/0xfnzero/sol-trade-sdk) | 交易构建、签名与多通道提交 | `v10.0.0` |
| Node.js | [sol-trade-sdk-nodejs](https://github.com/0xfnzero/sol-trade-sdk-nodejs) | 交易构建、签名与多通道提交 | `v10.0.0` |
| Python | [sol-trade-sdk-python](https://github.com/0xfnzero/sol-trade-sdk-python) | 交易构建、签名与多通道提交 | `v10.0.0` |
| Go | [sol-trade-sdk-golang](https://github.com/0xfnzero/sol-trade-sdk-golang) | 交易构建、签名与多通道提交 | `v10.0.0` |
| Rust | [sol-shred-sdk](https://github.com/0xfnzero/sol-shred-sdk) | 原始 Shred 解码与 ShredStream 指令事件 | `v6.0.2` |
| Rust | [solana-streamer](https://github.com/0xfnzero/solana-streamer) | gRPC / ShredStream 订阅与事件流封装 | `v5.0.1` |
| Rust | [sol-trade-router-sdk](https://github.com/0xfnzero/sol-trade-router-sdk) | 链上多跳 Router 与客户端 SDK | `v0.4.0` |

<a id="怎么用"></a>


Pump.fun ALT 与官方多跳真实交易回放：`python examples/pump_execution_replay.py [交易签名]`；不传签名时离线运行。[解析行为与示例说明](docs/cross-language-sync.md)。

## 怎么用

### 1. 安装

**PyPI**

```bash
pip install sol-parser-sdk-python==0.10.0
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
# 填写 GRPC_URL（或 GRPC_ENDPOINT）、GRPC_AUTH_TOKEN 或 GRPC_TOKEN
```

在该目录下运行示例，以便加载 `.env`（与 Node 包行为一致）。

**命令行覆盖：** `--grpc-url` / `-g`、`--grpc-token` / `--token`（亦支持 `--grpc-url=https://host:443`）。**与 Rust 示例一致的名字：** `GRPC_AUTH_TOKEN`、`GRPC_ENDPOINT`（URL 别名）。**旧名：** `GEYSER_ENDPOINT` / `GEYSER_API_TOKEN`。**优先级：** 命令行 > `GRPC_URL` / `GRPC_ENDPOINT` > `GEYSER_*`；Token：命令行 > `GRPC_AUTH_TOKEN` > `GRPC_TOKEN` > `GEYSER_API_TOKEN`。已在 shell 里 `export` 的变量优先于 `.env`；`python-dotenv` 不会覆盖已有环境变量。

辅助函数：`sol_parser.env_config`（`parse_grpc_credentials`、`require_grpc_env`、`parse_shredstream_url` 等），亦可从 `sol_parser` 直接导入。

### 3. 冒烟

```bash
python examples/pumpfun_quick_test.py
```

需要 `GRPC_URL`（或 `GRPC_ENDPOINT`）以及多数提供商要求的 `GRPC_AUTH_TOKEN` 或 `GRPC_TOKEN`（写在 `.env` 或环境中），也可用命令行传入，见步骤 2。

### 4. 最小 gRPC 订阅示例

```python
import asyncio
import os

import base58

from sol_parser import parse_logs_only
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import Protocol, SubscribeCallbacks, transaction_filter_for_protocols

async def main():
    endpoint = (
        os.environ.get("GRPC_URL", "").strip()
        or os.environ.get("GRPC_ENDPOINT", "").strip()
        or os.environ.get("GEYSER_ENDPOINT", "solana-yellowstone-grpc.publicnode.com:443")
    )
    token = (
        os.environ.get("GRPC_AUTH_TOKEN", "").strip()
        or os.environ.get("GRPC_TOKEN", "").strip()
        or os.environ.get("GEYSER_API_TOKEN", "")
    )

    client = YellowstoneGrpc(endpoint)
    if token:
        client.set_x_token(token)
    await client.connect()

    filter_ = transaction_filter_for_protocols([Protocol.PUMP_FUN, Protocol.PUMP_SWAP])
    filter_.vote = False
    filter_.failed = False

    def on_update(update):
        if update.transaction is None or update.transaction.transaction is None:
            return
        tx_info = update.transaction.transaction
        slot = update.transaction.slot
        logs = tx_info.log_messages
        if not logs:
            return
        sb = bytes(tx_info.signature) if tx_info.signature else b""
        sig = base58.b58encode(sb).decode("ascii") if len(sb) == 64 else ""
        events = parse_logs_only(
            logs, sig, slot, None, subscribe_tx_info=tx_info
        )  # 来自 gRPC 的 tx_info，用于从指令账户补全字段
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

Python 已提供原生 ShredStream 客户端（`ShredStreamClient`、`ShredStreamConfig`），并保留与 Node 相同的配置方式（`parse_shredstream_url`：`SHREDSTREAM_URL` / `SHRED_URL`，`--url` / `-u` / `--endpoint=`）。安装可选依赖：`pip install 'sol-parser-sdk-python[shredstream]'`。ShredStream 使用独立端点，**不要**用 `GRPC_URL`。

已知的 Pump.fun 原生指令（包括 `create_v2` 和 V1/V2/V3 买卖）在 ALT 尚未展开时保留回调；缺失地址保持默认公钥，不猜测报价币或 Token Program。传入缓存加载地址可补全账户字段。其它协议仍要求账户完整，解析热路径不调用 RPC。旧占位行为需显式调用 `parse_shred_transaction_best_effort`。未知 Pump.fun 包装指令通过 PumpFunTrade 输出未解析候选并保留 third_program，原始 shred 无法还原任意 CPI。Inner CPI / 仅日志事件仍需 Yellowstone/RPC 路径。

<a id="这个-sdk-适合什么场景"></a>

## 这个 SDK 适合什么场景

这是 FnZero Solana DEX Parser SDK 的 Python 实现，适合 asyncio 服务、研究脚本、索引器、跟单系统、狙击交易管线和后端任务，把实时链上交易解析成统一的 DEX 事件。

| 范围 | 覆盖内容 |
|------|----------|
| 解析输入 | Yellowstone gRPC、ShredStream、RPC transactions、encoded transactions、协议账户数据 |
| DEX 协议 | PumpFun、PumpSwap、Pump Fees、Raydium LaunchLab、Raydium CPMM、Raydium CLMM、Raydium AMM V4、Meteora DAMM v2、Meteora DLMM、Meteora DBC、Orca Whirlpool |
| 使用场景 | 实时 DEX 事件解析、代币发射监控、跟单交易、狙击机器人、分析脚本、JSON 事件管线 |
| 运行环境 | Python 3.10+、asyncio worker、后端服务、数据管线、低延迟机器人基础设施 |

<a id="交易来源与解析边界"></a>

## 交易来源与解析边界

gRPC/RPC 使用提供的执行元数据和实际 CPI 指令；Shred 只能看到外层指令与本地已解析的账户。未知第三方指令在自身账户中引用 Pump.fun 时，可回调 `PumpFunTrade` 候选，携带 `third_program` 原始输入与 `Unresolved` 状态；这不证明交易已执行，也不确定方向或金额。买入／卖出专用过滤器不会把未知方向当作成交。

解析热路径不调用 RPC。按 `parse_status` 判断证据，缺失字段的默认值不代表实际零成交。账户顺序与原始指令数据保留在 `third_program`；交易序号和接收时间仍在事件元数据中，本地 Shred 序号不等于全 slot 执行顺序。详见 [第三方包装交易](docs/wrapped-pumpfun.md)及[跨语言接口与证据约定](docs/cross-language-sync.md)。

<a id="示例列表"></a>

## 示例列表

在**包根目录**执行，`pip install -e .` 之后。运行：`python examples/<文件>.py`。示例的**打印格式与环境变量命名**与 Rust 仓库 [sol-parser-sdk/examples](https://github.com/0xfnzero/sol-parser-sdk/tree/main/examples) 对齐；流式订阅在 Python 侧为 `subscribe_transactions` + `parse_logs_only`，Program ID 与 Rust `TransactionFilter::for_protocols` 一致。

| 描述 | 运行命令 | 源码 |
|------|----------|------|
| **PumpFun** | | |
| PumpFun 交易过滤 | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) | `v0.10.0` |
| PumpFun 事件 + 性能指标 | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) | `v0.10.0` |
| PumpFun 快速连接测试 | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) | `v0.10.0` |
| **PumpSwap** | | |
| PumpSwap 超低延迟 | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) | `v0.10.0` |
| PumpSwap 事件 + 性能指标 | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) | `v0.10.0` |
| **Meteora DAMM** | | |
| Meteora DAMM V2 事件 | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) | `v0.10.0` |
| **多协议** | | |
| 订阅 Rust `Protocol` / `program_ids` 中的全部程序 | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) | `v0.10.0` |
| **工具** | | |
| 按签名解析交易（HTTP RPC，非 gRPC）。`.env` 或环境中 `TX_SIGNATURE` / `RPC_URL` 或 `SOLANA_RPC_URL`，或 `--sig` / `--rpc`。 | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) | `v0.10.0` |

**环境变量：** gRPC 示例需要 **`GRPC_URL`** 或 **`GRPC_ENDPOINT`**，以及 **`GRPC_AUTH_TOKEN`** 或 **`GRPC_TOKEN`**（或旧名 `GEYSER_*`）。详见 **`.env.example`**。

<a id="协议"></a>

## 协议

PumpFun、PumpSwap、Raydium AMM V4 / CLMM / CPMM、Orca Whirlpool、Meteora DAMM V2 / DLMM、Raydium LaunchLab（见 `sol_parser/`）。

<a id="常用-api"></a>

## 常用 API

- `parse_logs_only` — 从 gRPC 日志消息解析 DEX 事件。
- `format_dex_event_json` / `dex_event_to_jsonable` — 将 `DexEvent` 格式化为缩进 JSON（一行一个字段）；直接 `print(ev)`/`repr` 为 dataclass 默认单行，不是 JSON。
- `YellowstoneGrpc` — 异步 Yellowstone 客户端（`connect`、`subscribe_transactions`、`disconnect`）。
- `now_micros` — 微秒时间戳（对应 Rust `sol_parser_sdk::core::now_micros`）。
- `transaction_filter_for_protocols` / `program_ids_for_protocols` / `account_filter_for_protocols` — 与 Rust `Protocol` + `for_protocols` 相同的 Program ID。
- `parse_grpc_credentials` / `require_grpc_env` — 加载 `.env` + 环境变量 + 命令行（与 [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) 的 `grpc_env` 对齐）。

<a id="项目结构"></a>

## 项目结构

```
sol-parser-sdk-python/
├── sol_parser/
│   ├── grpc_client.py          # YellowstoneGrpc（异步连接 / 订阅）
│   ├── env_config.py           # GRPC_URL、.env、命令行（与 Node 对齐）
│   ├── clock.py                # now_micros()
│   ├── grpc_types.py           # TransactionFilter、SubscribeCallbacks、for_protocols 等
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

<a id="开发"></a>

## 开发

```bash
pip install -e ".[dev]"
pytest tests/
```

<a id="api-兼容性"></a>

## API 兼容性

完整跨语言 API 对齐仍在进行；公开行为和支持边界见 [API 迁移说明](docs/USAGE.md#api-compatibility)，使用方法见 examples 目录。

PumpFun create/create_v2 的共享主网样本、重放方法和验证边界见 [验证说明](https://github.com/0xfnzero/sol-parser-sdk-golang/tree/main/validation/pumpfun_create_20261007)。

### Pump ShredStream 离线回归

用户示例位于 examples，自动回归测试单独维护。旧路由意图模拟入口及其无引用快照已移除；当前包装交易回放与过滤语义见 [包装交易说明](docs/wrapped-pumpfun.md)。Shred 只解码已解析完整的外层账户；第三方候选通过 PumpFunTrade 的 third_program 透传，不能当作已确认成交，热路径不调用 RPC。

<a id="文档导航"></a>

## 文档导航

- [发布与迁移](RELEASE_NOTES.md)
- [使用指南](docs/USAGE.md)
- [跨语言功能与边界](docs/cross-language-sync.md)


<a id="许可证"></a>

## 许可证

MIT — https://github.com/0xfnzero/sol-parser-sdk-python

<a id="联系我们"></a>

## 联系我们

- **仓库**: https://github.com/0xfnzero/sol-parser-sdk-python
- **官网**: https://fnzero.dev/
- **Telegram**: https://t.me/fnzero_group
- **Discord**: https://discord.gg/vuazbGkqQE


股票池同步：33 种官方股票/ETF、58 个股票池；配置扩展、USDC 起点、缓存选路与使用边界见 [11 SDK 同步说明](docs/STOCK_BRIDGE_SYNC.md)。
