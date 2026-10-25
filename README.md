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
    <a href="#license">
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

Current version: **0.10.0**. Read the [migration notes](RELEASE_NOTES.md) before upgrading; see the [changelog](CHANGELOG.md) for historical changes.

## Contents

- [SDK Versions and Related SDKs](#sdk-versions-and-related-sdks)
- [How to use](#how-to-use)
- [What This SDK Is For](#what-this-sdk-is-for)
- [Trade provenance and parsing boundaries](#trade-provenance-and-parsing-boundaries)
- [Examples](#examples)
- [Protocols](#protocols)
- [Documentation](#documentation)

<a id="sdk-versions-and-related-sdks"></a>

## 📦 SDK Versions and Related SDKs

Repositories are versioned independently; follow each SDK’s installation guide for compatible dependencies.

| Language | Repository | Purpose | Version |
|----------|------------|-------------|---------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) | DEX transaction and account event parsing | `v0.10.0` |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) | DEX transaction and account event parsing | `v0.10.0` |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) | DEX transaction and account event parsing | `v0.10.0` |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) | DEX transaction and account event parsing | `v0.10.0` |
| Rust | [sol-trade-sdk](https://github.com/0xfnzero/sol-trade-sdk) | Transaction building, signing and multi-channel submission | `v10.0.0` |
| Node.js | [sol-trade-sdk-nodejs](https://github.com/0xfnzero/sol-trade-sdk-nodejs) | Transaction building, signing and multi-channel submission | `v10.0.0` |
| Python | [sol-trade-sdk-python](https://github.com/0xfnzero/sol-trade-sdk-python) | Transaction building, signing and multi-channel submission | `v10.0.0` |
| Go | [sol-trade-sdk-golang](https://github.com/0xfnzero/sol-trade-sdk-golang) | Transaction building, signing and multi-channel submission | `v10.0.0` |
| Rust | [sol-shred-sdk](https://github.com/0xfnzero/sol-shred-sdk) | Raw shred decoding and ShredStream instruction events | `v6.0.2` |
| Rust | [solana-streamer](https://github.com/0xfnzero/solana-streamer) | gRPC / ShredStream subscriptions and event streaming | `v5.0.1` |
| Rust | [sol-trade-router-sdk](https://github.com/0xfnzero/sol-trade-router-sdk) | On-chain multi-hop router and client SDK | `v0.4.0` |

<a id="how-to-use"></a>


Replay the reported Pump.fun ALT and official multi-hop transactions: `python examples/pump_execution_replay.py [SIGNATURE]`. See [parsing behavior and native examples](docs/cross-language-sync.md).

## How to use

### 1. Install

**From PyPI**

```bash
pip install sol-parser-sdk-python==0.10.0
```

**From source**

```bash
git clone https://github.com/0xfnzero/sol-parser-sdk-python
cd sol-parser-sdk-python
pip install -e .
pip install grpcio grpcio-tools protobuf base58 python-dotenv
```

### 2. Environment (Yellowstone gRPC examples)

At the **package root** (next to `pyproject.toml`):

```bash
cp .env.example .env
# Set GRPC_URL (or GRPC_ENDPOINT) and GRPC_AUTH_TOKEN or GRPC_TOKEN
```

Run examples from that directory so `.env` is picked up (same idea as the Node.js package).

**CLI overrides:** `--grpc-url` / `-g`, `--grpc-token` / `--token` (also `--grpc-url=https://host:443`). **Rust-compatible names:** `GRPC_AUTH_TOKEN` (same as [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) examples), `GRPC_ENDPOINT` (alias for URL). **Legacy env:** `GEYSER_ENDPOINT` / `GEYSER_API_TOKEN`. **Precedence:** CLI > `GRPC_URL` / `GRPC_ENDPOINT` > `GEYSER_*` > defaults; token: CLI > `GRPC_AUTH_TOKEN` > `GRPC_TOKEN` > `GEYSER_API_TOKEN`. Explicit shell `export` wins over `.env`; `python-dotenv` does not overwrite existing variables.

Helpers: `sol_parser.env_config` (`parse_grpc_credentials`, `require_grpc_env`, `parse_shredstream_url`, …), re-exported from `sol_parser`.

### 3. Smoke test

```bash
python examples/pumpfun_quick_test.py
```

Requires `GRPC_URL` (or `GRPC_ENDPOINT`) and (for most providers) `GRPC_AUTH_TOKEN` or `GRPC_TOKEN` in `.env` or the environment. You can pass credentials on the command line instead; see step 2.

### 4. Minimal gRPC subscribe + parse

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
        )  # tx_info from gRPC update — fills accounts from instruction keys
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

**Lighter path:** `parse_logs_only(logs, …)` only needs log messages from the update (no full wire transaction).

### 5. ShredStream (HTTP — not Yellowstone gRPC)

Python includes a native ShredStream client (`ShredStreamClient`, `ShredStreamConfig`) plus the same env/CLI helpers as Node (`parse_shredstream_url`: `SHREDSTREAM_URL` / `SHRED_URL`, `--url` / `-u` / `--endpoint=`). Install the optional extra with `pip install 'sol-parser-sdk-python[shredstream]'`. ShredStream uses its own endpoint, **not** `GRPC_URL`.

Known native Pump.fun instructions, including `create_v2` and V1/V2/V3 trades, retain callbacks with static keys even when declared ALT accounts are not yet loaded. Unavailable addresses stay at the default public key; unknown quote mints and token programs are never assumed. Load cached addresses for complete account fields. Other protocols still require resolved accounts. No RPC is performed by the parsing hot path. Legacy placeholders require the explicit `parse_shred_transaction_best_effort` API. Unknown Pump.fun wrappers produce unresolved PumpFunTrade candidates with third_program; raw shreds cannot reconstruct arbitrary CPI. Inner CPI/log-only events still require the Yellowstone/RPC paths.

<a id="what-this-sdk-is-for"></a>

## What This SDK Is For

This is the Python implementation of the FnZero Solana DEX parser SDK for asyncio services, research scripts, indexers, copy-trading systems, sniper pipelines, and backend jobs that need normalized real-time DEX events.

| Area | Coverage |
|------|----------|
| Parser inputs | Yellowstone gRPC, ShredStream, RPC transactions, encoded transactions, protocol account data |
| DEX protocols | PumpFun, PumpSwap, Pump Fees, Raydium LaunchLab, Raydium CPMM, Raydium CLMM, Raydium AMM V4, Meteora DAMM v2, Meteora DLMM, Meteora DBC, Orca Whirlpool |
| Use cases | Real-time DEX event parsing, token launch monitoring, copy trading, sniper bots, analytics notebooks, JSON event pipelines |
| Runtime | Python 3.10+, asyncio workers, backend services, data pipelines, low-latency bot infrastructure |

<a id="trade-provenance-and-parsing-boundaries"></a>

## Trade provenance and parsing boundaries

gRPC/RPC use supplied execution metadata and actual CPI instructions; Shred sees outer instructions and locally resolved accounts. An unknown third-party instruction referencing Pump.fun in its own accounts can produce a `PumpFunTrade` candidate with the original input in `third_program` and `Unresolved` status. This does not establish execution, direction or amounts. Buy/sell-only filters do not treat an unknown direction as a fill.

The parsing hot path performs no RPC. Check `parse_status` before interpreting defaults as amounts. Original account order and instruction bytes remain in `third_program`; transaction position and receive time remain in event metadata. A local Shred index is not confirmed slot-wide execution order. See [wrapped transactions](docs/wrapped-pumpfun.md) and [cross-language contracts](docs/cross-language-sync.md).

<a id="examples"></a>

## Examples

From the **package root** after `pip install -e .`. Run with `python examples/<file>.py`. Scripts are written to mirror the **output layout and env names** of [sol-parser-sdk/examples](https://github.com/0xfnzero/sol-parser-sdk/tree/main/examples) (Rust); streaming uses `subscribe_transactions` + `parse_logs_only` with the same program IDs as `TransactionFilter::for_protocols` in Rust.

| Description | Run command | Source |
|-------------|-------------|--------|
| **PumpFun** | | |
| PumpFun trade filtering | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) | `v0.10.0` |
| PumpFun events + metrics | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) | `v0.10.0` |
| Quick PumpFun connection test | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) | `v0.10.0` |
| **PumpSwap** | | |
| PumpSwap ultra-low latency | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) | `v0.10.0` |
| PumpSwap events + metrics | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) | `v0.10.0` |
| **Meteora DAMM** | | |
| Meteora DAMM V2 events | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) | `v0.10.0` |
| **Multi-protocol** | | |
| Subscribe to every program in Rust `Protocol` / `program_ids` | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) | `v0.10.0` |
| **Utility** | | |
| Parse tx by signature (HTTP RPC; not gRPC). `TX_SIGNATURE` / `RPC_URL` or `SOLANA_RPC_URL` in `.env` or `--sig` / `--rpc`. | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) | `v0.10.0` |

**Env:** gRPC examples need **`GRPC_URL`** or **`GRPC_ENDPOINT`**, plus **`GRPC_AUTH_TOKEN`** or **`GRPC_TOKEN`** (or legacy `GEYSER_*`). See **`.env.example`**.

<a id="protocols"></a>

## Protocols

PumpFun, PumpSwap, Raydium AMM V4 / CLMM / CPMM, Orca Whirlpool, Meteora DAMM V2 / DLMM, Raydium LaunchLab (see `sol_parser/`).

<a id="useful-exports"></a>

## Useful exports

- `parse_logs_only` — log-based DEX events from gRPC log messages.
- `format_dex_event_json` / `dex_event_to_jsonable` — pretty-print `DexEvent` as indented JSON (one field per line); `repr(ev)` is the default dataclass single-line form, not JSON.
- `YellowstoneGrpc` — async Yellowstone gRPC client (`connect`, `subscribe_transactions`, `disconnect`).
- `now_micros` — microsecond clock (same role as Rust `sol_parser_sdk::core::now_micros`).
- `transaction_filter_for_protocols` / `program_ids_for_protocols` / `account_filter_for_protocols` — same program IDs as Rust `Protocol` + `for_protocols` in `grpc/filter.rs`.
- `parse_grpc_credentials` / `require_grpc_env` — load `.env` + env + CLI (aligned with [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) `grpc_env`).

<a id="advanced"></a>

## Advanced

### Custom gRPC endpoint

```python
import os

from sol_parser.grpc_client import YellowstoneGrpc

endpoint = os.environ.get("GRPC_URL") or os.environ.get("GRPC_ENDPOINT") or os.environ.get(
    "GEYSER_ENDPOINT", "solana-yellowstone-grpc.publicnode.com:443"
)
token = (
    os.environ.get("GRPC_AUTH_TOKEN")
    or os.environ.get("GRPC_TOKEN")
    or os.environ.get("GEYSER_API_TOKEN", "")
)
client = YellowstoneGrpc(endpoint)
if token:
    client.set_x_token(token)
```

### Create + buy detection

`parse_logs_only` can detect create-and-buy patterns from program logs; see the PumpFun examples.

<a id="project-structure"></a>

## Project structure

```
sol-parser-sdk-python/
├── sol_parser/
│   ├── grpc_client.py          # YellowstoneGrpc (async connect / subscribe)
│   ├── env_config.py           # GRPC_URL, .env, CLI helpers (Node parity)
│   ├── clock.py                # now_micros()
│   ├── grpc_types.py           # TransactionFilter, SubscribeCallbacks, for_protocols helpers, …
│   ├── parser.py               # parse_logs_only, …
│   ├── geyser_pb2.py           # Generated proto (Yellowstone)
│   └── …
├── examples/
│   ├── pumpfun_trade_filter.py
│   ├── pumpfun_quick_test.py
│   └── …
├── .env.example
└── pyproject.toml
```

<a id="development"></a>

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

<a id="api-compatibility"></a>

## API compatibility

Full cross-language API parity is still in progress. See the [API migration guide](docs/USAGE.md#api-compatibility) for public behavior and support boundaries, and the examples directory for usage.


Live parser-to-trade integration uses Yellowstone **gRPC**. See [gRPC cache integration and language examples](docs/USAGE.md#grpc-cache). Quoting and construction read cached state without hot-path RPC.

Shared PumpFun create/create_v2 mainnet fixtures, replay instructions and verification limits are documented in the [validation guide](https://github.com/0xfnzero/sol-parser-sdk-golang/tree/main/validation/pumpfun_create_20261007).

### Offline Pump ShredStream regressions

User examples live in examples; automated regression tests are maintained separately. Obsolete route-intent simulation entry points and their unused snapshots have been removed. See [wrapped transaction replay and filters](docs/wrapped-pumpfun.md). Shred decodes resolved outer instructions; third-party candidates retain original input in PumpFunTrade.third_program and are not confirmed fills. No RPC runs in the parser hot path.

Native offline CPU benchmark: `python -m examples.hot_path_benchmark`.
`examples/hot_path_benchmark.json` fixes warmup and measured iterations for six
signed wrapped-CPI/ALT transactions. Reported percentiles are per six-transaction
batch; fixture decoding and I/O occur before timing. Parsing performs no RPC.
Public wire-decoder dictionaries and resolver callbacks retain base58 strings;
the internal ShredStream path avoids an instruction-data base58 round trip.

<a id="documentation"></a>

## Documentation

- [Release and migration](RELEASE_NOTES.md)
- [Usage guide](docs/USAGE.md)
- [Cross-language support and boundaries](docs/cross-language-sync.md)


<a id="license"></a>

## License

MIT — https://github.com/0xfnzero/sol-parser-sdk-python

<a id="contact"></a>

## Contact

- **Repository**: https://github.com/0xfnzero/sol-parser-sdk-python
- **Website**: https://fnzero.dev/
- **Telegram**: https://t.me/fnzero_group
- **Discord**: https://discord.gg/vuazbGkqQE


Shared stock bridges: 33 official stock/ETF mints and 58 pools. See [eleven-SDK catalog and routing alignment](docs/STOCK_BRIDGE_SYNC.md) for configuration, USDC routing and cache-only boundaries.
