"""gRPC 类型定义，对齐 yellowstone-grpc 和 TypeScript SDK"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Callable
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
    # PumpFun
    BONK_TRADE = "BonkTrade"
    BONK_POOL_CREATE = "BonkPoolCreate"
    BONK_MIGRATE_AMM = "BonkMigrateAmm"
    PUMP_FUN_TRADE = "PumpFunTrade"
    PUMP_FUN_BUY = "PumpFunBuy"
    PUMP_FUN_SELL = "PumpFunSell"
    PUMP_FUN_BUY_EXACT_SOL_IN = "PumpFunBuyExactSolIn"
    PUMP_FUN_CREATE = "PumpFunCreate"
    PUMP_FUN_CREATE_V2 = "PumpFunCreateV2"
    PUMP_FUN_COMPLETE = "PumpFunComplete"
    PUMP_FUN_MIGRATE = "PumpFunMigrate"
    # PumpSwap
    PUMP_SWAP_TRADE = "PumpSwapTrade"
    PUMP_SWAP_BUY = "PumpSwapBuy"
    PUMP_SWAP_SELL = "PumpSwapSell"
    PUMP_SWAP_CREATE_POOL = "PumpSwapCreatePool"
    PUMP_SWAP_LIQUIDITY_ADDED = "PumpSwapLiquidityAdded"
    PUMP_SWAP_LIQUIDITY_REMOVED = "PumpSwapLiquidityRemoved"
    # Raydium CLMM
    RAYDIUM_CLMM_SWAP = "RaydiumClmmSwap"
    RAYDIUM_CLMM_INCREASE_LIQUIDITY = "RaydiumClmmIncreaseLiquidity"
    RAYDIUM_CLMM_DECREASE_LIQUIDITY = "RaydiumClmmDecreaseLiquidity"
    RAYDIUM_CLMM_CREATE_POOL = "RaydiumClmmCreatePool"
    RAYDIUM_CLMM_OPEN_POSITION = "RaydiumClmmOpenPosition"
    RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT = "RaydiumClmmOpenPositionWithTokenExtNft"
    RAYDIUM_CLMM_CLOSE_POSITION = "RaydiumClmmClosePosition"
    RAYDIUM_CLMM_COLLECT_FEE = "RaydiumClmmCollectFee"
    # Raydium CPMM
    RAYDIUM_CPMM_SWAP = "RaydiumCpmmSwap"
    RAYDIUM_CPMM_DEPOSIT = "RaydiumCpmmDeposit"
    RAYDIUM_CPMM_WITHDRAW = "RaydiumCpmmWithdraw"
    RAYDIUM_CPMM_INITIALIZE = "RaydiumCpmmInitialize"
    # Raydium AMM V4
    RAYDIUM_AMM_V4_SWAP = "RaydiumAmmV4Swap"
    RAYDIUM_AMM_V4_DEPOSIT = "RaydiumAmmV4Deposit"
    RAYDIUM_AMM_V4_WITHDRAW = "RaydiumAmmV4Withdraw"
    RAYDIUM_AMM_V4_WITHDRAW_PNL = "RaydiumAmmV4WithdrawPnl"
    RAYDIUM_AMM_V4_INITIALIZE2 = "RaydiumAmmV4Initialize2"
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
    METEORA_DAMM_V2_CREATE_POSITION = "MeteoraDammV2CreatePosition"
    METEORA_DAMM_V2_CLOSE_POSITION = "MeteoraDammV2ClosePosition"
    METEORA_DAMM_V2_INITIALIZE_POOL = "MeteoraDammV2InitializePool"
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
    ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG = "AccountPumpSwapGlobalConfig"
    ACCOUNT_PUMP_SWAP_POOL = "AccountPumpSwapPool"


def all_event_types() -> List[EventType]:
    """返回所有支持的事件类型列表"""
    return [
        # Block
        EventType.BLOCK_META,
        # Bonk
        EventType.BONK_TRADE,
        EventType.BONK_POOL_CREATE,
        EventType.BONK_MIGRATE_AMM,
        # PumpFun
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        EventType.PUMP_FUN_CREATE,
        EventType.PUMP_FUN_CREATE_V2,
        EventType.PUMP_FUN_COMPLETE,
        EventType.PUMP_FUN_MIGRATE,
        # PumpSwap
        EventType.PUMP_SWAP_TRADE,
        EventType.PUMP_SWAP_BUY,
        EventType.PUMP_SWAP_SELL,
        EventType.PUMP_SWAP_CREATE_POOL,
        EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
        # Raydium CLMM
        EventType.RAYDIUM_CLMM_SWAP,
        EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
        EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
        EventType.RAYDIUM_CLMM_CREATE_POOL,
        EventType.RAYDIUM_CLMM_OPEN_POSITION,
        EventType.RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT,
        EventType.RAYDIUM_CLMM_CLOSE_POSITION,
        EventType.RAYDIUM_CLMM_COLLECT_FEE,
        # Raydium CPMM
        EventType.RAYDIUM_CPMM_SWAP,
        EventType.RAYDIUM_CPMM_DEPOSIT,
        EventType.RAYDIUM_CPMM_WITHDRAW,
        EventType.RAYDIUM_CPMM_INITIALIZE,
        # Raydium AMM V4
        EventType.RAYDIUM_AMM_V4_SWAP,
        EventType.RAYDIUM_AMM_V4_DEPOSIT,
        EventType.RAYDIUM_AMM_V4_WITHDRAW,
        EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
        EventType.RAYDIUM_AMM_V4_INITIALIZE2,
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
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
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
        EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
        EventType.ACCOUNT_PUMP_SWAP_POOL,
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
        # 空列表表示包含所有类型
        if not self.include_only:
            return True
        if event_type in self.include_only:
            return True
        # PumpFunTrade 包含 PumpFunBuy, PumpFunSell, PumpFunBuyExactSolIn
        if event_type == EventType.PUMP_FUN_TRADE:
            pumpfun_types = [
                EventType.PUMP_FUN_BUY,
                EventType.PUMP_FUN_SELL,
                EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
            ]
            if any(t in self.include_only for t in pumpfun_types):
                return True
        return False


class ExcludeFilter(EventTypeFilter):
    """排除指定类型的事件过滤器"""

    def __init__(self, exclude_types: List[EventType]):
        self.exclude_types = exclude_types

    def should_include(self, event_type: EventType) -> bool:
        return event_type not in self.exclude_types


def event_type_filter_include_only(types: List[EventType]) -> EventTypeFilter:
    """创建仅包含指定类型的事件过滤器"""
    return IncludeOnlyFilter(types)


def event_type_filter_exclude(types: List[EventType]) -> EventTypeFilter:
    """创建排除指定类型的事件过滤器"""
    return ExcludeFilter(types)


def event_type_filter_includes_pumpfun(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 PumpFun 相关类型"""
    pumpfun_types = [
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        EventType.PUMP_FUN_CREATE,
        EventType.PUMP_FUN_CREATE_V2,
        EventType.PUMP_FUN_COMPLETE,
        EventType.PUMP_FUN_MIGRATE,
    ]
    return any(filter.should_include(t) for t in pumpfun_types)


