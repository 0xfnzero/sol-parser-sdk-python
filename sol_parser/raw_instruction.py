"""Lossless outer instructions, without inferred CPI or trade semantics."""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from .event_types import DexEventBase

INFRASTRUCTURE_PROGRAMS = frozenset(["11111111111111111111111111111111","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb","ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL","ComputeBudget111111111111111111111111111111","MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr","Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo","AddressLookupTab1e1111111111111111111111111","Vote111111111111111111111111111111111111111","Ed25519SigVerify111111111111111111111111111","KeccakSecp256k11111111111111111111111111111","Secp256r1SigVerify1111111111111111111111111"])

class RawInstructionDexType(str, Enum):
    """Stable DEX identifiers; serialized as the original strings."""
    PUMPFUN = "pumpfun"
    PUMPSWAP = "pumpswap"
    RAYDIUM_LAUNCHLAB = "raydium_launchlab"
    RAYDIUM_CPMM = "raydium_cpmm"
    RAYDIUM_CLMM = "raydium_clmm"
    RAYDIUM_AMM_V4 = "raydium_amm_v4"
    ORCA_WHIRLPOOL = "orca_whirlpool"
    METEORA_POOLS = "meteora_pools"
    METEORA_DAMM_V2 = "meteora_damm_v2"
    METEORA_DLMM = "meteora_dlmm"
    METEORA_DBC = "meteora_dbc"


@dataclass
class RawInstructionDex:
    """DEX program reference, not proof of CPI execution or a pool layout."""
    dex_type: RawInstructionDexType
    program_id: str
    pool: Optional[str] = None

    def __post_init__(self):
        # Normalize JSON strings and reject unsupported identifiers.
        self.dex_type = RawInstructionDexType(self.dex_type)

@dataclass
class RawInstructionEvent(DexEventBase):
    dexes: list[RawInstructionDex] = field(default_factory=list)
    program_id: str = ''
    instruction_index: int = 0
    # Original order including duplicates. None denotes an unresolved ALT key.
    accounts: list[Optional[str]] = field(default_factory=list)
    account_indices: list[int] = field(default_factory=list)
    instruction_data: list[int] = field(default_factory=list)

def raw_instruction_dexes(program, accounts):
    from . import instructions as program_ids
    return [RawInstructionDex(name, getattr(program_ids, pid)) for name, pid, _ in _DEX_PROGRAMS
            if program == getattr(program_ids, pid) or getattr(program_ids, pid) in accounts]

_DEX_PROGRAMS = [
    (RawInstructionDexType.PUMPFUN, "PUMPFUN_PROGRAM_ID", "PumpFunTrade"),
    (RawInstructionDexType.PUMPSWAP, "PUMPSWAP_PROGRAM_ID", "PumpSwapTrade"),
    (RawInstructionDexType.RAYDIUM_LAUNCHLAB, "RAYDIUM_LAUNCHLAB_PROGRAM_ID", "RaydiumLaunchlabTrade"),
    (RawInstructionDexType.RAYDIUM_CPMM, "RAYDIUM_CPMM_PROGRAM_ID", "RaydiumCpmmSwap"),
    (RawInstructionDexType.RAYDIUM_CLMM, "RAYDIUM_CLMM_PROGRAM_ID", "RaydiumClmmSwap"),
    (RawInstructionDexType.RAYDIUM_AMM_V4, "RAYDIUM_AMM_V4_PROGRAM_ID", "RaydiumAmmV4Swap"),
    (RawInstructionDexType.ORCA_WHIRLPOOL, "ORCA_WHIRLPOOL_PROGRAM_ID", "OrcaWhirlpoolSwap"),
    (RawInstructionDexType.METEORA_POOLS, "METEORA_POOLS_PROGRAM_ID", "MeteoraPoolsSwap"),
    (RawInstructionDexType.METEORA_DAMM_V2, "METEORA_DAMM_V2_PROGRAM_ID", "MeteoraDammV2Swap"),
    (RawInstructionDexType.METEORA_DLMM, "METEORA_DLMM_PROGRAM_ID", "MeteoraDlmmSwap"),
    (RawInstructionDexType.METEORA_DBC, "METEORA_DBC_PROGRAM_ID", "MeteoraDbcSwap"),
]

def raw_instruction_matches_filter(dexes, filter):
    from .grpc_types import EventType
    if filter is None:
        return True
    if EventType.RAW_INSTRUCTION in (getattr(filter, "exclude_types", None) or ()):
        return False
    included = getattr(filter, "include_only", None)
    if included is not None and EventType.RAW_INSTRUCTION in included:
        return True
    if not dexes:
        return included is None
    return any(dex.dex_type == name and (included is None or EventType(event) in included)
               and filter.should_include(EventType(event))
               for dex in dexes for name, _, event in _DEX_PROGRAMS)
