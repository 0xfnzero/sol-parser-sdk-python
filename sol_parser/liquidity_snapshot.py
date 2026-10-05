"""Native liquidity identity decoders and immutable raw subscription snapshots."""

from __future__ import annotations
from dataclasses import dataclass
import base58
from .accounts import AccountData
from .grpc_types import EventMetadata
from .transaction_route import PROGRAMS


@dataclass
class RawAccountSnapshotEvent:
    metadata: EventMetadata
    account: AccountData
    write_version: int
    is_startup: bool


@dataclass
class LiquidityAccountSnapshotEvent:
    metadata: EventMetadata
    pubkey: str
    owner: str
    kind: dict | str
    data: bytes


def parse_liquidity_account(account: AccountData, metadata: EventMetadata):
    if account.lamports <= 0 or account.executable:
        return None
    d, owner = bytes(account.data), account.owner
    disc = d[:8]

    def key(o):
        return base58.b58encode(d[o : o + 32]).decode()

    def number(o, n, signed=False):
        return int.from_bytes(d[o : o + n], "little", signed=signed)

    kind = None
    if owner == PROGRAMS["LaunchLab"]:
        if disc == bytes([247, 237, 227, 245, 215, 195, 222, 70]) and len(d) >= 429:
            kind = {
                "LaunchLabPool": dict(
                    base_mint=key(205),
                    quote_mint=key(237),
                    global_config=key(141),
                    platform_config=key(173),
                )
            }
        elif disc == bytes([149, 8, 156, 202, 160, 252, 176, 217]) and len(d) >= 35:
            kind = "LaunchLabGlobalConfig"
        elif disc == bytes([160, 78, 128, 0, 248, 83, 230, 160]) and len(d) >= 728:
            kind = "LaunchLabPlatformConfig"
    elif owner == PROGRAMS["MeteoraDlmm"]:
        if disc == bytes([33, 11, 49, 98, 181, 101, 177, 13]) and len(d) >= 904:
            kind = {
                "DlmmPool": dict(
                    token_x_mint=key(88),
                    token_y_mint=key(120),
                    active_id=number(76, 4, True),
                    bin_step=number(80, 2),
                )
            }
        elif disc == bytes([92, 142, 92, 220, 5, 148, 70, 181]) and len(d) >= 10136:
            kind = {"DlmmBinArray": dict(pool=key(24), index=number(8, 8, True))}
        elif disc == bytes([80, 111, 124, 113, 55, 237, 18, 5]) and len(d) >= 1576:
            kind = {"DlmmBitmap": dict(pool=key(8))}
    elif owner == PROGRAMS["OrcaWhirlpool"]:
        if disc == bytes([17, 216, 246, 142, 225, 199, 218, 56]) and len(d) >= 148:
            bitmap, offset = number(44, 16), 60
            if bitmap >> 88:
                return None
            for i in range(88):
                if (
                    offset >= len(d)
                    or d[offset] not in (0, 1)
                    or d[offset] != (bitmap >> i) & 1
                ):
                    return None
                offset += 1 + (112 if d[offset] else 0)
                if offset > len(d):
                    return None
            kind = {
                "OrcaDynamicTickArray": dict(
                    pool=key(12),
                    start_tick_index=number(8, 4, True),
                    tick_bitmap=bitmap,
                )
            }
        elif disc == bytes([139, 194, 131, 179, 140, 179, 229, 244]) and len(d) >= 254:
            kind = {"OrcaAdaptiveOracle": dict(pool=key(8))}
    elif (
        owner == PROGRAMS["RaydiumClmm"]
        and disc == bytes([60, 150, 36, 219, 97, 128, 139, 153])
        and len(d) >= 1832
    ):
        kind = {"ClmmBitmap": dict(pool=key(8))}
    if kind is None:
        return None
    return LiquidityAccountSnapshotEvent(metadata, account.pubkey, owner, kind, d)
