<div align="center">

## v0.5.17 — Shred 元数据透传与顺序范围

保留并验证 `tx_index`、接收时间从解析入口传到原始指令回调。明确 Entries 消息内序号与 Yellowstone 节点 index 的区别：本地序号不是全 slot 索引；跨消息去重使用交易签名。此版本完善文档和回归保护，不改变现有字段或编号规则。


## v0.5.17 — RawInstruction 协议过滤与 DEX 枚举

修复原始指令绕过 DEX 订阅范围的问题。按单条指令引用的官方程序识别 DEX，使用 `RawInstructionDexType` 枚举；JSON 字符串保持不变。未知 router 不推断池子地址、买卖方向或方法版本。


## v0.5.17 — Pump 执行事件与最新回放示例

修复官方 Anchor CPI TradeEvent 前缀识别，保留历史编码兼容。RPC/gRPC 的实际 `sol_amount`、`quote_amount`、`token_amount` 只从执行事件合并；预算和最小输出保留在指令参数字段。如果日志及事件 CPI 均缺失，实际金额字段为 0（表示无执行数据，不代表已确认零成交）。非 SOL 报价金额不能当作 SOL。

在本仓库运行 `.venv/bin/python examples/pump_execution_replay.py`，离线回放 2026-10-19 重新抓取的真实交易。示例输出完整日志、无日志、截断日志三种结果；命令末尾追加最新签名可在线验证。通过 `SOLANA_RPC_URL` 选择 RPC，支持 transaction v1。

新 Delta 卖出样本：`4ARos3Yq1SMNE3izDpy9YdKrRgMmD7UCDxvnVrBRaGCJHiifPHSmQWc4DPfjUaEUcxS7puGmEN64K7EZdeXLJaj2`，slot 458542546。日期样本文件还包含 Rapid 创建后买入、BuyV3 和 PumpSwap 买入的完整签名及 slot。旧的五种双跳组合仅作为回归样本，未冒充本次新抓取交易。

## v0.5.17 — Shred 原始指令透传

默认 Shred 入口将未适配的第三方程序（包括 Rapid/Delta）作为 `RawInstruction` 返回，不再推断买卖方向、金额或内部 buy 版本。System、Token、ATA、ComputeBudget 等基础程序默认不透传；已支持的官方 DEX 指令继续正常解析，官方 Pump/PumpSwap 多跳仍返回 `PumpRouteIntent`。

事件包含 `program_id`、`instruction_index`、`accounts`、`account_indices`、`instruction_data` 和交易 metadata。账户保留原顺序与重复项；未解析 ALT 地址为 null/None，原始索引仍保留。使用缓存 loaded-addresses/resolver 补齐，热路径不请求 RPC。data 是完整原始字节，不要求已知布局。

运行 `uv run python examples/raw_instruction_filter.py` 对比同一组已签名交易的 PumpFun、Raydium CPMM 与全量原始指令订阅；输出包含 `dexes`。

原始事件保留调用方传入的 `metadata.tx_index` 和 `metadata.grpc_recv_us`（streamer 对应 `metadata.recv_us`）。默认 Entries 客户端的交易序号仅在单条接收消息内递增，下一条消息从 0 重新计数，不等于已确认的整个 slot 交易序号。`instruction_index` 表示交易内外层指令顺序；接收时间是本地微秒时间戳，不保证链上执行顺序。独立回放 API 可能默认填 0，调用时应传入上游已有的序号与接收时间。

无过滤器时返回未知第三方指令。宽泛交易/Swap 订阅（如 `PumpFunTrade`、`RaydiumCpmmSwap`）也返回关联该 DEX 的原始指令；买/卖方向订阅不推测方向。显式 `RawInstruction` 仅在未限制协议时返回全部外层指令，streamer 的协议限制始终生效；显式排除 `RawInstruction` 优先。`dex_type` 使用公开枚举 `RawInstructionDexType`（Go 为命名字符串类型与常量）；JSON 仍为 `"pumpfun"`、`"raydium_cpmm"` 等原有字符串。`dexes` 数组包含各关联 DEX 的 `{ dex_type, program_id, pool }`，只识别本条指令直接调用或账户中引用的 DEX 程序，不借用同笔其他指令的账户；多 DEX 包装保留所有关联。未知或未解析 ALT 中的程序不能匹配 DEX 订阅。`pool` 当前为 null：未知包装布局无法确定池子账户。program 引用不证明执行了 CPI，原始回调不是成交。

