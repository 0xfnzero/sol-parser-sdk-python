# Native Python Pump regression examples

Run from the repository root:

```sh
python -m pip install -e ".[dev,simulation]"
python examples/pump_shred_routes.py
python examples/pump_offline_bank.py
python -m pytest -q
```

Install dependencies once before offline execution. After that both examples use only bundled files; no endpoint, funded wallet or broadcast is required. The replay example verifies all signatures on six original mainnet wires, including V1 wrappers, with strict ALT resolution, metadata, hops, filters, malformed layouts and repeatability. It also signs direct curve route boundary cases. This is signed-wire replay, not wrapper-program execution.

The bank example uses `examples/offline_bank/config.json` by default. An optional first argument selects another JSON config. Snapshot paths remain relative to `examples/offline_bank`; `repetitions` must be at least 2. Tests call the same native example functions. Every repetition builds and signs 20 new V0 transactions and executes SBF locally: curve→curve buy/sell, pool→curve, curve→pool, pool→pool × static/ALT × success/slippage failure. It checks signature rejection, invalid writable/readonly ALT indices, parent rollback with fee debit, route-intent arguments and per-hop log fields against an independent oracle. Repeated signed wires and execution logs must match. Each example also feeds local execution status into the offline RPC-format decoder and verifies parent failures produce no settled fills; this conversion makes no RPC request.

The bank runs directly in the language runtime, using LiteSVM as a development dependency. It verifies simulation is read-only and committed success accounts match simulated post-accounts. No subprocess or RPC is involved.

## Parsing contract

`parse_shred_transaction` is strict by default. Use `parse_shred_transaction_with_loaded_addresses(raw, writable, readonly, ...)` for cached ALT addresses. Alternatively pass `address_lookup_resolver(decoded_transaction, slot)` to `parse_shred_transaction`, or configure `ShredStreamClient.with_address_lookup_resolver(resolver)`. The resolver returns `(writable, readonly)` or `None` on a cache miss. It must only read a slot-aware prewarmed cache. Mismatched counts raise `ValueError`; resolver exceptions propagate to direct callers and are reported through the stream error handler. `parse_shred_transaction_best_effort` explicitly opts into legacy placeholders; route adapters always require resolved keys.

`PumpRouteIntent` describes the outer instruction, not an executed fill. Supported adapters bind to the exact official Pump/Pump AMM, Rapid and Delta program IDs and account layouts. The existing `PumpFunTrade` filter includes these intents; `PumpSwapTrade` includes only AMM routes. Create/directional-only filters do not include intents; explicitly excluding `PumpRouteIntent` wins. Delta's input depends on runtime balances, so unknown amounts stay null; opaque instruction bytes are retained. A zero minimum output is valid; zero declared input is rejected.

Strict mode skips instructions containing unresolved accounts or programs; it does not guess addresses. Cache callbacks are synchronous and must never issue RPC. Loaded addresses are validated before producing events. Raw shreds lack CPI results and transaction status; they can describe an intent even when execution later fails. Log events from failed simulations describe attempted work and must not be booked as settled fills.

## Frozen input provenance

`snapshot.json.gz` contains pre-route account state, transaction inputs and unmodified deployed SBF bytes from the 2026-10-09 Pump validation fork. Users were locally funded; quote depth and synthetic token-paired coins/pools were prepared locally. The example rekeys users, ATAs and user-volume PDAs to a deterministic public test key. It stores no captured execution results. Each run executes programs again.

`config.json` pins the compressed SHA-256; `programs.json` records program hashes; `expected.json` is an independently decoded official-IDL oracle. The public deterministic key must never receive funds. These checks cover the pinned deployment, not arbitrary wrappers or production latency. Third-party wrapper programs are verified by signed-wire replay only.
