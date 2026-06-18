"""gRPC 类型定义，对齐 yellowstone-grpc 和 TypeScript SDK"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Sequence
from dataclasses import dataclass, field


class OrderMode(str, Enum):
    """gRPC 订阅顺序模式"""
    UNORDERED = "Unordered"
    ORDERED = "Ordered"
    STREAMING_ORDERED = "StreamingOrdered"
    MICRO_BATCH = "MicroBatch"


class CommitmentLevel(IntEnum):
    """Solana 确认级别"""
    PROCESSED = 0
    CONFIRMED = 1
    FINALIZED = 2


class SlotStatus(IntEnum):
    """Slot 状态"""
    PROCESSED = 0
    CONFIRMED = 1
    FINALIZED = 2
    FIRST_SHRED_RECEIVED = 3
    COMPLETED = 4
    CREATED_BANK = 5
    DEAD = 6


class EventType(str, Enum):
    """事件类型"""
    # Block
    BLOCK_META = "BlockMeta"
    # RaydiumLaunchlab
    RAYDIUM_LAUNCHLAB_TRADE = "RaydiumLaunchlabTrade"
    RAYDIUM_LAUNCHLAB_POOL_CREATE = "RaydiumLaunchlabPoolCreate"
    RAYDIUM_LAUNCHLAB_MIGRATE_AMM = "RaydiumLaunchlabMigrateAmm"
    # PumpFun
    PUMP_FUN_TRADE = "PumpFunTrade"
    PUMP_FUN_BUY = "PumpFunBuy"
    PUMP_FUN_SELL = "PumpFunSell"
    PUMP_FUN_BUY_EXACT_SOL_IN = "PumpFunBuyExactSolIn"
    PUMP_FUN_CREATE = "PumpFunCreate"
    PUMP_FUN_CREATE_V2 = "PumpFunCreateV2"
    PUMP_FUN_COMPLETE = "PumpFunComplete"
    PUMP_FUN_MIGRATE = "PumpFunMigrate"
    PUMP_FEES_CREATE_FEE_SHARING_CONFIG = "PumpFeesCreateFeeSharingConfig"
    PUMP_FEES_INITIALIZE_FEE_CONFIG = "PumpFeesInitializeFeeConfig"
    PUMP_FEES_RESET_FEE_SHARING_CONFIG = "PumpFeesResetFeeSharingConfig"
    PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY = "PumpFeesRevokeFeeSharingAuthority"
    PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY = "PumpFeesTransferFeeSharingAuthority"
    PUMP_FEES_UPDATE_ADMIN = "PumpFeesUpdateAdmin"
    PUMP_FEES_UPDATE_FEE_CONFIG = "PumpFeesUpdateFeeConfig"
    PUMP_FEES_UPDATE_FEE_SHARES = "PumpFeesUpdateFeeShares"
    PUMP_FEES_UPSERT_FEE_TIERS = "PumpFeesUpsertFeeTiers"
    PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR = "PumpFunMigrateBondingCurveCreator"
    # PumpSwap
    PUMP_SWAP_TRADE = "PumpSwapTrade"
    PUMP_SWAP_BUY = "PumpSwapBuy"
    PUMP_SWAP_SELL = "PumpSwapSell"
    PUMP_SWAP_CREATE_POOL = "PumpSwapCreatePool"
    PUMP_SWAP_LIQUIDITY_ADDED = "PumpSwapLiquidityAdded"
    PUMP_SWAP_LIQUIDITY_REMOVED = "PumpSwapLiquidityRemoved"
    # Raydium CPMM
    RAYDIUM_CPMM_SWAP = "RaydiumCpmmSwap"
    RAYDIUM_CPMM_DEPOSIT = "RaydiumCpmmDeposit"
    RAYDIUM_CPMM_WITHDRAW = "RaydiumCpmmWithdraw"
    RAYDIUM_CPMM_INITIALIZE = "RaydiumCpmmInitialize"
    # Raydium CLMM
    RAYDIUM_CLMM_SWAP = "RaydiumClmmSwap"
    RAYDIUM_CLMM_CREATE_POOL = "RaydiumClmmCreatePool"
    RAYDIUM_CLMM_OPEN_POSITION = "RaydiumClmmOpenPosition"
    RAYDIUM_CLMM_CLOSE_POSITION = "RaydiumClmmClosePosition"
    RAYDIUM_CLMM_INCREASE_LIQUIDITY = "RaydiumClmmIncreaseLiquidity"
    RAYDIUM_CLMM_DECREASE_LIQUIDITY = "RaydiumClmmDecreaseLiquidity"
    RAYDIUM_CLMM_LIQUIDITY_CHANGE = "RaydiumClmmLiquidityChange"
    RAYDIUM_CLMM_CONFIG_CHANGE = "RaydiumClmmConfigChange"
    RAYDIUM_CLMM_CREATE_PERSONAL_POSITION = "RaydiumClmmCreatePersonalPosition"
    RAYDIUM_CLMM_LIQUIDITY_CALCULATE = "RaydiumClmmLiquidityCalculate"
    RAYDIUM_CLMM_OPEN_LIMIT_ORDER = "RaydiumClmmOpenLimitOrder"
    RAYDIUM_CLMM_INCREASE_LIMIT_ORDER = "RaydiumClmmIncreaseLimitOrder"
    RAYDIUM_CLMM_DECREASE_LIMIT_ORDER = "RaydiumClmmDecreaseLimitOrder"
    RAYDIUM_CLMM_SETTLE_LIMIT_ORDER = "RaydiumClmmSettleLimitOrder"
    RAYDIUM_CLMM_UPDATE_REWARD_INFOS = "RaydiumClmmUpdateRewardInfos"
    RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT = "RaydiumClmmOpenPositionWithTokenExtNft"
    RAYDIUM_CLMM_COLLECT_FEE = "RaydiumClmmCollectFee"
    # Raydium AMM V4
    RAYDIUM_AMM_V4_SWAP = "RaydiumAmmV4Swap"
    RAYDIUM_AMM_V4_DEPOSIT = "RaydiumAmmV4Deposit"
    RAYDIUM_AMM_V4_WITHDRAW = "RaydiumAmmV4Withdraw"
    RAYDIUM_AMM_V4_INITIALIZE2 = "RaydiumAmmV4Initialize2"
    RAYDIUM_AMM_V4_WITHDRAW_PNL = "RaydiumAmmV4WithdrawPnl"
    # Orca Whirlpool
    ORCA_WHIRLPOOL_SWAP = "OrcaWhirlpoolSwap"
    ORCA_WHIRLPOOL_LIQUIDITY_INCREASED = "OrcaWhirlpoolLiquidityIncreased"
    ORCA_WHIRLPOOL_LIQUIDITY_DECREASED = "OrcaWhirlpoolLiquidityDecreased"
    ORCA_WHIRLPOOL_POOL_INITIALIZED = "OrcaWhirlpoolPoolInitialized"
    # Meteora Pools
    METEORA_POOLS_SWAP = "MeteoraPoolsSwap"
    METEORA_POOLS_ADD_LIQUIDITY = "MeteoraPoolsAddLiquidity"
    METEORA_POOLS_REMOVE_LIQUIDITY = "MeteoraPoolsRemoveLiquidity"
    METEORA_POOLS_BOOTSTRAP_LIQUIDITY = "MeteoraPoolsBootstrapLiquidity"
    METEORA_POOLS_POOL_CREATED = "MeteoraPoolsPoolCreated"
    METEORA_POOLS_SET_POOL_FEES = "MeteoraPoolsSetPoolFees"
    # Meteora DAMM V2
    METEORA_DAMM_V2_SWAP = "MeteoraDammV2Swap"
    METEORA_DAMM_V2_ADD_LIQUIDITY = "MeteoraDammV2AddLiquidity"
    METEORA_DAMM_V2_REMOVE_LIQUIDITY = "MeteoraDammV2RemoveLiquidity"
    METEORA_DAMM_V2_INITIALIZE_POOL = "MeteoraDammV2InitializePool"
    METEORA_DAMM_V2_CREATE_POSITION = "MeteoraDammV2CreatePosition"
    METEORA_DAMM_V2_CLOSE_POSITION = "MeteoraDammV2ClosePosition"
    # Meteora DBC
    METEORA_DBC_SWAP = "MeteoraDbcSwap"
    METEORA_DBC_INITIALIZE_POOL = "MeteoraDbcInitializePool"
    METEORA_DBC_CURVE_COMPLETE = "MeteoraDbcCurveComplete"
    # Meteora DLMM
    METEORA_DLMM_SWAP = "MeteoraDlmmSwap"
    METEORA_DLMM_ADD_LIQUIDITY = "MeteoraDlmmAddLiquidity"
    METEORA_DLMM_REMOVE_LIQUIDITY = "MeteoraDlmmRemoveLiquidity"
    METEORA_DLMM_INITIALIZE_POOL = "MeteoraDlmmInitializePool"
    METEORA_DLMM_INITIALIZE_BIN_ARRAY = "MeteoraDlmmInitializeBinArray"
    METEORA_DLMM_CREATE_POSITION = "MeteoraDlmmCreatePosition"
    METEORA_DLMM_CLOSE_POSITION = "MeteoraDlmmClosePosition"
    METEORA_DLMM_CLAIM_FEE = "MeteoraDlmmClaimFee"
    # Account types
    TOKEN_ACCOUNT = "TokenAccount"
    TOKEN_INFO = "TokenInfo"
    NONCE_ACCOUNT = "NonceAccount"
    ACCOUNT_PUMP_FUN_GLOBAL = "AccountPumpFunGlobal"
    ACCOUNT_PUMP_FUN_BONDING_CURVE = "AccountPumpFunBondingCurve"
    ACCOUNT_PUMP_FUN_FEE_CONFIG = "AccountPumpFunFeeConfig"
    ACCOUNT_PUMP_FUN_SHARING_CONFIG = "AccountPumpFunSharingConfig"
    ACCOUNT_PUMP_FUN_GLOBAL_VOLUME_ACCUMULATOR = "AccountPumpFunGlobalVolumeAccumulator"
    ACCOUNT_PUMP_FUN_USER_VOLUME_ACCUMULATOR = "AccountPumpFunUserVolumeAccumulator"
    ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG = "AccountPumpSwapGlobalConfig"
    ACCOUNT_PUMP_SWAP_POOL = "AccountPumpSwapPool"
    ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG = "AccountRaydiumClmmAmmConfig"
    ACCOUNT_RAYDIUM_CLMM_POOL_STATE = "AccountRaydiumClmmPoolState"
    ACCOUNT_RAYDIUM_CLMM_TICK_ARRAY_STATE = "AccountRaydiumClmmTickArrayState"
    ACCOUNT_RAYDIUM_CPMM_AMM_CONFIG = "AccountRaydiumCpmmAmmConfig"
    ACCOUNT_RAYDIUM_CPMM_POOL_STATE = "AccountRaydiumCpmmPoolState"
    ACCOUNT_ORCA_WHIRLPOOL = "AccountOrcaWhirlpool"
    ACCOUNT_ORCA_POSITION = "AccountOrcaPosition"
    ACCOUNT_ORCA_TICK_ARRAY = "AccountOrcaTickArray"
    ACCOUNT_ORCA_FEE_TIER = "AccountOrcaFeeTier"
    ACCOUNT_ORCA_WHIRLPOOLS_CONFIG = "AccountOrcaWhirlpoolsConfig"


PUMPFUN_BUY_FAMILY = (
    EventType.PUMP_FUN_BUY,
    EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
)
PUMPFUN_TRADE_FAMILY = (
    EventType.PUMP_FUN_BUY,
    EventType.PUMP_FUN_SELL,
    EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
)
PUMPFUN_CREATE_FAMILY = (
    EventType.PUMP_FUN_CREATE,
    EventType.PUMP_FUN_CREATE_V2,
)
PUMPSWAP_TRADE_FAMILY = (
    EventType.PUMP_SWAP_BUY,
    EventType.PUMP_SWAP_SELL,
)
PUMP_FEES_EVENT_TYPES = (
    EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
    EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
    EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
    EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
    EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
    EventType.PUMP_FEES_UPDATE_ADMIN,
    EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
    EventType.PUMP_FEES_UPDATE_FEE_SHARES,
    EventType.PUMP_FEES_UPSERT_FEE_TIERS,
)
PUMPFUN_FILTER_TYPES = (
    EventType.PUMP_FUN_TRADE,
    EventType.PUMP_FUN_BUY,
    EventType.PUMP_FUN_SELL,
    EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
    EventType.PUMP_FUN_CREATE,
    EventType.PUMP_FUN_CREATE_V2,
    EventType.PUMP_FUN_COMPLETE,
    EventType.PUMP_FUN_MIGRATE,
    EventType.PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR,
)
PUMPSWAP_FILTER_TYPES = (
    EventType.PUMP_SWAP_TRADE,
    EventType.PUMP_SWAP_BUY,
    EventType.PUMP_SWAP_SELL,
    EventType.PUMP_SWAP_CREATE_POOL,
    EventType.PUMP_SWAP_LIQUIDITY_ADDED,
    EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
)
METEORA_DAMM_V2_FILTER_TYPES = (
    EventType.METEORA_DAMM_V2_SWAP,
    EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
    EventType.METEORA_DAMM_V2_CREATE_POSITION,
    EventType.METEORA_DAMM_V2_CLOSE_POSITION,
    EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
    EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
)
METEORA_DBC_FILTER_TYPES = (
    EventType.METEORA_DBC_SWAP,
    EventType.METEORA_DBC_INITIALIZE_POOL,
    EventType.METEORA_DBC_CURVE_COMPLETE,
)
RAYDIUM_CLMM_FILTER_TYPES = (
    EventType.RAYDIUM_CLMM_SWAP,
    EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
    EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
    EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE,
    EventType.RAYDIUM_CLMM_CONFIG_CHANGE,
    EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION,
    EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE,
    EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER,
    EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER,
    EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER,
    EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER,
    EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS,
    EventType.RAYDIUM_CLMM_CREATE_POOL,
    EventType.RAYDIUM_CLMM_OPEN_POSITION,
    EventType.RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT,
    EventType.RAYDIUM_CLMM_CLOSE_POSITION,
    EventType.RAYDIUM_CLMM_COLLECT_FEE,
)
RAYDIUM_CPMM_FILTER_TYPES = (
    EventType.RAYDIUM_CPMM_SWAP,
    EventType.RAYDIUM_CPMM_DEPOSIT,
    EventType.RAYDIUM_CPMM_WITHDRAW,
    EventType.RAYDIUM_CPMM_INITIALIZE,
)
RAYDIUM_AMM_V4_FILTER_TYPES = (
    EventType.RAYDIUM_AMM_V4_SWAP,
    EventType.RAYDIUM_AMM_V4_DEPOSIT,
    EventType.RAYDIUM_AMM_V4_WITHDRAW,
    EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
    EventType.RAYDIUM_AMM_V4_INITIALIZE2,
)
ORCA_WHIRLPOOL_FILTER_TYPES = (
    EventType.ORCA_WHIRLPOOL_SWAP,
    EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
    EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED,
    EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
)
METEORA_POOLS_FILTER_TYPES = (
    EventType.METEORA_POOLS_SWAP,
    EventType.METEORA_POOLS_ADD_LIQUIDITY,
    EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
    EventType.METEORA_POOLS_BOOTSTRAP_LIQUIDITY,
    EventType.METEORA_POOLS_POOL_CREATED,
    EventType.METEORA_POOLS_SET_POOL_FEES,
)
METEORA_DLMM_FILTER_TYPES = (
    EventType.METEORA_DLMM_SWAP,
    EventType.METEORA_DLMM_ADD_LIQUIDITY,
    EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
    EventType.METEORA_DLMM_INITIALIZE_POOL,
    EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
    EventType.METEORA_DLMM_CREATE_POSITION,
    EventType.METEORA_DLMM_CLOSE_POSITION,
    EventType.METEORA_DLMM_CLAIM_FEE,
)
RAYDIUM_LAUNCHLAB_FILTER_TYPES = (
    EventType.RAYDIUM_LAUNCHLAB_TRADE,
    EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE,
    EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM,
)
INSTRUCTION_EVENT_TYPES = (
    *PUMPFUN_FILTER_TYPES,
    *PUMP_FEES_EVENT_TYPES,
    *PUMPSWAP_FILTER_TYPES,
    *METEORA_DAMM_V2_FILTER_TYPES,
    *METEORA_POOLS_FILTER_TYPES,
    *METEORA_DLMM_FILTER_TYPES,
    *RAYDIUM_CLMM_FILTER_TYPES,
    *RAYDIUM_CPMM_FILTER_TYPES,
    *RAYDIUM_AMM_V4_FILTER_TYPES,
    *ORCA_WHIRLPOOL_FILTER_TYPES,
    *RAYDIUM_LAUNCHLAB_FILTER_TYPES,
)
INSTRUCTION_EVENT_TYPE_SET = frozenset(INSTRUCTION_EVENT_TYPES)


def all_event_types() -> List[EventType]:
    """返回所有支持的事件类型列表"""
    return [
        # Block
        EventType.BLOCK_META,
        # RaydiumLaunchlab
        EventType.RAYDIUM_LAUNCHLAB_TRADE,
        EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE,
        EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM,
        # PumpFun
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        EventType.PUMP_FUN_CREATE,
        EventType.PUMP_FUN_CREATE_V2,
        EventType.PUMP_FUN_COMPLETE,
        EventType.PUMP_FUN_MIGRATE,
        EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
        EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
        EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
        EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
        EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
        EventType.PUMP_FEES_UPDATE_ADMIN,
        EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
        EventType.PUMP_FEES_UPDATE_FEE_SHARES,
        EventType.PUMP_FEES_UPSERT_FEE_TIERS,
        EventType.PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR,
        # PumpSwap
        EventType.PUMP_SWAP_TRADE,
        EventType.PUMP_SWAP_BUY,
        EventType.PUMP_SWAP_SELL,
        EventType.PUMP_SWAP_CREATE_POOL,
        EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
        # Raydium CPMM
        EventType.RAYDIUM_CPMM_SWAP,
        EventType.RAYDIUM_CPMM_DEPOSIT,
        EventType.RAYDIUM_CPMM_WITHDRAW,
        EventType.RAYDIUM_CPMM_INITIALIZE,
        # Raydium CLMM
        EventType.RAYDIUM_CLMM_SWAP,
        EventType.RAYDIUM_CLMM_CREATE_POOL,
        EventType.RAYDIUM_CLMM_OPEN_POSITION,
        EventType.RAYDIUM_CLMM_CLOSE_POSITION,
        EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
        EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
        EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE,
        EventType.RAYDIUM_CLMM_CONFIG_CHANGE,
        EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION,
        EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE,
        EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER,
        EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER,
        EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER,
        EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER,
        EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS,
        EventType.RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT,
        EventType.RAYDIUM_CLMM_COLLECT_FEE,
        # Raydium AMM V4
        EventType.RAYDIUM_AMM_V4_SWAP,
        EventType.RAYDIUM_AMM_V4_DEPOSIT,
        EventType.RAYDIUM_AMM_V4_WITHDRAW,
        EventType.RAYDIUM_AMM_V4_INITIALIZE2,
        EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
        # Orca Whirlpool
        EventType.ORCA_WHIRLPOOL_SWAP,
        EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
        EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED,
        EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
        # Meteora Pools
        EventType.METEORA_POOLS_SWAP,
        EventType.METEORA_POOLS_ADD_LIQUIDITY,
        EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
        EventType.METEORA_POOLS_BOOTSTRAP_LIQUIDITY,
        EventType.METEORA_POOLS_POOL_CREATED,
        EventType.METEORA_POOLS_SET_POOL_FEES,
        # Meteora DAMM V2
        EventType.METEORA_DAMM_V2_SWAP,
        EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        # Meteora DBC
        EventType.METEORA_DBC_SWAP,
        EventType.METEORA_DBC_INITIALIZE_POOL,
        EventType.METEORA_DBC_CURVE_COMPLETE,
        # Meteora DLMM
        EventType.METEORA_DLMM_SWAP,
        EventType.METEORA_DLMM_ADD_LIQUIDITY,
        EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
        EventType.METEORA_DLMM_INITIALIZE_POOL,
        EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
        EventType.METEORA_DLMM_CREATE_POSITION,
        EventType.METEORA_DLMM_CLOSE_POSITION,
        EventType.METEORA_DLMM_CLAIM_FEE,
        # Account types
        EventType.TOKEN_ACCOUNT,
        EventType.TOKEN_INFO,
        EventType.NONCE_ACCOUNT,
        EventType.ACCOUNT_PUMP_FUN_GLOBAL,
        EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE,
        EventType.ACCOUNT_PUMP_FUN_FEE_CONFIG,
        EventType.ACCOUNT_PUMP_FUN_SHARING_CONFIG,
        EventType.ACCOUNT_PUMP_FUN_GLOBAL_VOLUME_ACCUMULATOR,
        EventType.ACCOUNT_PUMP_FUN_USER_VOLUME_ACCUMULATOR,
        EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
        EventType.ACCOUNT_PUMP_SWAP_POOL,
        EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG,
        EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE,
        EventType.ACCOUNT_RAYDIUM_CLMM_TICK_ARRAY_STATE,
        EventType.ACCOUNT_RAYDIUM_CPMM_AMM_CONFIG,
        EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE,
        EventType.ACCOUNT_ORCA_WHIRLPOOL,
        EventType.ACCOUNT_ORCA_POSITION,
        EventType.ACCOUNT_ORCA_TICK_ARRAY,
        EventType.ACCOUNT_ORCA_FEE_TIER,
        EventType.ACCOUNT_ORCA_WHIRLPOOLS_CONFIG,
    ]


@dataclass
class EventMetadata:
    """事件元数据"""

    signature: str = ""
    slot: int = 0
    #: 区块内交易序号（Yellowstone ``SubscribeUpdateTransactionInfo.index`` / RPC ``transactionIndex``）
    tx_index: int = 0
    block_time_us: int = 0
    grpc_recv_us: int = 0
    recent_blockhash: str = ""
    is_created_buy: bool = False


@dataclass
class ClientConfig:
    """gRPC 客户端配置"""
    enable_metrics: bool = False
    connection_timeout_ms: int = 8000
    request_timeout_ms: int = 15000
    enable_tls: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    max_concurrent_streams: int = 100
    keep_alive_interval_ms: int = 30000
    keep_alive_timeout_ms: int = 5000
    buffer_size: int = 8192
    order_mode: OrderMode = OrderMode.UNORDERED
    order_timeout_ms: int = 100
    micro_batch_us: int = 100

    @staticmethod
    def default() -> ClientConfig:
        """返回默认客户端配置"""
        return ClientConfig()

    @staticmethod
    def low_latency() -> ClientConfig:
        """对齐 Rust ``ClientConfig::low_latency``"""
        return ClientConfig(
            enable_metrics=False,
            connection_timeout_ms=5000,
            request_timeout_ms=10000,
            enable_tls=True,
            max_retries=1,
            retry_delay_ms=100,
            max_concurrent_streams=200,
            keep_alive_interval_ms=10000,
            keep_alive_timeout_ms=2000,
            buffer_size=16384,
            order_mode=OrderMode.UNORDERED,
            order_timeout_ms=50,
            micro_batch_us=50,
        )

    @staticmethod
    def high_throughput() -> ClientConfig:
        """对齐 Rust ``ClientConfig::high_throughput``"""
        return ClientConfig(
            enable_metrics=True,
            connection_timeout_ms=10000,
            request_timeout_ms=30000,
            enable_tls=True,
            max_retries=5,
            retry_delay_ms=2000,
            max_concurrent_streams=500,
            keep_alive_interval_ms=60000,
            keep_alive_timeout_ms=10000,
            buffer_size=32768,
            order_mode=OrderMode.UNORDERED,
            order_timeout_ms=200,
            micro_batch_us=200,
        )


@dataclass
class TransactionFilter:
    """交易过滤器"""
    account_include: List[str] = field(default_factory=list)
    account_exclude: List[str] = field(default_factory=list)
    account_required: List[str] = field(default_factory=list)
    vote: Optional[bool] = None
    failed: Optional[bool] = None
    signature: str = ""

    @staticmethod
    def new() -> TransactionFilter:
        """创建新的交易过滤器"""
        return TransactionFilter()

    @staticmethod
    def from_program_ids(program_ids: List[str]) -> TransactionFilter:
        """对齐 Rust ``TransactionFilter::from_program_ids``"""
        return TransactionFilter(account_include=list(program_ids))

    def include_account(self, account: str) -> TransactionFilter:
        self.account_include.append(account)
        return self

    def exclude_account(self, account: str) -> TransactionFilter:
        self.account_exclude.append(account)
        return self

    def require_account(self, account: str) -> TransactionFilter:
        self.account_required.append(account)
        return self


class EventTypeFilter:
    """事件类型过滤器接口"""

    def should_include(self, event_type: EventType) -> bool:
        raise NotImplementedError


class IncludeOnlyFilter(EventTypeFilter):
    """仅包含指定类型的事件过滤器"""

    def __init__(self, include_only: List[EventType]):
        self.include_only = include_only

    def should_include(self, event_type: EventType) -> bool:
        if event_type in self.include_only:
            return True
        if event_type == EventType.PUMP_FUN_TRADE:
            if _types_intersect(self.include_only, PUMPFUN_TRADE_FAMILY):
                return True
        if event_type in PUMPFUN_TRADE_FAMILY:
            if EventType.PUMP_FUN_TRADE in self.include_only:
                return True
            if event_type in PUMPFUN_BUY_FAMILY:
                return _types_intersect(self.include_only, PUMPFUN_BUY_FAMILY)
            return False
        if event_type in PUMPFUN_CREATE_FAMILY:
            return _types_intersect(self.include_only, PUMPFUN_CREATE_FAMILY)
        if event_type in PUMPSWAP_TRADE_FAMILY:
            return EventType.PUMP_SWAP_TRADE in self.include_only
        return False


class ExcludeFilter(EventTypeFilter):
    """排除指定类型的事件过滤器"""

    def __init__(self, exclude_types: List[EventType]):
        self.exclude_types = exclude_types

    def should_include(self, event_type: EventType) -> bool:
        if event_type in self.exclude_types:
            return False
        if (
            event_type in PUMPFUN_TRADE_FAMILY
            and EventType.PUMP_FUN_TRADE in self.exclude_types
        ):
            return False
        if event_type in PUMPFUN_BUY_FAMILY and _types_intersect(
            self.exclude_types, PUMPFUN_BUY_FAMILY
        ):
            return False
        if event_type in PUMPFUN_CREATE_FAMILY and _types_intersect(
            self.exclude_types, PUMPFUN_CREATE_FAMILY
        ):
            return False
        if (
            event_type in PUMPSWAP_TRADE_FAMILY
            and EventType.PUMP_SWAP_TRADE in self.exclude_types
        ):
            return False
        return True


def event_type_filter_include_only(types: List[EventType]) -> EventTypeFilter:
    """创建仅包含指定类型的事件过滤器"""
    return IncludeOnlyFilter(types)


def event_type_filter_exclude(types: List[EventType]) -> EventTypeFilter:
    """创建排除指定类型的事件过滤器"""
    return ExcludeFilter(types)


def _types_intersect(left: Sequence[EventType], right: Sequence[EventType]) -> bool:
    return any(t in right for t in left)


def _event_type_filter_includes_any(
    filter: EventTypeFilter,
    types: Sequence[EventType],
) -> bool:
    if isinstance(filter, IncludeOnlyFilter):
        return _types_intersect(filter.include_only, types)
    if isinstance(filter, ExcludeFilter):
        return any(filter.should_include(t) for t in types)
    return any(filter.should_include(t) for t in types)


def event_type_filter_includes_pumpfun(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 PumpFun 相关类型"""
    return _event_type_filter_includes_any(filter, PUMPFUN_FILTER_TYPES)


