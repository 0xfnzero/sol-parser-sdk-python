"""强类型事件定义

提供所有 DEX 事件的强类型 dataclass 定义。
用户可以使用这些类型获得 IDE 自动补全和类型检查。

使用示例:
    from sol_parser.event_types import PumpFunTradeEvent, DexEvent
    
    # 解析事件
    event = parse_trade_from_data(data, meta, False)
    
    # 直接访问强类型数据
    if event.type == EventType.PUMP_FUN_TRADE:
        trade = event.data  # 类型为 PumpFunTradeEvent
        print(f"User: {trade.user}")
        print(f"Amount: {trade.sol_amount}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union, List, Optional, Any, Generic, TypeVar, Dict, Tuple

from .grpc_types import EventMetadata, EventType

T = TypeVar('T')


@dataclass
class DexEvent:
    """强类型 DEX 事件容器
    
    Attributes:
        type: 事件类型
        data: 具体的事件数据（如 PumpFunTradeEvent 等）
    
    控制台可读输出请用 :func:`sol_parser.format_dex_event_json`（缩进 JSON），
    默认 ``repr``/``print(ev)`` 为单行 dataclass 表示，并非 JSON。
    """
    type: EventType = field(default=EventType.BLOCK_META)
    data: Any = None  # 具体的事件类型，如 PumpFunTradeEvent
    
    def is_valid(self) -> bool:
        """检查事件是否有效"""
        return self.data is not None
    
    def is_trade(self) -> bool:
        """判断是否为交易事件"""
        return self.type in (
            EventType.PUMP_FUN_TRADE, EventType.PUMP_FUN_BUY, EventType.PUMP_FUN_SELL,
            EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
            EventType.PUMP_SWAP_BUY, EventType.PUMP_SWAP_SELL,
            EventType.RAYDIUM_AMM_V4_SWAP, EventType.RAYDIUM_CLMM_SWAP, EventType.RAYDIUM_CPMM_SWAP,
            EventType.ORCA_WHIRLPOOL_SWAP, EventType.METEORA_DLMM_SWAP,
            EventType.METEORA_POOLS_SWAP, EventType.METEORA_DAMM_V2_SWAP,
            EventType.METEORA_DBC_SWAP,
            EventType.RAYDIUM_LAUNCHLAB_TRADE,
        )
    
    def as_pumpfun_trade(self) -> Optional['PumpFunTradeEvent']:
        """转换为 PumpFunTradeEvent"""
        if isinstance(self.data, PumpFunTradeEvent):
            return self.data
        return None
    
    def as_pumpswap_buy(self) -> Optional['PumpSwapBuyEvent']:
        """转换为 PumpSwapBuyEvent"""
        if isinstance(self.data, PumpSwapBuyEvent):
            return self.data
        return None
    
    def as_pumpswap_sell(self) -> Optional['PumpSwapSellEvent']:
        """转换为 PumpSwapSellEvent"""
        if isinstance(self.data, PumpSwapSellEvent):
            return self.data
        return None


def event_key_and_payload(ev: Union["DexEvent", Dict[str, Any]]) -> Tuple[str, Any]:
    """从强类型 :class:`DexEvent` 或历史「单键 dict」形态取出事件名与 payload。"""
    if isinstance(ev, DexEvent):
        if ev.data is None:
            return "", None
        return str(ev.type.value), ev.data
    if isinstance(ev, dict) and ev:
        k = next(iter(ev))
        return k, ev.get(k)
    return "", None


def grpc_recv_us_from_payload(data: Any) -> int:
    """读取 metadata.grpc_recv_us（兼容 dict 与 dataclass payload）。"""
    if data is None:
        return 0
    if isinstance(data, dict):
        m = data.get("metadata") or {}
        if isinstance(m, dict):
            return int(m.get("grpc_recv_us", 0) or 0)
        return int(getattr(m, "grpc_recv_us", 0) or 0)
    meta = getattr(data, "metadata", None)
    if meta is None:
        return 0
    return int(getattr(meta, "grpc_recv_us", 0) or 0)


# ============================================================
# 基础类型
# ============================================================

@dataclass
class DexEventBase:
    """所有事件的基类"""
    metadata: EventMetadata = field(default_factory=EventMetadata)


# ============================================================
# PumpFun 事件
# ============================================================

@dataclass
class PumpFunTradeEvent(DexEventBase):
    """PumpFun 交易事件"""
    mint: str = ""
    sol_amount: int = 0
    token_amount: int = 0
    is_buy: bool = False
    is_created_buy: bool = False
    user: str = ""
    timestamp: int = 0
    virtual_sol_reserves: int = 0
    virtual_token_reserves: int = 0
    real_sol_reserves: int = 0
    real_token_reserves: int = 0
    fee_recipient: str = ""
    fee_basis_points: int = 0
    fee: int = 0
    creator: str = ""
    creator_fee_basis_points: int = 0
    creator_fee: int = 0
    track_volume: bool = False
    total_unclaimed_tokens: int = 0
    total_claimed_tokens: int = 0
    current_sol_volume: int = 0
    last_update_timestamp: int = 0
    ix_name: str = ""
    mayhem_mode: bool = False
    cashback_fee_basis_points: int = 0
    cashback: int = 0
    buyback_fee_basis_points: int = 0
    buyback_fee: int = 0
    shareholders: List[PumpFeesShareholder] = field(default_factory=list)
    quote_mint: str = ""
    quote_amount: int = 0
    virtual_quote_reserves: int = 0
    real_quote_reserves: int = 0
    is_cashback_coin: bool = False
    amount: int = 0
    max_sol_cost: int = 0
    min_sol_output: int = 0
    spendable_sol_in: int = 0
    spendable_quote_in: int = 0
    min_tokens_out: int = 0
    global_account: str = ""
    bonding_curve: str = ""
    bonding_curve_v2: str = ""
    associated_bonding_curve: str = ""
    associated_user: str = ""
    system_program: str = ""
    token_program: str = ""
    quote_token_program: str = ""
    associated_token_program: str = ""
    creator_vault: str = ""
    associated_quote_fee_recipient: str = ""
    buyback_fee_recipient: str = ""
    associated_quote_buyback_fee_recipient: str = ""
    associated_quote_bonding_curve: str = ""
    associated_quote_user: str = ""
    associated_creator_vault: str = ""
    sharing_config: str = ""
    event_authority: str = ""
    program: str = ""
    global_volume_accumulator: str = ""
    user_volume_accumulator: str = ""
    associated_user_volume_accumulator: str = ""
    fee_config: str = ""
    fee_program: str = ""
    #: Legacy fallback alias for the last post-upgrade extra account. Prefer structured fields above.
    extra_instruction_account: str = ""


@dataclass
class PumpFunCreateEvent(DexEventBase):
    """PumpFun 创建代币事件"""
    name: str = ""
    symbol: str = ""
    uri: str = ""
    mint: str = ""
    bonding_curve: str = ""
    user: str = ""
    creator: str = ""
    timestamp: int = 0
    virtual_token_reserves: int = 0
    virtual_sol_reserves: int = 0
    real_token_reserves: int = 0
    token_total_supply: int = 0
    token_program: str = ""
    is_mayhem_mode: bool = False
    is_cashback_enabled: bool = False
    quote_mint: str = ""
    quote_vault: str = ""
    quote_token_program: str = ""
    virtual_quote_reserves: int = 0


@dataclass
class PumpFunCreateV2TokenEvent(DexEventBase):
    """PumpFun CreateV2（SPL-22 / Mayhem）；指令解析时从 accounts 填充。

    ``observed_fee_recipient`` 由同笔交易中后续 Buy 的 fee recipient 回填（见 ``pumpfun_fee_enrich``）。
    """

    name: str = ""
    symbol: str = ""
    uri: str = ""
    mint: str = ""
    bonding_curve: str = ""
    user: str = ""
    creator: str = ""
    timestamp: int = 0
    virtual_token_reserves: int = 0
    virtual_sol_reserves: int = 0
    real_token_reserves: int = 0
    token_total_supply: int = 0
    token_program: str = ""
    is_mayhem_mode: bool = False
    is_cashback_enabled: bool = False
    quote_mint: str = ""
    quote_vault: str = ""
    quote_token_program: str = ""
    virtual_quote_reserves: int = 0
    mint_authority: str = ""
    associated_bonding_curve: str = ""
    global_account: str = ""  # Rust `global` PumpFun global config
    system_program: str = ""
    associated_token_program: str = ""
    mayhem_program_id: str = ""
    global_params: str = ""
    sol_vault: str = ""
    mayhem_state: str = ""
    mayhem_token_vault: str = ""
    event_authority: str = ""
    program: str = ""
    observed_fee_recipient: str = ""


@dataclass
class PumpFunMigrateEvent(DexEventBase):
    """PumpFun 迁移事件"""
    user: str = ""
    mint: str = ""
    mint_amount: int = 0
    sol_amount: int = 0
    pool_migration_fee: int = 0
    bonding_curve: str = ""
    timestamp: int = 0
    pool: str = ""


@dataclass
class PumpFeesShareholder:
    address: str = ""
    share_bps: int = 0


@dataclass
class PumpFeesFees:
    lp_fee_bps: int = 0
    protocol_fee_bps: int = 0
    creator_fee_bps: int = 0


@dataclass
class PumpFeesFeeTier:
    market_cap_lamports_threshold: int = 0
    fees: PumpFeesFees = field(default_factory=PumpFeesFees)


@dataclass
class PumpFeesCreateFeeSharingConfigEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    bonding_curve: str = ""
    pool: str = ""
    sharing_config: str = ""
    admin: str = ""
    initial_shareholders: List[PumpFeesShareholder] = field(default_factory=list)
    status: str = "Active"


@dataclass
class PumpFeesInitializeFeeConfigEvent(DexEventBase):
    timestamp: int = 0
    admin: str = ""
    fee_config: str = ""


@dataclass
class PumpFeesResetFeeSharingConfigEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    sharing_config: str = ""
    old_admin: str = ""
    old_shareholders: List[PumpFeesShareholder] = field(default_factory=list)
    new_admin: str = ""
    new_shareholders: List[PumpFeesShareholder] = field(default_factory=list)


@dataclass
class PumpFeesRevokeFeeSharingAuthorityEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    sharing_config: str = ""
    admin: str = ""


@dataclass
class PumpFeesTransferFeeSharingAuthorityEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    sharing_config: str = ""
    old_admin: str = ""
    new_admin: str = ""


@dataclass
class PumpFeesUpdateAdminEvent(DexEventBase):
    timestamp: int = 0
    old_admin: str = ""
    new_admin: str = ""


@dataclass
class PumpFeesUpdateFeeConfigEvent(DexEventBase):
    timestamp: int = 0
    admin: str = ""
    fee_config: str = ""
    fee_tiers: List[PumpFeesFeeTier] = field(default_factory=list)
    flat_fees: PumpFeesFees = field(default_factory=PumpFeesFees)


@dataclass
class PumpFeesUpdateFeeSharesEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    sharing_config: str = ""
    admin: str = ""
    bonding_curve: str = ""
    pump_creator_vault: str = ""
    new_shareholders: List[PumpFeesShareholder] = field(default_factory=list)


@dataclass
class PumpFeesUpsertFeeTiersEvent(DexEventBase):
    timestamp: int = 0
    admin: str = ""
    fee_config: str = ""
    fee_tiers: List[PumpFeesFeeTier] = field(default_factory=list)
    offset: int = 0


@dataclass
class PumpFunMigrateBondingCurveCreatorEvent(DexEventBase):
    timestamp: int = 0
    mint: str = ""
    bonding_curve: str = ""
    sharing_config: str = ""
    old_creator: str = ""
    new_creator: str = ""


# ============================================================
# PumpSwap 事件
# ============================================================

@dataclass
class PumpSwapBuyEvent(DexEventBase):
    """PumpSwap 买入事件"""
    timestamp: int = 0
    base_amount_out: int = 0
    max_quote_amount_in: int = 0
    user_base_token_reserves: int = 0
    user_quote_token_reserves: int = 0
    pool_base_token_reserves: int = 0
    pool_quote_token_reserves: int = 0
    quote_amount_in: int = 0
    lp_fee_basis_points: int = 0
    lp_fee: int = 0
    protocol_fee_basis_points: int = 0
    protocol_fee: int = 0
    quote_amount_in_with_lp_fee: int = 0
    user_quote_amount_in: int = 0
    pool: str = ""
    user: str = ""
    user_base_token_account: str = ""
    user_quote_token_account: str = ""
    protocol_fee_recipient: str = ""
    protocol_fee_recipient_token_account: str = ""
    coin_creator: str = ""
    coin_creator_fee_basis_points: int = 0
    coin_creator_fee: int = 0
    track_volume: bool = False
    total_unclaimed_tokens: int = 0
    total_claimed_tokens: int = 0
    current_sol_volume: int = 0
    last_update_timestamp: int = 0
    min_base_amount_out: int = 0
    ix_name: str = ""
    mayhem_mode: bool = False
    cashback_fee_basis_points: int = 0
    cashback: int = 0
    buyback_fee_basis_points: int = 0
    buyback_fee: int = 0
    virtual_quote_reserves: int = 0
    can_boost: bool = False
    base_supply: int = 0
    is_cashback_coin: bool = False
    base_mint: str = ""
    quote_mint: str = ""
    pool_base_token_account: str = ""
    pool_quote_token_account: str = ""
    coin_creator_vault_ata: str = ""
    coin_creator_vault_authority: str = ""
    base_token_program: str = ""
    quote_token_program: str = ""
    pool_v2: str = ""
    fee_recipient: str = ""
    fee_recipient_quote_token_account: str = ""
    is_pump_pool: bool = False


@dataclass
class PumpSwapSellEvent(DexEventBase):
    """PumpSwap 卖出事件"""
    timestamp: int = 0
    base_amount_in: int = 0
    min_quote_amount_out: int = 0
    user_base_token_reserves: int = 0
    user_quote_token_reserves: int = 0
    pool_base_token_reserves: int = 0
    pool_quote_token_reserves: int = 0
    quote_amount_out: int = 0
    lp_fee_basis_points: int = 0
    lp_fee: int = 0
    protocol_fee_basis_points: int = 0
    protocol_fee: int = 0
    quote_amount_out_without_lp_fee: int = 0
    user_quote_amount_out: int = 0
    pool: str = ""
    user: str = ""
    user_base_token_account: str = ""
    user_quote_token_account: str = ""
    protocol_fee_recipient: str = ""
    protocol_fee_recipient_token_account: str = ""
    coin_creator: str = ""
    coin_creator_fee_basis_points: int = 0
    coin_creator_fee: int = 0
    cashback_fee_basis_points: int = 0
    cashback: int = 0
    buyback_fee_basis_points: int = 0
    buyback_fee: int = 0
    virtual_quote_reserves: int = 0
    can_boost: bool = False
    base_supply: int = 0
    base_mint: str = ""
    quote_mint: str = ""
    pool_base_token_account: str = ""
    pool_quote_token_account: str = ""
    coin_creator_vault_ata: str = ""
    coin_creator_vault_authority: str = ""
    base_token_program: str = ""
    quote_token_program: str = ""
    pool_v2: str = ""
    fee_recipient: str = ""
    fee_recipient_quote_token_account: str = ""
    is_pump_pool: bool = False


@dataclass
class PumpSwapCreatePoolEvent(DexEventBase):
    """PumpSwap 创建池子事件"""
    timestamp: int = 0
    index: int = 0
    creator: str = ""
    base_mint: str = ""
    quote_mint: str = ""
    base_mint_decimals: int = 0
    quote_mint_decimals: int = 0
    base_amount_in: int = 0
    quote_amount_in: int = 0
    pool_base_amount: int = 0
    pool_quote_amount: int = 0
    minimum_liquidity: int = 0
    initial_liquidity: int = 0
    lp_token_amount_out: int = 0
    pool_bump: int = 0
    pool: str = ""
    lp_mint: str = ""
    user_base_token_account: str = ""
    user_quote_token_account: str = ""
    coin_creator: str = ""
    is_mayhem_mode: bool = False


@dataclass
class PumpSwapLiquidityAddedEvent(DexEventBase):
    """PumpSwap 添加流动性事件"""
    timestamp: int = 0
    lp_token_amount_out: int = 0
    max_base_amount_in: int = 0
    max_quote_amount_in: int = 0
    user_base_token_reserves: int = 0
    user_quote_token_reserves: int = 0
    pool_base_token_reserves: int = 0
    pool_quote_token_reserves: int = 0
    base_amount_in: int = 0
    quote_amount_in: int = 0
    lp_mint_supply: int = 0
    pool: str = ""
    user: str = ""
    user_base_token_account: str = ""
    user_quote_token_account: str = ""
    user_pool_token_account: str = ""


@dataclass
class PumpSwapLiquidityRemovedEvent(DexEventBase):
    """PumpSwap 移除流动性事件"""
    timestamp: int = 0
    lp_token_amount_in: int = 0
    min_base_amount_out: int = 0
    min_quote_amount_out: int = 0
    user_base_token_reserves: int = 0
    user_quote_token_reserves: int = 0
    pool_base_token_reserves: int = 0
    pool_quote_token_reserves: int = 0
    base_amount_out: int = 0
    quote_amount_out: int = 0
    lp_mint_supply: int = 0
    pool: str = ""
    user: str = ""
    user_base_token_account: str = ""
    user_quote_token_account: str = ""
    user_pool_token_account: str = ""


# ============================================================
# Raydium AMM V4（legacy AMM）事件 — 与 dex_parsers Program data 布局一致
# ============================================================

_PLACEHOLDER_PK = "11111111111111111111111111111111"


@dataclass
class RaydiumAmmV4SwapEvent(DexEventBase):
    """Raydium AMM V4 交换（swap_base_in / swap_base_out）"""
    amm: str = ""
    user_source_owner: str = ""
    amount_in: int = 0
    minimum_amount_out: int = 0
    max_amount_in: int = 0
    amount_out: int = 0
    token_program: str = _PLACEHOLDER_PK
    amm_authority: str = _PLACEHOLDER_PK
    amm_open_orders: str = _PLACEHOLDER_PK
    pool_coin_token_account: str = _PLACEHOLDER_PK
    pool_pc_token_account: str = _PLACEHOLDER_PK
    serum_program: str = _PLACEHOLDER_PK
    serum_market: str = _PLACEHOLDER_PK
    serum_bids: str = _PLACEHOLDER_PK
    serum_asks: str = _PLACEHOLDER_PK
    serum_event_queue: str = _PLACEHOLDER_PK
    serum_coin_vault_account: str = _PLACEHOLDER_PK
    serum_pc_vault_account: str = _PLACEHOLDER_PK
    serum_vault_signer: str = _PLACEHOLDER_PK
    user_source_token_account: str = _PLACEHOLDER_PK
    user_destination_token_account: str = _PLACEHOLDER_PK


@dataclass
class RaydiumAmmV4DepositEvent(DexEventBase):
    amm: str = ""
    user_owner: str = ""
    max_coin_amount: int = 0
    max_pc_amount: int = 0
    base_side: int = 0
    token_program: str = _PLACEHOLDER_PK
    amm_authority: str = _PLACEHOLDER_PK
    amm_open_orders: str = _PLACEHOLDER_PK
    amm_target_orders: str = _PLACEHOLDER_PK
    lp_mint_address: str = _PLACEHOLDER_PK
    pool_coin_token_account: str = _PLACEHOLDER_PK
    pool_pc_token_account: str = _PLACEHOLDER_PK
    serum_market: str = _PLACEHOLDER_PK
    user_coin_token_account: str = _PLACEHOLDER_PK
    user_pc_token_account: str = _PLACEHOLDER_PK
    user_lp_token_account: str = _PLACEHOLDER_PK
    serum_event_queue: str = _PLACEHOLDER_PK


@dataclass
class RaydiumAmmV4WithdrawEvent(DexEventBase):
    amm: str = ""
    user_owner: str = ""
    amount: int = 0
    token_program: str = _PLACEHOLDER_PK
    amm_authority: str = _PLACEHOLDER_PK
    amm_open_orders: str = _PLACEHOLDER_PK
    amm_target_orders: str = _PLACEHOLDER_PK
    lp_mint_address: str = _PLACEHOLDER_PK
    pool_coin_token_account: str = _PLACEHOLDER_PK
    pool_pc_token_account: str = _PLACEHOLDER_PK
    pool_withdraw_queue: str = _PLACEHOLDER_PK
    pool_temp_lp_token_account: str = _PLACEHOLDER_PK
    serum_program: str = _PLACEHOLDER_PK
    serum_market: str = _PLACEHOLDER_PK
    serum_coin_vault_account: str = _PLACEHOLDER_PK
    serum_pc_vault_account: str = _PLACEHOLDER_PK
    serum_vault_signer: str = _PLACEHOLDER_PK
    user_lp_token_account: str = _PLACEHOLDER_PK
    user_coin_token_account: str = _PLACEHOLDER_PK
    user_pc_token_account: str = _PLACEHOLDER_PK
    serum_event_queue: str = _PLACEHOLDER_PK
    serum_bids: str = _PLACEHOLDER_PK
    serum_asks: str = _PLACEHOLDER_PK


@dataclass
class RaydiumAmmV4WithdrawPnlEvent(DexEventBase):
    token_program: str = _PLACEHOLDER_PK
    amm: str = ""
    amm_config: str = _PLACEHOLDER_PK
    amm_authority: str = _PLACEHOLDER_PK
    amm_open_orders: str = _PLACEHOLDER_PK
    pool_coin_token_account: str = _PLACEHOLDER_PK
    pool_pc_token_account: str = _PLACEHOLDER_PK
    coin_pnl_token_account: str = _PLACEHOLDER_PK
    pc_pnl_token_account: str = _PLACEHOLDER_PK
    pnl_owner: str = ""
    amm_target_orders: str = _PLACEHOLDER_PK
    serum_program: str = _PLACEHOLDER_PK
    serum_market: str = _PLACEHOLDER_PK
    serum_event_queue: str = _PLACEHOLDER_PK
    serum_coin_vault_account: str = _PLACEHOLDER_PK
    serum_pc_vault_account: str = _PLACEHOLDER_PK
    serum_vault_signer: str = _PLACEHOLDER_PK


@dataclass
class RaydiumAmmV4Initialize2Event(DexEventBase):
    nonce: int = 0
    open_time: int = 0
    init_pc_amount: int = 0
    init_coin_amount: int = 0
    token_program: str = _PLACEHOLDER_PK
    spl_associated_token_account: str = _PLACEHOLDER_PK
    system_program: str = _PLACEHOLDER_PK
    rent: str = _PLACEHOLDER_PK
    amm: str = ""
    amm_authority: str = _PLACEHOLDER_PK
    amm_open_orders: str = _PLACEHOLDER_PK
    lp_mint: str = _PLACEHOLDER_PK
    coin_mint: str = _PLACEHOLDER_PK
    pc_mint: str = _PLACEHOLDER_PK
    pool_coin_token_account: str = _PLACEHOLDER_PK
    pool_pc_token_account: str = _PLACEHOLDER_PK
    pool_withdraw_queue: str = _PLACEHOLDER_PK
    amm_target_orders: str = _PLACEHOLDER_PK
    pool_temp_lp: str = _PLACEHOLDER_PK
    serum_program: str = _PLACEHOLDER_PK
    serum_market: str = _PLACEHOLDER_PK
    user_wallet: str = ""
    user_token_coin: str = _PLACEHOLDER_PK
    user_token_pc: str = _PLACEHOLDER_PK
    user_lp_token_account: str = _PLACEHOLDER_PK


# ============================================================
# Raydium CLMM 事件
# ============================================================

@dataclass
class RaydiumClmmSwapEvent(DexEventBase):
    """Raydium CLMM 交换事件"""
    pool_state: str = ""
    sender: str = ""
    token_account_0: str = ""
    token_account_1: str = ""
    amount_0: int = 0
    amount_1: int = 0
    zero_for_one: bool = False
    sqrt_price_x64: str = ""
    liquidity: str = ""
    transfer_fee_0: int = 0
    transfer_fee_1: int = 0
    tick: int = 0


@dataclass
class RaydiumClmmIncreaseLiquidityEvent(DexEventBase):
    """Raydium CLMM 增加流动性事件"""
    pool: str = ""
    position_nft_mint: str = ""
    user: str = ""
    liquidity: str = ""
    amount_0: int = 0
    amount_1: int = 0
    amount_0_transfer_fee: int = 0
    amount_1_transfer_fee: int = 0
    amount0_max: int = 0
    amount1_max: int = 0


@dataclass
class RaydiumClmmDecreaseLiquidityEvent(DexEventBase):
    """Raydium CLMM 减少流动性事件"""
    pool: str = ""
    position_nft_mint: str = ""
    user: str = ""
    liquidity: str = ""
    decrease_amount_0: int = 0
    decrease_amount_1: int = 0
    fee_amount_0: int = 0
    fee_amount_1: int = 0
    reward_amounts: List[int] = field(default_factory=list)
    transfer_fee_0: int = 0
    transfer_fee_1: int = 0
    amount0_min: int = 0
    amount1_min: int = 0


@dataclass
class RaydiumClmmOpenPositionEvent(DexEventBase):
    """Raydium CLMM 开启仓位事件"""
    pool: str = ""
    user: str = ""
    position_nft_mint: str = ""
    tick_lower_index: int = 0
    tick_upper_index: int = 0
    liquidity: str = ""


@dataclass
class RaydiumClmmOpenPositionWithTokenExtNftEvent(DexEventBase):
    """Raydium CLMM Token-2022 NFT 开启仓位事件"""
    pool: str = ""
    user: str = ""
    position_nft_mint: str = ""
    tick_lower_index: int = 0
    tick_upper_index: int = 0
    liquidity: str = ""


@dataclass
class RaydiumClmmClosePositionEvent(DexEventBase):
    """Raydium CLMM 关闭仓位事件"""
    pool: str = ""
    user: str = ""
    position_nft_mint: str = ""


@dataclass
class RaydiumClmmCreatePoolEvent(DexEventBase):
    """Raydium CLMM 创建池子事件"""
    pool: str = ""
    creator: str = ""
    token_0_mint: str = ""
    token_1_mint: str = ""
    tick_spacing: int = 0
    fee_rate: int = 0
    sqrt_price_x64: str = ""
    tick: int = 0
    token_vault_0: str = ""
    token_vault_1: str = ""
    open_time: int = 0


@dataclass
class RaydiumClmmCollectFeeEvent(DexEventBase):
    """Raydium CLMM 收取费用事件"""
    pool_state: str = ""
    position_nft_mint: str = ""
    recipient_token_account_0: str = ""
    recipient_token_account_1: str = ""
    amount_0: int = 0
    amount_1: int = 0


@dataclass
class RaydiumClmmLiquidityChangeEvent(DexEventBase):
    pool_state: str = ""
    tick: int = 0
    tick_lower: int = 0
    tick_upper: int = 0
    liquidity_before: str = ""
    liquidity_after: str = ""


@dataclass
class RaydiumClmmConfigChangeEvent(DexEventBase):
    index: int = 0
    owner: str = ""
    protocol_fee_rate: int = 0
    trade_fee_rate: int = 0
    tick_spacing: int = 0
    fund_fee_rate: int = 0
    fund_owner: str = ""


@dataclass
class RaydiumClmmCreatePersonalPositionEvent(DexEventBase):
    pool_state: str = ""
    minter: str = ""
    nft_owner: str = ""
    tick_lower_index: int = 0
    tick_upper_index: int = 0
    liquidity: str = ""
    deposit_amount_0: int = 0
    deposit_amount_1: int = 0
    deposit_amount_0_transfer_fee: int = 0
    deposit_amount_1_transfer_fee: int = 0


@dataclass
class RaydiumClmmLiquidityCalculateEvent(DexEventBase):
    pool_liquidity: str = ""
    pool_sqrt_price_x64: str = ""
    pool_tick: int = 0
    calc_amount_0: int = 0
    calc_amount_1: int = 0
    trade_fee_owed_0: int = 0
    trade_fee_owed_1: int = 0
    transfer_fee_0: int = 0
    transfer_fee_1: int = 0


@dataclass
class RaydiumClmmOpenLimitOrderEvent(DexEventBase):
    pool_id: str = ""
    limit_order: str = ""
    zero_for_one: bool = False
    tick_index: int = 0
    total_amount: int = 0
    transfer_fee: int = 0


@dataclass
class RaydiumClmmIncreaseLimitOrderEvent(DexEventBase):
    pool_id: str = ""
    limit_order: str = ""
    zero_for_one: bool = False
    tick_index: int = 0
    total_amount: int = 0
    increased_amount: int = 0
    transfer_fee: int = 0


@dataclass
class RaydiumClmmDecreaseLimitOrderEvent(DexEventBase):
    pool_id: str = ""
    limit_order: str = ""
    zero_for_one: bool = False
    tick_index: int = 0
    total_amount: int = 0
    filled_amount: int = 0
    settled_output_amount: int = 0
    decreased_amount: int = 0


@dataclass
class RaydiumClmmSettleLimitOrderEvent(DexEventBase):
    pool_id: str = ""
    limit_order: str = ""
    zero_for_one: bool = False
    tick_index: int = 0
    total_amount: int = 0
    filled_amount: int = 0
    settled_amount_out: int = 0


@dataclass
class RaydiumClmmUpdateRewardInfosEvent(DexEventBase):
    reward_growth_global_x64: List[str] = field(default_factory=list)


# ============================================================
# Raydium CPMM 事件
# ============================================================

@dataclass
class RaydiumCpmmSwapEvent(DexEventBase):
    """Raydium CPMM 交换事件"""
    pool_id: str = ""
    input_amount: int = 0
    output_amount: int = 0
    input_vault_before: int = 0
    output_vault_before: int = 0
    input_transfer_fee: int = 0
    output_transfer_fee: int = 0
    base_input: bool = False


@dataclass
class RaydiumCpmmDepositEvent(DexEventBase):
    """Raydium CPMM 存款事件"""
    pool: str = ""
    user: str = ""
    lp_token_amount: int = 0
    token0_amount: int = 0
    token1_amount: int = 0


@dataclass
class RaydiumCpmmWithdrawEvent(DexEventBase):
    """Raydium CPMM 取款事件"""
    pool: str = ""
    user: str = ""
    lp_token_amount: int = 0
    token0_amount: int = 0
    token1_amount: int = 0


@dataclass
class RaydiumCpmmInitializeEvent(DexEventBase):
    """Raydium CPMM 初始化事件"""
    pool: str = ""
    creator: str = ""
    init_amount0: int = 0
    init_amount1: int = 0


# ============================================================
# Orca Whirlpool 事件
# ============================================================

@dataclass
class OrcaWhirlpoolSwapEvent(DexEventBase):
    """Orca Whirlpool 交换事件"""
    whirlpool: str = ""
    a_to_b: bool = False
    pre_sqrt_price: str = ""
    post_sqrt_price: str = ""
    input_amount: int = 0
    output_amount: int = 0
    input_transfer_fee: int = 0
    output_transfer_fee: int = 0
    lp_fee: int = 0
    protocol_fee: int = 0


@dataclass
class OrcaWhirlpoolLiquidityIncreasedEvent(DexEventBase):
    """Orca Whirlpool 增加流动性事件"""
    whirlpool: str = ""
    position: str = ""
    tick_lower_index: int = 0
    tick_upper_index: int = 0
    liquidity: str = ""
    token_a_amount: int = 0
    token_b_amount: int = 0
    token_a_transfer_fee: int = 0
    token_b_transfer_fee: int = 0


@dataclass
class OrcaWhirlpoolLiquidityDecreasedEvent(DexEventBase):
    """Orca Whirlpool 减少流动性事件"""
    whirlpool: str = ""
    position: str = ""
    tick_lower_index: int = 0
    tick_upper_index: int = 0
    liquidity: str = ""
    token_a_amount: int = 0
    token_b_amount: int = 0
    token_a_transfer_fee: int = 0
    token_b_transfer_fee: int = 0


@dataclass
class OrcaWhirlpoolPoolInitializedEvent(DexEventBase):
    """Orca Whirlpool 池子初始化事件"""
    whirlpool: str = ""
    whirlpools_config: str = ""
    token_mint_a: str = ""
    token_mint_b: str = ""
    tick_spacing: int = 0
    token_program_a: str = ""
    token_program_b: str = ""
    decimals_a: int = 0
    decimals_b: int = 0
    initial_sqrt_price: str = ""


# ============================================================
# Meteora DLMM 事件
# ============================================================

@dataclass
class MeteoraDlmmSwapEvent(DexEventBase):
    """Meteora DLMM 交换事件"""
    pool: str = ""
    from_addr: str = ""
    start_bin_id: int = 0
    end_bin_id: int = 0
    amount_in: int = 0
    amount_out: int = 0
    swap_for_y: bool = False
    fee: int = 0
    protocol_fee: int = 0
    fee_bps: str = ""
    host_fee: int = 0


@dataclass
class MeteoraDlmmAddLiquidityEvent(DexEventBase):
    """Meteora DLMM 添加流动性事件"""
    pool: str = ""
    from_addr: str = ""
    position: str = ""
    amounts: List[int] = field(default_factory=list)
    active_bin_id: int = 0


@dataclass
class MeteoraDlmmRemoveLiquidityEvent(DexEventBase):
    """Meteora DLMM 移除流动性事件"""
    pool: str = ""
    from_addr: str = ""
    position: str = ""
    amounts: List[int] = field(default_factory=list)
    active_bin_id: int = 0


@dataclass
class MeteoraDlmmInitializePoolEvent(DexEventBase):
    """Meteora DLMM 初始化池子事件"""
    pool: str = ""
    creator: str = ""
    active_bin_id: int = 0
    bin_step: int = 0


@dataclass
class MeteoraDlmmInitializeBinArrayEvent(DexEventBase):
    """Meteora DLMM 初始化 Bin Array 事件"""
    pool: str = ""
    bin_array: str = ""
    index: int = 0


@dataclass
class MeteoraDlmmCreatePositionEvent(DexEventBase):
    """Meteora DLMM 创建仓位事件"""
    pool: str = ""
    position: str = ""
    owner: str = ""
    lower_bin_id: int = 0
    width: int = 0


@dataclass
class MeteoraDlmmClosePositionEvent(DexEventBase):
    """Meteora DLMM 关闭仓位事件"""
    pool: str = ""
    position: str = ""
    owner: str = ""


@dataclass
class MeteoraDlmmClaimFeeEvent(DexEventBase):
    """Meteora DLMM 收取费用事件"""
    pool: str = ""
    position: str = ""
    owner: str = ""
    fee_x: int = 0
    fee_y: int = 0


# ============================================================
# Meteora Pools 事件
# ============================================================


@dataclass
class MeteoraPoolsSetPoolFeesEvent(DexEventBase):
    """Meteora Pools 设置池子费率"""
    trade_fee_numerator: int = 0
    trade_fee_denominator: int = 0
    owner_trade_fee_numerator: int = 0
    owner_trade_fee_denominator: int = 0
    pool: str = ""


@dataclass
class MeteoraPoolsSwapEvent(DexEventBase):
    """Meteora Pools 交换事件"""
    in_amount: int = 0
    out_amount: int = 0
    trade_fee: int = 0
    admin_fee: int = 0
    host_fee: int = 0


@dataclass
class MeteoraPoolsAddLiquidityEvent(DexEventBase):
    """Meteora Pools 添加流动性事件"""
    lp_mint_amount: int = 0
    token_a_amount: int = 0
    token_b_amount: int = 0


@dataclass
class MeteoraPoolsRemoveLiquidityEvent(DexEventBase):
    """Meteora Pools 移除流动性事件"""
    lp_unmint_amount: int = 0
    token_a_out_amount: int = 0
    token_b_out_amount: int = 0


@dataclass
class MeteoraPoolsBootstrapLiquidityEvent(DexEventBase):
    """Meteora Pools 引导流动性事件"""
    lp_mint_amount: int = 0
    token_a_amount: int = 0
    token_b_amount: int = 0
    pool: str = ""


@dataclass
class MeteoraPoolsPoolCreatedEvent(DexEventBase):
    """Meteora Pools 创建池子事件"""
    lp_mint: str = ""
    token_a_mint: str = ""
    token_b_mint: str = ""
    pool_type: int = 0
    pool: str = ""


# ============================================================
# Meteora DAMM v2 事件
# ============================================================

@dataclass
class MeteoraDammV2SwapEvent(DexEventBase):
    """Meteora DAMM v2 交换事件"""
    pool: str = ""
    trade_direction: int = 0
    has_referral: bool = False
    amount_in: int = 0
    minimum_amount_out: int = 0
    output_amount: int = 0
    next_sqrt_price: str = ""
    lp_fee: int = 0
    protocol_fee: int = 0
    partner_fee: int = 0
    referral_fee: int = 0
    actual_amount_in: int = 0
    current_timestamp: int = 0
    token_a_vault: str = ""
    token_b_vault: str = ""
    token_a_mint: str = ""
    token_b_mint: str = ""
    token_a_program: str = ""
    token_b_program: str = ""


@dataclass
class MeteoraDammV2CreatePositionEvent(DexEventBase):
    """Meteora DAMM v2 创建仓位事件"""
    pool: str = ""
    owner: str = ""
    position: str = ""
    position_nft_mint: str = ""


@dataclass
class MeteoraDammV2ClosePositionEvent(DexEventBase):
    """Meteora DAMM v2 关闭仓位事件"""
    pool: str = ""
    owner: str = ""
    position: str = ""
    position_nft_mint: str = ""


@dataclass
class MeteoraDammV2AddLiquidityEvent(DexEventBase):
    """Meteora DAMM v2 添加流动性事件"""
    pool: str = ""
    position: str = ""
    owner: str = ""
    liquidity_delta: str = ""
    token_a_amount_threshold: int = 0
    token_b_amount_threshold: int = 0
    token_a_amount: int = 0
    token_b_amount: int = 0
    total_amount_a: int = 0
    total_amount_b: int = 0


@dataclass
class MeteoraDammV2RemoveLiquidityEvent(DexEventBase):
    """Meteora DAMM v2 移除流动性事件"""
    pool: str = ""
    position: str = ""
    owner: str = ""
    liquidity_delta: str = ""
    token_a_amount_threshold: int = 0
    token_b_amount_threshold: int = 0
    token_a_amount: int = 0
    token_b_amount: int = 0


@dataclass
class MeteoraDammV2InitializePoolEvent(DexEventBase):
    """Meteora DAMM v2 初始化池子事件"""
    pool: str = ""
    position: str = ""
    position_nft_mint: str = ""
    token_a_mint: str = ""
    token_b_mint: str = ""
    creator: str = ""
    payer: str = ""
    alpha_vault: str = ""
    pool_fees: Any = None
    sqrt_min_price: str = ""
    sqrt_max_price: str = ""
    activation_type: int = 0
    collect_fee_mode: int = 0
    liquidity: str = ""
    sqrt_price: str = ""
    activation_point: int = 0
    token_a_flag: int = 0
    token_b_flag: int = 0
    token_a_amount: int = 0
    token_b_amount: int = 0
    total_amount_a: int = 0
    total_amount_b: int = 0
    pool_type: int = 0


@dataclass
class MeteoraDbcSwapEvent(DexEventBase):
    """Meteora DBC 交易事件"""
    pool: str = ""
    config: str = ""
    trade_direction: int = 0
    has_referral: bool = False
    amount_in: int = 0
    minimum_amount_out: int = 0
    actual_input_amount: int = 0
    output_amount: int = 0
    next_sqrt_price: int = 0
    trading_fee: int = 0
    protocol_fee: int = 0
    referral_fee: int = 0
    current_timestamp: int = 0


@dataclass
class MeteoraDbcInitializePoolEvent(DexEventBase):
    """Meteora DBC 初始化池子事件"""
    pool: str = ""
    config: str = ""
    creator: str = ""
    base_mint: str = ""
    pool_type: int = 0
    activation_point: int = 0


@dataclass
class MeteoraDbcCurveCompleteEvent(DexEventBase):
    """Meteora DBC 曲线完成事件"""
    pool: str = ""
    config: str = ""
    base_reserve: int = 0
    quote_reserve: int = 0


# ============================================================
# RaydiumLaunchlab 事件
# ============================================================

@dataclass
class RaydiumLaunchlabTradeEvent(DexEventBase):
    """RaydiumLaunchlab 交易事件"""
    pool_state: str = ""
    user: str = ""
    amount_in: int = 0
    amount_out: int = 0
    is_buy: bool = False
    trade_direction: str = ""
    exact_in: bool = False


@dataclass
class RaydiumLaunchlabPoolCreateEvent(DexEventBase):
    """RaydiumLaunchlab 创建池子事件"""
    pool_state: str = ""
    creator: str = ""
    base_mint_param: Optional[Dict[str, Any]] = None


@dataclass
class RaydiumLaunchlabMigrateAmmEvent(DexEventBase):
    """RaydiumLaunchlab 迁移 AMM 事件"""
    old_pool: str = ""
    new_pool: str = ""
    user: str = ""
    liquidity_amount: int = 0


# ============================================================
# 类型联合
# ============================================================

TypedDexEvent = Union[
    PumpFunTradeEvent,
    PumpFunCreateEvent,
    PumpFunCreateV2TokenEvent,
    PumpFunMigrateEvent,
    PumpFeesCreateFeeSharingConfigEvent,
    PumpFeesInitializeFeeConfigEvent,
    PumpFeesResetFeeSharingConfigEvent,
    PumpFeesRevokeFeeSharingAuthorityEvent,
    PumpFeesTransferFeeSharingAuthorityEvent,
    PumpFeesUpdateAdminEvent,
    PumpFeesUpdateFeeConfigEvent,
    PumpFeesUpdateFeeSharesEvent,
    PumpFeesUpsertFeeTiersEvent,
    PumpFunMigrateBondingCurveCreatorEvent,
    PumpSwapBuyEvent,
    PumpSwapSellEvent,
    PumpSwapCreatePoolEvent,
    PumpSwapLiquidityAddedEvent,
    PumpSwapLiquidityRemovedEvent,
    RaydiumAmmV4SwapEvent,
    RaydiumAmmV4DepositEvent,
    RaydiumAmmV4WithdrawEvent,
    RaydiumAmmV4WithdrawPnlEvent,
    RaydiumAmmV4Initialize2Event,
    RaydiumClmmSwapEvent,
    RaydiumClmmIncreaseLiquidityEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmCreatePoolEvent,
    RaydiumClmmOpenPositionEvent,
    RaydiumClmmOpenPositionWithTokenExtNftEvent,
    RaydiumClmmClosePositionEvent,
    RaydiumClmmCollectFeeEvent,
    RaydiumCpmmSwapEvent,
    RaydiumCpmmDepositEvent,
    RaydiumCpmmWithdrawEvent,
    RaydiumCpmmInitializeEvent,
    OrcaWhirlpoolSwapEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolLiquidityDecreasedEvent,
    OrcaWhirlpoolPoolInitializedEvent,
    MeteoraDlmmSwapEvent,
    MeteoraDlmmAddLiquidityEvent,
    MeteoraDlmmRemoveLiquidityEvent,
    MeteoraDlmmInitializePoolEvent,
    MeteoraDlmmInitializeBinArrayEvent,
    MeteoraDlmmCreatePositionEvent,
    MeteoraDlmmClosePositionEvent,
    MeteoraDlmmClaimFeeEvent,
    MeteoraPoolsSetPoolFeesEvent,
    MeteoraPoolsSwapEvent,
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsBootstrapLiquidityEvent,
    MeteoraPoolsPoolCreatedEvent,
    MeteoraDammV2SwapEvent,
    MeteoraDammV2CreatePositionEvent,
    MeteoraDammV2ClosePositionEvent,
    MeteoraDammV2AddLiquidityEvent,
    MeteoraDammV2RemoveLiquidityEvent,
    MeteoraDammV2InitializePoolEvent,
    RaydiumLaunchlabTradeEvent,
    RaydiumLaunchlabPoolCreateEvent,
    RaydiumLaunchlabMigrateAmmEvent,
]


# ============================================================
# 辅助函数
# ============================================================

def _get_metadata(m: dict) -> EventMetadata:
    """从 dict 中提取 metadata"""
    v = m.get("metadata")
    if isinstance(v, EventMetadata):
        return v
    if isinstance(v, dict):
        return EventMetadata(
            signature=v.get("signature", ""),
            slot=v.get("slot", 0),
            tx_index=v.get("tx_index", 0),
            block_time_us=v.get("block_time_us", 0),
            grpc_recv_us=v.get("grpc_recv_us", 0),
            recent_blockhash=v.get("recent_blockhash", ""),
        )
    return EventMetadata()


def _get_str(m: dict, key: str) -> str:
    v = m.get(key, "")
    return str(v) if v is not None else ""


def _get_int(m: dict, key: str) -> int:
    v = m.get(key, 0)
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v, 10)
        except ValueError:
            pass
    return 0


def _get_bool(m: dict, key: str) -> bool:
    v = m.get(key, False)
    return bool(v)


def _get_list(m: dict, key: str) -> List[int]:
    v = m.get(key, [])
    if isinstance(v, (list, tuple)):
        return [int(x) for x in v]
    return []


def _get_dict_any(m: dict, key: str) -> Optional[Dict[str, Any]]:
    v = m.get(key)
    return v if isinstance(v, dict) else None


def _get_pump_shareholders(m: dict, key: str) -> List[PumpFeesShareholder]:
    v = m.get(key, [])
    if not isinstance(v, (list, tuple)):
        return []
    out: List[PumpFeesShareholder] = []
    for item in v:
        if isinstance(item, PumpFeesShareholder):
            out.append(item)
        elif isinstance(item, dict):
            out.append(
                PumpFeesShareholder(
                    address=_get_str(item, "address"),
                    share_bps=_get_int(item, "share_bps"),
                )
            )
    return out


def to_typed_event(event: dict) -> Optional[TypedDexEvent]:
    """将旧版 DexEvent dict 转换为强类型事件
    
    Args:
        event: 旧版 DexEvent dict，格式为 { "EventType": { ... } }
    
    Returns:
        强类型事件对象，如果无法识别则返回 None
    """
    if not event:
        return None
    
    # 获取事件类型和数据
    event_type_str = None
    data = None
    for k, v in event.items():
        event_type_str = k
        data = v if isinstance(v, dict) else {}
        break
    
    if not event_type_str or not data:
        return None
    
    try:
        event_type = EventType(event_type_str)
    except ValueError:
        return None
    
    meta = _get_metadata(data)
    
    # PumpFun events
    if event_type in (EventType.PUMP_FUN_TRADE, EventType.PUMP_FUN_BUY,
                      EventType.PUMP_FUN_SELL, EventType.PUMP_FUN_BUY_EXACT_SOL_IN):
        return PumpFunTradeEvent(
            metadata=meta,
            mint=_get_str(data, "mint"),
            sol_amount=_get_int(data, "sol_amount"),
            token_amount=_get_int(data, "token_amount"),
            is_buy=_get_bool(data, "is_buy"),
            is_created_buy=_get_bool(data, "is_created_buy"),
            user=_get_str(data, "user"),
            timestamp=_get_int(data, "timestamp"),
            virtual_sol_reserves=_get_int(data, "virtual_sol_reserves"),
            virtual_token_reserves=_get_int(data, "virtual_token_reserves"),
            real_sol_reserves=_get_int(data, "real_sol_reserves"),
            real_token_reserves=_get_int(data, "real_token_reserves"),
            fee_recipient=_get_str(data, "fee_recipient"),
            fee_basis_points=_get_int(data, "fee_basis_points"),
            fee=_get_int(data, "fee"),
            creator=_get_str(data, "creator"),
            creator_fee_basis_points=_get_int(data, "creator_fee_basis_points"),
            creator_fee=_get_int(data, "creator_fee"),
            track_volume=_get_bool(data, "track_volume"),
            total_unclaimed_tokens=_get_int(data, "total_unclaimed_tokens"),
            total_claimed_tokens=_get_int(data, "total_claimed_tokens"),
            current_sol_volume=_get_int(data, "current_sol_volume"),
            last_update_timestamp=_get_int(data, "last_update_timestamp"),
            ix_name=_get_str(data, "ix_name"),
            mayhem_mode=_get_bool(data, "mayhem_mode"),
            cashback_fee_basis_points=_get_int(data, "cashback_fee_basis_points"),
            cashback=_get_int(data, "cashback"),
            buyback_fee_basis_points=_get_int(data, "buyback_fee_basis_points"),
            buyback_fee=_get_int(data, "buyback_fee"),
            shareholders=_get_pump_shareholders(data, "shareholders"),
            quote_mint=_get_str(data, "quote_mint"),
            quote_amount=_get_int(data, "quote_amount"),
            virtual_quote_reserves=_get_int(data, "virtual_quote_reserves"),
            real_quote_reserves=_get_int(data, "real_quote_reserves"),
            is_cashback_coin=_get_bool(data, "is_cashback_coin"),
            amount=_get_int(data, "amount"),
            max_sol_cost=_get_int(data, "max_sol_cost"),
            min_sol_output=_get_int(data, "min_sol_output"),
            spendable_sol_in=_get_int(data, "spendable_sol_in"),
            spendable_quote_in=_get_int(data, "spendable_quote_in"),
            min_tokens_out=_get_int(data, "min_tokens_out"),
            global_account=_get_str(data, "global") or _get_str(data, "global_account"),
            bonding_curve=_get_str(data, "bonding_curve"),
            bonding_curve_v2=_get_str(data, "bonding_curve_v2"),
            associated_bonding_curve=_get_str(data, "associated_bonding_curve"),
            associated_user=_get_str(data, "associated_user"),
            system_program=_get_str(data, "system_program"),
            token_program=_get_str(data, "token_program"),
            quote_token_program=_get_str(data, "quote_token_program"),
            associated_token_program=_get_str(data, "associated_token_program"),
            creator_vault=_get_str(data, "creator_vault"),
            associated_quote_fee_recipient=_get_str(data, "associated_quote_fee_recipient"),
            buyback_fee_recipient=_get_str(data, "buyback_fee_recipient"),
            associated_quote_buyback_fee_recipient=_get_str(data, "associated_quote_buyback_fee_recipient"),
            associated_quote_bonding_curve=_get_str(data, "associated_quote_bonding_curve"),
            associated_quote_user=_get_str(data, "associated_quote_user"),
            associated_creator_vault=_get_str(data, "associated_creator_vault"),
            sharing_config=_get_str(data, "sharing_config"),
            event_authority=_get_str(data, "event_authority"),
            program=_get_str(data, "program"),
            global_volume_accumulator=_get_str(data, "global_volume_accumulator"),
            user_volume_accumulator=_get_str(data, "user_volume_accumulator"),
            associated_user_volume_accumulator=_get_str(data, "associated_user_volume_accumulator"),
            fee_config=_get_str(data, "fee_config"),
            fee_program=_get_str(data, "fee_program"),
            extra_instruction_account=_get_str(data, "account") or _get_str(data, "extra_instruction_account"),
        )
    
    if event_type == EventType.PUMP_FUN_CREATE:
        return PumpFunCreateEvent(
            metadata=meta,
            name=_get_str(data, "name"),
            symbol=_get_str(data, "symbol"),
            uri=_get_str(data, "uri"),
            mint=_get_str(data, "mint"),
            bonding_curve=_get_str(data, "bonding_curve"),
            user=_get_str(data, "user"),
            creator=_get_str(data, "creator"),
            timestamp=_get_int(data, "timestamp"),
            virtual_token_reserves=_get_int(data, "virtual_token_reserves"),
            virtual_sol_reserves=_get_int(data, "virtual_sol_reserves"),
            real_token_reserves=_get_int(data, "real_token_reserves"),
            token_total_supply=_get_int(data, "token_total_supply"),
            token_program=_get_str(data, "token_program"),
            is_mayhem_mode=_get_bool(data, "is_mayhem_mode"),
            is_cashback_enabled=_get_bool(data, "is_cashback_enabled"),
            quote_mint=_get_str(data, "quote_mint"),
            quote_vault=_get_str(data, "quote_vault"),
            quote_token_program=_get_str(data, "quote_token_program"),
            virtual_quote_reserves=_get_int(data, "virtual_quote_reserves"),
        )

    if event_type == EventType.PUMP_FUN_CREATE_V2:
        g = _get_str(data, "global") or _get_str(data, "global_account")
        return PumpFunCreateV2TokenEvent(
            metadata=meta,
            name=_get_str(data, "name"),
            symbol=_get_str(data, "symbol"),
            uri=_get_str(data, "uri"),
            mint=_get_str(data, "mint"),
            bonding_curve=_get_str(data, "bonding_curve"),
            user=_get_str(data, "user"),
            creator=_get_str(data, "creator"),
            timestamp=_get_int(data, "timestamp"),
            virtual_token_reserves=_get_int(data, "virtual_token_reserves"),
            virtual_sol_reserves=_get_int(data, "virtual_sol_reserves"),
            real_token_reserves=_get_int(data, "real_token_reserves"),
            token_total_supply=_get_int(data, "token_total_supply"),
            token_program=_get_str(data, "token_program"),
            is_mayhem_mode=_get_bool(data, "is_mayhem_mode"),
            is_cashback_enabled=_get_bool(data, "is_cashback_enabled"),
            quote_mint=_get_str(data, "quote_mint"),
            quote_vault=_get_str(data, "quote_vault"),
            quote_token_program=_get_str(data, "quote_token_program"),
            virtual_quote_reserves=_get_int(data, "virtual_quote_reserves"),
            mint_authority=_get_str(data, "mint_authority"),
            associated_bonding_curve=_get_str(data, "associated_bonding_curve"),
            global_account=g,
            system_program=_get_str(data, "system_program"),
            associated_token_program=_get_str(data, "associated_token_program"),
            mayhem_program_id=_get_str(data, "mayhem_program_id"),
            global_params=_get_str(data, "global_params"),
            sol_vault=_get_str(data, "sol_vault"),
            mayhem_state=_get_str(data, "mayhem_state"),
            mayhem_token_vault=_get_str(data, "mayhem_token_vault"),
            event_authority=_get_str(data, "event_authority"),
            program=_get_str(data, "program"),
            observed_fee_recipient=_get_str(data, "observed_fee_recipient"),
        )
    
    if event_type == EventType.PUMP_FUN_MIGRATE:
        return PumpFunMigrateEvent(
            metadata=meta,
            user=_get_str(data, "user"),
            mint=_get_str(data, "mint"),
            mint_amount=_get_int(data, "mint_amount"),
            sol_amount=_get_int(data, "sol_amount"),
            pool_migration_fee=_get_int(data, "pool_migration_fee"),
            bonding_curve=_get_str(data, "bonding_curve"),
            timestamp=_get_int(data, "timestamp"),
            pool=_get_str(data, "pool"),
        )
    
    # PumpSwap events
    if event_type == EventType.PUMP_SWAP_BUY:
        return PumpSwapBuyEvent(
            metadata=meta,
            timestamp=_get_int(data, "timestamp"),
            base_amount_out=_get_int(data, "base_amount_out"),
            max_quote_amount_in=_get_int(data, "max_quote_amount_in"),
            user_base_token_reserves=_get_int(data, "user_base_token_reserves"),
            user_quote_token_reserves=_get_int(data, "user_quote_token_reserves"),
            pool_base_token_reserves=_get_int(data, "pool_base_token_reserves"),
            pool_quote_token_reserves=_get_int(data, "pool_quote_token_reserves"),
            quote_amount_in=_get_int(data, "quote_amount_in"),
            lp_fee_basis_points=_get_int(data, "lp_fee_basis_points"),
            lp_fee=_get_int(data, "lp_fee"),
            protocol_fee_basis_points=_get_int(data, "protocol_fee_basis_points"),
            protocol_fee=_get_int(data, "protocol_fee"),
            quote_amount_in_with_lp_fee=_get_int(data, "quote_amount_in_with_lp_fee"),
            user_quote_amount_in=_get_int(data, "user_quote_amount_in"),
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            user_base_token_account=_get_str(data, "user_base_token_account"),
            user_quote_token_account=_get_str(data, "user_quote_token_account"),
            protocol_fee_recipient=_get_str(data, "protocol_fee_recipient"),
            protocol_fee_recipient_token_account=_get_str(data, "protocol_fee_recipient_token_account"),
            coin_creator=_get_str(data, "coin_creator"),
            coin_creator_fee_basis_points=_get_int(data, "coin_creator_fee_basis_points"),
            coin_creator_fee=_get_int(data, "coin_creator_fee"),
            track_volume=_get_bool(data, "track_volume"),
            total_unclaimed_tokens=_get_int(data, "total_unclaimed_tokens"),
            total_claimed_tokens=_get_int(data, "total_claimed_tokens"),
            current_sol_volume=_get_int(data, "current_sol_volume"),
            last_update_timestamp=_get_int(data, "last_update_timestamp"),
            min_base_amount_out=_get_int(data, "min_base_amount_out"),
            ix_name=_get_str(data, "ix_name"),
            mayhem_mode=_get_bool(data, "mayhem_mode"),
            cashback_fee_basis_points=_get_int(data, "cashback_fee_basis_points"),
            cashback=_get_int(data, "cashback"),
            buyback_fee_basis_points=_get_int(data, "buyback_fee_basis_points"),
            buyback_fee=_get_int(data, "buyback_fee"),
            virtual_quote_reserves=_get_int(data, "virtual_quote_reserves"),
            can_boost=_get_bool(data, "can_boost"),
            base_supply=_get_int(data, "base_supply"),
            is_cashback_coin=_get_bool(data, "is_cashback_coin"),
            is_pump_pool=_get_bool(data, "is_pump_pool"),
            base_mint=_get_str(data, "base_mint"),
            quote_mint=_get_str(data, "quote_mint"),
            pool_base_token_account=_get_str(data, "pool_base_token_account"),
            pool_quote_token_account=_get_str(data, "pool_quote_token_account"),
            coin_creator_vault_ata=_get_str(data, "coin_creator_vault_ata"),
            coin_creator_vault_authority=_get_str(data, "coin_creator_vault_authority"),
            base_token_program=_get_str(data, "base_token_program"),
            quote_token_program=_get_str(data, "quote_token_program"),
            pool_v2=_get_str(data, "pool_v2"),
            fee_recipient=_get_str(data, "fee_recipient"),
            fee_recipient_quote_token_account=_get_str(data, "fee_recipient_quote_token_account"),
        )
    
    if event_type == EventType.PUMP_SWAP_SELL:
        return PumpSwapSellEvent(
            metadata=meta,
            timestamp=_get_int(data, "timestamp"),
            base_amount_in=_get_int(data, "base_amount_in"),
            min_quote_amount_out=_get_int(data, "min_quote_amount_out"),
            user_base_token_reserves=_get_int(data, "user_base_token_reserves"),
            user_quote_token_reserves=_get_int(data, "user_quote_token_reserves"),
            pool_base_token_reserves=_get_int(data, "pool_base_token_reserves"),
            pool_quote_token_reserves=_get_int(data, "pool_quote_token_reserves"),
            quote_amount_out=_get_int(data, "quote_amount_out"),
            lp_fee_basis_points=_get_int(data, "lp_fee_basis_points"),
            lp_fee=_get_int(data, "lp_fee"),
            protocol_fee_basis_points=_get_int(data, "protocol_fee_basis_points"),
            protocol_fee=_get_int(data, "protocol_fee"),
            quote_amount_out_without_lp_fee=_get_int(data, "quote_amount_out_without_lp_fee"),
            user_quote_amount_out=_get_int(data, "user_quote_amount_out"),
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            user_base_token_account=_get_str(data, "user_base_token_account"),
            user_quote_token_account=_get_str(data, "user_quote_token_account"),
            protocol_fee_recipient=_get_str(data, "protocol_fee_recipient"),
            protocol_fee_recipient_token_account=_get_str(data, "protocol_fee_recipient_token_account"),
            coin_creator=_get_str(data, "coin_creator"),
            coin_creator_fee_basis_points=_get_int(data, "coin_creator_fee_basis_points"),
            coin_creator_fee=_get_int(data, "coin_creator_fee"),
            cashback_fee_basis_points=_get_int(data, "cashback_fee_basis_points"),
            cashback=_get_int(data, "cashback"),
            buyback_fee_basis_points=_get_int(data, "buyback_fee_basis_points"),
            buyback_fee=_get_int(data, "buyback_fee"),
            virtual_quote_reserves=_get_int(data, "virtual_quote_reserves"),
            can_boost=_get_bool(data, "can_boost"),
            base_supply=_get_int(data, "base_supply"),
            is_pump_pool=_get_bool(data, "is_pump_pool"),
            base_mint=_get_str(data, "base_mint"),
            quote_mint=_get_str(data, "quote_mint"),
            pool_base_token_account=_get_str(data, "pool_base_token_account"),
            pool_quote_token_account=_get_str(data, "pool_quote_token_account"),
            coin_creator_vault_ata=_get_str(data, "coin_creator_vault_ata"),
            coin_creator_vault_authority=_get_str(data, "coin_creator_vault_authority"),
            base_token_program=_get_str(data, "base_token_program"),
            quote_token_program=_get_str(data, "quote_token_program"),
            pool_v2=_get_str(data, "pool_v2"),
            fee_recipient=_get_str(data, "fee_recipient"),
            fee_recipient_quote_token_account=_get_str(data, "fee_recipient_quote_token_account"),
        )
    
    if event_type == EventType.PUMP_SWAP_CREATE_POOL:
        return PumpSwapCreatePoolEvent(
            metadata=meta,
            timestamp=_get_int(data, "timestamp"),
            index=_get_int(data, "index"),
            creator=_get_str(data, "creator"),
            base_mint=_get_str(data, "base_mint"),
            quote_mint=_get_str(data, "quote_mint"),
            base_mint_decimals=_get_int(data, "base_mint_decimals"),
            quote_mint_decimals=_get_int(data, "quote_mint_decimals"),
            base_amount_in=_get_int(data, "base_amount_in"),
            quote_amount_in=_get_int(data, "quote_amount_in"),
            pool_base_amount=_get_int(data, "pool_base_amount"),
            pool_quote_amount=_get_int(data, "pool_quote_amount"),
            minimum_liquidity=_get_int(data, "minimum_liquidity"),
            initial_liquidity=_get_int(data, "initial_liquidity"),
            lp_token_amount_out=_get_int(data, "lp_token_amount_out"),
            pool_bump=_get_int(data, "pool_bump"),
            pool=_get_str(data, "pool"),
            lp_mint=_get_str(data, "lp_mint"),
            user_base_token_account=_get_str(data, "user_base_token_account"),
            user_quote_token_account=_get_str(data, "user_quote_token_account"),
            coin_creator=_get_str(data, "coin_creator"),
            is_mayhem_mode=_get_bool(data, "is_mayhem_mode"),
        )
    
    if event_type == EventType.PUMP_SWAP_LIQUIDITY_ADDED:
        return PumpSwapLiquidityAddedEvent(
            metadata=meta,
            timestamp=_get_int(data, "timestamp"),
            lp_token_amount_out=_get_int(data, "lp_token_amount_out"),
            max_base_amount_in=_get_int(data, "max_base_amount_in"),
            max_quote_amount_in=_get_int(data, "max_quote_amount_in"),
            user_base_token_reserves=_get_int(data, "user_base_token_reserves"),
            user_quote_token_reserves=_get_int(data, "user_quote_token_reserves"),
            pool_base_token_reserves=_get_int(data, "pool_base_token_reserves"),
            pool_quote_token_reserves=_get_int(data, "pool_quote_token_reserves"),
            base_amount_in=_get_int(data, "base_amount_in"),
            quote_amount_in=_get_int(data, "quote_amount_in"),
            lp_mint_supply=_get_int(data, "lp_mint_supply"),
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            user_base_token_account=_get_str(data, "user_base_token_account"),
            user_quote_token_account=_get_str(data, "user_quote_token_account"),
            user_pool_token_account=_get_str(data, "user_pool_token_account"),
        )
    
    if event_type == EventType.PUMP_SWAP_LIQUIDITY_REMOVED:
        return PumpSwapLiquidityRemovedEvent(
            metadata=meta,
            timestamp=_get_int(data, "timestamp"),
            lp_token_amount_in=_get_int(data, "lp_token_amount_in"),
            min_base_amount_out=_get_int(data, "min_base_amount_out"),
            min_quote_amount_out=_get_int(data, "min_quote_amount_out"),
            user_base_token_reserves=_get_int(data, "user_base_token_reserves"),
            user_quote_token_reserves=_get_int(data, "user_quote_token_reserves"),
            pool_base_token_reserves=_get_int(data, "pool_base_token_reserves"),
            pool_quote_token_reserves=_get_int(data, "pool_quote_token_reserves"),
            base_amount_out=_get_int(data, "base_amount_out"),
            quote_amount_out=_get_int(data, "quote_amount_out"),
            lp_mint_supply=_get_int(data, "lp_mint_supply"),
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            user_base_token_account=_get_str(data, "user_base_token_account"),
            user_quote_token_account=_get_str(data, "user_quote_token_account"),
            user_pool_token_account=_get_str(data, "user_pool_token_account"),
        )

    # Meteora DAMM v2 / Raydium / Orca — 指令级占位（与 instructions.py 一致）
    if event_type == EventType.METEORA_DAMM_V2_SWAP:
        return MeteoraDammV2SwapEvent(metadata=meta, pool=_get_str(data, "pool"))
    if event_type == EventType.METEORA_DAMM_V2_ADD_LIQUIDITY:
        return MeteoraDammV2AddLiquidityEvent(metadata=meta, pool=_get_str(data, "pool"))
    if event_type == EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY:
        return MeteoraDammV2RemoveLiquidityEvent(metadata=meta, pool=_get_str(data, "pool"))
    if event_type == EventType.METEORA_DAMM_V2_CREATE_POSITION:
        return MeteoraDammV2CreatePositionEvent(metadata=meta, pool=_get_str(data, "pool"))
    if event_type == EventType.METEORA_DAMM_V2_CLOSE_POSITION:
        return MeteoraDammV2ClosePositionEvent(metadata=meta, pool=_get_str(data, "pool"))
    if event_type == EventType.METEORA_DAMM_V2_INITIALIZE_POOL:
        return MeteoraDammV2InitializePoolEvent(metadata=meta, pool=_get_str(data, "pool"))

    if event_type == EventType.RAYDIUM_CLMM_SWAP:
        return RaydiumClmmSwapEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            sender=_get_str(data, "sender"),
            token_account_0=_get_str(data, "token_account_0"),
            token_account_1=_get_str(data, "token_account_1"),
            amount_0=_get_int(data, "amount_0"),
            amount_1=_get_int(data, "amount_1"),
            zero_for_one=_get_bool(data, "zero_for_one"),
            sqrt_price_x64=_get_str(data, "sqrt_price_x64"),
            liquidity=_get_str(data, "liquidity"),
            transfer_fee_0=_get_int(data, "transfer_fee_0"),
            transfer_fee_1=_get_int(data, "transfer_fee_1"),
            tick=_get_int(data, "tick"),
        )
    if event_type == EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY:
        return RaydiumClmmIncreaseLiquidityEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
            user=_get_str(data, "user"),
            liquidity=_get_str(data, "liquidity"),
            amount_0=_get_int(data, "amount_0"),
            amount_1=_get_int(data, "amount_1"),
            amount_0_transfer_fee=_get_int(data, "amount_0_transfer_fee"),
            amount_1_transfer_fee=_get_int(data, "amount_1_transfer_fee"),
            amount0_max=_get_int(data, "amount0_max"),
            amount1_max=_get_int(data, "amount1_max"),
        )
    if event_type == EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY:
        return RaydiumClmmDecreaseLiquidityEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
            user=_get_str(data, "user"),
            liquidity=_get_str(data, "liquidity"),
            decrease_amount_0=_get_int(data, "decrease_amount_0"),
            decrease_amount_1=_get_int(data, "decrease_amount_1"),
            fee_amount_0=_get_int(data, "fee_amount_0"),
            fee_amount_1=_get_int(data, "fee_amount_1"),
            reward_amounts=list(data.get("reward_amounts", [])) if isinstance(data, dict) else [],
            transfer_fee_0=_get_int(data, "transfer_fee_0"),
            transfer_fee_1=_get_int(data, "transfer_fee_1"),
            amount0_min=_get_int(data, "amount0_min"),
            amount1_min=_get_int(data, "amount1_min"),
        )
    if event_type == EventType.RAYDIUM_CLMM_CREATE_POOL:
        return RaydiumClmmCreatePoolEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            creator=_get_str(data, "creator"),
            token_0_mint=_get_str(data, "token_0_mint"),
            token_1_mint=_get_str(data, "token_1_mint"),
            tick_spacing=_get_int(data, "tick_spacing"),
            fee_rate=_get_int(data, "fee_rate"),
            sqrt_price_x64=_get_str(data, "sqrt_price_x64"),
            tick=_get_int(data, "tick"),
            token_vault_0=_get_str(data, "token_vault_0"),
            token_vault_1=_get_str(data, "token_vault_1"),
            open_time=_get_int(data, "open_time"),
        )
    if event_type == EventType.RAYDIUM_CLMM_OPEN_POSITION:
        return RaydiumClmmOpenPositionEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
            tick_lower_index=_get_int(data, "tick_lower_index"),
            tick_upper_index=_get_int(data, "tick_upper_index"),
            liquidity=_get_str(data, "liquidity"),
        )
    if event_type == EventType.RAYDIUM_CLMM_OPEN_POSITION_WITH_TOKEN_EXT_NFT:
        return RaydiumClmmOpenPositionWithTokenExtNftEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
            tick_lower_index=_get_int(data, "tick_lower_index"),
            tick_upper_index=_get_int(data, "tick_upper_index"),
            liquidity=_get_str(data, "liquidity"),
        )
    if event_type == EventType.RAYDIUM_CLMM_CLOSE_POSITION:
        return RaydiumClmmClosePositionEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
        )
    if event_type == EventType.RAYDIUM_CLMM_COLLECT_FEE:
        return RaydiumClmmCollectFeeEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            position_nft_mint=_get_str(data, "position_nft_mint"),
            recipient_token_account_0=_get_str(data, "recipient_token_account_0"),
            recipient_token_account_1=_get_str(data, "recipient_token_account_1"),
            amount_0=_get_int(data, "amount_0"),
            amount_1=_get_int(data, "amount_1"),
        )
    if event_type == EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE:
        return RaydiumClmmLiquidityChangeEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            tick=_get_int(data, "tick"),
            tick_lower=_get_int(data, "tick_lower"),
            tick_upper=_get_int(data, "tick_upper"),
            liquidity_before=_get_str(data, "liquidity_before"),
            liquidity_after=_get_str(data, "liquidity_after"),
        )
    if event_type == EventType.RAYDIUM_CLMM_CONFIG_CHANGE:
        return RaydiumClmmConfigChangeEvent(
            metadata=meta,
            index=_get_int(data, "index"),
            owner=_get_str(data, "owner"),
            protocol_fee_rate=_get_int(data, "protocol_fee_rate"),
            trade_fee_rate=_get_int(data, "trade_fee_rate"),
            tick_spacing=_get_int(data, "tick_spacing"),
            fund_fee_rate=_get_int(data, "fund_fee_rate"),
            fund_owner=_get_str(data, "fund_owner"),
        )
    if event_type == EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION:
        return RaydiumClmmCreatePersonalPositionEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            minter=_get_str(data, "minter"),
            nft_owner=_get_str(data, "nft_owner"),
            tick_lower_index=_get_int(data, "tick_lower_index"),
            tick_upper_index=_get_int(data, "tick_upper_index"),
            liquidity=_get_str(data, "liquidity"),
            deposit_amount_0=_get_int(data, "deposit_amount_0"),
            deposit_amount_1=_get_int(data, "deposit_amount_1"),
            deposit_amount_0_transfer_fee=_get_int(data, "deposit_amount_0_transfer_fee"),
            deposit_amount_1_transfer_fee=_get_int(data, "deposit_amount_1_transfer_fee"),
        )
    if event_type == EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE:
        return RaydiumClmmLiquidityCalculateEvent(
            metadata=meta,
            pool_liquidity=_get_str(data, "pool_liquidity"),
            pool_sqrt_price_x64=_get_str(data, "pool_sqrt_price_x64"),
            pool_tick=_get_int(data, "pool_tick"),
            calc_amount_0=_get_int(data, "calc_amount_0"),
            calc_amount_1=_get_int(data, "calc_amount_1"),
            trade_fee_owed_0=_get_int(data, "trade_fee_owed_0"),
            trade_fee_owed_1=_get_int(data, "trade_fee_owed_1"),
            transfer_fee_0=_get_int(data, "transfer_fee_0"),
            transfer_fee_1=_get_int(data, "transfer_fee_1"),
        )
    if event_type == EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER:
        return RaydiumClmmOpenLimitOrderEvent(
            metadata=meta,
            pool_id=_get_str(data, "pool_id"),
            limit_order=_get_str(data, "limit_order"),
            zero_for_one=_get_bool(data, "zero_for_one"),
            tick_index=_get_int(data, "tick_index"),
            total_amount=_get_int(data, "total_amount"),
            transfer_fee=_get_int(data, "transfer_fee"),
        )
    if event_type == EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER:
        return RaydiumClmmIncreaseLimitOrderEvent(
            metadata=meta,
            pool_id=_get_str(data, "pool_id"),
            limit_order=_get_str(data, "limit_order"),
            zero_for_one=_get_bool(data, "zero_for_one"),
            tick_index=_get_int(data, "tick_index"),
            total_amount=_get_int(data, "total_amount"),
            increased_amount=_get_int(data, "increased_amount"),
            transfer_fee=_get_int(data, "transfer_fee"),
        )
    if event_type == EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER:
        return RaydiumClmmDecreaseLimitOrderEvent(
            metadata=meta,
            pool_id=_get_str(data, "pool_id"),
            limit_order=_get_str(data, "limit_order"),
            zero_for_one=_get_bool(data, "zero_for_one"),
            tick_index=_get_int(data, "tick_index"),
            total_amount=_get_int(data, "total_amount"),
            filled_amount=_get_int(data, "filled_amount"),
            settled_output_amount=_get_int(data, "settled_output_amount"),
            decreased_amount=_get_int(data, "decreased_amount"),
        )
    if event_type == EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER:
        return RaydiumClmmSettleLimitOrderEvent(
            metadata=meta,
            pool_id=_get_str(data, "pool_id"),
            limit_order=_get_str(data, "limit_order"),
            zero_for_one=_get_bool(data, "zero_for_one"),
            tick_index=_get_int(data, "tick_index"),
            total_amount=_get_int(data, "total_amount"),
            filled_amount=_get_int(data, "filled_amount"),
            settled_amount_out=_get_int(data, "settled_amount_out"),
        )
    if event_type == EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS:
        raw = data.get("reward_growth_global_x64", [])
        rewards = [str(v) for v in raw] if isinstance(raw, list) else []
        return RaydiumClmmUpdateRewardInfosEvent(
            metadata=meta,
            reward_growth_global_x64=rewards,
        )

    if event_type == EventType.RAYDIUM_CPMM_SWAP:
        return RaydiumCpmmSwapEvent(
            metadata=meta,
            pool_id=_get_str(data, "pool_id"),
            input_amount=_get_int(data, "input_amount"),
            output_amount=_get_int(data, "output_amount"),
            input_vault_before=_get_int(data, "input_vault_before"),
            output_vault_before=_get_int(data, "output_vault_before"),
            input_transfer_fee=_get_int(data, "input_transfer_fee"),
            output_transfer_fee=_get_int(data, "output_transfer_fee"),
            base_input=_get_bool(data, "base_input"),
        )
    if event_type == EventType.RAYDIUM_CPMM_DEPOSIT:
        return RaydiumCpmmDepositEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            lp_token_amount=_get_int(data, "lp_token_amount"),
            token0_amount=_get_int(data, "token0_amount"),
            token1_amount=_get_int(data, "token1_amount"),
        )
    if event_type == EventType.RAYDIUM_CPMM_WITHDRAW:
        return RaydiumCpmmWithdrawEvent(
            metadata=meta,
            pool=_get_str(data, "pool"),
            user=_get_str(data, "user"),
            lp_token_amount=_get_int(data, "lp_token_amount"),
            token0_amount=_get_int(data, "token0_amount"),
            token1_amount=_get_int(data, "token1_amount"),
        )

    if event_type == EventType.RAYDIUM_AMM_V4_SWAP:
        return RaydiumAmmV4SwapEvent(
            metadata=meta,
            amm=_get_str(data, "amm"),
            user_source_owner=_get_str(data, "user_source_owner"),
            amount_in=_get_int(data, "amount_in"),
            minimum_amount_out=_get_int(data, "minimum_amount_out"),
            max_amount_in=_get_int(data, "max_amount_in"),
            amount_out=_get_int(data, "amount_out"),
            token_program=_get_str(data, "token_program"),
            amm_authority=_get_str(data, "amm_authority"),
            amm_open_orders=_get_str(data, "amm_open_orders"),
            pool_coin_token_account=_get_str(data, "pool_coin_token_account"),
            pool_pc_token_account=_get_str(data, "pool_pc_token_account"),
            serum_program=_get_str(data, "serum_program"),
            serum_market=_get_str(data, "serum_market"),
            serum_bids=_get_str(data, "serum_bids"),
            serum_asks=_get_str(data, "serum_asks"),
            serum_event_queue=_get_str(data, "serum_event_queue"),
            serum_coin_vault_account=_get_str(data, "serum_coin_vault_account"),
            serum_pc_vault_account=_get_str(data, "serum_pc_vault_account"),
            serum_vault_signer=_get_str(data, "serum_vault_signer"),
            user_source_token_account=_get_str(data, "user_source_token_account"),
            user_destination_token_account=_get_str(data, "user_destination_token_account"),
        )

    if event_type == EventType.ORCA_WHIRLPOOL_SWAP:
        return OrcaWhirlpoolSwapEvent(
            metadata=meta,
            whirlpool=_get_str(data, "whirlpool"),
            a_to_b=_get_bool(data, "a_to_b"),
            pre_sqrt_price=_get_str(data, "pre_sqrt_price"),
            post_sqrt_price=_get_str(data, "post_sqrt_price"),
            input_amount=_get_int(data, "input_amount"),
            output_amount=_get_int(data, "output_amount"),
            input_transfer_fee=_get_int(data, "input_transfer_fee"),
            output_transfer_fee=_get_int(data, "output_transfer_fee"),
            lp_fee=_get_int(data, "lp_fee"),
            protocol_fee=_get_int(data, "protocol_fee"),
        )
    if event_type == EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED:
        return OrcaWhirlpoolLiquidityIncreasedEvent(
            metadata=meta,
            whirlpool=_get_str(data, "whirlpool"),
            position=_get_str(data, "position"),
            tick_lower_index=_get_int(data, "tick_lower_index"),
            tick_upper_index=_get_int(data, "tick_upper_index"),
            liquidity=_get_str(data, "liquidity"),
            token_a_amount=_get_int(data, "token_a_amount"),
            token_b_amount=_get_int(data, "token_b_amount"),
            token_a_transfer_fee=_get_int(data, "token_a_transfer_fee"),
            token_b_transfer_fee=_get_int(data, "token_b_transfer_fee"),
        )
    if event_type == EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED:
        return OrcaWhirlpoolLiquidityDecreasedEvent(
            metadata=meta,
            whirlpool=_get_str(data, "whirlpool"),
            position=_get_str(data, "position"),
            tick_lower_index=_get_int(data, "tick_lower_index"),
            tick_upper_index=_get_int(data, "tick_upper_index"),
            liquidity=_get_str(data, "liquidity"),
            token_a_amount=_get_int(data, "token_a_amount"),
            token_b_amount=_get_int(data, "token_b_amount"),
            token_a_transfer_fee=_get_int(data, "token_a_transfer_fee"),
            token_b_transfer_fee=_get_int(data, "token_b_transfer_fee"),
        )
    if event_type == EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED:
        return OrcaWhirlpoolPoolInitializedEvent(
            metadata=meta,
            whirlpool=_get_str(data, "whirlpool"),
            whirlpools_config=_get_str(data, "whirlpools_config"),
            token_mint_a=_get_str(data, "token_mint_a"),
            token_mint_b=_get_str(data, "token_mint_b"),
            tick_spacing=_get_int(data, "tick_spacing"),
            token_program_a=_get_str(data, "token_program_a"),
            token_program_b=_get_str(data, "token_program_b"),
            decimals_a=_get_int(data, "decimals_a"),
            decimals_b=_get_int(data, "decimals_b"),
            initial_sqrt_price=_get_str(data, "initial_sqrt_price"),
        )

    # RaydiumLaunchlab events
    if event_type == EventType.RAYDIUM_LAUNCHLAB_TRADE:
        return RaydiumLaunchlabTradeEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            user=_get_str(data, "user"),
            amount_in=_get_int(data, "amount_in"),
            amount_out=_get_int(data, "amount_out"),
            is_buy=_get_bool(data, "is_buy"),
            trade_direction=_get_str(data, "trade_direction"),
            exact_in=_get_bool(data, "exact_in"),
        )
    
    if event_type == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE:
        return RaydiumLaunchlabPoolCreateEvent(
            metadata=meta,
            pool_state=_get_str(data, "pool_state"),
            creator=_get_str(data, "creator"),
            base_mint_param=_get_dict_any(data, "base_mint_param"),
        )
    
    if event_type == EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM:
        return RaydiumLaunchlabMigrateAmmEvent(
            metadata=meta,
            old_pool=_get_str(data, "old_pool"),
            new_pool=_get_str(data, "new_pool"),
            user=_get_str(data, "user"),
            liquidity_amount=_get_int(data, "liquidity_amount"),
        )
    
    # Add more event type conversions as needed...

    return None


def legacy_dict_to_dex_event(d: dict) -> Optional[DexEvent]:
    """将单键 legacy dict ``{ EventType.value: payload }`` 转为 :class:`DexEvent`（供指令解析等路径）。"""
    if not d:
        return None
    typed = to_typed_event(d)
    if typed is None:
        return None
    key = next(iter(d))
    try:
        et = EventType(key)
    except ValueError:
        return None
    return DexEvent(type=et, data=typed)
