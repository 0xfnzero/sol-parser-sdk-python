"""EventType inventory parity with Rust ``sol_parser_sdk::grpc::EventType``."""

from __future__ import annotations

from .grpc_types import all_event_types

RUST_EVENT_TYPES = [
    "BlockMeta",
    "RaydiumLaunchlabTrade",
    "RaydiumLaunchlabPoolCreate",
    "RaydiumLaunchlabMigrateAmm",
    "PumpFunTrade",
    "PumpFunBuy",
    "PumpFunSell",
    "PumpFunBuyExactSolIn",
    "PumpFunCreate",
    "PumpFunCreateV2",
    "PumpFunComplete",
    "PumpFunMigrate",
    "PumpFeesCreateFeeSharingConfig",
    "PumpFeesInitializeFeeConfig",
    "PumpFeesResetFeeSharingConfig",
    "PumpFeesRevokeFeeSharingAuthority",
    "PumpFeesTransferFeeSharingAuthority",
    "PumpFeesUpdateAdmin",
    "PumpFeesUpdateFeeConfig",
    "PumpFeesUpdateFeeShares",
    "PumpFeesUpsertFeeTiers",
    "PumpFunMigrateBondingCurveCreator",
    "PumpSwapTrade",
    "PumpSwapBuy",
    "PumpSwapSell",
    "PumpSwapCreatePool",
    "PumpSwapLiquidityAdded",
    "PumpSwapLiquidityRemoved",
    "RaydiumCpmmSwap",
    "RaydiumCpmmDeposit",
    "RaydiumCpmmWithdraw",
    "RaydiumCpmmInitialize",
    "RaydiumClmmSwap",
    "RaydiumClmmCreatePool",
    "RaydiumClmmOpenPosition",
    "RaydiumClmmClosePosition",
    "RaydiumClmmIncreaseLiquidity",
    "RaydiumClmmDecreaseLiquidity",
    "RaydiumClmmLiquidityChange",
    "RaydiumClmmConfigChange",
    "RaydiumClmmCreatePersonalPosition",
    "RaydiumClmmLiquidityCalculate",
    "RaydiumClmmOpenLimitOrder",
    "RaydiumClmmIncreaseLimitOrder",
    "RaydiumClmmDecreaseLimitOrder",
    "RaydiumClmmSettleLimitOrder",
    "RaydiumClmmUpdateRewardInfos",
    "RaydiumClmmOpenPositionWithTokenExtNft",
    "RaydiumClmmCollectFee",
    "RaydiumAmmV4Swap",
    "RaydiumAmmV4Deposit",
    "RaydiumAmmV4Withdraw",
    "RaydiumAmmV4Initialize2",
    "RaydiumAmmV4WithdrawPnl",
    "OrcaWhirlpoolSwap",
    "OrcaWhirlpoolLiquidityIncreased",
    "OrcaWhirlpoolLiquidityDecreased",
    "OrcaWhirlpoolPoolInitialized",
    "MeteoraPoolsSwap",
    "MeteoraPoolsAddLiquidity",
    "MeteoraPoolsRemoveLiquidity",
    "MeteoraPoolsBootstrapLiquidity",
    "MeteoraPoolsPoolCreated",
    "MeteoraPoolsSetPoolFees",
    "MeteoraDammV2Swap",
    "MeteoraDammV2AddLiquidity",
    "MeteoraDammV2RemoveLiquidity",
    "MeteoraDammV2InitializePool",
    "MeteoraDammV2CreatePosition",
    "MeteoraDammV2ClosePosition",
    "MeteoraDbcSwap",
    "MeteoraDbcInitializePool",
    "MeteoraDbcCurveComplete",
    "MeteoraDlmmSwap",
    "MeteoraDlmmAddLiquidity",
    "MeteoraDlmmRemoveLiquidity",
    "MeteoraDlmmInitializePool",
    "MeteoraDlmmInitializeBinArray",
    "MeteoraDlmmCreatePosition",
    "MeteoraDlmmClosePosition",
    "MeteoraDlmmClaimFee",
    "TokenAccount",
    "TokenInfo",
    "NonceAccount",
    "AccountPumpFunGlobal",
    "AccountPumpFunBondingCurve",
    "AccountPumpFunFeeConfig",
    "AccountPumpFunSharingConfig",
    "AccountPumpFunGlobalVolumeAccumulator",
    "AccountPumpFunUserVolumeAccumulator",
    "AccountPumpSwapGlobalConfig",
    "AccountPumpSwapPool",
    "AccountRaydiumClmmAmmConfig",
    "AccountRaydiumClmmPoolState",
    "AccountRaydiumClmmTickArrayState",
    "AccountRaydiumCpmmAmmConfig",
    "AccountRaydiumCpmmPoolState",
    "AccountOrcaWhirlpool",
    "AccountOrcaPosition",
    "AccountOrcaTickArray",
    "AccountOrcaFeeTier",
    "AccountOrcaWhirlpoolsConfig",
]


def run_event_type_parity_check() -> int:
    actual = [event_type.value for event_type in all_event_types()]
    if actual == RUST_EVENT_TYPES:
        print(f"[event-type-parity] OK：EventType 与 Rust 清单一致（共 {len(actual)} 个）")
        return 0
    only_expected = [x for x in RUST_EVENT_TYPES if x not in actual]
    only_actual = [x for x in actual if x not in RUST_EVENT_TYPES]
    print("[event-type-parity] EventType 与 Rust 清单不一致")
    if only_expected:
        print("  Python 缺:", ", ".join(only_expected))
    if only_actual:
        print("  Python 多:", ", ".join(only_actual))
    return 1


if __name__ == "__main__":
    raise SystemExit(run_event_type_parity_check())
