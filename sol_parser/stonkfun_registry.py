"""Caller-owned, replay-safe provenance for successfully migrated StonkFun pools."""

from __future__ import annotations
from dataclasses import asdict, dataclass
import base64
import base58
from .transaction_route import (
    PROGRAMS,
    ZERO,
    stonkfun_mode_from_platform_config,
    analyze_rpc_transaction_routes,
)
from .wire_transaction import decode_wire_transaction


@dataclass(frozen=True)
class StonkFunGraduatedPool:
    curve_pool: str
    pool: str
    base_mint: str
    quote_mint: str
    platform_config: str
    migration_signature: str
    migration_slot: int

    def mode(self):
        return stonkfun_mode_from_platform_config(self.platform_config)

    def validate(self):
        if (
            self.mode() is None
            or self.curve_pool == self.pool
            or self.base_mint == self.quote_mint
        ):
            raise ValueError("Invalid StonkFun registry identity")
        for key in (self.curve_pool, self.pool, self.base_mint, self.quote_mint):
            if key == ZERO or len(base58.b58decode(key)) != 32:
                raise ValueError("Invalid StonkFun registry key")
        if (
            len(base58.b58decode(self.migration_signature)) != 64
            or type(self.migration_slot) is not int
            or not 0 <= self.migration_slot < 1 << 64
        ):
            raise ValueError("Invalid migration provenance")


class StonkFunPoolRegistry:
    def __init__(self, pools=()):
        self._pools = {}
        for entry in pools:
            entry.validate()
            if entry.pool in self._pools:
                raise ValueError("Duplicate StonkFun registry entry")
            self._pools[entry.pool] = entry

    def get(self, pool):
        return self._pools.get(pool)

    def pools_for_base_mint(self, mint):
        return [
            self._pools[k]
            for k in sorted(self._pools)
            if self._pools[k].base_mint == mint
        ]

    def verified_cpmm_pools(self):
        return sorted(self._pools)

    def to_dict(self):
        return {"pools": [asdict(self._pools[k]) for k in sorted(self._pools)]}

    @classmethod
    def from_dict(cls, data):
        return cls(StonkFunGraduatedPool(**p) for p in data["pools"])

    def observe_migrations(self, entries, succeeded):
        if not succeeded:
            return 0
        pending = {}
        for entry in entries:
            entry.validate()
            prior = pending.get(entry.pool) or self._pools.get(entry.pool)
            if prior is not None and prior != entry:
                raise ValueError("Conflicting migration provenance")
            pending[entry.pool] = entry
        count = sum(k not in self._pools for k in pending)
        self._pools.update(pending)
        return count

    def observe_rpc_transaction(self, transaction):
        tx = transaction.get("result", transaction)
        if not isinstance(tx.get("meta"), dict):
            raise ValueError("Transaction metadata missing")
        if "err" not in tx["meta"]:
            raise ValueError("Transaction execution status missing")
        if tx["meta"]["err"] is not None:
            return 0
        analyze_rpc_transaction_routes(transaction)
        body = tx["transaction"]
        if isinstance(body, list):
            if body[1] != "base64":
                raise ValueError("Expected base64 encoding")
            body, _ = decode_wire_transaction(base64.b64decode(body[0], validate=True))
        message, loaded = body["message"], tx["meta"].get("loadedAddresses") or {}
        keys = (
            [k if isinstance(k, str) else k["pubkey"] for k in message["accountKeys"]]
            + loaded.get("writable", [])
            + loaded.get("readonly", [])
        )
        instructions = list(message["instructions"])
        for group in tx["meta"].get("innerInstructions") or []:
            instructions.extend(group["instructions"])
        entries = []
        for ix in instructions:
            data = (
                base58.b58decode(ix["data"])
                if isinstance(ix["data"], str)
                else bytes(ix["data"])
            )
            if (
                keys[ix["programIdIndex"]] != PROGRAMS["LaunchLab"]
                or data[:8] != bytes([136, 92, 200, 103, 28, 218, 144, 140])
                or len(ix["accounts"]) < 28
            ):
                continue
            a = [keys[k] if 0 <= k < len(keys) else ZERO for k in ix["accounts"]]
            if (
                a[4] != PROGRAMS["RaydiumCpmm"]
                or stonkfun_mode_from_platform_config(a[3]) is None
            ):
                continue
            if ZERO in (a[17], a[5], a[1], a[2]) or a[17] == a[5] or a[1] == a[2]:
                continue
            entries.append(
                StonkFunGraduatedPool(
                    a[17], a[5], a[1], a[2], a[3], body["signatures"][0], tx["slot"]
                )
            )
        return self.observe_migrations(entries, True)