已有 wrapper 适配函数仅作为显式调用的兼容接口保留，不参与默认 Shred 解码。以下已发布版本的历史说明描述旧行为。

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

## 📦 SDK 版本与相关项目

解析 SDK 的各语言版本及相关 Rust SDK：

| 语言 | 仓库 | 描述 | 版本 |
|------|------|------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) | Solana DEX 交易与账户事件解析 | `v0.7.18` |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) | TypeScript/JavaScript，Node.js 支持 | `v0.5.24` |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) | 原生 async/await 支持 | `v0.5.17` |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) | Go 交易与账户事件解析 | `v0.5.17` |
| **Rust** | [sol-shred-sdk](https://github.com/0xfnzero/sol-shred-sdk) | Solana 原始 shred 解码与 ShredStream DEX 事件解析 | `v4.0.9` |
| **Rust** | [sol-trade-sdk](https://github.com/0xfnzero/sol-trade-sdk) | Solana DEX 交易构建与交易执行 | `v6.0.2` |

---

## 这个 SDK 适合什么场景

这是 FnZero Solana DEX Parser SDK 的 Python 实现，适合 asyncio 服务、研究脚本、索引器、跟单系统、狙击交易管线和后端任务，把实时链上交易解析成统一的 DEX 事件。

| 范围 | 覆盖内容 |
|------|----------|
| 解析输入 | Yellowstone gRPC、ShredStream、RPC transactions、encoded transactions、协议账户数据 |
| DEX 协议 | PumpFun、PumpSwap、Pump Fees、Raydium LaunchLab、Raydium CPMM、Raydium CLMM、Raydium AMM V4、Meteora DAMM v2、Meteora DLMM、Meteora DBC、Orca Whirlpool |
| 使用场景 | 实时 DEX 事件解析、代币发射监控、跟单交易、狙击机器人、分析脚本、JSON 事件管线 |
| 运行环境 | Python 3.10+、asyncio worker、后端服务、数据管线、低延迟机器人基础设施 |

---

## 发布说明

## v0.5.14 — Pump 路由方向与指令名称

路由事件沿用 `is_buy`、`ix_name` 命名。RapidBuy 为买入意图，指令名为官方 IDL 的 `buy_exact_quote_in_v2`；BuyPumpDelta 仅确定买入方向。多跳路由方向和无法确定的方法保持为空。币种读取 `hops[].base_mint` / `quote_mint`。这些字段不代表已成交；过滤器不会把路由事件转换为交易事件。

旧 JSON 缺少新字段时保持未知。Rust 结构体字面量须补齐新字段；Go 新字段为指针，Node.js/Python 未知值为 null/None。Streamer 新增 `DexEvent::PumpRouteIntentEvent` 并保留路由字段，支持协议与事件过滤。

## v0.5.13 — Pump routes and offline replay

Adds native Pump route-intent parsing for official multi-hop instructions and the exact RapidBuy/BuyPumpDelta wrapper layouts captured in reported transactions. Adds locally cached ALT resolution and rejects unresolved account identities by default, with explicit best-effort compatibility APIs where supported. Route intents expose instruction constraints and hop identities; confirmed execution amounts require execution metadata.

Includes the latest complete implementation, signed transaction fixtures, native offline-bank regression examples and reproducible local hot-path benchmarks. Unknown wrapper layouts are not inferred from embedded bytes. Local tests do not measure production network latency.

## v0.5.12 — Pump depth-2 compatibility

Adds signed Pump depth-2 create-event replay coverage, including ALT-loaded accounts and executed logs. Existing event layouts and public parsing interfaces remain unchanged.

Validation includes official Pump SDK 4.1.0 instruction comparisons, signed local LiteSVM simulations and SDK regressions. Local simulation state/config is synthetic; no funded transactions were broadcast and production latency was not measured.

## v0.5.11 — Signed transaction and hot-path hardening

Hardens signed transaction sanitization, loaded-address boundaries, ordered stream filtering and parser lifecycle. Aligns CLMM and DEX instruction/event layouts, nested CPI route attribution and liquidity/reward accounting. Adds independently signed wire fixtures, ALT failure cases and offline bank regressions.

Validation includes local CPU benchmarks and offline signed-bank scenarios. Measured hot paths use cached inputs without RPC. Benchmarks do not establish production network or transaction-landing latency. No funded mainnet transactions were broadcast.

### v0.5.10

- 按实际指令 discriminator 和事件 mint 匹配 PumpFun create/create_v2 账户，支持 CPI，并拒绝猜测有歧义的匹配。
- 停止从 create_v2 的任意尾部账户推断 quote mint、vault、token program，保留权威解码字段。
- 恢复历史 CreateEvent 布局，并通过保存的真实主网成功、失败交易验证。
- 过滤失败交易中已经回滚的 Create/Buy 等 DEX 事件，并在 RPC/gRPC 转换中保留失败状态。

### v0.5.9

- Adds native gRPC lifecycle and block metadata support, instruction-level route analysis and StonkFun registry/snapshot examples.
- Improves exact metadata serialization, account matching and wire transaction bounds validation.
- Includes native alignment evidence and simulation route fixtures. These language releases do not yet implement the new CPMM creator-fee collection event API.

### v0.5.8

- 与 Rust **sol-parser-sdk 0.7.3** 对齐，覆盖当前 PumpFun、PumpSwap 与 Pump Fees 协议定义。
- 新增 Meteora DAMM v2：`UpdateDelegatePermission`、`WithdrawDeadLiquidityReward`、`CreateConfig`、`CreateDynamicConfig`。
- 修复 DAMM v2 `EvtSwap2` 完整 180 字节布局、三种 SwapMode、transfer fee、reserve，以及 compounding-fee 布局激活槽位 `406048752`。
- 统一 `EvtLiquidityChange` 按 `change_type` 路由为 AddLiquidity / RemoveLiquidity。
- 补充 DLMM mint/用户 token/`min_amount_out`、PumpFun 交易前后余额、LaunchLab quote/global/platform 账户字段。
- 在 PumpFun/PumpSwap instruction、log、account、gRPC 与 JSON 事件链路中补齐 creator fee 和 holder reward 字段。
- 拒绝 PumpSwap trade 与 CreatePool 已知字段的截断尾部，同时兼容完整历史布局。

### v0.5.6

- 新增 Meteora DBC 日志解析，并按当前 program context 做路由与过滤。
- 新增 Raydium CLMM/CPMM、Orca account parser 与导出。
- 修复默认无 filter 的 RPC/Yellowstone 指令解析，不再被误当作空 include-only filter。
- RPC 指令账户表合并 ALT loaded writable/readonly keys。
- ShredStream/RPC 对 account-only 或空 include-only filter 直接跳过指令解析。

### v0.5.5

- ShredStream 低延迟静态账户路径与 Rust/Node.js/Go 对齐。
- V0 ALT-loaded 指令账户不再整条跳过，而是用默认 pubkey 占位继续 best-effort 解析。
- 当 ShredStream 外层 program id 来自 ALT 时，按 discriminator 做候选 program id fallback。
- 修复 Pump.fun ShredStream create/create_v2 fallback，确保按 instruction-order 账户解析。
- 改进 Pump.fun v2 短账户解析、事件类型过滤和多协议路由一致性。

---

## 怎么用

### 1. 安装

**PyPI**

```bash
pip install sol-parser-sdk-python==0.5.17
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

Python ShredStream 热路径默认严格解析静态账户；V0 ALT 指令需传入加载地址或读取预热缓存的 slot-aware resolver，未解析完整时跳过。旧占位行为需显式调用 `parse_shred_transaction_best_effort`。受支持的包装与官方路由输出 `PumpRouteIntent`，原始 shred 无法还原任意 CPI。Inner CPI / 仅日志事件仍需 Yellowstone/RPC 路径。

---

## 示例列表

在**包根目录**执行，`pip install -e .` 之后。运行：`python examples/<文件>.py`。示例的**打印格式与环境变量命名**与 Rust 仓库 [sol-parser-sdk/examples](https://github.com/0xfnzero/sol-parser-sdk/tree/main/examples) 对齐；流式订阅在 Python 侧为 `subscribe_transactions` + `parse_logs_only`，Program ID 与 Rust `TransactionFilter::for_protocols` 一致。

| 描述 | 运行命令 | 源码 |
|------|----------|------|
| **PumpFun** | | |
| PumpFun 交易过滤 | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) | `v0.5.17` |
| PumpFun 事件 + 性能指标 | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) | `v0.5.17` |
| PumpFun 快速连接测试 | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) | `v0.5.17` |
| **PumpSwap** | | |
| PumpSwap 超低延迟 | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) | `v0.5.17` |
| PumpSwap 事件 + 性能指标 | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) | `v0.5.17` |
| **Meteora DAMM** | | |
| Meteora DAMM V2 事件 | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) | `v0.5.17` |
| **多协议** | | |
| 订阅 Rust `Protocol` / `program_ids` 中的全部程序 | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) | `v0.5.17` |
| **工具** | | |
| 按签名解析交易（HTTP RPC，非 gRPC）。`.env` 或环境中 `TX_SIGNATURE` / `RPC_URL` 或 `SOLANA_RPC_URL`，或 `--sig` / `--rpc`。 | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) | `v0.5.17` |

**环境变量：** gRPC 示例需要 **`GRPC_URL`** 或 **`GRPC_ENDPOINT`**，以及 **`GRPC_AUTH_TOKEN`** 或 **`GRPC_TOKEN`**（或旧名 `GEYSER_*`）。详见 **`.env.example`**。

---

## 协议

PumpFun、PumpSwap、Raydium AMM V4 / CLMM / CPMM、Orca Whirlpool、Meteora DAMM V2 / DLMM、Raydium LaunchLab（见 `sol_parser/`）。

---

## 常用 API

- `parse_logs_only` — 从 gRPC 日志消息解析 DEX 事件。
- `format_dex_event_json` / `dex_event_to_jsonable` — 将 `DexEvent` 格式化为缩进 JSON（一行一个字段）；直接 `print(ev)`/`repr` 为 dataclass 默认单行，不是 JSON。
- `YellowstoneGrpc` — 异步 Yellowstone 客户端（`connect`、`subscribe_transactions`、`disconnect`）。
- `now_micros` — 微秒时间戳（对应 Rust `sol_parser_sdk::core::now_micros`）。
- `transaction_filter_for_protocols` / `program_ids_for_protocols` / `account_filter_for_protocols` — 与 Rust `Protocol` + `for_protocols` 相同的 Program ID。
- `parse_grpc_credentials` / `require_grpc_env` — 加载 `.env` + 环境变量 + 命令行（与 [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) 的 `grpc_env` 对齐）。

---

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

## API 兼容性

完整跨语言 API 对齐仍在进行；公开行为和支持边界见 [API 迁移说明](docs/USAGE.md#api-compatibility)，使用方法见 examples 目录。

PumpFun create/create_v2 的共享主网样本、重放方法和验证边界见 [验证说明](https://github.com/0xfnzero/sol-parser-sdk-golang/tree/main/validation/pumpfun_create_20261007)。

### Pump ShredStream 离线回归

已同步路由意图事件、严格 ALT 缓存解析和本语言原生签名回放／SBF 模拟示例。运行命令、缓存 API、冻结数据来源与测试范围见 [examples/offline_bank/README.md](examples/offline_bank/README.md)。默认跳过账户未解析完整的指令；旧行为需显式使用 best-effort 入口。路由意图不等于已成交事件，解析热路径不调用 RPC。
