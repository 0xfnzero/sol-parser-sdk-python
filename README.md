<div align="center">

## v0.5.17 — Shred metadata passthrough and ordering scope

Preserve and verify transaction position and receive time through raw instruction callbacks. Entries indexes are message-local, unlike Yellowstone node indexes; use signatures for cross-message deduplication. This release clarifies API documentation and adds regression protection without changing metadata fields or numbering behavior.


## v0.5.17 — DEX-scoped RawInstruction and typed DEX identifiers

Raw instructions now respect DEX subscriptions using programs referenced by each instruction. `RawInstructionDexType` provides typed identifiers with unchanged JSON strings. Unknown router layouts do not establish pool addresses, trade direction, or method versions.


## v0.5.17 — Pump execution replay

Current Anchor TradeEvent CPI decoding is supported alongside the historical encoding. RPC/gRPC instruction budgets and minimum outputs remain in instruction fields. Execution fields `sol_amount`, `quote_amount`, and `token_amount` come from execution events; without logs or event CPIs they remain zero (unavailable, not a proven zero fill).

Run `.venv/bin/python examples/pump_execution_replay.py` from this repository to replay real transactions fetched on 2026-10-19 offline. The example prints full/no-log/truncated-log results. Append a recent signature for online replay. Set `SOLANA_RPC_URL` for your RPC; transaction v1 is supported.

The current Delta sell signature is `4ARos3Yq1SMNE3izDpy9YdKrRgMmD7UCDxvnVrBRaGCJHiifPHSmQWc4DPfjUaEUcxS7puGmEN64K7EZdeXLJaj2` (slot 458542546). The dated fixture also includes Rapid create/buy, BuyV3, and PumpSwap buy with their full signatures and slots. Older five-combination multi-hop fixtures are retained as regression tests, not labeled as new mainnet captures.

## v0.5.17 — raw Shred instructions

Default Shred parsing emits `RawInstruction` for unsupported third-party programs, including Rapid/Delta, without inferring direction, amounts, or internal buy methods. Infrastructure programs (System, Token, ATA, ComputeBudget, etc.) are omitted by default. Supported official DEX parsers are unchanged; official Pump/PumpSwap multi-hop instructions retain `PumpRouteIntent`.

The payload contains `program_id`, `instruction_index`, `accounts`, `account_indices`, `instruction_data`, and transaction metadata. Account order and duplicates are preserved. Unresolved ALT addresses are null/None, with original indices retained; supply cached loaded addresses or a resolver. No hot-path RPC is performed. Data is copied verbatim without requiring a known layout.

Run `uv run python examples/raw_instruction_filter.py` to compare PumpFun-only, Raydium CPMM-only, and all-raw subscriptions against signed offline transactions; the output includes `dexes`.

The raw event retains `metadata.tx_index` and `metadata.grpc_recv_us` from the parser arguments (streamer names the receive field `metadata.recv_us`). The default Entries client index is local to one received Entries message and restarts at zero for the next message; it is not a confirmed slot-wide transaction index. `instruction_index` orders outer instructions within a transaction. Receive time is a local microsecond timestamp, not an execution-order guarantee. Standalone replay APIs may default these values to zero; pass the upstream values when available.

Without a filter, unknown third-party instructions are returned. Broad trade/swap filters (for example `PumpFunTrade` or `RaydiumCpmmSwap`) also return raw instructions associated with that DEX; direction-specific filters do not infer a buy or sell. Explicit `RawInstruction` selects all outer instructions only when no protocol restriction is set; streamer protocol restrictions always apply. Excluding `RawInstruction` wins. `dex_type` uses the public `RawInstructionDexType` enum (typed string constants in Go); JSON values remain unchanged, such as `"pumpfun"` and `"raydium_cpmm"`. `dexes` contains `{ dex_type, program_id, pool }` for each recognized DEX program targeted or referenced by this instruction, not other instructions in the transaction. Multi-DEX wrappers retain every association. Unknown or unresolved ALT references cannot satisfy a DEX subscription. `pool` is currently null: an unknown wrapper layout cannot establish the pool account. A program reference is not proof of an executed CPI. Raw callbacks are not fills.