def event_type_filter_includes_pumpswap(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 PumpSwap 相关类型"""
    pumpswap_types = [
        EventType.PUMP_SWAP_BUY,
        EventType.PUMP_SWAP_SELL,
        EventType.PUMP_SWAP_CREATE_POOL,
        EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
    ]
    return any(filter.should_include(t) for t in pumpswap_types)


def event_type_filter_includes_meteora_damm_v2(filter: EventTypeFilter) -> bool:
    """判断过滤器是否包含 Meteora DAMM V2 相关类型"""
    meteora_types = [
        EventType.METEORA_DAMM_V2_SWAP,
        EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
        EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
    ]
    return any(filter.should_include(t) for t in meteora_types)


def event_type_filter_allows_instruction_parsing(include_only: List[EventType]) -> bool:
    """判断过滤器是否允许指令解析"""
    ix_types = [
        EventType.PUMP_FUN_MIGRATE,
        EventType.METEORA_DAMM_V2_SWAP,
        EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
        EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
    ]
    return any(t in include_only for t in ix_types)


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
    BONK = "Bonk"
    RAYDIUM_CPMM = "RaydiumCpmm"
    RAYDIUM_CLMM = "RaydiumClmm"
    RAYDIUM_AMM_V4 = "RaydiumAmmV4"
    METEORA_DAMM_V2 = "MeteoraDammV2"


# 与 Rust ``grpc/program_ids::PROTOCOL_PROGRAM_IDS`` 一致
_PROTOCOL_PROGRAM_IDS: Dict[Protocol, List[str]] = {
    Protocol.PUMP_FUN: ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"],
    Protocol.PUMP_SWAP: ["pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"],
    Protocol.BONK: ["BSwp6bEBihVLdqJRKS58NaebUBSDNjN7MdpFwNaR6gn3"],
    Protocol.RAYDIUM_CPMM: ["CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"],
    Protocol.RAYDIUM_CLMM: ["CAMMCzo5YL8w4VFF8KVHrK22GGUQtcaMpgYqJPXBDvfE"],
    Protocol.RAYDIUM_AMM_V4: ["675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"],
    Protocol.METEORA_DAMM_V2: ["cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"],
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
