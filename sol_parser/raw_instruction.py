"""Lossless outer instructions, without inferred CPI or trade semantics."""
from enum import Enum

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