Wrapper adapter functions remain explicit compatibility helpers only; default Shred parsing does not call them. The released-version history below describes previous behavior.

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

---

## 📦 SDK Versions and Related SDKs

Parser SDK language versions and related Rust SDKs:

| Language | Repository | Description | Version |
|----------|------------|-------------|---------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) | Solana DEX transaction and account event parsing | `v0.7.18` |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) | TypeScript/JavaScript for Node.js | `v0.5.24` |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) | Async/await native support | `v0.5.17` |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) | Go transaction and account event parsing | `v0.5.17` |
| **Rust** | [sol-shred-sdk](https://github.com/0xfnzero/sol-shred-sdk) | Raw Solana shred decoding and ShredStream DEX event parsing | `v4.0.9` |
| **Rust** | [sol-trade-sdk](https://github.com/0xfnzero/sol-trade-sdk) | Solana DEX trade construction and transaction execution | `v6.0.2` |

---

## v0.5.14 — Pump route direction and instruction names

Route intents now expose `is_buy` and `ix_name`, following existing trade field names and official IDL instruction names. RapidBuy reports a buy intent and `buy_exact_quote_in_v2`; BuyPumpDelta reports only a buy intent. Multi-hop direction and unknown methods remain null. Read currencies from `hops[].base_mint` / `quote_mint`. These hints do not confirm execution, and filters do not convert intents into trades.

Older JSON without the fields remains readable as unknown. Rust struct literals must supply the new fields; Go uses pointers and Node.js/Python use null/None for unknown values. Streamer now forwards `DexEvent::PumpRouteIntentEvent` with protocol and event filtering.

## v0.5.13 — Pump routes and offline replay

Adds native Pump route-intent parsing for official multi-hop instructions and the exact RapidBuy/BuyPumpDelta wrapper layouts captured in reported transactions. Adds locally cached ALT resolution and rejects unresolved account identities by default, with explicit best-effort compatibility APIs where supported. Route intents expose instruction constraints and hop identities; confirmed execution amounts require execution metadata.

Includes the latest complete implementation, signed transaction fixtures, native offline-bank regression examples and reproducible local hot-path benchmarks. Unknown wrapper layouts are not inferred from embedded bytes. Local tests do not measure production network latency.

## v0.5.12 — Pump depth-2 compatibility

Adds signed Pump depth-2 create-event replay coverage, including ALT-loaded accounts and executed logs. Existing event layouts and public parsing interfaces remain unchanged.

Validation includes official Pump SDK 4.1.0 instruction comparisons, signed local LiteSVM simulations and SDK regressions. Local simulation state/config is synthetic; no funded transactions were broadcast and production latency was not measured.

## v0.5.11 — Signed transaction and hot-path hardening

Hardens signed transaction sanitization, loaded-address boundaries, ordered stream filtering and parser lifecycle. Aligns CLMM and DEX instruction/event layouts, nested CPI route attribution and liquidity/reward accounting. Adds independently signed wire fixtures, ALT failure cases and offline bank regressions.

Validation includes local CPU benchmarks and offline signed-bank scenarios. Measured hot paths use cached inputs without RPC. Benchmarks do not establish production network or transaction-landing latency. No funded mainnet transactions were broadcast.

## What This SDK Is For

This is the Python implementation of the FnZero Solana DEX parser SDK for asyncio services, research scripts, indexers, copy-trading systems, sniper pipelines, and backend jobs that need normalized real-time DEX events.

| Area | Coverage |
|------|----------|
| Parser inputs | Yellowstone gRPC, ShredStream, RPC transactions, encoded transactions, protocol account data |
| DEX protocols | PumpFun, PumpSwap, Pump Fees, Raydium LaunchLab, Raydium CPMM, Raydium CLMM, Raydium AMM V4, Meteora DAMM v2, Meteora DLMM, Meteora DBC, Orca Whirlpool |
| Use cases | Real-time DEX event parsing, token launch monitoring, copy trading, sniper bots, analytics notebooks, JSON event pipelines |
| Runtime | Python 3.10+, asyncio workers, backend services, data pipelines, low-latency bot infrastructure |

---

## Release notes

### v0.5.10

- Matches PumpFun create/create_v2 accounts by the actual instruction discriminator and event mint, including CPI calls; ambiguous matches are left unspecified.
- Stops inferring quote mint/vault/token-program fields from arbitrary remaining create_v2 accounts and preserves authoritative decoded fields.
- Restores historical CreateEvent decoding and verifies successful and failed transactions using saved mainnet fixtures.
- Suppresses rolled-back DEX events from failed transactions and preserves failure status through RPC/gRPC adapters.

### v0.5.9

- Adds native gRPC lifecycle and block metadata support, instruction-level route analysis and StonkFun registry/snapshot examples.
- Improves exact metadata serialization, account matching and wire transaction bounds validation.
- Includes native alignment evidence and simulation route fixtures. These language releases do not yet implement the new CPMM creator-fee collection event API.

### v0.5.8

- Syncs with Rust **sol-parser-sdk 0.7.3**, including the current PumpFun, PumpSwap, and Pump Fees protocol definitions.
- Adds Meteora DAMM v2 events: `UpdateDelegatePermission`, `WithdrawDeadLiquidityReward`, `CreateConfig`, `CreateDynamicConfig`.
- Fixes DAMM v2 `EvtSwap2` full 180-byte layout, three swap modes, transfer fees, reserves, and compounding-fee layout activation slot `406048752`.
- Routes unified `EvtLiquidityChange` by `change_type` to AddLiquidity / RemoveLiquidity.
- Adds DLMM mint/user-token/`min_amount_out` context, PumpFun pre/post token & SOL balances, and LaunchLab quote/global/platform account fields.
- Adds current PumpFun/PumpSwap creator-fee and holder-reward fields across instruction, log, account, gRPC, and JSON event paths.
- Rejects truncated known PumpSwap trade and CreatePool tails while retaining complete historical layouts.

### v0.5.6

- Adds Meteora DBC log parsing with program-context routing and filter parity.
- Adds Raydium CLMM/CPMM and Orca account parsers and exports.
- Fixes default no-filter RPC/Yellowstone instruction parsing so it no longer behaves like an empty include-only filter.
- Merges RPC ALT loaded writable/readonly keys into the full instruction account table.
- Skips ShredStream/RPC instruction parsing early for account-only or empty include-only filters.

### v0.5.5

- Aligns ShredStream parsing with Rust/Node.js/Go for low-latency static-account paths.
- Uses default pubkey placeholders for V0 ALT-loaded instruction accounts instead of dropping the instruction.
- Adds discriminator fallback when the ShredStream outer program id is ALT-loaded.
- Fixes Pump.fun ShredStream create/create_v2 fallback to use instruction-order accounts.
- Improves Pump.fun v2 short-account parsing, event-type filtering, and multi-protocol routing parity.

---

## How to use

### 1. Install

**From PyPI**

```bash
pip install sol-parser-sdk-python==0.5.17
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

The Python ShredStream hot path uses strict static-account parsing by default. Supply loaded addresses or a slot-aware prewarmed-cache resolver for V0 ALT instructions; unresolved instructions are skipped. Legacy placeholders require the explicit `parse_shred_transaction_best_effort` API. Recognized wrapper/official routes emit `PumpRouteIntent`; raw shreds cannot reconstruct arbitrary CPI. Inner CPI/log-only events still require the Yellowstone/RPC paths.

---

## Examples

From the **package root** after `pip install -e .`. Run with `python examples/<file>.py`. Scripts are written to mirror the **output layout and env names** of [sol-parser-sdk/examples](https://github.com/0xfnzero/sol-parser-sdk/tree/main/examples) (Rust); streaming uses `subscribe_transactions` + `parse_logs_only` with the same program IDs as `TransactionFilter::for_protocols` in Rust.

| Description | Run command | Source |
|-------------|-------------|--------|
| **PumpFun** | | |
| PumpFun trade filtering | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) | `v0.5.17` |
| PumpFun events + metrics | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) | `v0.5.17` |
| Quick PumpFun connection test | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) | `v0.5.17` |
| **PumpSwap** | | |
| PumpSwap ultra-low latency | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) | `v0.5.17` |
| PumpSwap events + metrics | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) | `v0.5.17` |
| **Meteora DAMM** | | |
| Meteora DAMM V2 events | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) | `v0.5.17` |
| **Multi-protocol** | | |
| Subscribe to every program in Rust `Protocol` / `program_ids` | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) | `v0.5.17` |
| **Utility** | | |
| Parse tx by signature (HTTP RPC; not gRPC). `TX_SIGNATURE` / `RPC_URL` or `SOLANA_RPC_URL` in `.env` or `--sig` / `--rpc`. | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) | `v0.5.17` |

**Env:** gRPC examples need **`GRPC_URL`** or **`GRPC_ENDPOINT`**, plus **`GRPC_AUTH_TOKEN`** or **`GRPC_TOKEN`** (or legacy `GEYSER_*`). See **`.env.example`**.

---

## Protocols

PumpFun, PumpSwap, Raydium AMM V4 / CLMM / CPMM, Orca Whirlpool, Meteora DAMM V2 / DLMM, Raydium LaunchLab (see `sol_parser/`).

---

## Useful exports

- `parse_logs_only` — log-based DEX events from gRPC log messages.
- `format_dex_event_json` / `dex_event_to_jsonable` — pretty-print `DexEvent` as indented JSON (one field per line); `repr(ev)` is the default dataclass single-line form, not JSON.
- `YellowstoneGrpc` — async Yellowstone gRPC client (`connect`, `subscribe_transactions`, `disconnect`).
- `now_micros` — microsecond clock (same role as Rust `sol_parser_sdk::core::now_micros`).
- `transaction_filter_for_protocols` / `program_ids_for_protocols` / `account_filter_for_protocols` — same program IDs as Rust `Protocol` + `for_protocols` in `grpc/filter.rs`.
- `parse_grpc_credentials` / `require_grpc_env` — load `.env` + env + CLI (aligned with [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) `grpc_env`).

---

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

---

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

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

---

## License

MIT — https://github.com/0xfnzero/sol-parser-sdk-python

---

## Contact

- **Repository**: https://github.com/0xfnzero/sol-parser-sdk-python  
- **Website**: https://fnzero.dev/  
- **Telegram**: https://t.me/fnzero_group  
- **Discord**: https://discord.gg/vuazbGkqQE  

## API compatibility

Full cross-language API parity is still in progress. See the [API migration guide](docs/USAGE.md#api-compatibility) for public behavior and support boundaries, and the examples directory for usage.


实时 parser → trade 接入使用 Yellowstone **gRPC**；见 [gRPC 缓存接入与三语言示例](docs/USAGE.md#grpc-cache)。此路径不使用 WebSocket，报价和构建热路径不调用 RPC。

Shared PumpFun create/create_v2 mainnet fixtures, replay instructions and verification limits are documented in the [validation guide](https://github.com/0xfnzero/sol-parser-sdk-golang/tree/main/validation/pumpfun_create_20261007).

### Offline Pump ShredStream regressions

Pump route intents, strict cached ALT resolution and native signed replay/SBF simulation examples are documented in [examples/offline_bank/README.md](examples/offline_bank/README.md). Run the language-native examples and tests from this repository; no other-language test driver or RPC endpoint is needed. Unresolved instructions now skip by default; use the explicit best-effort API only for legacy behavior. Route intents must not be treated as confirmed fills.

Native offline CPU benchmark: `python -m examples.hot_path_benchmark`.
`examples/hot_path_benchmark.json` fixes warmup and measured iterations for six
signed wrapped-CPI/ALT transactions. Reported percentiles are per six-transaction
batch; fixture decoding and I/O occur before timing. Parsing performs no RPC.
Public wire-decoder dictionaries and resolver callbacks retain base58 strings;
the internal ShredStream path avoids an instruction-data base58 round trip.