def event_type_filter_includes_pump_fees(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Pump Fees 相关类型"""
    return _event_type_filter_includes_any(filter, PUMP_FEES_EVENT_TYPES)


def event_type_filter_includes_pumpswap(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 PumpSwap 相关类型"""
    return _event_type_filter_includes_any(filter, PUMPSWAP_FILTER_TYPES)


def event_type_filter_includes_meteora_damm_v2(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Meteora DAMM V2 相关类型"""
    return _event_type_filter_includes_any(filter, METEORA_DAMM_V2_FILTER_TYPES)


def event_type_filter_includes_meteora_dbc(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Meteora DBC 相关类型"""
    return _event_type_filter_includes_any(filter, METEORA_DBC_FILTER_TYPES)


def event_type_filter_includes_meteora_pools(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Meteora Pools 相关类型"""
    return _event_type_filter_includes_any(filter, METEORA_POOLS_FILTER_TYPES)


def event_type_filter_includes_meteora_dlmm(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Meteora DLMM 相关类型"""
    return _event_type_filter_includes_any(filter, METEORA_DLMM_FILTER_TYPES)


def event_type_filter_includes_raydium_clmm(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Raydium CLMM 相关类型"""
    return _event_type_filter_includes_any(filter, RAYDIUM_CLMM_FILTER_TYPES)


def event_type_filter_includes_raydium_cpmm(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Raydium CPMM 相关类型"""
    return _event_type_filter_includes_any(filter, RAYDIUM_CPMM_FILTER_TYPES)


def event_type_filter_includes_raydium_amm_v4(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Raydium AMM V4 相关类型"""
    return _event_type_filter_includes_any(filter, RAYDIUM_AMM_V4_FILTER_TYPES)


def event_type_filter_includes_orca_whirlpool(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Orca Whirlpool 相关类型"""
    return _event_type_filter_includes_any(filter, ORCA_WHIRLPOOL_FILTER_TYPES)


def event_type_filter_includes_raydium_launchlab(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Raydium LaunchLab 相关类型"""
    return _event_type_filter_includes_any(filter, RAYDIUM_LAUNCHLAB_FILTER_TYPES)


def event_type_filter_allows_instruction_parsing(include_only: List[EventType]) -> bool:
    """判断过滤器是否允许指令解析"""
    return any(t in INSTRUCTION_EVENT_TYPE_SET for t in include_only)


# Subscribe 请求/响应类型

@dataclass
class SubscribeRequestFilterAccountsFilterMemcmp:
    """Memcmp 过滤器"""
    offset: int
    bytes: Optional[bytes] = None
    base58: str = ""
    base64: str = ""


@dataclass
class SubscribeRequestFilterAccountsFilterLamports:
    """Lamports 过滤器"""
    eq: Optional[int] = None
    ne: Optional[int] = None
    lt: Optional[int] = None
    gt: Optional[int] = None


@dataclass
class SubscribeRequestFilterAccountsFilter:
    """账户过滤条件"""
    memcmp: Optional[SubscribeRequestFilterAccountsFilterMemcmp] = None
    datasize: Optional[int] = None
    token_account_state: Optional[bool] = None
    lamports: Optional[SubscribeRequestFilterAccountsFilterLamports] = None


@dataclass
class AccountFilter:
    """账户订阅过滤器（对齐 Rust ``grpc/types::AccountFilter``，用于 ``subscribe_builder``）"""

    account: List[str] = field(default_factory=list)
    owner: List[str] = field(default_factory=list)
    filters: List[SubscribeRequestFilterAccountsFilter] = field(default_factory=list)

    @staticmethod
    def new() -> AccountFilter:
        return AccountFilter()

    def add_account(self, account: str) -> AccountFilter:
        self.account.append(account)
        return self

    def add_owner(self, owner: str) -> AccountFilter:
        self.owner.append(owner)
        return self

    def add_filter(self, f: SubscribeRequestFilterAccountsFilter) -> AccountFilter:
        self.filters.append(f)
        return self

    @staticmethod
    def from_program_owners(program_ids: List[str]) -> AccountFilter:
        return AccountFilter(owner=list(program_ids))


class Protocol(str, Enum):
    """DEX 协议枚举（对齐 Rust ``grpc/types::Protocol``）"""

    PUMP_FUN = "PumpFun"
    PUMP_SWAP = "PumpSwap"
    PUMP_FEES = "PumpFees"
    RAYDIUM_LAUNCHLAB = "RaydiumLaunchlab"
    RAYDIUM_CPMM = "RaydiumCpmm"
    RAYDIUM_CLMM = "RaydiumClmm"
    RAYDIUM_AMM_V4 = "RaydiumAmmV4"
    ORCA_WHIRLPOOL = "OrcaWhirlpool"
    METEORA_POOLS = "MeteoraPools"
    METEORA_DAMM_V2 = "MeteoraDammV2"
    METEORA_DLMM = "MeteoraDlmm"
    METEORA_DBC = "MeteoraDbc"


# 与 Rust ``grpc/program_ids::PROTOCOL_PROGRAM_IDS`` 一致
_PROTOCOL_PROGRAM_IDS: Dict[Protocol, List[str]] = {
    Protocol.PUMP_FUN: ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"],
    Protocol.PUMP_SWAP: ["pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"],
    Protocol.PUMP_FEES: ["pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"],
    Protocol.RAYDIUM_LAUNCHLAB: ["LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"],
    Protocol.RAYDIUM_CPMM: ["CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"],
    Protocol.RAYDIUM_CLMM: ["CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"],
    Protocol.RAYDIUM_AMM_V4: ["675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"],
    Protocol.ORCA_WHIRLPOOL: ["whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"],
    Protocol.METEORA_POOLS: ["Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"],
    Protocol.METEORA_DAMM_V2: ["cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"],
    Protocol.METEORA_DLMM: ["LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"],
    Protocol.METEORA_DBC: ["dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"],
}


def program_ids_for_protocols(protocols: List[Protocol]) -> List[str]:
    """对齐 Rust ``get_program_ids_for_protocols``。"""
    out: List[str] = []
    for p in protocols:
        out.extend(_PROTOCOL_PROGRAM_IDS.get(p, []))
    return sorted(set(out))


def transaction_filter_for_protocols(protocols: List[Protocol]) -> TransactionFilter:
    """对齐 Rust ``TransactionFilter::for_protocols``。"""
    ids = program_ids_for_protocols(protocols)
    return TransactionFilter(account_include=ids, account_exclude=[], account_required=[])


def account_filter_for_protocols(protocols: List[Protocol]) -> AccountFilter:
    """对齐 Rust ``AccountFilter::for_protocols``（owner = 程序 ID 列表）。"""
    ids = program_ids_for_protocols(protocols)
    return AccountFilter(account=[], owner=ids, filters=[])


@dataclass
class SlotFilter:
    """Slot 范围过滤（对齐 Rust ``SlotFilter``）"""

    min_slot: Optional[int] = None
    max_slot: Optional[int] = None

    @staticmethod
    def new() -> SlotFilter:
        return SlotFilter()


def account_filter_memcmp(offset: int, bs: bytes) -> SubscribeRequestFilterAccountsFilter:
    """对齐 Rust ``account_filter_memcmp``：用于 ``AccountFilter.filters``。"""
    return SubscribeRequestFilterAccountsFilter(
        memcmp=SubscribeRequestFilterAccountsFilterMemcmp(offset=offset, bytes=bs)
    )


@dataclass
class SubscribeRequestFilterAccounts:
    """账户过滤器"""
    account: List[str] = field(default_factory=list)
    owner: List[str] = field(default_factory=list)
    filters: List[SubscribeRequestFilterAccountsFilter] = field(default_factory=list)
    nonempty_txn_signature: Optional[bool] = None


@dataclass
class SubscribeRequestFilterSlots:
    """Slot 过滤器"""
    filter_by_commitment: Optional[bool] = None
    interslot_updates: Optional[bool] = None


@dataclass
class SubscribeRequestFilterTransactions:
    """交易过滤器（proto 定义）"""
    vote: Optional[bool] = None
    failed: Optional[bool] = None
    signature: str = ""
    account_include: List[str] = field(default_factory=list)
    account_exclude: List[str] = field(default_factory=list)
    account_required: List[str] = field(default_factory=list)


@dataclass
class SubscribeRequestFilterBlocks:
    """区块过滤器"""
    account_include: List[str] = field(default_factory=list)
    include_transactions: Optional[bool] = None
    include_accounts: Optional[bool] = None
    include_entries: Optional[bool] = None


@dataclass
class SubscribeRequestFilterBlocksMeta:
    """区块元数据过滤器"""
    pass


@dataclass
class SubscribeRequestFilterEntry:
    """Entry 过滤器"""
    pass


@dataclass
class SubscribeRequestAccountsDataSlice:
    """账户数据切片"""
    offset: int = 0
    length: int = 0


@dataclass
class SubscribeRequestPing:
    """Ping 请求"""
    id: int = 0


@dataclass
class SubscribeRequest:
    """订阅请求"""
    accounts: Dict[str, SubscribeRequestFilterAccounts] = field(default_factory=dict)
    slots: Dict[str, SubscribeRequestFilterSlots] = field(default_factory=dict)
    transactions: Dict[str, SubscribeRequestFilterTransactions] = field(default_factory=dict)
    transactions_status: Dict[str, SubscribeRequestFilterTransactions] = field(default_factory=dict)
    blocks: Dict[str, SubscribeRequestFilterBlocks] = field(default_factory=dict)
    blocks_meta: Dict[str, SubscribeRequestFilterBlocksMeta] = field(default_factory=dict)
    entry: Dict[str, SubscribeRequestFilterEntry] = field(default_factory=dict)
    commitment: Optional[CommitmentLevel] = None
    accounts_data_slice: List[SubscribeRequestAccountsDataSlice] = field(default_factory=list)
    ping: Optional[SubscribeRequestPing] = None
    from_slot: Optional[int] = None


# Subscribe 更新类型

@dataclass
class SubscribeUpdateAccountInfo:
    """账户信息"""
    pubkey: bytes = b""
    lamports: int = 0
    owner: bytes = b""
    executable: bool = False
    rent_epoch: int = 0
    data: bytes = b""
    write_version: int = 0
    txn_signature: Optional[bytes] = None


@dataclass
class SubscribeUpdateAccount:
    """账户更新"""
    account: Optional[SubscribeUpdateAccountInfo] = None
    slot: int = 0
    is_startup: bool = False


@dataclass
class SubscribeUpdateSlot:
    """Slot 更新"""
    slot: int = 0
    parent: Optional[int] = None
    status: SlotStatus = SlotStatus.PROCESSED
    dead_error: Optional[str] = None


@dataclass
class SubscribeUpdateTransactionInfo:
    """交易信息"""
    signature: bytes = b""
    is_vote: bool = False
    transaction_raw: bytes = b""
    meta_raw: bytes = b""
    index: int = 0
    log_messages: List[str] = field(default_factory=list)


@dataclass
class SubscribeUpdateTransaction:
    """交易更新"""
    transaction: Optional[SubscribeUpdateTransactionInfo] = None
    slot: int = 0


@dataclass
class SubscribeUpdateTransactionStatus:
    """交易状态更新"""
    slot: int = 0
    signature: bytes = b""
    is_vote: bool = False
    index: int = 0
    err: bytes = b""


@dataclass
class SubscribeUpdateBlock:
    """区块更新"""
    slot: int = 0
    blockhash: str = ""
    parent_slot: int = 0
    parent_blockhash: str = ""
    executed_transaction_count: int = 0
    transactions: List[SubscribeUpdateTransactionInfo] = field(default_factory=list)


@dataclass
class SubscribeUpdatePing:
    """Ping 更新"""
    pass


@dataclass
class SubscribeUpdatePong:
    """Pong 更新"""
    id: int = 0


@dataclass
class SubscribeUpdateBlockMeta:
    """区块元数据更新"""
    slot: int = 0
    blockhash: str = ""
    parent_slot: int = 0
    parent_blockhash: str = ""
    executed_transaction_count: int = 0


@dataclass
class SubscribeUpdateEntry:
    """Entry 更新"""
    slot: int = 0
    index: int = 0
    num_hashes: int = 0
    hash: bytes = b""
    executed_transaction_count: int = 0
    starting_transaction_index: int = 0


@dataclass
class SubscribeUpdate:
    """订阅更新"""
    filters: List[str] = field(default_factory=list)
    account: Optional[SubscribeUpdateAccount] = None
    slot: Optional[SubscribeUpdateSlot] = None
    transaction: Optional[SubscribeUpdateTransaction] = None
    transaction_status: Optional[SubscribeUpdateTransactionStatus] = None
    block: Optional[SubscribeUpdateBlock] = None
    ping: Optional[SubscribeUpdatePing] = None
    pong: Optional[SubscribeUpdatePong] = None
    block_meta: Optional[SubscribeUpdateBlockMeta] = None
    entry: Optional[SubscribeUpdateEntry] = None
    created_at: Optional[int] = None  # Unix timestamp in microseconds


# RPC 请求/响应类型

@dataclass
class GetLatestBlockhashRequest:
    """获取最新区块哈希请求"""
    commitment: Optional[CommitmentLevel] = None


@dataclass
class GetLatestBlockhashResponse:
    """获取最新区块哈希响应"""
    slot: int = 0
    blockhash: str = ""
    last_valid_block_height: int = 0


@dataclass
class GetBlockHeightRequest:
    """获取区块高度请求"""
    commitment: Optional[CommitmentLevel] = None


@dataclass
class GetBlockHeightResponse:
    """获取区块高度响应"""
    block_height: int = 0


@dataclass
class GetSlotRequest:
    """获取 Slot 请求"""
    commitment: Optional[CommitmentLevel] = None


@dataclass
class GetSlotResponse:
    """获取 Slot 响应"""
    slot: int = 0


@dataclass
class GetVersionRequest:
    """获取版本请求"""
    pass


@dataclass
class GetVersionResponse:
    """获取版本响应"""
    version: str = ""


@dataclass
class IsBlockhashValidRequest:
    """验证区块哈希请求"""
    blockhash: str = ""
    commitment: Optional[CommitmentLevel] = None


@dataclass
class IsBlockhashValidResponse:
    """验证区块哈希响应"""
    slot: int = 0
    valid: bool = False


@dataclass
class PingRequest:
    """Ping 请求"""
    count: int = 0


@dataclass
class PongResponse:
    """Pong 响应"""
    count: int = 0


@dataclass
class SubscribeReplayInfoRequest:
    """订阅重放信息请求"""
    pass


@dataclass
class SubscribeReplayInfoResponse:
    """订阅重放信息响应"""
    first_available: Optional[int] = None


# SubscribeCallbacks 类型

@dataclass
class SubscribeCallbacks:
    """订阅回调函数"""
    on_update: Optional[Callable[[SubscribeUpdate], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    on_end: Optional[Callable[[], None]] = None
