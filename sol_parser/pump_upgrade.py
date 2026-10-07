"""Pump retained-fee and synthetic completion events (official 8cda1fa)."""

from dataclasses import dataclass
from .event_types import DexEvent
from .grpc_types import EventMetadata, EventType
import base58


@dataclass
class PumpFunPostCompleteBuyEvent:
    metadata: EventMetadata
    user: str
    mint: str
    bonding_curve: str
    quote_mint: str
    timestamp: int
    base_out: int
    quote_in: int
    fee_basis_points: int
    fee: int
    creator_fee_basis_points: int
    creator_fee: int
    buyback_fee: int
    pool_base_reserves_before: int
    pool_quote_reserves_before: int
    pool_base_reserves_after: int
    pool_quote_reserves_after: int


@dataclass
class PumpFunSweepBondingCurveFeeEvent:
    metadata: EventMetadata
    timestamp: int
    mint: str
    bonding_curve: str
    quote_mint: str
    recipient: str
    amount: int
    bucket: int


@dataclass
class PumpFunCompleteEvent:
    metadata: EventMetadata
    user: str
    mint: str
    bonding_curve: str
    timestamp: int
    quote_mint: str


@dataclass
class PumpSwapSweepPoolFeeEvent:
    metadata: EventMetadata
    timestamp: int
    pool: str
    base_mint: str
    quote_mint: str
    recipient: str
    payer: str
    amount: int
    bucket: int


_EVENTS = {
    18146529233607700591: (
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        EventType.PUMP_FUN_POST_COMPLETE_BUY,
        PumpFunPostCompleteBuyEvent,
        [
            ("user", "pubkey"),
            ("mint", "pubkey"),
            ("bonding_curve", "pubkey"),
            ("quote_mint", "pubkey"),
            ("timestamp", "i64"),
            ("base_out", "u64"),
            ("quote_in", "u64"),
            ("fee_basis_points", "u64"),
            ("fee", "u64"),
            ("creator_fee_basis_points", "u64"),
            ("creator_fee", "u64"),
            ("buyback_fee", "u64"),
            ("pool_base_reserves_before", "u64"),
            ("pool_quote_reserves_before", "u64"),
            ("pool_base_reserves_after", "u64"),
            ("pool_quote_reserves_after", "u64"),
        ],
    ),
    3118876958563052404: (
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        EventType.PUMP_FUN_SWEEP_BONDING_CURVE_FEE,
        PumpFunSweepBondingCurveFeeEvent,
        [
            ("timestamp", "i64"),
            ("mint", "pubkey"),
            ("bonding_curve", "pubkey"),
            ("quote_mint", "pubkey"),
            ("recipient", "pubkey"),
            ("amount", "u64"),
            ("bucket", "u8"),
        ],
    ),
    619296439455019615: (
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        EventType.PUMP_FUN_COMPLETE,
        PumpFunCompleteEvent,
        [
            ("user", "pubkey"),
            ("mint", "pubkey"),
            ("bonding_curve", "pubkey"),
            ("timestamp", "i64"),
            ("quote_mint", "pubkey"),
        ],
    ),
    11927646055507993730: (
        "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
        EventType.PUMP_SWAP_SWEEP_POOL_FEE,
        PumpSwapSweepPoolFeeEvent,
        [
            ("timestamp", "i64"),
            ("pool", "pubkey"),
            ("base_mint", "pubkey"),
            ("quote_mint", "pubkey"),
            ("recipient", "pubkey"),
            ("payer", "pubkey"),
            ("amount", "u64"),
            ("bucket", "u8"),
        ],
    ),
}


def pump_upgrade_event_type(disc, program_id=None):
    spec = _EVENTS.get(disc)
    return spec[1] if spec and (not program_id or program_id == spec[0]) else None


def parse_pump_upgrade_event(disc, data, metadata, program_id=None):
    if pump_upgrade_event_type(disc, program_id) is None:
        return None
    _, kind, cls, fields = _EVENTS[disc]
    if cls is PumpFunCompleteEvent and len(data) == 104:
        data = data + bytes(
            base58.b58decode("So11111111111111111111111111111111111111112")
        )
    offset = 0
    values = {}
    for name, t in fields:
        size = 32 if t == "pubkey" else 1 if t == "u8" else 8
        raw = data[offset : offset + size]
        if len(raw) != size:
            return None
        values[name] = (
            base58.b58encode(raw).decode()
            if t == "pubkey"
            else int.from_bytes(raw, "little", signed=t == "i64")
        )
        offset += size
    if offset != len(data):
        return None
    return DexEvent(kind, cls(metadata=metadata, **values))


def decode_pump_multi_hop_intent(program, data, accounts):
    """Instruction limits only. Actual execution is reported by per-hop trade events."""
    if (
        program != "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        or len(data) != 24
        or data[:8] != bytes([43, 100, 73, 19, 233, 246, 111, 148])
        or len(accounts) < 21
        or (len(accounts) - 16) % 5
    ):
        return None
    amount_in = int.from_bytes(data[8:16], "little")
    minimum = int.from_bytes(data[16:24], "little")
    if not amount_in or not minimum:
        return None
    return dict(
        user=accounts[0],
        input_account=accounts[1],
        output_account=accounts[2],
        amount_in=amount_in,
        min_amount_out=minimum,
        hops=[
            dict(
                base_mint=accounts[i],
                quote_mint=accounts[i + 1],
                venue=accounts[i + 2],
                base_vault=accounts[i + 3],
                quote_vault=accounts[i + 4],
            )
            for i in range(16, len(accounts), 5)
        ],
    )
