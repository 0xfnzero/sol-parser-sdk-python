"""与 `sol-parser-sdk-golang/solparser` matcher 对齐的程序数据解析（Program data 行）。

由小端 u128 承载的语义字段（Meteora DAMM v2、Raydium CLMM、Orca Whirlpool、Meteora DLMM Swap 的 `fee_bps` 等）
在 Python 结果里为 **十进制字符串**，与 TS `bigint` 十进制及 Go `u128LEDecimalString` 一致。
`python3 -m sol_parser.check_migration` 会额外跑 `u128_parity`（标量 + Orca 合成用例）。
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional

import base58

from .grpc_types import EventType, EventMetadata
from .event_types import (
    DexEvent, PumpFunTradeEvent, PumpFunCreateEvent, PumpFunMigrateEvent,
    PumpFeesShareholder, PumpFeesFees, PumpFeesFeeTier,
    PumpFeesCreateFeeSharingConfigEvent, PumpFeesInitializeFeeConfigEvent,
    PumpFeesResetFeeSharingConfigEvent, PumpFeesRevokeFeeSharingAuthorityEvent,
    PumpFeesTransferFeeSharingAuthorityEvent, PumpFeesUpdateAdminEvent,
    PumpFeesUpdateFeeConfigEvent, PumpFeesUpdateFeeSharesEvent, PumpFeesUpsertFeeTiersEvent,
    PumpFunMigrateBondingCurveCreatorEvent,
    PumpSwapBuyEvent, PumpSwapSellEvent, PumpSwapCreatePoolEvent,
    PumpSwapLiquidityAddedEvent, PumpSwapLiquidityRemovedEvent,
    RaydiumAmmV4SwapEvent, RaydiumAmmV4DepositEvent, RaydiumAmmV4WithdrawEvent,
    RaydiumAmmV4WithdrawPnlEvent, RaydiumAmmV4Initialize2Event,
    RaydiumClmmSwapEvent, RaydiumClmmIncreaseLiquidityEvent,
    RaydiumClmmDecreaseLiquidityEvent, RaydiumClmmCreatePoolEvent,
    RaydiumClmmCollectFeeEvent, RaydiumClmmLiquidityChangeEvent,
    RaydiumClmmConfigChangeEvent, RaydiumClmmCreatePersonalPositionEvent,
    RaydiumClmmLiquidityCalculateEvent, RaydiumClmmOpenLimitOrderEvent,
    RaydiumClmmIncreaseLimitOrderEvent, RaydiumClmmDecreaseLimitOrderEvent,
    RaydiumClmmSettleLimitOrderEvent, RaydiumClmmUpdateRewardInfosEvent,
    RaydiumCpmmSwapEvent, RaydiumCpmmDepositEvent,
    RaydiumCpmmWithdrawEvent, RaydiumCpmmInitializeEvent,
    OrcaWhirlpoolSwapEvent, OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolLiquidityDecreasedEvent, OrcaWhirlpoolPoolInitializedEvent,
    MeteoraDlmmSwapEvent, MeteoraDlmmAddLiquidityEvent, MeteoraDlmmRemoveLiquidityEvent,
    MeteoraDlmmInitializePoolEvent, MeteoraDlmmInitializeBinArrayEvent,
    MeteoraDlmmCreatePositionEvent, MeteoraDlmmClosePositionEvent,
    MeteoraDlmmClaimFeeEvent, MeteoraPoolsSetPoolFeesEvent, MeteoraPoolsSwapEvent,
    MeteoraPoolsAddLiquidityEvent, MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsBootstrapLiquidityEvent, MeteoraPoolsPoolCreatedEvent, MeteoraDammV2SwapEvent,
    MeteoraDammV2CreatePositionEvent, MeteoraDammV2ClosePositionEvent,
    MeteoraDammV2AddLiquidityEvent, MeteoraDammV2RemoveLiquidityEvent,
    MeteoraDammV2InitializePoolEvent,
    MeteoraDbcCurveCompleteEvent, MeteoraDbcInitializePoolEvent, MeteoraDbcSwapEvent,
    RaydiumLaunchlabTradeEvent, RaydiumLaunchlabPoolCreateEvent,
)

Z = "11111111111111111111111111111111"


def normalize_pumpfun_ix_name(ix_name: str) -> str:
    if ix_name == "buy_v2":
        return "buy"
    if ix_name == "sell_v2":
        return "sell"
    if ix_name == "buy_exact_quote_in_v2":
        return "buy_exact_quote_in"
    return ix_name


def _u64le(b: bytes, o: int) -> int:
    return struct.unpack_from("<Q", b, o)[0]


def _i64le(b: bytes, o: int) -> int:
    return struct.unpack_from("<q", b, o)[0]


def _i32le(b: bytes, o: int) -> int:
    return struct.unpack_from("<i", b, o)[0]


def _u32le(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def _u16le(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _u8(b: bytes, o: int) -> int:
    return b[o]


def _pub(b: bytes, o: int) -> str:
    return base58.b58encode(b[o : o + 32]).decode()


def _optional_u64(b: bytes, o: List[int]) -> int:
    if o[0] + 8 > len(b):
        return 0
    v = _u64le(b, o[0])
    o[0] += 8
    return v


def _optional_pub(b: bytes, o: List[int]) -> str:
    if o[0] + 32 > len(b):
        return Z
    v = _pub(b, o[0])
    o[0] += 32
    return v


def _trade_shareholders(b: bytes, o: List[int]) -> Optional[List[PumpFeesShareholder]]:
    if o[0] + 4 > len(b):
        return []
    n = _u32le(b, o[0])
    if n > 64:
        return None
    o[0] += 4
    if o[0] + n * 34 > len(b):
        return None
    out: List[PumpFeesShareholder] = []
    for _ in range(n):
        address = _pub(b, o[0])
        o[0] += 32
        share_bps = _u16le(b, o[0])
        o[0] += 2
        out.append(PumpFeesShareholder(address=address, share_bps=share_bps))
    return out


def _bool(b: bytes, o: int) -> bool:
    return b[o] == 1


def _u128le_int(b: bytes, o: int) -> int:
    return int.from_bytes(b[o : o + 16], "little")


def _borsh_str(b: bytes, o: int) -> tuple[str, int]:
    (n,) = struct.unpack_from("<I", b, o)
    o += 4
    return b[o : o + n].decode("utf-8", errors="replace"), o + n


def _disc8(bs: bytes) -> int:
    return struct.unpack("<Q", bs)[0]


def _d(*xs: int) -> int:
    return struct.unpack("<Q", bytes(xs))[0]


def _u64_at(b: bytes, o: List[int]) -> int:
    v = _u64le(b, o[0])
    o[0] += 8
    return v


# --- PumpFun ---

PUMP_TRADE = _d(189, 219, 127, 211, 78, 230, 97, 238)
PUMP_CREATE = _d(27, 114, 169, 77, 222, 235, 99, 118)
PUMP_MIGRATE = _d(189, 233, 93, 185, 92, 148, 234, 148)
PUMP_MIGRATE_BONDING_CURVE_CREATOR = _d(155, 167, 104, 220, 213, 108, 243, 3)
PUMP_FEES_CREATE_FEE_SHARING_CONFIG = _d(133, 105, 170, 200, 184, 116, 251, 88)
PUMP_FEES_INITIALIZE_FEE_CONFIG = _d(89, 138, 244, 230, 10, 56, 226, 126)
PUMP_FEES_RESET_FEE_SHARING_CONFIG = _d(203, 204, 151, 226, 120, 55, 214, 243)
PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY = _d(114, 23, 101, 60, 14, 190, 153, 62)
PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY = _d(124, 143, 198, 245, 77, 184, 8, 236)
PUMP_FEES_UPDATE_ADMIN = _d(225, 152, 171, 87, 246, 63, 66, 234)
PUMP_FEES_UPDATE_FEE_CONFIG = _d(90, 23, 65, 35, 62, 244, 188, 208)
PUMP_FEES_UPDATE_FEE_SHARES = _d(21, 186, 196, 184, 91, 228, 225, 203)
PUMP_FEES_UPSERT_FEE_TIERS = _d(171, 89, 169, 187, 122, 186, 33, 204)


def _make_meta(meta: dict) -> EventMetadata:
    """从 dict 构造 EventMetadata"""
    if isinstance(meta, EventMetadata):
        return meta
    if isinstance(meta, dict):
        return EventMetadata(
            signature=meta.get("signature", ""),
            slot=meta.get("slot", 0),
            tx_index=meta.get("tx_index", 0),
            block_time_us=meta.get("block_time_us", 0),
            grpc_recv_us=meta.get("grpc_recv_us", 0),
            recent_blockhash=meta.get("recent_blockhash", ""),
        )
    return EventMetadata()


def parse_trade_from_data(data: bytes, meta: dict, is_created_buy: bool) -> DexEvent:
    if len(data) < 200:
        return DexEvent()
    o = 0
    mint = _pub(data, o)
    o += 32
    sol_amount = _u64le(data, o)
    o += 8
    token_amount = _u64le(data, o)
    o += 8
    is_buy = _bool(data, o)
    o += 1
    user = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    vsol = _u64le(data, o)
    o += 8
    vtok = _u64le(data, o)
    o += 8
    rsol = _u64le(data, o)
    o += 8
    rtok = _u64le(data, o)
    o += 8
    fee_rec = _pub(data, o)
    o += 32
    fee_bps = _u64le(data, o)
    o += 8
    fee = _u64le(data, o)
    o += 8
    creator = _pub(data, o)
    o += 32
    cfbps = _u64le(data, o)
    o += 8
    cfee = _u64le(data, o)
    o += 8
    tv = _bool(data, o) if o < len(data) else False
    o += 1
    tuc = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    tcc = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    csv = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    lut = _i64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    ix_name = ""
    if o + 4 <= len(data):
        ix_name, o = _borsh_str(data, o)
    ix_name = normalize_pumpfun_ix_name(ix_name)
    mm = _bool(data, o) if o < len(data) else False
    o += 1
    cb_bps = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    cb = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    tail = [o]
    buyback_fee_basis_points = _optional_u64(data, tail)
    buyback_fee = _optional_u64(data, tail)
    shareholders = _trade_shareholders(data, tail)
    if shareholders is None:
        return DexEvent()
    quote_mint = _optional_pub(data, tail)
    quote_amount = _optional_u64(data, tail)
    virtual_quote_reserves = _optional_u64(data, tail)
    real_quote_reserves = _optional_u64(data, tail)
    
    event_data = PumpFunTradeEvent(
        metadata=_make_meta(meta),
        mint=mint,
        sol_amount=sol_amount,
        token_amount=token_amount,
        is_buy=is_buy,
        is_created_buy=is_created_buy,
        user=user,
        timestamp=ts,
        virtual_sol_reserves=vsol,
        virtual_token_reserves=vtok,
        real_sol_reserves=rsol,
        real_token_reserves=rtok,
        fee_recipient=fee_rec,
        fee_basis_points=fee_bps,
        fee=fee,
        creator=creator,
        creator_fee_basis_points=cfbps,
        creator_fee=cfee,
        track_volume=tv,
        total_unclaimed_tokens=tuc,
        total_claimed_tokens=tcc,
        current_sol_volume=csv,
        last_update_timestamp=lut,
        ix_name=ix_name,
        mayhem_mode=mm,
        cashback_fee_basis_points=cb_bps,
        cashback=cb,
        buyback_fee_basis_points=buyback_fee_basis_points,
        buyback_fee=buyback_fee,
        shareholders=shareholders,
        quote_mint=quote_mint,
        quote_amount=quote_amount,
        virtual_quote_reserves=virtual_quote_reserves,
        real_quote_reserves=real_quote_reserves,
        is_cashback_coin=cb_bps > 0,
        bonding_curve=Z,
        associated_bonding_curve=Z,
        token_program=Z,
        creator_vault=Z,
    )
    
    if ix_name == "buy":
        return DexEvent(type=EventType.PUMP_FUN_BUY, data=event_data)
    if ix_name == "sell":
        return DexEvent(type=EventType.PUMP_FUN_SELL, data=event_data)
    if ix_name == "buy_exact_sol_in":
        return DexEvent(type=EventType.PUMP_FUN_BUY_EXACT_SOL_IN, data=event_data)
    if ix_name == "buy_exact_quote_in":
        return DexEvent(type=EventType.PUMP_FUN_BUY, data=event_data)
    return DexEvent(type=EventType.PUMP_FUN_TRADE, data=event_data)


def parse_create_from_data(data: bytes, meta: dict) -> DexEvent:
    o = 0
    try:
        name, o = _borsh_str(data, o)
        sym, o = _borsh_str(data, o)
        uri, o = _borsh_str(data, o)
    except Exception:
        return DexEvent()
    if len(data) < o + 32 * 4 + 8 * 5 + 32 + 1:
        return DexEvent()
    mint = _pub(data, o)
    o += 32
    bc = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    creator = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    vtr = _u64le(data, o)
    o += 8
    vsol = _u64le(data, o)
    o += 8
    rtr = _u64le(data, o)
    o += 8
    tts = _u64le(data, o)
    o += 8
    tp = _pub(data, o) if o + 32 <= len(data) else Z
    o += 32
    mm = _bool(data, o) if o < len(data) else False
    o += 1
    ice = _bool(data, o) if o < len(data) else False
    o += 1
    quote_mint = _pub(data, o) if o + 32 <= len(data) else Z
    o += 32
    virtual_quote_reserves = _u64le(data, o) if o + 8 <= len(data) else 0
    
    return DexEvent(
        type=EventType.PUMP_FUN_CREATE,
        data=PumpFunCreateEvent(
            metadata=_make_meta(meta),
            name=name,
            symbol=sym,
            uri=uri,
            mint=mint,
            bonding_curve=bc,
            user=user,
            creator=creator,
            timestamp=ts,
            virtual_token_reserves=vtr,
            virtual_sol_reserves=vsol,
            real_token_reserves=rtr,
            token_total_supply=tts,
            token_program=tp,
            is_mayhem_mode=mm,
            is_cashback_enabled=ice,
            quote_mint=quote_mint,
            virtual_quote_reserves=virtual_quote_reserves,
        ),
    )


def parse_migrate_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 32 + 8 + 32:
        return DexEvent()
    o = 0
    user = _pub(data, o)
    o += 32
    mint = _pub(data, o)
    o += 32
    ma = _u64le(data, o)
    o += 8
    sa = _u64le(data, o)
    o += 8
    pmf = _u64le(data, o)
    o += 8
    bc = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    pool = _pub(data, o)
    
    return DexEvent(
        type=EventType.PUMP_FUN_MIGRATE,
        data=PumpFunMigrateEvent(
            metadata=_make_meta(meta),
            user=user,
            mint=mint,
            mint_amount=ma,
            sol_amount=sa,
            pool_migration_fee=pmf,
            bonding_curve=bc,
            timestamp=ts,
            pool=pool,
        ),
    )


def _read_fees_at(data: bytes, o: List[int]) -> Optional[PumpFeesFees]:
    if o[0] + 24 > len(data):
        return None
    lp_fee_bps = _u64_at(data, o)
    protocol_fee_bps = _u64_at(data, o)
    creator_fee_bps = _u64_at(data, o)
    return PumpFeesFees(
        lp_fee_bps=lp_fee_bps,
        protocol_fee_bps=protocol_fee_bps,
        creator_fee_bps=creator_fee_bps,
    )


def read_pump_fees_shareholders_vec(data: bytes, o: List[int]) -> Optional[List[PumpFeesShareholder]]:
    if o[0] + 4 > len(data):
        return None
    n = _u32le(data, o[0])
    o[0] += 4
    if n > 64:
        return None
    out: List[PumpFeesShareholder] = []
    for _ in range(n):
        if o[0] + 34 > len(data):
            return None
        address = _pub(data, o[0])
        o[0] += 32
        share_bps = _u16le(data, o[0])
        o[0] += 2
        out.append(PumpFeesShareholder(address=address, share_bps=share_bps))
    return out


def read_pump_fees_fee_tiers_vec(data: bytes, o: List[int]) -> Optional[List[PumpFeesFeeTier]]:
    if o[0] + 4 > len(data):
        return None
    n = _u32le(data, o[0])
    o[0] += 4
    if n > 64:
        return None
    out: List[PumpFeesFeeTier] = []
    for _ in range(n):
        if o[0] + 16 > len(data):
            return None
        threshold = _u128le_int(data, o[0])
        o[0] += 16
        fees = _read_fees_at(data, o)
        if fees is None:
            return None
        out.append(PumpFeesFeeTier(market_cap_lamports_threshold=threshold, fees=fees))
    return out


def _read_option_pubkey_at(data: bytes, o: List[int]) -> Optional[str]:
    if o[0] >= len(data):
        return None
    tag = _u8(data, o[0])
    o[0] += 1
    if tag == 0:
        return ""
    if tag != 1 or o[0] + 32 > len(data):
        return None
    v = _pub(data, o[0])
    o[0] += 32
    return v


def _read_config_status_at(data: bytes, o: List[int]) -> Optional[str]:
    if o[0] >= len(data):
        return None
    tag = _u8(data, o[0])
    o[0] += 1
    if tag == 0:
        return "Paused"
    if tag == 1:
        return "Active"
    return None


def parse_migrate_bonding_curve_creator_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 8 + 32 * 5:
        return DexEvent()
    o = 0
    ts = _i64le(data, o)
    o += 8
    mint = _pub(data, o)
    o += 32
    bonding_curve = _pub(data, o)
    o += 32
    sharing_config = _pub(data, o)
    o += 32
    old_creator = _pub(data, o)
    o += 32
    new_creator = _pub(data, o)
    return DexEvent(
        type=EventType.PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR,
        data=PumpFunMigrateBondingCurveCreatorEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            mint=mint,
            bonding_curve=bonding_curve,
            sharing_config=sharing_config,
            old_creator=old_creator,
            new_creator=new_creator,
        ),
    )


def parse_pump_fees_create_fee_sharing_config_from_data(data: bytes, meta: dict) -> DexEvent:
    o = [0]
    if len(data) < 8 + 32 * 4 + 1 + 4 + 1:
        return DexEvent()
    ts = _i64le(data, o[0])
    o[0] += 8
    mint = _pub(data, o[0])
    o[0] += 32
    bonding_curve = _pub(data, o[0])
    o[0] += 32
    pool = _read_option_pubkey_at(data, o)
    if pool is None:
        return DexEvent()
    sharing_config = _pub(data, o[0])
    o[0] += 32
    admin = _pub(data, o[0])
    o[0] += 32
    shareholders = read_pump_fees_shareholders_vec(data, o)
    if shareholders is None:
        return DexEvent()
    status = _read_config_status_at(data, o)
    if status is None or o[0] != len(data):
        return DexEvent()
    return DexEvent(
        type=EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
        data=PumpFeesCreateFeeSharingConfigEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            mint=mint,
            bonding_curve=bonding_curve,
            pool=pool,
            sharing_config=sharing_config,
            admin=admin,
            initial_shareholders=shareholders,
            status=status,
        ),
    )


def parse_pump_fees_initialize_fee_config_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) != 8 + 32 + 32:
        return DexEvent()
    o = 0
    ts = _i64le(data, o)
    o += 8
    admin = _pub(data, o)
    o += 32
    fee_config = _pub(data, o)
    return DexEvent(
        type=EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
        data=PumpFeesInitializeFeeConfigEvent(
            metadata=_make_meta(meta), timestamp=ts, admin=admin, fee_config=fee_config
        ),
    )


def parse_pump_fees_reset_fee_sharing_config_from_data(data: bytes, meta: dict) -> DexEvent:
    o = [0]
    if len(data) < 8 + 32 * 4 + 4 + 4:
        return DexEvent()
    ts = _i64le(data, o[0])
    o[0] += 8
    mint = _pub(data, o[0])
    o[0] += 32
    sharing_config = _pub(data, o[0])
    o[0] += 32
    old_admin = _pub(data, o[0])
    o[0] += 32
    old_shareholders = read_pump_fees_shareholders_vec(data, o)
    if old_shareholders is None:
        return DexEvent()
    new_admin = _pub(data, o[0])
    o[0] += 32
    new_shareholders = read_pump_fees_shareholders_vec(data, o)
    if new_shareholders is None or o[0] != len(data):
        return DexEvent()
    return DexEvent(
        type=EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
        data=PumpFeesResetFeeSharingConfigEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            mint=mint,
            sharing_config=sharing_config,
            old_admin=old_admin,
            old_shareholders=old_shareholders,
            new_admin=new_admin,
            new_shareholders=new_shareholders,
        ),
    )


def parse_pump_fees_revoke_fee_sharing_authority_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) != 8 + 32 * 3:
        return DexEvent()
    o = 0
    ts = _i64le(data, o)
    o += 8
    mint = _pub(data, o)
    o += 32
    sharing_config = _pub(data, o)
    o += 32
    admin = _pub(data, o)
    return DexEvent(
        type=EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
        data=PumpFeesRevokeFeeSharingAuthorityEvent(
            metadata=_make_meta(meta), timestamp=ts, mint=mint, sharing_config=sharing_config, admin=admin
        ),
    )


def parse_pump_fees_transfer_fee_sharing_authority_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) != 8 + 32 * 4:
        return DexEvent()
    o = 0
    ts = _i64le(data, o)
    o += 8
    mint = _pub(data, o)
    o += 32
    sharing_config = _pub(data, o)
    o += 32
    old_admin = _pub(data, o)
    o += 32
    new_admin = _pub(data, o)
    return DexEvent(
        type=EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
        data=PumpFeesTransferFeeSharingAuthorityEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            mint=mint,
            sharing_config=sharing_config,
            old_admin=old_admin,
            new_admin=new_admin,
        ),
    )


def parse_pump_fees_update_admin_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) != 8 + 32 + 32:
        return DexEvent()
    o = 0
    ts = _i64le(data, o)
    o += 8
    old_admin = _pub(data, o)
    o += 32
    new_admin = _pub(data, o)
    return DexEvent(
        type=EventType.PUMP_FEES_UPDATE_ADMIN,
        data=PumpFeesUpdateAdminEvent(
            metadata=_make_meta(meta), timestamp=ts, old_admin=old_admin, new_admin=new_admin
        ),
    )


def parse_pump_fees_update_fee_config_from_data(data: bytes, meta: dict) -> DexEvent:
    o = [0]
    if len(data) < 8 + 32 + 32 + 4 + 24:
        return DexEvent()
    ts = _i64le(data, o[0])
    o[0] += 8
    admin = _pub(data, o[0])
    o[0] += 32
    fee_config = _pub(data, o[0])
    o[0] += 32
    fee_tiers = read_pump_fees_fee_tiers_vec(data, o)
    if fee_tiers is None:
        return DexEvent()
    flat_fees = _read_fees_at(data, o)
    if flat_fees is None or o[0] != len(data):
        return DexEvent()
    return DexEvent(
        type=EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
        data=PumpFeesUpdateFeeConfigEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            admin=admin,
            fee_config=fee_config,
            fee_tiers=fee_tiers,
            flat_fees=flat_fees,
        ),
    )


def parse_pump_fees_update_fee_shares_from_data(data: bytes, meta: dict) -> DexEvent:
    o = [0]
    if len(data) < 8 + 32 * 3 + 4:
        return DexEvent()
    ts = _i64le(data, o[0])
    o[0] += 8
    mint = _pub(data, o[0])
    o[0] += 32
    sharing_config = _pub(data, o[0])
    o[0] += 32
    admin = _pub(data, o[0])
    o[0] += 32
    shareholders = read_pump_fees_shareholders_vec(data, o)
    if shareholders is None or o[0] != len(data):
        return DexEvent()
    return DexEvent(
        type=EventType.PUMP_FEES_UPDATE_FEE_SHARES,
        data=PumpFeesUpdateFeeSharesEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            mint=mint,
            sharing_config=sharing_config,
            admin=admin,
            bonding_curve=Z,
            pump_creator_vault=Z,
            new_shareholders=shareholders,
        ),
    )


def parse_pump_fees_upsert_fee_tiers_from_data(data: bytes, meta: dict) -> DexEvent:
    o = [0]
    if len(data) < 8 + 32 + 32 + 4 + 1:
        return DexEvent()
    ts = _i64le(data, o[0])
    o[0] += 8
    admin = _pub(data, o[0])
    o[0] += 32
    fee_config = _pub(data, o[0])
    o[0] += 32
    fee_tiers = read_pump_fees_fee_tiers_vec(data, o)
    if fee_tiers is None or o[0] >= len(data):
        return DexEvent()
    offset = _u8(data, o[0])
    o[0] += 1
    if o[0] != len(data):
        return DexEvent()
    return DexEvent(
        type=EventType.PUMP_FEES_UPSERT_FEE_TIERS,
        data=PumpFeesUpsertFeeTiersEvent(
            metadata=_make_meta(meta),
            timestamp=ts,
            admin=admin,
            fee_config=fee_config,
            fee_tiers=fee_tiers,
            offset=offset,
        ),
    )


# --- Raydium CLMM ---


def parse_clmm_swap_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 32 + 32 + 8 + 8 + 8 + 8 + 1 + 16 + 16 + 4:
        return DexEvent()
    o = 0
    ps = _pub(data, o)
    o += 32
    sender = _pub(data, o)
    o += 32
    token_account_0 = _pub(data, o)
    o += 32
    token_account_1 = _pub(data, o)
    o += 32
    amount_0 = _u64le(data, o)
    o += 8
    transfer_fee_0 = _u64le(data, o)
    o += 8
    amount_1 = _u64le(data, o)
    o += 8
    transfer_fee_1 = _u64le(data, o)
    o += 8
    zfo = _bool(data, o)
    o += 1
    sqrt = str(_u128le_int(data, o))
    o += 16
    liq = str(_u128le_int(data, o))
    o += 16
    tick = _i32le(data, o)
    
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_SWAP,
        data=RaydiumClmmSwapEvent(
            metadata=_make_meta(meta),
            pool_state=ps,
            sender=sender,
            token_account_0=token_account_0,
            token_account_1=token_account_1,
            amount_0=amount_0,
            amount_1=amount_1,
            zero_for_one=zfo,
            sqrt_price_x64=sqrt,
            liquidity=liq,
            transfer_fee_0=transfer_fee_0,
            transfer_fee_1=transfer_fee_1,
            tick=tick,
        ),
    )


def parse_clmm_inc_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 16 + 8 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    position_nft_mint = _pub(data, o)
    o += 32
    liq = str(_u128le_int(data, o))
    o += 16
    amount_0 = _u64le(data, o)
    o += 8
    amount_1 = _u64le(data, o)
    o += 8
    amount_0_transfer_fee = _u64le(data, o)
    o += 8
    amount_1_transfer_fee = _u64le(data, o)
    
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
        data=RaydiumClmmIncreaseLiquidityEvent(
            metadata=_make_meta(meta),
            pool=Z,
            position_nft_mint=position_nft_mint,
            user=Z,
            liquidity=liq,
            amount_0=amount_0,
            amount_1=amount_1,
            amount_0_transfer_fee=amount_0_transfer_fee,
            amount_1_transfer_fee=amount_1_transfer_fee,
            amount0_max=0,
            amount1_max=0,
        ),
    )


def parse_clmm_dec_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 16 + 8 + 8 + 8 + 8 + 8 + 8 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    position_nft_mint = _pub(data, o)
    o += 32
    liq = str(_u128le_int(data, o))
    o += 16
    decrease_amount_0 = _u64le(data, o)
    o += 8
    decrease_amount_1 = _u64le(data, o)
    o += 8
    fee_amount_0 = _u64le(data, o)
    o += 8
    fee_amount_1 = _u64le(data, o)
    o += 8
    reward_amounts = [_u64le(data, o), _u64le(data, o + 8), _u64le(data, o + 16)]
    o += 24
    transfer_fee_0 = _u64le(data, o)
    o += 8
    transfer_fee_1 = _u64le(data, o)
    
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
        data=RaydiumClmmDecreaseLiquidityEvent(
            metadata=_make_meta(meta),
            pool=Z,
            position_nft_mint=position_nft_mint,
            user=Z,
            liquidity=liq,
            decrease_amount_0=decrease_amount_0,
            decrease_amount_1=decrease_amount_1,
            fee_amount_0=fee_amount_0,
            fee_amount_1=fee_amount_1,
            reward_amounts=reward_amounts,
            transfer_fee_0=transfer_fee_0,
            transfer_fee_1=transfer_fee_1,
            amount0_min=0,
            amount1_min=0,
        ),
    )


def parse_clmm_create_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 2 + 32 + 16 + 4 + 32 + 32:
        return DexEvent()
    o = 0
    token_0_mint = _pub(data, o)
    o += 32
    token_1_mint = _pub(data, o)
    o += 32
    tick_spacing = _u16le(data, o)
    o += 2
    pool = _pub(data, o)
    o += 32
    sqrt = str(_u128le_int(data, o))
    o += 16
    tick = _i32le(data, o)
    o += 4
    token_vault_0 = _pub(data, o)
    o += 32
    token_vault_1 = _pub(data, o)
    
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_CREATE_POOL,
        data=RaydiumClmmCreatePoolEvent(
            metadata=_make_meta(meta),
            pool=pool,
            creator=Z,
            token_0_mint=token_0_mint,
            token_1_mint=token_1_mint,
            tick_spacing=tick_spacing,
            fee_rate=0,
            sqrt_price_x64=sqrt,
            tick=tick,
            token_vault_0=token_vault_0,
            token_vault_1=token_vault_1,
            open_time=0,
        ),
    )


def parse_clmm_collect_personal_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 32 + 8 + 8:
        return DexEvent()
    o = 0
    pn = _pub(data, o)
    o += 32
    recipient_0 = _pub(data, o)
    o += 32
    recipient_1 = _pub(data, o)
    o += 32
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_COLLECT_FEE,
        data=RaydiumClmmCollectFeeEvent(
            metadata=_make_meta(meta),
            pool_state=Z,
            position_nft_mint=pn,
            recipient_token_account_0=recipient_0,
            recipient_token_account_1=recipient_1,
            amount_0=a0,
            amount_1=a1,
        ),
    )


def parse_clmm_collect_protocol_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 32 + 8 + 8:
        return DexEvent()
    o = 0
    ps = _pub(data, o)
    o += 32
    recipient_0 = _pub(data, o)
    o += 32
    recipient_1 = _pub(data, o)
    o += 32
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)

    return DexEvent(
        type=EventType.RAYDIUM_CLMM_COLLECT_FEE,
        data=RaydiumClmmCollectFeeEvent(
            metadata=_make_meta(meta),
            pool_state=ps,
            position_nft_mint=Z,
            recipient_token_account_0=recipient_0,
            recipient_token_account_1=recipient_1,
            amount_0=a0,
            amount_1=a1,
        ),
    )


def parse_clmm_liquidity_change_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 4 + 4 + 4 + 16 + 16:
        return DexEvent()
    o = 0
    pool_state = _pub(data, o)
    o += 32
    tick = _i32le(data, o)
    o += 4
    tick_lower = _i32le(data, o)
    o += 4
    tick_upper = _i32le(data, o)
    o += 4
    before = str(_u128le_int(data, o))
    o += 16
    after = str(_u128le_int(data, o))
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE,
        data=RaydiumClmmLiquidityChangeEvent(
            metadata=_make_meta(meta),
            pool_state=pool_state,
            tick=tick,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            liquidity_before=before,
            liquidity_after=after,
        ),
    )


def parse_clmm_config_change_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 2 + 32 + 4 + 4 + 2 + 4 + 32:
        return DexEvent()
    o = 0
    index = _u16le(data, o)
    o += 2
    owner = _pub(data, o)
    o += 32
    protocol_fee_rate = _u32le(data, o)
    o += 4
    trade_fee_rate = _u32le(data, o)
    o += 4
    tick_spacing = _u16le(data, o)
    o += 2
    fund_fee_rate = _u32le(data, o)
    o += 4
    fund_owner = _pub(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_CONFIG_CHANGE,
        data=RaydiumClmmConfigChangeEvent(
            metadata=_make_meta(meta),
            index=index,
            owner=owner,
            protocol_fee_rate=protocol_fee_rate,
            trade_fee_rate=trade_fee_rate,
            tick_spacing=tick_spacing,
            fund_fee_rate=fund_fee_rate,
            fund_owner=fund_owner,
        ),
    )


def parse_clmm_create_personal_position_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 32 + 4 + 4 + 16 + 8 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    pool_state = _pub(data, o)
    o += 32
    minter = _pub(data, o)
    o += 32
    nft_owner = _pub(data, o)
    o += 32
    tick_lower_index = _i32le(data, o)
    o += 4
    tick_upper_index = _i32le(data, o)
    o += 4
    liquidity = str(_u128le_int(data, o))
    o += 16
    deposit_amount_0 = _u64le(data, o)
    o += 8
    deposit_amount_1 = _u64le(data, o)
    o += 8
    deposit_amount_0_transfer_fee = _u64le(data, o)
    o += 8
    deposit_amount_1_transfer_fee = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION,
        data=RaydiumClmmCreatePersonalPositionEvent(
            metadata=_make_meta(meta),
            pool_state=pool_state,
            minter=minter,
            nft_owner=nft_owner,
            tick_lower_index=tick_lower_index,
            tick_upper_index=tick_upper_index,
            liquidity=liquidity,
            deposit_amount_0=deposit_amount_0,
            deposit_amount_1=deposit_amount_1,
            deposit_amount_0_transfer_fee=deposit_amount_0_transfer_fee,
            deposit_amount_1_transfer_fee=deposit_amount_1_transfer_fee,
        ),
    )


def parse_clmm_liquidity_calculate_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 16 + 16 + 4 + 8 + 8 + 8 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    pool_liquidity = str(_u128le_int(data, o))
    o += 16
    pool_sqrt_price_x64 = str(_u128le_int(data, o))
    o += 16
    pool_tick = _i32le(data, o)
    o += 4
    calc_amount_0 = _u64le(data, o)
    o += 8
    calc_amount_1 = _u64le(data, o)
    o += 8
    trade_fee_owed_0 = _u64le(data, o)
    o += 8
    trade_fee_owed_1 = _u64le(data, o)
    o += 8
    transfer_fee_0 = _u64le(data, o)
    o += 8
    transfer_fee_1 = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE,
        data=RaydiumClmmLiquidityCalculateEvent(
            metadata=_make_meta(meta),
            pool_liquidity=pool_liquidity,
            pool_sqrt_price_x64=pool_sqrt_price_x64,
            pool_tick=pool_tick,
            calc_amount_0=calc_amount_0,
            calc_amount_1=calc_amount_1,
            trade_fee_owed_0=trade_fee_owed_0,
            trade_fee_owed_1=trade_fee_owed_1,
            transfer_fee_0=transfer_fee_0,
            transfer_fee_1=transfer_fee_1,
        ),
    )


def parse_clmm_open_limit_order_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 1 + 4 + 8 + 8:
        return DexEvent()
    o = 0
    pool_id = _pub(data, o)
    o += 32
    limit_order = _pub(data, o)
    o += 32
    zero_for_one = _bool(data, o)
    o += 1
    tick_index = _i32le(data, o)
    o += 4
    total_amount = _u64le(data, o)
    o += 8
    transfer_fee = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER,
        data=RaydiumClmmOpenLimitOrderEvent(
            metadata=_make_meta(meta),
            pool_id=pool_id,
            limit_order=limit_order,
            zero_for_one=zero_for_one,
            tick_index=tick_index,
            total_amount=total_amount,
            transfer_fee=transfer_fee,
        ),
    )


def parse_clmm_increase_limit_order_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 1 + 4 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    pool_id = _pub(data, o)
    o += 32
    limit_order = _pub(data, o)
    o += 32
    zero_for_one = _bool(data, o)
    o += 1
    tick_index = _i32le(data, o)
    o += 4
    total_amount = _u64le(data, o)
    o += 8
    increased_amount = _u64le(data, o)
    o += 8
    transfer_fee = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER,
        data=RaydiumClmmIncreaseLimitOrderEvent(
            metadata=_make_meta(meta),
            pool_id=pool_id,
            limit_order=limit_order,
            zero_for_one=zero_for_one,
            tick_index=tick_index,
            total_amount=total_amount,
            increased_amount=increased_amount,
            transfer_fee=transfer_fee,
        ),
    )


def parse_clmm_decrease_limit_order_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 1 + 4 + 8 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    pool_id = _pub(data, o)
    o += 32
    limit_order = _pub(data, o)
    o += 32
    zero_for_one = _bool(data, o)
    o += 1
    tick_index = _i32le(data, o)
    o += 4
    total_amount = _u64le(data, o)
    o += 8
    filled_amount = _u64le(data, o)
    o += 8
    settled_output_amount = _u64le(data, o)
    o += 8
    decreased_amount = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER,
        data=RaydiumClmmDecreaseLimitOrderEvent(
            metadata=_make_meta(meta),
            pool_id=pool_id,
            limit_order=limit_order,
            zero_for_one=zero_for_one,
            tick_index=tick_index,
            total_amount=total_amount,
            filled_amount=filled_amount,
            settled_output_amount=settled_output_amount,
            decreased_amount=decreased_amount,
        ),
    )


def parse_clmm_settle_limit_order_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 32 + 32 + 1 + 4 + 8 + 8 + 8:
        return DexEvent()
    o = 0
    pool_id = _pub(data, o)
    o += 32
    limit_order = _pub(data, o)
    o += 32
    zero_for_one = _bool(data, o)
    o += 1
    tick_index = _i32le(data, o)
    o += 4
    total_amount = _u64le(data, o)
    o += 8
    filled_amount = _u64le(data, o)
    o += 8
    settled_amount_out = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER,
        data=RaydiumClmmSettleLimitOrderEvent(
            metadata=_make_meta(meta),
            pool_id=pool_id,
            limit_order=limit_order,
            zero_for_one=zero_for_one,
            tick_index=tick_index,
            total_amount=total_amount,
            filled_amount=filled_amount,
            settled_amount_out=settled_amount_out,
        ),
    )


def parse_clmm_update_reward_infos_from_data(data: bytes, meta: dict) -> DexEvent:
    if len(data) < 16 * 3:
        return DexEvent()
    rewards = [str(_u128le_int(data, i * 16)) for i in range(3)]
    return DexEvent(
        type=EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS,
        data=RaydiumClmmUpdateRewardInfosEvent(
            metadata=_make_meta(meta),
            reward_growth_global_x64=rewards,
        ),
    )


# --- Raydium AMM ---


def _amm_swap_event(
    meta: dict, amm: str, user: str, ai: int, mo: int, mai: int, ao: int
) -> RaydiumAmmV4SwapEvent:
    return RaydiumAmmV4SwapEvent(
        metadata=_make_meta(meta),
        amm=amm,
        user_source_owner=user,
        amount_in=ai,
        minimum_amount_out=mo,
        max_amount_in=mai,
        amount_out=ao,
    )


def parse_amm_swap_in_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    ai = _u64le(data, o)
    o += 8
    mo = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_SWAP,
        data=_amm_swap_event(meta, amm, user, ai, mo, 0, 0),
    )


def parse_amm_swap_out_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    mai = _u64le(data, o)
    o += 8
    ao = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_SWAP,
        data=_amm_swap_event(meta, amm, user, 0, 0, mai, ao),
    )


def parse_amm_deposit_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    mc = _u64le(data, o)
    o += 8
    mp = _u64le(data, o)
    o += 8
    bs = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_DEPOSIT,
        data=RaydiumAmmV4DepositEvent(
            metadata=_make_meta(meta),
            amm=amm,
            user_owner=user,
            max_coin_amount=mc,
            max_pc_amount=mp,
            base_side=bs,
        ),
    )


def parse_amm_withdraw_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    amt = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_WITHDRAW,
        data=RaydiumAmmV4WithdrawEvent(
            metadata=_make_meta(meta),
            amm=amm,
            user_owner=user,
            amount=amt,
        ),
    )


def parse_amm_withdraw_pnl_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 64:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    pnl_owner = _pub(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
        data=RaydiumAmmV4WithdrawPnlEvent(
            metadata=_make_meta(meta),
            amm=amm,
            pnl_owner=pnl_owner,
        ),
    )


def parse_amm_init2_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 1 + 8 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    nonce = _u8(data, o)
    o += 1
    ot = _u64le(data, o)
    o += 8
    ipc = _u64le(data, o)
    o += 8
    ic = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_AMM_V4_INITIALIZE2,
        data=RaydiumAmmV4Initialize2Event(
            metadata=_make_meta(meta),
            nonce=nonce,
            open_time=ot,
            init_pc_amount=ipc,
            init_coin_amount=ic,
            amm=amm,
            user_wallet=user,
        ),
    )


# --- Raydium CPMM ---


def parse_cpmm_swap_in_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 1:
        return None
    o = 0
    pool = _pub(data, o)
    o += 64
    ai = _u64le(data, o)
    o += 16
    ao = _u64le(data, o)
    o += 8
    bi = _bool(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CPMM_SWAP,
        data=RaydiumCpmmSwapEvent(
            metadata=_make_meta(meta),
            pool_id=pool,
            input_amount=ai,
            output_amount=ao,
            base_input=bi,
        ),
    )


def parse_cpmm_swap_out_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 1:
        return None
    o = 0
    pool = _pub(data, o)
    o += 64
    o += 8
    ao = _u64le(data, o)
    o += 8
    ai = _u64le(data, o)
    o += 8
    bo = _bool(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CPMM_SWAP,
        data=RaydiumCpmmSwapEvent(
            metadata=_make_meta(meta),
            pool_id=pool,
            input_amount=ai,
            output_amount=ao,
            base_input=not bo,
        ),
    )


def parse_cpmm_create_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 32 + 32 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    o += 32
    o += 32
    creator = _pub(data, o)
    o += 32
    init_amount0 = _u64le(data, o)
    o += 8
    init_amount1 = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CPMM_INITIALIZE,
        data=RaydiumCpmmInitializeEvent(
            metadata=_make_meta(meta),
            pool=pool,
            creator=creator,
            init_amount0=init_amount0,
            init_amount1=init_amount1,
        ),
    )


def parse_cpmm_deposit_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    lp = _u64le(data, o)
    o += 8
    t0 = _u64le(data, o)
    o += 8
    t1 = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CPMM_DEPOSIT,
        data=RaydiumCpmmDepositEvent(
            metadata=_make_meta(meta),
            pool=pool,
            user=user,
            lp_token_amount=lp,
            token0_amount=t0,
            token1_amount=t1,
        ),
    )


def parse_cpmm_withdraw_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    lp = _u64le(data, o)
    o += 8
    t0 = _u64le(data, o)
    o += 8
    t1 = _u64le(data, o)
    return DexEvent(
        type=EventType.RAYDIUM_CPMM_WITHDRAW,
        data=RaydiumCpmmWithdrawEvent(
            metadata=_make_meta(meta),
            pool=pool,
            user=user,
            lp_token_amount=lp,
            token0_amount=t0,
            token1_amount=t1,
        ),
    )


# --- Orca ---


def parse_orca_traded_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 1 + 16 + 16 + 8 * 6:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    atb = _bool(data, o)
    o += 1
    pre = str(_u128le_int(data, o))
    o += 16
    post = str(_u128le_int(data, o))
    o += 16
    ia = _u64le(data, o)
    o += 8
    oa = _u64le(data, o)
    o += 8
    itf = _u64le(data, o)
    o += 8
    otf = _u64le(data, o)
    o += 8
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    return DexEvent(
        type=EventType.ORCA_WHIRLPOOL_SWAP,
        data=OrcaWhirlpoolSwapEvent(
            metadata=_make_meta(meta),
            whirlpool=w,
            a_to_b=atb,
            pre_sqrt_price=pre,
            post_sqrt_price=post,
            input_amount=ia,
            output_amount=oa,
            input_transfer_fee=itf,
            output_transfer_fee=otf,
            lp_fee=lpf,
            protocol_fee=pf,
        ),
    )


def parse_orca_liq_inc_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 4 + 4 + 16 + 8 * 4:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    p = _pub(data, o)
    o += 32
    tl = _i32le(data, o)
    o += 4
    tu = _i32le(data, o)
    o += 4
    liq = str(_u128le_int(data, o))
    o += 16
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    taf = _u64le(data, o)
    o += 8
    tbf = _u64le(data, o)
    return DexEvent(
        type=EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
        data=OrcaWhirlpoolLiquidityIncreasedEvent(
            metadata=_make_meta(meta),
            whirlpool=w,
            position=p,
            tick_lower_index=tl,
            tick_upper_index=tu,
            liquidity=liq,
            token_a_amount=ta,
            token_b_amount=tb,
            token_a_transfer_fee=taf,
            token_b_transfer_fee=tbf,
        ),
    )


def parse_orca_liq_dec_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 4 + 4 + 16 + 8 * 4:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    p = _pub(data, o)
    o += 32
    tl = _i32le(data, o)
    o += 4
    tu = _i32le(data, o)
    o += 4
    liq = str(_u128le_int(data, o))
    o += 16
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    taf = _u64le(data, o)
    o += 8
    tbf = _u64le(data, o)
    return DexEvent(
        type=EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED,
        data=OrcaWhirlpoolLiquidityDecreasedEvent(
            metadata=_make_meta(meta),
            whirlpool=w,
            position=p,
            tick_lower_index=tl,
            tick_upper_index=tu,
            liquidity=liq,
            token_a_amount=ta,
            token_b_amount=tb,
            token_a_transfer_fee=taf,
            token_b_transfer_fee=tbf,
        ),
    )


def parse_orca_pool_init_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 5 + 2 + 1 + 1 + 16:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    cfg = _pub(data, o)
    o += 32
    ma = _pub(data, o)
    o += 32
    mb = _pub(data, o)
    o += 32
    ts = _u16le(data, o)
    o += 2
    tpa = _pub(data, o)
    o += 32
    tpb = _pub(data, o)
    o += 32
    da = _u8(data, o)
    o += 1
    db = _u8(data, o)
    o += 1
    isp = str(_u128le_int(data, o))
    return DexEvent(
        type=EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
        data=OrcaWhirlpoolPoolInitializedEvent(
            metadata=_make_meta(meta),
            whirlpool=w,
            whirlpools_config=cfg,
            token_mint_a=ma,
            token_mint_b=mb,
            tick_spacing=ts,
            token_program_a=tpa,
            token_program_b=tpb,
            decimals_a=da,
            decimals_b=db,
            initial_sqrt_price=isp,
        ),
    )


# --- Meteora Pools ---


def parse_meteora_swap_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 8 * 5:
        return None
    ox = [0]
    return DexEvent(
        type=EventType.METEORA_POOLS_SWAP,
        data=MeteoraPoolsSwapEvent(
            metadata=_make_meta(meta),
            in_amount=_u64_at(data, ox),
            out_amount=_u64_at(data, ox),
            trade_fee=_u64_at(data, ox),
            admin_fee=_u64_at(data, ox),
            host_fee=_u64_at(data, ox),
        ),
    )


def parse_meteora_add_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    ox = [0]
    return DexEvent(
        type=EventType.METEORA_POOLS_ADD_LIQUIDITY,
        data=MeteoraPoolsAddLiquidityEvent(
            metadata=_make_meta(meta),
            lp_mint_amount=_u64_at(data, ox),
            token_a_amount=_u64_at(data, ox),
            token_b_amount=_u64_at(data, ox),
        ),
    )


def parse_meteora_remove_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    ox = [0]
    return DexEvent(
        type=EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
        data=MeteoraPoolsRemoveLiquidityEvent(
            metadata=_make_meta(meta),
            lp_unmint_amount=_u64_at(data, ox),
            token_a_out_amount=_u64_at(data, ox),
            token_b_out_amount=_u64_at(data, ox),
        ),
    )


def parse_meteora_bootstrap_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24 + 32:
        return None
    ox = [0]
    lp = _u64_at(data, ox)
    ta = _u64_at(data, ox)
    tb = _u64_at(data, ox)
    pl = _pub(data, ox[0])
    return DexEvent(
        type=EventType.METEORA_POOLS_BOOTSTRAP_LIQUIDITY,
        data=MeteoraPoolsBootstrapLiquidityEvent(
            metadata=_make_meta(meta),
            lp_mint_amount=lp,
            token_a_amount=ta,
            token_b_amount=tb,
            pool=pl,
        ),
    )


def parse_meteora_pool_created_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4 + 1:
        return None
    o = 0
    lm = _pub(data, o)
    o += 32
    ta = _pub(data, o)
    o += 32
    tb = _pub(data, o)
    o += 32
    pt = _u8(data, o)
    o += 1
    pl = _pub(data, o)
    return DexEvent(
        type=EventType.METEORA_POOLS_POOL_CREATED,
        data=MeteoraPoolsPoolCreatedEvent(
            metadata=_make_meta(meta),
            lp_mint=lm,
            token_a_mint=ta,
            token_b_mint=tb,
            pool_type=pt,
            pool=pl,
        ),
    )


def parse_meteora_pools_set_pool_fees_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 8 + 8 + 8 + 8 + 32:
        return None
    o = 0
    tfn = _u64le(data, o)
    o += 8
    tfd = _u64le(data, o)
    o += 8
    ofn = _u64le(data, o)
    o += 8
    ofd = _u64le(data, o)
    o += 8
    pool = _pub(data, o)
    return DexEvent(
        type=EventType.METEORA_POOLS_SET_POOL_FEES,
        data=MeteoraPoolsSetPoolFeesEvent(
            metadata=_make_meta(meta),
            trade_fee_numerator=tfn,
            trade_fee_denominator=tfd,
            owner_trade_fee_numerator=ofn,
            owner_trade_fee_denominator=ofd,
            pool=pool,
        ),
    )


# --- Meteora DAMM (Swap / Swap2 only，与 Go/TS 一致) ---

DAMM_SWAP = _d(27, 60, 21, 213, 138, 170, 187, 147)
DAMM_SWAP2 = _d(189, 66, 51, 168, 38, 80, 117, 153)
DAMM_CREATE_POSITION = _d(156, 15, 119, 198, 29, 181, 221, 55)
DAMM_CLOSE_POSITION = _d(20, 145, 144, 68, 143, 142, 214, 178)
DAMM_ADD_LIQUIDITY = _d(175, 242, 8, 157, 30, 247, 185, 169)
DAMM_REMOVE_LIQUIDITY = _d(87, 46, 88, 98, 175, 96, 34, 91)
DAMM_INIT_POOL = _d(228, 50, 246, 85, 203, 66, 134, 37)
DBC_SWAP = DAMM_SWAP
DBC_INIT_POOL = DAMM_INIT_POOL
DBC_CURVE_COMPLETE = _d(229, 231, 86, 84, 156, 134, 75, 24)


def parse_meteora_damm_from_buf(buf: bytes, meta: dict) -> Optional[DexEvent]:
    if len(buf) < 8:
        return None
    d = _disc8(buf[:8])
    data = buf[8:]
    if d == DAMM_SWAP:
        return _parse_damm_swap(data, meta)
    if d == DAMM_SWAP2:
        return _parse_damm_swap2(data, meta)
    if d == DAMM_CREATE_POSITION:
        return _parse_damm_create_position(data, meta)
    if d == DAMM_CLOSE_POSITION:
        return _parse_damm_close_position(data, meta)
    if d == DAMM_ADD_LIQUIDITY:
        return _parse_damm_add_liquidity(data, meta)
    if d == DAMM_REMOVE_LIQUIDITY:
        return _parse_damm_remove_liquidity(data, meta)
    if d == DAMM_INIT_POOL:
        return _parse_damm_initialize_pool(data, meta)
    return None


def parse_meteora_dbc_from_discriminator(disc: int, data: bytes, meta: dict) -> Optional[DexEvent]:
    if disc == DBC_SWAP:
        return _parse_dbc_swap(data, meta)
    if disc == DBC_INIT_POOL:
        return _parse_dbc_initialize_pool(data, meta)
    if disc == DBC_CURVE_COMPLETE:
        return _parse_dbc_curve_complete(data, meta)
    return None


def _parse_dbc_swap(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 2 + 2 + 8 * 9 + 16:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    config = _pub(data, o)
    o += 32
    td = _u8(data, o)
    o += 1
    has_referral = _bool(data, o)
    o += 1
    params_amount_in = _u64le(data, o)
    o += 8
    minimum_amount_out = _u64le(data, o)
    o += 8
    actual_input_amount = _u64le(data, o)
    o += 8
    output_amount = _u64le(data, o)
    o += 8
    next_sqrt_price = _u128le_int(data, o)
    o += 16
    trading_fee = _u64le(data, o)
    o += 8
    protocol_fee = _u64le(data, o)
    o += 8
    referral_fee = _u64le(data, o)
    o += 8
    amount_in = _u64le(data, o) if o + 8 <= len(data) else params_amount_in
    o += 8
    current_timestamp = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DBC_SWAP,
        data=MeteoraDbcSwapEvent(
            metadata=_make_meta(meta),
            pool=pool,
            config=config,
            trade_direction=td,
            has_referral=has_referral,
            amount_in=amount_in,
            minimum_amount_out=minimum_amount_out,
            actual_input_amount=actual_input_amount,
            output_amount=output_amount,
            next_sqrt_price=next_sqrt_price,
            trading_fee=trading_fee,
            protocol_fee=protocol_fee,
            referral_fee=referral_fee,
            current_timestamp=current_timestamp,
        ),
    )


def _parse_dbc_initialize_pool(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4 + 1 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    config = _pub(data, o)
    o += 32
    creator = _pub(data, o)
    o += 32
    base_mint = _pub(data, o)
    o += 32
    pool_type = _u8(data, o)
    o += 1
    activation_point = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DBC_INITIALIZE_POOL,
        data=MeteoraDbcInitializePoolEvent(
            metadata=_make_meta(meta),
            pool=pool,
            config=config,
            creator=creator,
            base_mint=base_mint,
            pool_type=pool_type,
            activation_point=activation_point,
        ),
    )


def _parse_dbc_curve_complete(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 2 + 8 * 2:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    config = _pub(data, o)
    o += 32
    base_reserve = _u64le(data, o)
    o += 8
    quote_reserve = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DBC_CURVE_COMPLETE,
        data=MeteoraDbcCurveCompleteEvent(
            metadata=_make_meta(meta),
            pool=pool,
            config=config,
            base_reserve=base_reserve,
            quote_reserve=quote_reserve,
        ),
    )


def _parse_damm_swap(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 1 + 1 + 8 * 8 + 16 + 8 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32 + 32
    td = _u8(data, o)
    o += 1
    hr = _bool(data, o)
    o += 1
    ai = _u64le(data, o)
    o += 8
    mo = _u64le(data, o)
    o += 8
    aai = _u64le(data, o)
    o += 8
    oa = _u64le(data, o)
    o += 8
    nsp = str(_u128le_int(data, o))
    o += 16
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    o += 8
    rf = _u64le(data, o)
    o += 8
    o += 8
    ct = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_SWAP,
        data=MeteoraDammV2SwapEvent(
            metadata=_make_meta(meta),
            pool=pool,
            trade_direction=td,
            has_referral=hr,
            amount_in=ai,
            minimum_amount_out=mo,
            output_amount=oa,
            next_sqrt_price=nsp,
            lp_fee=lpf,
            protocol_fee=pf,
            partner_fee=0,
            referral_fee=rf,
            actual_amount_in=aai,
            current_timestamp=ct,
            token_a_vault=Z,
            token_b_vault=Z,
            token_a_mint=Z,
            token_b_mint=Z,
            token_a_program=Z,
            token_b_program=Z,
        ),
    )


def _parse_damm_swap2(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 1 + 1 + 1 + 8 * 2 + 1 + 8 * 6 + 16 + 8 * 4 + 8 * 3:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    td = _u8(data, o)
    o += 1
    o += 1
    hr = _bool(data, o)
    o += 1
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    o += 8
    sm = _u8(data, o)
    o += 1
    ifi = _u64le(data, o)
    o += 8
    o += 16
    oa = _u64le(data, o)
    o += 8
    nsp = str(_u128le_int(data, o))
    o += 16
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    o += 8
    rf = _u64le(data, o)
    o += 8
    o += 8
    o += 8
    ct = _u64le(data, o)
    ai, mo = (a0, a1) if sm == 0 else (a1, a0)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_SWAP,
        data=MeteoraDammV2SwapEvent(
            metadata=_make_meta(meta),
            pool=pool,
            trade_direction=td,
            has_referral=hr,
            amount_in=ai,
            minimum_amount_out=mo,
            output_amount=oa,
            next_sqrt_price=nsp,
            lp_fee=lpf,
            protocol_fee=pf,
            partner_fee=0,
            referral_fee=rf,
            actual_amount_in=ifi,
            current_timestamp=ct,
            token_a_vault=Z,
            token_b_vault=Z,
            token_a_mint=Z,
            token_b_mint=Z,
            token_a_program=Z,
            token_b_program=Z,
        ),
    )


def _parse_damm_create_position(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    nft = _pub(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_CREATE_POSITION,
        data=MeteoraDammV2CreatePositionEvent(
            metadata=_make_meta(meta),
            pool=pool,
            owner=owner,
            position=position,
            position_nft_mint=nft,
        ),
    )


def _parse_damm_close_position(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    nft = _pub(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        data=MeteoraDammV2ClosePositionEvent(
            metadata=_make_meta(meta),
            pool=pool,
            owner=owner,
            position=position,
            position_nft_mint=nft,
        ),
    )


def _parse_damm_add_liquidity(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 3 + 16 + 8 * 6:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    ld = str(_u128le_int(data, o))
    o += 16
    tat = _u64le(data, o)
    o += 8
    tbt = _u64le(data, o)
    o += 8
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    tota = _u64le(data, o)
    o += 8
    totb = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        data=MeteoraDammV2AddLiquidityEvent(
            metadata=_make_meta(meta),
            pool=pool,
            position=position,
            owner=owner,
            liquidity_delta=ld,
            token_a_amount_threshold=tat,
            token_b_amount_threshold=tbt,
            token_a_amount=ta,
            token_b_amount=tb,
            total_amount_a=tota,
            total_amount_b=totb,
        ),
    )


def _parse_damm_dynamic_fee(data: bytes, o: int) -> Optional[tuple[dict, int]]:
    if o + 32 > len(data):
        return None
    bs = _u16le(data, o)
    o += 2
    bu = _u128le_int(data, o)
    o += 16
    fp = _u16le(data, o)
    o += 2
    dp = _u16le(data, o)
    o += 2
    rf = _u16le(data, o)
    o += 2
    mva = _u32le(data, o)
    o += 4
    vfc = _u32le(data, o)
    o += 4
    return (
        {
            "bin_step": bs,
            "bin_step_u128": str(bu),
            "filter_period": fp,
            "decay_period": dp,
            "reduction_factor": rf,
            "max_volatility_accumulator": mva,
            "variable_fee_control": vfc,
        },
        o,
    )


def _parse_damm_pool_fees(data: bytes, start: int) -> Optional[tuple[dict, int]]:
    if start + 30 > len(data):
        return None
    o = start
    base_hex = data[o : o + 27].hex()
    o += 27
    cfb = _u16le(data, o)
    o += 2
    pad = _u8(data, o)
    o += 1
    tag = _u8(data, o)
    o += 1
    dyn = None
    if tag == 1:
        inner = _parse_damm_dynamic_fee(data, o)
        if not inner:
            return None
        dyn, o = inner
    elif tag != 0:
        return None
    return (
        {
            "base_fee_data": base_hex,
            "compounding_fee_bps": cfb,
            "padding": pad,
            "dynamic_fee": dyn,
        },
        o,
    )


def _parse_damm_initialize_pool(data: bytes, meta: dict) -> Optional[DexEvent]:
    min_after_pub = 31 + 109
    if len(data) < 32 * 6 + min_after_pub:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    tam = _pub(data, o)
    o += 32
    tbm = _pub(data, o)
    o += 32
    creator = _pub(data, o)
    o += 32
    payer = _pub(data, o)
    o += 32
    av = _pub(data, o)
    o += 32
    pfp = _parse_damm_pool_fees(data, o)
    if not pfp:
        return None
    fees, o = pfp
    if o + 109 > len(data):
        return None
    smin = str(_u128le_int(data, o))
    o += 16
    smax = str(_u128le_int(data, o))
    o += 16
    act = _u8(data, o)
    o += 1
    cfm = _u8(data, o)
    o += 1
    liq = str(_u128le_int(data, o))
    o += 16
    sqrt_p = str(_u128le_int(data, o))
    o += 16
    ap = _u64le(data, o)
    o += 8
    taf = _u8(data, o)
    o += 1
    tbf = _u8(data, o)
    o += 1
    tau = _u64le(data, o)
    o += 8
    tbu = _u64le(data, o)
    o += 8
    tota = _u64le(data, o)
    o += 8
    totb = _u64le(data, o)
    o += 8
    pt = _u8(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
        data=MeteoraDammV2InitializePoolEvent(
            metadata=_make_meta(meta),
            pool=pool,
            token_a_mint=tam,
            token_b_mint=tbm,
            creator=creator,
            payer=payer,
            alpha_vault=av,
            pool_fees=fees,
            sqrt_min_price=smin,
            sqrt_max_price=smax,
            activation_type=act,
            collect_fee_mode=cfm,
            liquidity=liq,
            sqrt_price=sqrt_p,
            activation_point=ap,
            token_a_flag=taf,
            token_b_flag=tbf,
            token_a_amount=tau,
            token_b_amount=tbu,
            total_amount_a=tota,
            total_amount_b=totb,
            pool_type=pt,
        ),
    )


def _parse_damm_remove_liquidity(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 3 + 16 + 8 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    ld = str(_u128le_int(data, o))
    o += 16
    tat = _u64le(data, o)
    o += 8
    tbt = _u64le(data, o)
    o += 8
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    return DexEvent(
        type=EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
        data=MeteoraDammV2RemoveLiquidityEvent(
            metadata=_make_meta(meta),
            pool=pool,
            position=position,
            owner=owner,
            liquidity_delta=ld,
            token_a_amount_threshold=tat,
            token_b_amount_threshold=tbt,
            token_a_amount=ta,
            token_b_amount=tb,
        ),
    )


# --- RaydiumLaunchlab ---

DISC_RAYDIUM_LAUNCHLAB_TRADE = _d(189, 219, 127, 211, 78, 230, 97, 238)
DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE = _d(151, 215, 226, 9, 118, 161, 115, 174)


def parse_raydium_launchlab_from_discriminator(disc: int, data: bytes, meta: dict) -> Optional[DexEvent]:
    if disc == DISC_RAYDIUM_LAUNCHLAB_TRADE:
        return _parse_raydium_launchlab_trade(data, meta)
    if disc == DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE:
        return _parse_raydium_launchlab_pool_create(data, meta)
    return None


def _parse_raydium_launchlab_trade(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 139:
        return None
    pool = _pub(data, 0)
    ai = _u64le(data, 88)
    ao = _u64le(data, 96)
    is_buy = _u8(data, 136) == 0
    ex_in = _bool(data, 138)
    d = "Buy" if is_buy else "Sell"
    return DexEvent(
        type=EventType.RAYDIUM_LAUNCHLAB_TRADE,
        data=RaydiumLaunchlabTradeEvent(
            metadata=_make_meta(meta),
            pool_state=pool,
            user=Z,
            amount_in=ai,
            amount_out=ao,
            is_buy=is_buy,
            trade_direction=d,
            exact_in=ex_in,
        ),
    )


def _parse_raydium_launchlab_pool_create(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 97:
        return None
    pool = _pub(data, 0)
    creator = _pub(data, 32)
    o = 96
    decimals = _u8(data, o)
    o += 1
    try:
        name, o = _borsh_str(data, o)
        symbol, o = _borsh_str(data, o)
        uri, o = _borsh_str(data, o)
    except (struct.error, UnicodeDecodeError):
        return None
    return DexEvent(
        type=EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE,
        data=RaydiumLaunchlabPoolCreateEvent(
            metadata=_make_meta(meta),
            base_mint_param={"symbol": symbol, "name": name, "uri": uri, "decimals": decimals},
            pool_state=pool,
            creator=creator,
        ),
    )


# --- PumpSwap ---


def parse_ps_buy_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    min_len = 16 * 8 + 7 * 32 + 1 + 5 * 8 + 4
    if len(data) < min_len:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    ts = ri()
    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ts,
        "base_amount_out": rd(),
        "max_quote_amount_in": rd(),
        "user_base_token_reserves": rd(),
        "user_quote_token_reserves": rd(),
        "pool_base_token_reserves": rd(),
        "pool_quote_token_reserves": rd(),
        "quote_amount_in": rd(),
        "lp_fee_basis_points": rd(),
        "lp_fee": rd(),
        "protocol_fee_basis_points": rd(),
        "protocol_fee": rd(),
        "quote_amount_in_with_lp_fee": rd(),
        "user_quote_amount_in": rd(),
        "pool": rp(),
        "user": rp(),
        "user_base_token_account": rp(),
        "user_quote_token_account": rp(),
        "protocol_fee_recipient": rp(),
        "protocol_fee_recipient_token_account": rp(),
        "coin_creator": rp(),
        "coin_creator_fee_basis_points": rd(),
        "coin_creator_fee": rd(),
    }
    tv = _bool(data, o)
    o += 1
    ev["track_volume"] = tv
    ev["total_unclaimed_tokens"] = rd()
    ev["total_claimed_tokens"] = rd()
    ev["current_sol_volume"] = rd()
    ev["last_update_timestamp"] = ri()
    ev["min_base_amount_out"] = rd()
    ix = ""
    if o + 4 <= len(data):
        ln = _u32le(data, o)
        o += 4
        if o + ln <= len(data):
            ix = data[o : o + ln].decode("utf-8", errors="replace")
    ev["ix_name"] = ix
    # Mayhem mode and cashback fields
    mm = False
    if o < len(data):
        mm = _bool(data, o)
        o += 1
    cb_bps = 0
    cb = 0
    if o + 16 <= len(data):
        cb_bps = _u64le(data, o)
        o += 8
        cb = _u64le(data, o)
    ev["mayhem_mode"] = mm
    ev["cashback_fee_basis_points"] = cb_bps
    ev["cashback"] = cb
    ev["is_cashback_coin"] = cb_bps > 0
    md = ev.pop("metadata", meta)
    return DexEvent(
        type=EventType.PUMP_SWAP_BUY,
        data=PumpSwapBuyEvent(metadata=_make_meta(md), **ev),
    )


def parse_ps_sell_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    req = 13 * 8 + 7 * 32
    if len(data) < req:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ri(),
        "base_amount_in": rd(),
        "min_quote_amount_out": rd(),
        "user_base_token_reserves": rd(),
        "user_quote_token_reserves": rd(),
        "pool_base_token_reserves": rd(),
        "pool_quote_token_reserves": rd(),
        "quote_amount_out": rd(),
        "lp_fee_basis_points": rd(),
        "lp_fee": rd(),
        "protocol_fee_basis_points": rd(),
        "protocol_fee": rd(),
        "quote_amount_out_without_lp_fee": rd(),
        "user_quote_amount_out": rd(),
        "pool": rp(),
        "user": rp(),
        "user_base_token_account": rp(),
        "user_quote_token_account": rp(),
        "protocol_fee_recipient": rp(),
        "protocol_fee_recipient_token_account": rp(),
        "coin_creator": rp(),
        "coin_creator_fee_basis_points": rd(),
        "coin_creator_fee": rd(),
    }
    cash_bps, cash = 0, 0
    if len(data) >= 368:
        cash_bps = _u64le(data, 352)
        cash = _u64le(data, 360)
    ev["cashback_fee_basis_points"] = cash_bps
    ev["cashback"] = cash
    md = ev.pop("metadata", meta)
    return DexEvent(
        type=EventType.PUMP_SWAP_SELL,
        data=PumpSwapSellEvent(metadata=_make_meta(md), **ev),
    )


def parse_ps_create_pool_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    req = 8 + 2 + 32 * 6 + 2 + 8 * 7 + 1
    if len(data) < req:
        return None
    o = 0
    ts = _i64le(data, o)
    o += 8
    idx = _u16le(data, o)
    o += 2
    creator = _pub(data, o)
    o += 32
    bm = _pub(data, o)
    o += 32
    qm = _pub(data, o)
    o += 32
    bd = _u8(data, o)
    o += 1
    qd = _u8(data, o)
    o += 1

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ts,
        "index": idx,
        "creator": creator,
        "base_mint": bm,
        "quote_mint": qm,
        "base_mint_decimals": bd,
        "quote_mint_decimals": qd,
        "base_amount_in": rd(),
        "quote_amount_in": rd(),
        "pool_base_amount": rd(),
        "pool_quote_amount": rd(),
        "minimum_liquidity": rd(),
        "initial_liquidity": rd(),
        "lp_token_amount_out": rd(),
    }
    pb = _u8(data, o)
    o += 1
    pool = _pub(data, o)
    o += 32
    lp = _pub(data, o)
    o += 32
    uba = _pub(data, o)
    o += 32
    uqa = _pub(data, o)
    o += 32
    cc = _pub(data, o)
    ev["pool_bump"] = pb
    ev["pool"] = pool
    ev["lp_mint"] = lp
    ev["user_base_token_account"] = uba
    ev["user_quote_token_account"] = uqa
    ev["coin_creator"] = cc
    ev["is_mayhem_mode"] = len(data) > 325 and _bool(data, 325)
    md = ev.pop("metadata", meta)
    return DexEvent(
        type=EventType.PUMP_SWAP_CREATE_POOL,
        data=PumpSwapCreatePoolEvent(metadata=_make_meta(md), **ev),
    )


def parse_ps_add_liq_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 10 * 8 + 5 * 32:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    return DexEvent(
        type=EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        data=PumpSwapLiquidityAddedEvent(
            metadata=_make_meta(meta),
            timestamp=ri(),
            lp_token_amount_out=rd(),
            max_base_amount_in=rd(),
            max_quote_amount_in=rd(),
            user_base_token_reserves=rd(),
            user_quote_token_reserves=rd(),
            pool_base_token_reserves=rd(),
            pool_quote_token_reserves=rd(),
            base_amount_in=rd(),
            quote_amount_in=rd(),
            lp_mint_supply=rd(),
            pool=rp(),
            user=rp(),
            user_base_token_account=rp(),
            user_quote_token_account=rp(),
            user_pool_token_account=rp(),
        ),
    )


def parse_ps_remove_liq_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 10 * 8 + 5 * 32:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    return DexEvent(
        type=EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
        data=PumpSwapLiquidityRemovedEvent(
            metadata=_make_meta(meta),
            timestamp=ri(),
            lp_token_amount_in=rd(),
            min_base_amount_out=rd(),
            min_quote_amount_out=rd(),
            user_base_token_reserves=rd(),
            user_quote_token_reserves=rd(),
            pool_base_token_reserves=rd(),
            pool_quote_token_reserves=rd(),
            base_amount_out=rd(),
            quote_amount_out=rd(),
            lp_mint_supply=rd(),
            pool=rp(),
            user=rp(),
            user_base_token_account=rp(),
            user_quote_token_account=rp(),
            user_pool_token_account=rp(),
        ),
    )


# --- Meteora DLMM ---

DLMM_SWAP = _d(143, 190, 90, 218, 196, 30, 51, 222)
DLMM_ADD_LIQ = _d(181, 157, 89, 67, 143, 182, 52, 72)
DLMM_REMOVE_LIQ = _d(80, 85, 209, 72, 24, 206, 35, 178)
DLMM_INIT_POOL = _d(95, 180, 10, 172, 84, 174, 232, 40)
DLMM_INIT_BIN = _d(11, 18, 155, 194, 33, 115, 238, 119)
DLMM_CREATE_POS = _d(123, 233, 11, 43, 146, 180, 97, 119)
DLMM_CLOSE_POS = _d(94, 168, 102, 45, 59, 122, 137, 54)
DLMM_CLAIM_FEE = _d(152, 70, 208, 111, 104, 91, 44, 1)


def parse_dlmm_from_program_data(buf: bytes, meta: dict) -> Optional[DexEvent]:
    if len(buf) < 8:
        return None
    d = _disc8(buf[:8])
    data = buf[8:]
    if d == DLMM_SWAP:
        if len(data) < 32 + 32 + 4 + 4 + 8 + 8 + 1 + 8 + 8 + 16 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        sb = _i32le(data, o)
        o += 4
        eb = _i32le(data, o)
        o += 4
        ai = _u64le(data, o)
        o += 8
        ao = _u64le(data, o)
        o += 8
        sy = _bool(data, o)
        o += 1
        fee = _u64le(data, o)
        o += 8
        pf = _u64le(data, o)
        o += 8
        fbps = str(_u128le_int(data, o))
        o += 16
        hf = _u64le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_SWAP,
            data=MeteoraDlmmSwapEvent(
                metadata=_make_meta(meta),
                pool=pool,
                from_addr=frm,
                start_bin_id=sb,
                end_bin_id=eb,
                amount_in=ai,
                amount_out=ao,
                swap_for_y=sy,
                fee=fee,
                protocol_fee=pf,
                fee_bps=fbps,
                host_fee=hf,
            ),
        )
    if d == DLMM_ADD_LIQ:
        if len(data) < 32 + 32 + 32 + 8 + 8 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        a0 = _u64le(data, o)
        o += 8
        a1 = _u64le(data, o)
        o += 8
        ab = _i32le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_ADD_LIQUIDITY,
            data=MeteoraDlmmAddLiquidityEvent(
                metadata=_make_meta(meta),
                pool=pool,
                from_addr=frm,
                position=pos,
                amounts=[a0, a1],
                active_bin_id=ab,
            ),
        )
    if d == DLMM_REMOVE_LIQ:
        if len(data) < 32 + 32 + 32 + 8 + 8 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        a0 = _u64le(data, o)
        o += 8
        a1 = _u64le(data, o)
        o += 8
        ab = _i32le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
            data=MeteoraDlmmRemoveLiquidityEvent(
                metadata=_make_meta(meta),
                pool=pool,
                from_addr=frm,
                position=pos,
                amounts=[a0, a1],
                active_bin_id=ab,
            ),
        )
    if d == DLMM_INIT_POOL:
        if len(data) < 32 + 32 + 4 + 2:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        creator = _pub(data, o)
        o += 32
        ab = _i32le(data, o)
        o += 4
        bs = _u16le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_INITIALIZE_POOL,
            data=MeteoraDlmmInitializePoolEvent(
                metadata=_make_meta(meta),
                pool=pool,
                creator=creator,
                active_bin_id=ab,
                bin_step=bs,
            ),
        )
    if d == DLMM_INIT_BIN:
        if len(data) < 32 + 32 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        ba = _pub(data, o)
        o += 32
        idx = _u64le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
            data=MeteoraDlmmInitializeBinArrayEvent(
                metadata=_make_meta(meta),
                pool=pool,
                bin_array=ba,
                index=int(idx),
            ),
        )
    if d == DLMM_CREATE_POS:
        if len(data) < 32 + 32 + 32 + 4 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        o += 32
        lb = _i32le(data, o)
        o += 4
        w = _u32le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_CREATE_POSITION,
            data=MeteoraDlmmCreatePositionEvent(
                metadata=_make_meta(meta),
                pool=pool,
                position=pos,
                owner=owner,
                lower_bin_id=lb,
                width=w,
            ),
        )
    if d == DLMM_CLOSE_POS:
        if len(data) < 32 + 32 + 32:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_CLOSE_POSITION,
            data=MeteoraDlmmClosePositionEvent(
                metadata=_make_meta(meta),
                pool=pool,
                position=pos,
                owner=owner,
            ),
        )
    if d == DLMM_CLAIM_FEE:
        if len(data) < 32 + 32 + 32 + 8 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        o += 32
        fx = _u64le(data, o)
        o += 8
        fy = _u64le(data, o)
        return DexEvent(
            type=EventType.METEORA_DLMM_CLAIM_FEE,
            data=MeteoraDlmmClaimFeeEvent(
                metadata=_make_meta(meta),
                pool=pool,
                position=pos,
                owner=owner,
                fee_x=fx,
                fee_y=fy,
            ),
        )
    return None


# --- 日志过滤（与优化 matcher 的 early-filter / actual-type filter 对齐） ---

_LOG_DISCRIMINATOR_EVENT_TYPES = {
    PUMP_CREATE: EventType.PUMP_FUN_CREATE,
    PUMP_TRADE: EventType.PUMP_FUN_TRADE,
    PUMP_MIGRATE: EventType.PUMP_FUN_MIGRATE,
    PUMP_MIGRATE_BONDING_CURVE_CREATOR: EventType.PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR,
    PUMP_FEES_CREATE_FEE_SHARING_CONFIG: EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
    PUMP_FEES_INITIALIZE_FEE_CONFIG: EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
    PUMP_FEES_RESET_FEE_SHARING_CONFIG: EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
    PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY: EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
    PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY: EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
    PUMP_FEES_UPDATE_ADMIN: EventType.PUMP_FEES_UPDATE_ADMIN,
    PUMP_FEES_UPDATE_FEE_CONFIG: EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
    PUMP_FEES_UPDATE_FEE_SHARES: EventType.PUMP_FEES_UPDATE_FEE_SHARES,
    PUMP_FEES_UPSERT_FEE_TIERS: EventType.PUMP_FEES_UPSERT_FEE_TIERS,
    _d(103, 244, 82, 31, 44, 245, 119, 119): EventType.PUMP_SWAP_BUY,
    _d(62, 47, 55, 10, 165, 3, 220, 42): EventType.PUMP_SWAP_SELL,
    _d(177, 49, 12, 210, 160, 118, 167, 116): EventType.PUMP_SWAP_CREATE_POOL,
    _d(120, 248, 61, 83, 31, 142, 107, 144): EventType.PUMP_SWAP_LIQUIDITY_ADDED,
    _d(22, 9, 133, 26, 160, 44, 71, 192): EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
    _d(64, 198, 205, 232, 38, 8, 113, 226): EventType.RAYDIUM_CLMM_SWAP,
    _d(49, 79, 105, 212, 32, 34, 30, 84): EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
    _d(58, 222, 86, 58, 68, 50, 85, 56): EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
    _d(126, 240, 175, 206, 158, 88, 153, 107): EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE,
    _d(247, 189, 7, 119, 106, 112, 95, 151): EventType.RAYDIUM_CLMM_CONFIG_CHANGE,
    _d(100, 30, 87, 249, 196, 223, 154, 206): EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION,
    _d(237, 112, 148, 230, 57, 84, 180, 162): EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE,
    _d(106, 24, 71, 85, 57, 169, 158, 216): EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER,
    _d(11, 120, 13, 204, 199, 87, 19, 200): EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER,
    _d(70, 48, 40, 221, 219, 237, 212, 163): EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER,
    _d(88, 119, 77, 164, 125, 124, 10, 194): EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER,
    _d(109, 127, 186, 78, 114, 65, 37, 236): EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS,
    _d(25, 94, 75, 47, 112, 99, 53, 63): EventType.RAYDIUM_CLMM_CREATE_POOL,
    _d(166, 174, 105, 192, 81, 161, 83, 105): EventType.RAYDIUM_CLMM_COLLECT_FEE,
    _d(206, 87, 17, 79, 45, 41, 213, 61): EventType.RAYDIUM_CLMM_COLLECT_FEE,
    _d(143, 190, 90, 218, 196, 30, 51, 222): EventType.RAYDIUM_CPMM_SWAP,
    _d(55, 217, 98, 86, 163, 74, 180, 173): EventType.RAYDIUM_CPMM_SWAP,
    _d(233, 146, 209, 142, 207, 104, 64, 188): EventType.RAYDIUM_CPMM_INITIALIZE,
    _d(242, 35, 198, 137, 82, 225, 242, 182): EventType.RAYDIUM_CPMM_DEPOSIT,
    _d(183, 18, 70, 156, 148, 109, 161, 34): EventType.RAYDIUM_CPMM_WITHDRAW,
    _d(0, 0, 0, 0, 0, 0, 0, 9): EventType.RAYDIUM_AMM_V4_SWAP,
    _d(0, 0, 0, 0, 0, 0, 0, 11): EventType.RAYDIUM_AMM_V4_SWAP,
    _d(0, 0, 0, 0, 0, 0, 0, 3): EventType.RAYDIUM_AMM_V4_DEPOSIT,
    _d(0, 0, 0, 0, 0, 0, 0, 4): EventType.RAYDIUM_AMM_V4_WITHDRAW,
    _d(0, 0, 0, 0, 0, 0, 0, 7): EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
    _d(0, 0, 0, 0, 0, 0, 0, 1): EventType.RAYDIUM_AMM_V4_INITIALIZE2,
    _d(225, 202, 73, 175, 147, 43, 160, 150): EventType.ORCA_WHIRLPOOL_SWAP,
    _d(30, 7, 144, 181, 102, 254, 155, 161): EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
    _d(166, 1, 36, 71, 112, 202, 181, 171): EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED,
    _d(100, 118, 173, 87, 12, 198, 254, 229): EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
    _d(81, 108, 227, 190, 205, 208, 10, 196): EventType.METEORA_POOLS_SWAP,
    _d(31, 94, 125, 90, 227, 52, 61, 186): EventType.METEORA_POOLS_ADD_LIQUIDITY,
    _d(116, 244, 97, 232, 103, 31, 152, 58): EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
    _d(121, 127, 38, 136, 92, 55, 14, 247): EventType.METEORA_POOLS_BOOTSTRAP_LIQUIDITY,
    _d(202, 44, 41, 88, 104, 220, 157, 82): EventType.METEORA_POOLS_POOL_CREATED,
    _d(245, 26, 198, 164, 88, 18, 75, 9): EventType.METEORA_POOLS_SET_POOL_FEES,
    DAMM_SWAP: EventType.METEORA_DAMM_V2_SWAP,
    DAMM_SWAP2: EventType.METEORA_DAMM_V2_SWAP,
    _d(175, 242, 8, 157, 30, 247, 185, 169): EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
    _d(87, 46, 88, 98, 175, 96, 34, 91): EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
    _d(228, 50, 246, 85, 203, 66, 134, 37): EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
    _d(156, 15, 119, 198, 29, 181, 221, 55): EventType.METEORA_DAMM_V2_CREATE_POSITION,
    _d(20, 145, 144, 68, 143, 142, 214, 178): EventType.METEORA_DAMM_V2_CLOSE_POSITION,
    DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE: EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE,
    DLMM_ADD_LIQ: EventType.METEORA_DLMM_ADD_LIQUIDITY,
    DLMM_REMOVE_LIQ: EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
    DLMM_INIT_POOL: EventType.METEORA_DLMM_INITIALIZE_POOL,
    DLMM_INIT_BIN: EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
    DLMM_CREATE_POS: EventType.METEORA_DLMM_CREATE_POSITION,
    DLMM_CLOSE_POS: EventType.METEORA_DLMM_CLOSE_POSITION,
    DLMM_CLAIM_FEE: EventType.METEORA_DLMM_CLAIM_FEE,
}


def event_type_for_discriminator(disc: int) -> Optional[EventType]:
    return _LOG_DISCRIMINATOR_EVENT_TYPES.get(disc)


RAYDIUM_LAUNCHLAB_PROGRAM_ID = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_FEES_PROGRAM_ID = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
RAYDIUM_CPMM_PROGRAM_ID = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
RAYDIUM_AMM_V4_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_WHIRLPOOL_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
METEORA_POOLS_PROGRAM_ID = "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"
METEORA_DAMM_V2_PROGRAM_ID = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
METEORA_DBC_PROGRAM_ID = "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"
METEORA_DLMM_PROGRAM_ID = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"


def event_type_for_program_discriminator(program_id: Optional[str], disc: int) -> Optional[EventType]:
    if program_id == PUMPFUN_PROGRAM_ID:
        if disc == PUMP_CREATE:
            return EventType.PUMP_FUN_CREATE
        if disc == PUMP_TRADE:
            return EventType.PUMP_FUN_TRADE
        if disc == PUMP_MIGRATE:
            return EventType.PUMP_FUN_MIGRATE
        if disc == PUMP_MIGRATE_BONDING_CURVE_CREATOR:
            return EventType.PUMP_FUN_MIGRATE_BONDING_CURVE_CREATOR
        return None
    if program_id == PUMP_FEES_PROGRAM_ID:
        mapping = {
            PUMP_FEES_CREATE_FEE_SHARING_CONFIG: EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
            PUMP_FEES_INITIALIZE_FEE_CONFIG: EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
            PUMP_FEES_RESET_FEE_SHARING_CONFIG: EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
            PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY: EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
            PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY: EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
            PUMP_FEES_UPDATE_ADMIN: EventType.PUMP_FEES_UPDATE_ADMIN,
            PUMP_FEES_UPDATE_FEE_CONFIG: EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
            PUMP_FEES_UPDATE_FEE_SHARES: EventType.PUMP_FEES_UPDATE_FEE_SHARES,
            PUMP_FEES_UPSERT_FEE_TIERS: EventType.PUMP_FEES_UPSERT_FEE_TIERS,
        }
        return mapping.get(disc)
    if program_id == PUMPSWAP_PROGRAM_ID:
        mapping = {
            _d(103, 244, 82, 31, 44, 245, 119, 119): EventType.PUMP_SWAP_BUY,
            _d(62, 47, 55, 10, 165, 3, 220, 42): EventType.PUMP_SWAP_SELL,
            _d(177, 49, 12, 210, 160, 118, 167, 116): EventType.PUMP_SWAP_CREATE_POOL,
            _d(120, 248, 61, 83, 31, 142, 107, 144): EventType.PUMP_SWAP_LIQUIDITY_ADDED,
            _d(22, 9, 133, 26, 160, 44, 71, 192): EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
        }
        return mapping.get(disc)
    if program_id == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
        if disc == DISC_RAYDIUM_LAUNCHLAB_TRADE:
            return EventType.RAYDIUM_LAUNCHLAB_TRADE
        if disc == DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE:
            return EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE
        return None
    if program_id == RAYDIUM_CLMM_PROGRAM_ID:
        mapping = {
            _d(64, 198, 205, 232, 38, 8, 113, 226): EventType.RAYDIUM_CLMM_SWAP,
            _d(49, 79, 105, 212, 32, 34, 30, 84): EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
            _d(58, 222, 86, 58, 68, 50, 85, 56): EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY,
            _d(126, 240, 175, 206, 158, 88, 153, 107): EventType.RAYDIUM_CLMM_LIQUIDITY_CHANGE,
            _d(247, 189, 7, 119, 106, 112, 95, 151): EventType.RAYDIUM_CLMM_CONFIG_CHANGE,
            _d(100, 30, 87, 249, 196, 223, 154, 206): EventType.RAYDIUM_CLMM_CREATE_PERSONAL_POSITION,
            _d(237, 112, 148, 230, 57, 84, 180, 162): EventType.RAYDIUM_CLMM_LIQUIDITY_CALCULATE,
            _d(106, 24, 71, 85, 57, 169, 158, 216): EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER,
            _d(11, 120, 13, 204, 199, 87, 19, 200): EventType.RAYDIUM_CLMM_INCREASE_LIMIT_ORDER,
            _d(70, 48, 40, 221, 219, 237, 212, 163): EventType.RAYDIUM_CLMM_DECREASE_LIMIT_ORDER,
            _d(88, 119, 77, 164, 125, 124, 10, 194): EventType.RAYDIUM_CLMM_SETTLE_LIMIT_ORDER,
            _d(109, 127, 186, 78, 114, 65, 37, 236): EventType.RAYDIUM_CLMM_UPDATE_REWARD_INFOS,
            _d(25, 94, 75, 47, 112, 99, 53, 63): EventType.RAYDIUM_CLMM_CREATE_POOL,
            _d(166, 174, 105, 192, 81, 161, 83, 105): EventType.RAYDIUM_CLMM_COLLECT_FEE,
            _d(206, 87, 17, 79, 45, 41, 213, 61): EventType.RAYDIUM_CLMM_COLLECT_FEE,
        }
        return mapping.get(disc)
    if program_id == RAYDIUM_CPMM_PROGRAM_ID:
        mapping = {
            _d(143, 190, 90, 218, 196, 30, 51, 222): EventType.RAYDIUM_CPMM_SWAP,
            _d(55, 217, 98, 86, 163, 74, 180, 173): EventType.RAYDIUM_CPMM_SWAP,
            _d(233, 146, 209, 142, 207, 104, 64, 188): EventType.RAYDIUM_CPMM_INITIALIZE,
            _d(242, 35, 198, 137, 82, 225, 242, 182): EventType.RAYDIUM_CPMM_DEPOSIT,
            _d(183, 18, 70, 156, 148, 109, 161, 34): EventType.RAYDIUM_CPMM_WITHDRAW,
        }
        return mapping.get(disc)
    if program_id == RAYDIUM_AMM_V4_PROGRAM_ID:
        mapping = {
            _d(0, 0, 0, 0, 0, 0, 0, 9): EventType.RAYDIUM_AMM_V4_SWAP,
            _d(0, 0, 0, 0, 0, 0, 0, 11): EventType.RAYDIUM_AMM_V4_SWAP,
            _d(0, 0, 0, 0, 0, 0, 0, 3): EventType.RAYDIUM_AMM_V4_DEPOSIT,
            _d(0, 0, 0, 0, 0, 0, 0, 4): EventType.RAYDIUM_AMM_V4_WITHDRAW,
            _d(0, 0, 0, 0, 0, 0, 0, 1): EventType.RAYDIUM_AMM_V4_INITIALIZE2,
            _d(0, 0, 0, 0, 0, 0, 0, 7): EventType.RAYDIUM_AMM_V4_WITHDRAW_PNL,
        }
        return mapping.get(disc)
    if program_id == ORCA_WHIRLPOOL_PROGRAM_ID:
        mapping = {
            _d(225, 202, 73, 175, 147, 43, 160, 150): EventType.ORCA_WHIRLPOOL_SWAP,
            _d(30, 7, 144, 181, 102, 254, 155, 161): EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
            _d(166, 1, 36, 71, 112, 202, 181, 171): EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED,
            _d(100, 118, 173, 87, 12, 198, 254, 229): EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
        }
        return mapping.get(disc)
    if program_id == METEORA_POOLS_PROGRAM_ID:
        mapping = {
            _d(81, 108, 227, 190, 205, 208, 10, 196): EventType.METEORA_POOLS_SWAP,
            _d(31, 94, 125, 90, 227, 52, 61, 186): EventType.METEORA_POOLS_ADD_LIQUIDITY,
            _d(116, 244, 97, 232, 103, 31, 152, 58): EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
            _d(121, 127, 38, 136, 92, 55, 14, 247): EventType.METEORA_POOLS_BOOTSTRAP_LIQUIDITY,
            _d(202, 44, 41, 88, 104, 220, 157, 82): EventType.METEORA_POOLS_POOL_CREATED,
            _d(245, 26, 198, 164, 88, 18, 75, 9): EventType.METEORA_POOLS_SET_POOL_FEES,
        }
        return mapping.get(disc)
    if program_id == METEORA_DAMM_V2_PROGRAM_ID:
        if disc in (DAMM_SWAP, DAMM_SWAP2):
            return EventType.METEORA_DAMM_V2_SWAP
        if disc == DAMM_ADD_LIQUIDITY:
            return EventType.METEORA_DAMM_V2_ADD_LIQUIDITY
        if disc == DAMM_REMOVE_LIQUIDITY:
            return EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY
        if disc == DAMM_INIT_POOL:
            return EventType.METEORA_DAMM_V2_INITIALIZE_POOL
        if disc == DAMM_CREATE_POSITION:
            return EventType.METEORA_DAMM_V2_CREATE_POSITION
        if disc == DAMM_CLOSE_POSITION:
            return EventType.METEORA_DAMM_V2_CLOSE_POSITION
        return None
    if program_id == METEORA_DBC_PROGRAM_ID:
        if disc == DBC_SWAP:
            return EventType.METEORA_DBC_SWAP
        if disc == DBC_INIT_POOL:
            return EventType.METEORA_DBC_INITIALIZE_POOL
        if disc == DBC_CURVE_COMPLETE:
            return EventType.METEORA_DBC_CURVE_COMPLETE
        return None
    if program_id == METEORA_DLMM_PROGRAM_ID:
        if disc == DLMM_SWAP:
            return EventType.METEORA_DLMM_SWAP
        if disc == DLMM_ADD_LIQ:
            return EventType.METEORA_DLMM_ADD_LIQUIDITY
        if disc == DLMM_REMOVE_LIQ:
            return EventType.METEORA_DLMM_REMOVE_LIQUIDITY
        if disc == DLMM_INIT_POOL:
            return EventType.METEORA_DLMM_INITIALIZE_POOL
        if disc == DLMM_INIT_BIN:
            return EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY
        if disc == DLMM_CREATE_POS:
            return EventType.METEORA_DLMM_CREATE_POSITION
        if disc == DLMM_CLOSE_POS:
            return EventType.METEORA_DLMM_CLOSE_POSITION
        if disc == DLMM_CLAIM_FEE:
            return EventType.METEORA_DLMM_CLAIM_FEE
        return None
    return event_type_for_discriminator(disc)


def filter_wants_pumpfun_trade(event_type_filter: Any) -> bool:
    return event_type_filter is None or any(
        event_type_filter.should_include(t)
        for t in (
            EventType.PUMP_FUN_TRADE,
            EventType.PUMP_FUN_BUY,
            EventType.PUMP_FUN_SELL,
            EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        )
    )


def filter_wants_raydium_launchlab_trade(event_type_filter: Any) -> bool:
    return event_type_filter is None or event_type_filter.should_include(
        EventType.RAYDIUM_LAUNCHLAB_TRADE
    )


def filter_allows_unscoped_discriminator(event_type_filter: Any, disc: int) -> bool:
    if event_type_filter is None:
        return True
    if disc == PUMP_TRADE:
        return filter_wants_pumpfun_trade(event_type_filter) or filter_wants_raydium_launchlab_trade(
            event_type_filter
        )
    if disc == DLMM_SWAP:
        return event_type_filter.should_include(EventType.RAYDIUM_CPMM_SWAP) or event_type_filter.should_include(
            EventType.METEORA_DLMM_SWAP
        )
    event_type = event_type_for_discriminator(disc)
    if event_type is not None:
        return event_type_filter.should_include(event_type)
    return filter_wants_supported_logs(event_type_filter)


def filter_wants_supported_logs(event_type_filter: Any) -> bool:
    return any(
        filter_includes_program(event_type_filter, program_id)
        for program_id in (
            PUMPFUN_PROGRAM_ID,
            PUMP_FEES_PROGRAM_ID,
            PUMPSWAP_PROGRAM_ID,
            RAYDIUM_LAUNCHLAB_PROGRAM_ID,
            RAYDIUM_CLMM_PROGRAM_ID,
            RAYDIUM_CPMM_PROGRAM_ID,
            RAYDIUM_AMM_V4_PROGRAM_ID,
            ORCA_WHIRLPOOL_PROGRAM_ID,
            METEORA_POOLS_PROGRAM_ID,
            METEORA_DAMM_V2_PROGRAM_ID,
            METEORA_DLMM_PROGRAM_ID,
            METEORA_DBC_PROGRAM_ID,
        )
    )


def dispatch_unscoped_pumpfun_launchlab_trade(
    data: bytes,
    meta: dict,
    is_created_buy: bool,
    event_type_filter: Any = None,
) -> Optional[DexEvent]:
    if filter_wants_pumpfun_trade(event_type_filter):
        pumpfun = apply_event_type_filter(
            parse_trade_from_data(data, meta, is_created_buy),
            event_type_filter,
        )
        if pumpfun is not None:
            return pumpfun
    if filter_wants_raydium_launchlab_trade(event_type_filter):
        return apply_event_type_filter(
            parse_raydium_launchlab_from_discriminator(PUMP_TRADE, data, meta),
            event_type_filter,
        )
    return None


def _pumpfun_trade_matches_include_only(ev: DexEvent, include_only: List[EventType]) -> bool:
    if ev.type == EventType.PUMP_FUN_BUY:
        return EventType.PUMP_FUN_BUY in include_only or EventType.PUMP_FUN_BUY_EXACT_SOL_IN in include_only
    if ev.type == EventType.PUMP_FUN_SELL:
        return EventType.PUMP_FUN_SELL in include_only
    if ev.type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN:
        return EventType.PUMP_FUN_BUY in include_only or EventType.PUMP_FUN_BUY_EXACT_SOL_IN in include_only
    if ev.type == EventType.PUMP_FUN_TRADE:
        return EventType.PUMP_FUN_TRADE in include_only
    if ev.type in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
        return EventType.PUMP_FUN_CREATE in include_only or EventType.PUMP_FUN_CREATE_V2 in include_only
    return False


def apply_pumpfun_secondary_filter(ev: Optional[DexEvent], event_type_filter: Any) -> Optional[DexEvent]:
    if ev is None or not ev.is_valid():
        return None
    include_only = getattr(event_type_filter, "include_only", None)
    if include_only:
        has_specific = any(
            t
            in (
                EventType.PUMP_FUN_BUY,
                EventType.PUMP_FUN_SELL,
                EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
                EventType.PUMP_FUN_CREATE,
                EventType.PUMP_FUN_CREATE_V2,
            )
            for t in include_only
        )
        if has_specific and not _pumpfun_trade_matches_include_only(ev, include_only):
            return None
    return apply_event_type_filter(ev, event_type_filter)


def dispatch_scoped_pumpfun_data(
    disc: int,
    data: bytes,
    meta: dict,
    is_created_buy: bool,
    event_type_filter: Any = None,
) -> Optional[DexEvent]:
    if disc == PUMP_TRADE:
        return apply_pumpfun_secondary_filter(
            parse_trade_from_data(data, meta, is_created_buy),
            event_type_filter,
        )
    if disc == PUMP_CREATE:
        return parse_create_from_data(data, meta)
    if disc == PUMP_MIGRATE:
        return parse_migrate_from_data(data, meta)
    if disc == PUMP_MIGRATE_BONDING_CURVE_CREATOR:
        return parse_migrate_bonding_curve_creator_from_data(data, meta)
    return None


def dispatch_scoped_pump_fees_data(disc: int, data: bytes, meta: dict) -> Optional[DexEvent]:
    if disc == PUMP_FEES_CREATE_FEE_SHARING_CONFIG:
        return parse_pump_fees_create_fee_sharing_config_from_data(data, meta)
    if disc == PUMP_FEES_INITIALIZE_FEE_CONFIG:
        return parse_pump_fees_initialize_fee_config_from_data(data, meta)
    if disc == PUMP_FEES_RESET_FEE_SHARING_CONFIG:
        return parse_pump_fees_reset_fee_sharing_config_from_data(data, meta)
    if disc == PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY:
        return parse_pump_fees_revoke_fee_sharing_authority_from_data(data, meta)
    if disc == PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY:
        return parse_pump_fees_transfer_fee_sharing_authority_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_ADMIN:
        return parse_pump_fees_update_admin_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_FEE_CONFIG:
        return parse_pump_fees_update_fee_config_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_FEE_SHARES:
        return parse_pump_fees_update_fee_shares_from_data(data, meta)
    if disc == PUMP_FEES_UPSERT_FEE_TIERS:
        return parse_pump_fees_upsert_fee_tiers_from_data(data, meta)
    return None


def dispatch_scoped_pumpswap_data(disc: int, data: bytes, meta: dict) -> Optional[DexEvent]:
    if disc == _d(103, 244, 82, 31, 44, 245, 119, 119):
        return parse_ps_buy_from_data(data, meta)
    if disc == _d(62, 47, 55, 10, 165, 3, 220, 42):
        return parse_ps_sell_from_data(data, meta)
    if disc == _d(177, 49, 12, 210, 160, 118, 167, 116):
        return parse_ps_create_pool_from_data(data, meta)
    if disc == _d(120, 248, 61, 83, 31, 142, 107, 144):
        return parse_ps_add_liq_from_data(data, meta)
    if disc == _d(22, 9, 133, 26, 160, 44, 71, 192):
        return parse_ps_remove_liq_from_data(data, meta)
    return None


def filter_includes_program(event_type_filter: Any, program_id: Optional[str]) -> bool:
    from .grpc_types import (
        METEORA_DAMM_V2_FILTER_TYPES,
        METEORA_DBC_FILTER_TYPES,
        METEORA_DLMM_FILTER_TYPES,
        METEORA_POOLS_FILTER_TYPES,
        ORCA_WHIRLPOOL_FILTER_TYPES,
        PUMP_FEES_EVENT_TYPES,
        PUMPFUN_FILTER_TYPES,
        PUMPSWAP_FILTER_TYPES,
        RAYDIUM_AMM_V4_FILTER_TYPES,
        RAYDIUM_CLMM_FILTER_TYPES,
        RAYDIUM_CPMM_FILTER_TYPES,
        RAYDIUM_LAUNCHLAB_FILTER_TYPES,
    )

    groups = {
        PUMPFUN_PROGRAM_ID: PUMPFUN_FILTER_TYPES,
        PUMP_FEES_PROGRAM_ID: PUMP_FEES_EVENT_TYPES,
        PUMPSWAP_PROGRAM_ID: PUMPSWAP_FILTER_TYPES,
        RAYDIUM_LAUNCHLAB_PROGRAM_ID: RAYDIUM_LAUNCHLAB_FILTER_TYPES,
        RAYDIUM_CLMM_PROGRAM_ID: RAYDIUM_CLMM_FILTER_TYPES,
        RAYDIUM_CPMM_PROGRAM_ID: RAYDIUM_CPMM_FILTER_TYPES,
        RAYDIUM_AMM_V4_PROGRAM_ID: RAYDIUM_AMM_V4_FILTER_TYPES,
        ORCA_WHIRLPOOL_PROGRAM_ID: ORCA_WHIRLPOOL_FILTER_TYPES,
        METEORA_POOLS_PROGRAM_ID: METEORA_POOLS_FILTER_TYPES,
        METEORA_DAMM_V2_PROGRAM_ID: METEORA_DAMM_V2_FILTER_TYPES,
        METEORA_DBC_PROGRAM_ID: METEORA_DBC_FILTER_TYPES,
        METEORA_DLMM_PROGRAM_ID: METEORA_DLMM_FILTER_TYPES,
    }
    types = groups.get(program_id)
    if types is None:
        return filter_allows_unknown_log_event(event_type_filter)
    include_only = getattr(event_type_filter, "include_only", None)
    if include_only is not None:
        return any(t in types for t in include_only)
    return any(event_type_filter.should_include(t) for t in types)


def filter_allows_unknown_log_event(event_type_filter: Any) -> bool:
    include_only = getattr(event_type_filter, "include_only", None)
    return include_only is None


def apply_event_type_filter(ev: Optional[DexEvent], event_type_filter: Any) -> Optional[DexEvent]:
    if ev is None or not ev.is_valid():
        return None
    if event_type_filter is not None and not event_type_filter.should_include(ev.type):
        return None
    return ev


# --- 主调度（与 Go matcher 分支顺序一致） ---

def dispatch_program_data(
    disc: int,
    data: bytes,
    buf: bytes,
    meta: dict,
    is_created_buy: bool,
    program_id: Optional[str] = None,
    event_type_filter: Any = None,
) -> Optional[DexEvent]:
    if program_id == PUMPFUN_PROGRAM_ID:
        return dispatch_scoped_pumpfun_data(disc, data, meta, is_created_buy, event_type_filter)
    if program_id == PUMP_FEES_PROGRAM_ID:
        return dispatch_scoped_pump_fees_data(disc, data, meta)
    if program_id == PUMPSWAP_PROGRAM_ID:
        return dispatch_scoped_pumpswap_data(disc, data, meta)
    if program_id == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
        return parse_raydium_launchlab_from_discriminator(disc, data, meta)
    if program_id == RAYDIUM_CLMM_PROGRAM_ID:
        if disc == _d(64, 198, 205, 232, 38, 8, 113, 226):
            return parse_clmm_swap_from_data(data, meta)
        if disc == _d(49, 79, 105, 212, 32, 34, 30, 84):
            return parse_clmm_inc_from_data(data, meta)
        if disc == _d(58, 222, 86, 58, 68, 50, 85, 56):
            return parse_clmm_dec_from_data(data, meta)
        if disc == _d(126, 240, 175, 206, 158, 88, 153, 107):
            return parse_clmm_liquidity_change_from_data(data, meta)
        if disc == _d(247, 189, 7, 119, 106, 112, 95, 151):
            return parse_clmm_config_change_from_data(data, meta)
        if disc == _d(100, 30, 87, 249, 196, 223, 154, 206):
            return parse_clmm_create_personal_position_from_data(data, meta)
        if disc == _d(237, 112, 148, 230, 57, 84, 180, 162):
            return parse_clmm_liquidity_calculate_from_data(data, meta)
        if disc == _d(106, 24, 71, 85, 57, 169, 158, 216):
            return parse_clmm_open_limit_order_from_data(data, meta)
        if disc == _d(11, 120, 13, 204, 199, 87, 19, 200):
            return parse_clmm_increase_limit_order_from_data(data, meta)
        if disc == _d(70, 48, 40, 221, 219, 237, 212, 163):
            return parse_clmm_decrease_limit_order_from_data(data, meta)
        if disc == _d(88, 119, 77, 164, 125, 124, 10, 194):
            return parse_clmm_settle_limit_order_from_data(data, meta)
        if disc == _d(109, 127, 186, 78, 114, 65, 37, 236):
            return parse_clmm_update_reward_infos_from_data(data, meta)
        if disc == _d(25, 94, 75, 47, 112, 99, 53, 63):
            return parse_clmm_create_from_data(data, meta)
        if disc == _d(166, 174, 105, 192, 81, 161, 83, 105):
            return parse_clmm_collect_personal_from_data(data, meta)
        if disc == _d(206, 87, 17, 79, 45, 41, 213, 61):
            return parse_clmm_collect_protocol_from_data(data, meta)
        return None
    if program_id == RAYDIUM_CPMM_PROGRAM_ID:
        if disc == _d(143, 190, 90, 218, 196, 30, 51, 222):
            return parse_cpmm_swap_in_from_data(data, meta)
        if disc == _d(55, 217, 98, 86, 163, 74, 180, 173):
            return parse_cpmm_swap_out_from_data(data, meta)
        if disc == _d(233, 146, 209, 142, 207, 104, 64, 188):
            return parse_cpmm_create_from_data(data, meta)
        if disc == _d(242, 35, 198, 137, 82, 225, 242, 182):
            return parse_cpmm_deposit_from_data(data, meta)
        if disc == _d(183, 18, 70, 156, 148, 109, 161, 34):
            return parse_cpmm_withdraw_from_data(data, meta)
        return None
    if program_id == RAYDIUM_AMM_V4_PROGRAM_ID:
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 9):
            return parse_amm_swap_in_from_data(data, meta)
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 11):
            return parse_amm_swap_out_from_data(data, meta)
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 3):
            return parse_amm_deposit_from_data(data, meta)
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 4):
            return parse_amm_withdraw_from_data(data, meta)
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 1):
            return parse_amm_init2_from_data(data, meta)
        if disc == _d(0, 0, 0, 0, 0, 0, 0, 7):
            return parse_amm_withdraw_pnl_from_data(data, meta)
        return None
    if program_id == ORCA_WHIRLPOOL_PROGRAM_ID:
        if disc == _d(225, 202, 73, 175, 147, 43, 160, 150):
            return parse_orca_traded_from_data(data, meta)
        if disc == _d(30, 7, 144, 181, 102, 254, 155, 161):
            return parse_orca_liq_inc_from_data(data, meta)
        if disc == _d(166, 1, 36, 71, 112, 202, 181, 171):
            return parse_orca_liq_dec_from_data(data, meta)
        if disc == _d(100, 118, 173, 87, 12, 198, 254, 229):
            return parse_orca_pool_init_from_data(data, meta)
        return None
    if program_id == METEORA_POOLS_PROGRAM_ID:
        if disc == _d(81, 108, 227, 190, 205, 208, 10, 196):
            return parse_meteora_swap_from_data(data, meta)
        if disc == _d(31, 94, 125, 90, 227, 52, 61, 186):
            return parse_meteora_add_from_data(data, meta)
        if disc == _d(116, 244, 97, 232, 103, 31, 152, 58):
            return parse_meteora_remove_from_data(data, meta)
        if disc == _d(121, 127, 38, 136, 92, 55, 14, 247):
            return parse_meteora_bootstrap_from_data(data, meta)
        if disc == _d(202, 44, 41, 88, 104, 220, 157, 82):
            return parse_meteora_pool_created_from_data(data, meta)
        if disc == _d(245, 26, 198, 164, 88, 18, 75, 9):
            return parse_meteora_pools_set_pool_fees_from_data(data, meta)
        return None
    if program_id == METEORA_DAMM_V2_PROGRAM_ID:
        return parse_meteora_damm_from_buf(buf, meta)
    if program_id == METEORA_DBC_PROGRAM_ID:
        return parse_meteora_dbc_from_discriminator(disc, data, meta)
    if program_id == METEORA_DLMM_PROGRAM_ID:
        return parse_dlmm_from_program_data(buf, meta)
    if disc == PUMP_TRADE:
        return dispatch_unscoped_pumpfun_launchlab_trade(
            data,
            meta,
            is_created_buy,
            event_type_filter,
        )
    if disc == _d(64, 198, 205, 232, 38, 8, 113, 226):
        return parse_clmm_swap_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 9):
        return parse_amm_swap_in_from_data(data, meta)
    if disc == _d(103, 244, 82, 31, 44, 245, 119, 119):
        return parse_ps_buy_from_data(data, meta)
    if disc == _d(62, 47, 55, 10, 165, 3, 220, 42):
        return parse_ps_sell_from_data(data, meta)
    if disc == PUMP_CREATE:
        return parse_create_from_data(data, meta)
    if disc == PUMP_MIGRATE:
        return parse_migrate_from_data(data, meta)
    if disc == PUMP_MIGRATE_BONDING_CURVE_CREATOR:
        return parse_migrate_bonding_curve_creator_from_data(data, meta)
    if disc == PUMP_FEES_CREATE_FEE_SHARING_CONFIG:
        return parse_pump_fees_create_fee_sharing_config_from_data(data, meta)
    if disc == PUMP_FEES_INITIALIZE_FEE_CONFIG:
        return parse_pump_fees_initialize_fee_config_from_data(data, meta)
    if disc == PUMP_FEES_RESET_FEE_SHARING_CONFIG:
        return parse_pump_fees_reset_fee_sharing_config_from_data(data, meta)
    if disc == PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY:
        return parse_pump_fees_revoke_fee_sharing_authority_from_data(data, meta)
    if disc == PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY:
        return parse_pump_fees_transfer_fee_sharing_authority_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_ADMIN:
        return parse_pump_fees_update_admin_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_FEE_CONFIG:
        return parse_pump_fees_update_fee_config_from_data(data, meta)
    if disc == PUMP_FEES_UPDATE_FEE_SHARES:
        return parse_pump_fees_update_fee_shares_from_data(data, meta)
    if disc == PUMP_FEES_UPSERT_FEE_TIERS:
        return parse_pump_fees_upsert_fee_tiers_from_data(data, meta)
    if disc == _d(177, 49, 12, 210, 160, 118, 167, 116):
        return parse_ps_create_pool_from_data(data, meta)
    if disc == _d(120, 248, 61, 83, 31, 142, 107, 144):
        return parse_ps_add_liq_from_data(data, meta)
    if disc == _d(22, 9, 133, 26, 160, 44, 71, 192):
        return parse_ps_remove_liq_from_data(data, meta)
    if disc == _d(49, 79, 105, 212, 32, 34, 30, 84):
        return parse_clmm_inc_from_data(data, meta)
    if disc == _d(58, 222, 86, 58, 68, 50, 85, 56):
        return parse_clmm_dec_from_data(data, meta)
    if disc == _d(126, 240, 175, 206, 158, 88, 153, 107):
        return parse_clmm_liquidity_change_from_data(data, meta)
    if disc == _d(247, 189, 7, 119, 106, 112, 95, 151):
        return parse_clmm_config_change_from_data(data, meta)
    if disc == _d(100, 30, 87, 249, 196, 223, 154, 206):
        return parse_clmm_create_personal_position_from_data(data, meta)
    if disc == _d(237, 112, 148, 230, 57, 84, 180, 162):
        return parse_clmm_liquidity_calculate_from_data(data, meta)
    if disc == _d(106, 24, 71, 85, 57, 169, 158, 216):
        return parse_clmm_open_limit_order_from_data(data, meta)
    if disc == _d(11, 120, 13, 204, 199, 87, 19, 200):
        return parse_clmm_increase_limit_order_from_data(data, meta)
    if disc == _d(70, 48, 40, 221, 219, 237, 212, 163):
        return parse_clmm_decrease_limit_order_from_data(data, meta)
    if disc == _d(88, 119, 77, 164, 125, 124, 10, 194):
        return parse_clmm_settle_limit_order_from_data(data, meta)
    if disc == _d(109, 127, 186, 78, 114, 65, 37, 236):
        return parse_clmm_update_reward_infos_from_data(data, meta)
    if disc == _d(25, 94, 75, 47, 112, 99, 53, 63):
        return parse_clmm_create_from_data(data, meta)
    if disc == _d(166, 174, 105, 192, 81, 161, 83, 105):
        return parse_clmm_collect_personal_from_data(data, meta)
    if disc == _d(206, 87, 17, 79, 45, 41, 213, 61):
        return parse_clmm_collect_protocol_from_data(data, meta)
    if disc == _d(143, 190, 90, 218, 196, 30, 51, 222):
        return apply_event_type_filter(parse_cpmm_swap_in_from_data(data, meta), event_type_filter)
    if disc == _d(55, 217, 98, 86, 163, 74, 180, 173):
        return parse_cpmm_swap_out_from_data(data, meta)
    if disc == _d(242, 35, 198, 137, 82, 225, 242, 182):
        return parse_cpmm_deposit_from_data(data, meta)
    if disc == _d(183, 18, 70, 156, 148, 109, 161, 34):
        return parse_cpmm_withdraw_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 11):
        return parse_amm_swap_out_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 3):
        return parse_amm_deposit_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 4):
        return parse_amm_withdraw_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 7):
        return parse_amm_withdraw_pnl_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 1):
        return parse_amm_init2_from_data(data, meta)
    if disc == _d(225, 202, 73, 175, 147, 43, 160, 150):
        return parse_orca_traded_from_data(data, meta)
    if disc == _d(30, 7, 144, 181, 102, 254, 155, 161):
        return parse_orca_liq_inc_from_data(data, meta)
    if disc == _d(166, 1, 36, 71, 112, 202, 181, 171):
        return parse_orca_liq_dec_from_data(data, meta)
    if disc == _d(100, 118, 173, 87, 12, 198, 254, 229):
        return parse_orca_pool_init_from_data(data, meta)
    if disc == _d(81, 108, 227, 190, 205, 208, 10, 196):
        return parse_meteora_swap_from_data(data, meta)
    if disc == _d(31, 94, 125, 90, 227, 52, 61, 186):
        return parse_meteora_add_from_data(data, meta)
    if disc == _d(116, 244, 97, 232, 103, 31, 152, 58):
        return parse_meteora_remove_from_data(data, meta)
    if disc == _d(121, 127, 38, 136, 92, 55, 14, 247):
        return parse_meteora_bootstrap_from_data(data, meta)
    if disc == _d(202, 44, 41, 88, 104, 220, 157, 82):
        return parse_meteora_pool_created_from_data(data, meta)
    if disc == _d(245, 26, 198, 164, 88, 18, 75, 9):
        return parse_meteora_pools_set_pool_fees_from_data(data, meta)
    if disc in (
        DAMM_SWAP,
        DAMM_SWAP2,
        _d(175, 242, 8, 157, 30, 247, 185, 169),
        _d(87, 46, 88, 98, 175, 96, 34, 91),
        _d(228, 50, 246, 85, 203, 66, 134, 37),
        _d(156, 15, 119, 198, 29, 181, 221, 55),
        _d(20, 145, 144, 68, 143, 142, 214, 178),
    ):
        return parse_meteora_damm_from_buf(buf, meta)
    raydium_launchlab = parse_raydium_launchlab_from_discriminator(disc, data, meta)
    if raydium_launchlab:
        return raydium_launchlab
    return parse_dlmm_from_program_data(buf, meta)
