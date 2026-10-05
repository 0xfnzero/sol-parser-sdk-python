"""Refresh saved cold-bootstrap snapshots with native parser gRPC updates.

GRPC_URL and GRPC_TOKEN are read from the environment. Usage:
python examples/stonkfun_snapshot_refresh.py snapshots.json --timeout 30
Supports named snapshots and accounts[] for cached_clmm/cached_route trade examples.
--require-pool-update requires fresh updates for every route pool.
Unchanged configs/mints retain cold-bootstrap snapshots; trade preparation rejects
stale accounts using read_slot and the caller's maximum_slot_age budget.
"""

import argparse
import asyncio
import base64
import json
import os
import math
import sys
from pathlib import Path
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import (
    AccountFilter,
    EventType,
    CommitmentLevel,
    event_type_filter_include_only,
)

CLOCK = "SysvarC1ock11111111111111111111111111111111"


def apply_raw_snapshot(current, raw):
    account = raw.account
    if current["pubkey"] != account.pubkey:
        raise ValueError("Snapshot identity mismatch")
    old = (int(current["slot"]), int(current["write_version"]))
    new = (raw.metadata.slot, raw.write_version)
    if new < old:
        return current
    updated = {
        "pubkey": account.pubkey,
        "owner": account.owner,
        "data": base64.b64encode(account.data if account.lamports else b"").decode(),
        "slot": str(new[0]),
        "write_version": str(new[1]),
    }
    if new == old:
        if current["owner"] != updated["owner"] or base64.b64decode(
            current["data"], validate=True
        ) != base64.b64decode(updated["data"], validate=True):
            raise ValueError("Conflicting account version; select a fork explicitly")
        return current
    return updated


async def refresh(path, timeout, require_pool_update):
    snapshot = json.loads(path.read_text())
    # Both named LaunchLab/CPMM snapshots and full CLMM/route account lists.
    listed = snapshot.get("accounts")
    if listed is not None:
        names = {a["pubkey"]: i for i, a in enumerate(listed) if a["pubkey"] != CLOCK}
    else:
        names = {
            snapshot[n]["pubkey"]: n
            for n in (
                "pool",
                "global",
                "platform",
                "config",
                "base_mint",
                "quote_mint",
                "base_vault",
                "quote_vault",
            )
            if isinstance(snapshot.get(n), dict)
        }
    pools = {h["pool"] for h in snapshot.get("legs", [])}
    pool = snapshot.get("pool")
    if pool:
        pools.add(pool["pubkey"] if isinstance(pool, dict) else pool)
    updated_pools = set()
    client = YellowstoneGrpc.new(os.environ["GRPC_URL"], os.environ.get("GRPC_TOKEN"))
    pool_updated = False
    clock_seen = False
    clock_snapshot = None
    deadline = asyncio.get_running_loop().time() + timeout
    try:
        queue = await asyncio.wait_for(
            client.subscribe_dex_events(
                [],
                [AccountFilter(account=[CLOCK, *names])],
                event_type_filter_include_only([EventType.ACCOUNT_RAW_SNAPSHOT]),
            ), max(0, deadline - asyncio.get_running_loop().time()),
        )
        while True:
            event = await asyncio.wait_for(
                queue.get(), max(0, deadline - asyncio.get_running_loop().time())
            )
            if event.type != EventType.ACCOUNT_RAW_SNAPSHOT:
                continue
            raw = event.data
            account = raw.account
            if account.pubkey in names:
                name = names[account.pubkey]
                current = listed[name] if listed is not None else snapshot[name]
                updated = apply_raw_snapshot(current, raw)
                if listed is not None:
                    listed[name] = updated
                else:
                    snapshot[name] = updated
                if account.pubkey in pools and updated is not current:
                    updated_pools.add(account.pubkey)
                pool_updated = bool(pools) and updated_pools == pools
            elif account.pubkey == CLOCK:
                if not account.lamports or len(account.data) != 40:
                    raise ValueError("Invalid Clock account snapshot")
                previous = clock_snapshot or {
                    "pubkey": CLOCK,
                    "owner": account.owner,
                    "data": "",
                    "slot": "0",
                    "write_version": "0",
                }
                updated = apply_raw_snapshot(previous, raw)
                if updated is clock_snapshot:
                    continue
                clock_snapshot = updated
                if listed is not None:
                    for i, saved in enumerate(listed):
                        if saved["pubkey"] == CLOCK:
                            listed[i] = updated
                snapshot["epoch"] = str(int.from_bytes(account.data[16:24], "little"))
                snapshot["unix_timestamp"] = str(
                    int.from_bytes(account.data[32:40], "little", signed=True)
                )
                snapshot["read_slot"] = str(int.from_bytes(account.data[:8], "little"))
                snapshot["slot"] = str(raw.metadata.slot)
                clock_seen = True
            if clock_seen and (pool_updated or not require_pool_update):
                blockhash = await asyncio.wait_for(
                    client.get_latest_blockhash(CommitmentLevel.CONFIRMED),
                    max(0, deadline - asyncio.get_running_loop().time()),
                )
                snapshot["recent_blockhash"] = blockhash.blockhash
                path.write_text(json.dumps(snapshot, indent=2) + "\n")
                print(
                    json.dumps(
                        {
                            "slot": snapshot["slot"],
                            "epoch": snapshot["epoch"],
                            "blockhash_slot": blockhash.slot,
                            "pool_updated": pool_updated,
                        }
                    )
                )
                return
    except TimeoutError:
        raise TimeoutError(
            f"gRPC snapshot deadline exceeded; clock_seen={clock_seen}, "
            f"missing_pool_updates={len(pools - updated_pools)}"
        ) from None
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--require-pool-update", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be finite and positive')
    try:
        asyncio.run(refresh(args.snapshots, args.timeout, args.require_pool_update))
    except TimeoutError as error:
        print(json.dumps({'status': 'not_ready', 'reason': str(error)}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
