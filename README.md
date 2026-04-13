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

---

## Other language SDKs

| Language | Repository |
|----------|------------|
| Rust | [sol-parser-sdk](https://github.com/0xfnzero/sol-parser-sdk) |
| Node.js | [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) |
| Python | [sol-parser-sdk-python](https://github.com/0xfnzero/sol-parser-sdk-python) |
| Go | [sol-parser-sdk-golang](https://github.com/0xfnzero/sol-parser-sdk-golang) |

---

## How to use

### 1. Install

**From PyPI**

```bash
pip install sol-parser-sdk-python
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
# Set GRPC_URL and GRPC_TOKEN
```

Run examples from that directory so `.env` is picked up (same idea as the Node.js package).

**CLI overrides:** `--grpc-url` / `-g`, `--grpc-token` / `--token` (also `--grpc-url=https://host:443`). **Legacy env:** `GEYSER_ENDPOINT` / `GEYSER_API_TOKEN`. **Precedence:** explicit shell `export` wins over `.env`; `python-dotenv` does not overwrite existing variables.

Helpers: `sol_parser.env_config` (`parse_grpc_credentials`, `require_grpc_env`, `parse_shredstream_url`, …), re-exported from `sol_parser`.

### 3. Smoke test

```bash
python examples/pumpfun_quick_test.py
```

Requires `GRPC_URL` and (for most providers) `GRPC_TOKEN` in `.env` or the environment. You can pass credentials on the command line instead; see step 2.

### 4. Minimal gRPC subscribe + parse

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

**Lighter path:** `parse_logs_only(logs, …)` only needs log messages from the update (no full wire transaction).

### 5. ShredStream (HTTP — not Yellowstone gRPC)

The Node.js SDK includes a ShredStream HTTP client. **Python** provides the same env/CLI helpers as Node (`parse_shredstream_url`: `SHREDSTREAM_URL` / `SHRED_URL`, `--url` / `-u` / `--endpoint=`) for configuration parity; a native ShredStream client may be added later. **Not** `GRPC_URL`.

---

## Examples

From the **package root** after `pip install -e .`. Run with `python examples/<file>.py`.

| Description | Run command | Source |
|-------------|-------------|--------|
| **PumpFun** | | |
| PumpFun trade filtering | `python examples/pumpfun_trade_filter.py` | [pumpfun_trade_filter.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_trade_filter.py) |
| PumpFun events + metrics | `python examples/pumpfun_with_metrics.py` | [pumpfun_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_with_metrics.py) |
| Quick PumpFun connection test | `python examples/pumpfun_quick_test.py` | [pumpfun_quick_test.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpfun_quick_test.py) |
| **PumpSwap** | | |
| PumpSwap ultra-low latency | `python examples/pumpswap_low_latency.py` | [pumpswap_low_latency.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_low_latency.py) |
| PumpSwap events + metrics | `python examples/pumpswap_with_metrics.py` | [pumpswap_with_metrics.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/pumpswap_with_metrics.py) |
| **Meteora DAMM** | | |
| Meteora DAMM V2 events | `python examples/meteora_damm_grpc.py` | [meteora_damm_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/meteora_damm_grpc.py) |
| **Multi-protocol** | | |
| Subscribe to all DEX protocols | `python examples/multi_protocol_grpc.py` | [multi_protocol_grpc.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/multi_protocol_grpc.py) |
| **Utility** | | |
| Parse tx by signature (HTTP RPC; not gRPC). `TX_SIGNATURE` / `RPC_URL` in `.env` or `--sig` / `--rpc`. | `python examples/parse_tx_by_signature.py` | [parse_tx_by_signature.py](https://github.com/0xfnzero/sol-parser-sdk-python/blob/main/examples/parse_tx_by_signature.py) |

**Env:** gRPC examples need **`GRPC_URL`** + **`GRPC_TOKEN`** (or legacy `GEYSER_*`). See **`.env.example`**.

---

## Protocols

PumpFun, PumpSwap, Raydium AMM V4 / CLMM / CPMM, Orca Whirlpool, Meteora DAMM V2 / DLMM, Bonk Launchpad (see `sol_parser/`).

---

## Useful exports

- `parse_logs_only` — log-based DEX events from gRPC log messages.
- `YellowstoneGrpc` — async Yellowstone gRPC client (`connect`, `subscribe_transactions`, `disconnect`).
- `parse_grpc_credentials` / `require_grpc_env` — load `.env` + env + CLI (aligned with [sol-parser-sdk-nodejs](https://github.com/0xfnzero/sol-parser-sdk-nodejs) `grpc_env`).

---

## Advanced

### Custom gRPC endpoint

```python
import os

from sol_parser.grpc_client import YellowstoneGrpc

endpoint = os.environ.get("GRPC_URL") or os.environ.get(
    "GEYSER_ENDPOINT", "solana-yellowstone-grpc.publicnode.com:443"
)
token = os.environ.get("GRPC_TOKEN") or os.environ.get("GEYSER_API_TOKEN", "")
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
│   ├── grpc_types.py           # TransactionFilter, SubscribeCallbacks, …
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
