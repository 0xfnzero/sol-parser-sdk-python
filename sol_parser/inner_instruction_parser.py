"""Inner instruction 解析（16 字节 discriminator），对齐 Rust ``grpc/instruction_parser::parse_inner_instruction``。"""

from __future__ import annotations

import struct
from typing import Optional

from .dex_parsers import (
    _parse_raydium_launchlab_trade,
    _parse_raydium_launchlab_pool_create,
    PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
    PUMP_FEES_INITIALIZE_FEE_CONFIG,
    PUMP_FEES_RESET_FEE_SHARING_CONFIG,
    PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
    PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
    PUMP_FEES_UPDATE_ADMIN,
    PUMP_FEES_UPDATE_FEE_CONFIG,
    PUMP_FEES_UPDATE_FEE_SHARES,
    PUMP_FEES_UPSERT_FEE_TIERS,
    parse_amm_deposit_from_data,
    parse_amm_init2_from_data,
    parse_amm_swap_in_from_data,
    parse_amm_swap_out_from_data,
    parse_amm_withdraw_from_data,
    parse_amm_withdraw_pnl_from_data,
    parse_clmm_collect_personal_from_data,
    parse_clmm_collect_protocol_from_data,
    parse_clmm_config_change_from_data,
    parse_clmm_create_from_data,
    parse_clmm_create_personal_position_from_data,
    parse_clmm_dec_from_data,
    parse_clmm_decrease_limit_order_from_data,
    parse_clmm_inc_from_data,
    parse_clmm_increase_limit_order_from_data,
    parse_clmm_liquidity_calculate_from_data,
    parse_clmm_liquidity_change_from_data,
    parse_clmm_open_limit_order_from_data,
    parse_clmm_settle_limit_order_from_data,
    parse_clmm_swap_from_data,
    parse_clmm_update_reward_infos_from_data,
    parse_cpmm_create_from_data,
    parse_cpmm_deposit_from_data,
    parse_cpmm_swap_in_from_data,
    parse_cpmm_swap_out_from_data,
    parse_cpmm_withdraw_from_data,
    parse_dlmm_from_program_data,
    parse_meteora_damm_from_buf,
    parse_meteora_add_from_data,
    parse_meteora_bootstrap_from_data,
    parse_meteora_pool_created_from_data,
    parse_meteora_pools_set_pool_fees_from_data,
    parse_meteora_remove_from_data,
    parse_meteora_swap_from_data,
    parse_orca_liq_dec_from_data,
    parse_orca_liq_inc_from_data,
    parse_orca_pool_init_from_data,
    parse_orca_traded_from_data,
    parse_pump_fees_create_fee_sharing_config_from_data,
    parse_pump_fees_initialize_fee_config_from_data,
    parse_pump_fees_reset_fee_sharing_config_from_data,
    parse_pump_fees_revoke_fee_sharing_authority_from_data,
    parse_pump_fees_transfer_fee_sharing_authority_from_data,
    parse_pump_fees_update_admin_from_data,
    parse_pump_fees_update_fee_config_from_data,
    parse_pump_fees_update_fee_shares_from_data,
    parse_pump_fees_upsert_fee_tiers_from_data,
    parse_ps_add_liq_from_data,
    parse_ps_buy_from_data,
    parse_ps_create_pool_from_data,
    parse_ps_remove_liq_from_data,
    parse_ps_sell_from_data,
    parse_create_from_data,
    parse_migrate_from_data,
    parse_trade_from_data,
    _make_meta,
)
from .event_types import (
    DexEvent,
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsSwapEvent,
)
from .grpc_types import EventType, EventTypeFilter
from .grpc_types import (
    event_type_filter_includes_pump_fees,
    event_type_filter_includes_meteora_damm_v2,
    event_type_filter_includes_meteora_dlmm,
    event_type_filter_includes_meteora_pools,
    event_type_filter_includes_orca_whirlpool,
    event_type_filter_includes_pumpfun,
    event_type_filter_includes_pumpswap,
    event_type_filter_includes_raydium_amm_v4,
    event_type_filter_includes_raydium_clmm,
    event_type_filter_includes_raydium_cpmm,
    event_type_filter_includes_raydium_launchlab,
)
from .instructions import (
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    PUMPFUN_PROGRAM_ID,
    PUMP_FEES_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    RAYDIUM_AMM_V4_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
)
# PumpFun inner（Rust pump_inner::discriminators）
_PUMPFUN_INNER_TRADE = bytes([189, 219, 127, 211, 78, 230, 97, 238, 155, 167, 108, 32, 122, 76, 173, 64])
_PUMPFUN_INNER_CREATE = bytes([27, 114, 169, 77, 222, 235, 99, 118, 155, 167, 108, 32, 122, 76, 173, 64])
_PUMPFUN_INNER_MIGRATE = bytes([189, 233, 93, 185, 92, 148, 234, 148, 155, 167, 108, 32, 122, 76, 173, 64])

# PumpSwap AMM（Rust pump_amm_inner::discriminators）
_PS_BUY = bytes([228, 69, 165, 46, 81, 203, 154, 29, 103, 244, 82, 31, 44, 245, 119, 119])
_PS_SELL = bytes([228, 69, 165, 46, 81, 203, 154, 29, 62, 47, 55, 10, 165, 3, 220, 42])
_PS_CREATE_POOL = bytes([228, 69, 165, 46, 81, 203, 154, 29, 177, 49, 12, 210, 160, 118, 167, 116])
_PS_ADD_LIQ = bytes([228, 69, 165, 46, 81, 203, 154, 29, 120, 248, 61, 83, 31, 142, 107, 144])
_PS_REMOVE_LIQ = bytes([228, 69, 165, 46, 81, 203, 154, 29, 22, 9, 133, 26, 160, 44, 71, 192])

# Raydium CLMM（raydium_clmm_inner::discriminators）
_CLMM_SWAP = bytes([64, 198, 205, 232, 38, 8, 113, 226, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_INC = bytes([49, 79, 105, 212, 32, 34, 30, 84, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_DEC = bytes([58, 222, 86, 58, 68, 50, 85, 56, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_LIQUIDITY_CHANGE = bytes([126, 240, 175, 206, 158, 88, 153, 107, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_CONFIG_CHANGE = bytes([247, 189, 7, 119, 106, 112, 95, 151, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_CREATE_PERSONAL_POSITION = bytes([100, 30, 87, 249, 196, 223, 154, 206, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_LIQUIDITY_CALCULATE = bytes([237, 112, 148, 230, 57, 84, 180, 162, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_OPEN_LIMIT_ORDER = bytes([106, 24, 71, 85, 57, 169, 158, 216, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_INCREASE_LIMIT_ORDER = bytes([11, 120, 13, 204, 199, 87, 19, 200, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_DECREASE_LIMIT_ORDER = bytes([70, 48, 40, 221, 219, 237, 212, 163, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_SETTLE_LIMIT_ORDER = bytes([88, 119, 77, 164, 125, 124, 10, 194, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_UPDATE_REWARD_INFOS = bytes([109, 127, 186, 78, 114, 65, 37, 236, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_CREATE_POOL = bytes([25, 94, 75, 47, 112, 99, 53, 63, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_COLLECT_PERSONAL_FEE = bytes([166, 174, 105, 192, 81, 161, 83, 105, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_COLLECT_PROTOCOL_FEE = bytes([206, 87, 17, 79, 45, 41, 213, 61, 155, 167, 108, 32, 122, 76, 173, 64])

# Raydium CPMM（all_inner::raydium_cpmm::discriminators）
_CPMM_SWAP_IN = bytes([143, 190, 90, 218, 196, 30, 51, 222, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_SWAP_OUT = bytes([55, 217, 98, 86, 163, 74, 180, 173, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_CREATE_POOL = bytes([233, 146, 209, 142, 207, 104, 64, 188, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_DEP = bytes([242, 35, 198, 137, 82, 225, 242, 182, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_WIT = bytes([183, 18, 70, 156, 148, 109, 161, 34, 155, 167, 108, 32, 122, 76, 173, 64])

# Raydium AMM V4
_AMM_SWAP_IN = bytes([0, 0, 0, 0, 0, 0, 0, 9, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_SWAP_OUT = bytes([0, 0, 0, 0, 0, 0, 0, 11, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_DEP = bytes([0, 0, 0, 0, 0, 0, 0, 3, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_WIT = bytes([0, 0, 0, 0, 0, 0, 0, 4, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_INIT2 = bytes([0, 0, 0, 0, 0, 0, 0, 1, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_WITHDRAW_PNL = bytes([0, 0, 0, 0, 0, 0, 0, 7, 155, 167, 108, 32, 122, 76, 173, 64])

# Orca
_ORCA_TRADED = bytes([225, 202, 73, 175, 147, 43, 160, 150, 155, 167, 108, 32, 122, 76, 173, 64])
_ORCA_LIQ_INC = bytes([30, 7, 144, 181, 102, 254, 155, 161, 155, 167, 108, 32, 122, 76, 173, 64])
_ORCA_LIQ_DEC = bytes([166, 1, 36, 71, 112, 202, 181, 171, 155, 167, 108, 32, 122, 76, 173, 64])
_ORCA_POOL_INITIALIZED = bytes([100, 118, 173, 87, 12, 198, 254, 229, 155, 167, 108, 32, 122, 76, 173, 64])

# Meteora Pools AMM
_MP_SWAP = bytes([81, 108, 227, 190, 205, 208, 10, 196, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_ADD = bytes([31, 94, 125, 90, 227, 52, 61, 186, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_REM = bytes([116, 244, 97, 232, 103, 31, 152, 58, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_BOOTSTRAP = bytes([121, 127, 38, 136, 92, 55, 14, 247, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_POOL_CREATED = bytes([202, 44, 41, 88, 104, 220, 157, 82, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_SET_POOL_FEES = bytes([245, 26, 198, 164, 88, 18, 75, 9, 155, 167, 108, 32, 122, 76, 173, 64])

_EVENT_CPI_PREFIX = bytes([228, 69, 165, 46, 81, 203, 154, 29])
_EVENT_CPI_SUFFIX = bytes([155, 167, 108, 32, 122, 76, 173, 64])


def _event_cpi_disc8(disc16: bytes) -> Optional[int]:
    if disc16[:8] == _EVENT_CPI_PREFIX:
        return struct.unpack("<Q", disc16[8:16])[0]
    if disc16[8:16] == _EVENT_CPI_SUFFIX:
        return struct.unpack("<Q", disc16[:8])[0]
    return None

# Meteora DAMM V2（inner 16 字节：magic + 8 字节 event disc，与 ``parse_meteora_damm_from_buf`` 的 disc 一致）
def _damm_buf_from_inner(disc16: bytes, inner: bytes) -> bytes:
    return disc16[8:16] + inner

# Raydium LaunchLab inner（event discriminator + Anchor CPI marker）
_RAYDIUM_LAUNCHLAB_TRADE = bytes([189, 219, 127, 211, 78, 230, 97, 238, 155, 167, 108, 32, 122, 76, 173, 64])
_RAYDIUM_LAUNCHLAB_POOL_CREATE = bytes([151, 215, 226, 9, 118, 161, 115, 174, 155, 167, 108, 32, 122, 76, 173, 64])

# DLMM（8 字节 event disc + payload）
def _dlmm_buf_from_inner(disc16: bytes, inner: bytes) -> bytes:
    return disc16[:8] + inner


def _meteora_pools_swap_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    if len(data) < 16:
        return None
    ia = struct.unpack_from("<Q", data, 0)[0]
    oa = struct.unpack_from("<Q", data, 8)[0]
    return DexEvent(
        type=EventType.METEORA_POOLS_SWAP,
        data=MeteoraPoolsSwapEvent(
            metadata=_make_meta(meta_d),
            in_amount=ia,
            out_amount=oa,
            trade_fee=0,
            admin_fee=0,
            host_fee=0,
        ),
    )


def _meteora_pools_add_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    lp = struct.unpack_from("<Q", data, 0)[0]
    ta = struct.unpack_from("<Q", data, 8)[0]
    tb = struct.unpack_from("<Q", data, 16)[0]
    return DexEvent(
        type=EventType.METEORA_POOLS_ADD_LIQUIDITY,
        data=MeteoraPoolsAddLiquidityEvent(
            metadata=_make_meta(meta_d),
            lp_mint_amount=lp,
            token_a_amount=ta,
            token_b_amount=tb,
        ),
    )


def _meteora_pools_rem_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    lp = struct.unpack_from("<Q", data, 0)[0]
    ta = struct.unpack_from("<Q", data, 8)[0]
    tb = struct.unpack_from("<Q", data, 16)[0]
    return DexEvent(
        type=EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
        data=MeteoraPoolsRemoveLiquidityEvent(
            metadata=_make_meta(meta_d),
            lp_unmint_amount=lp,
            token_a_out_amount=ta,
            token_b_out_amount=tb,
        ),
    )


def _raydium_launchlab_trade_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    return _parse_raydium_launchlab_trade(data, meta_d)


def _raydium_launchlab_pool_create_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    return _parse_raydium_launchlab_pool_create(data, meta_d)


def _filter_inner_event(
    ev: Optional[DexEvent],
    event_type_filter: Optional[EventTypeFilter],
) -> Optional[DexEvent]:
    if ev is None or event_type_filter is None:
        return ev
    return ev if event_type_filter.should_include(ev.type) else None


def parse_inner_instruction(
    data: bytes,
    program_id_b58: str,
    meta_d: dict,
    filter: Optional[EventTypeFilter],
    is_created_buy: bool,
) -> Optional[DexEvent]:
    if len(data) < 16:
        return None
    disc16 = bytes(data[:16])
    inner = data[16:]

    def emit(ev: Optional[DexEvent]) -> Optional[DexEvent]:
        return _filter_inner_event(ev, filter)

    if program_id_b58 == PUMPFUN_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_pumpfun(filter):
            return None
        if disc16 == _PUMPFUN_INNER_TRADE:
            ev = parse_trade_from_data(inner, meta_d, is_created_buy)
            return emit(ev if ev.is_valid() else None)
        if disc16 == _PUMPFUN_INNER_CREATE:
            ev = parse_create_from_data(inner, meta_d)
            return emit(ev if ev.is_valid() else None)
        if disc16 == _PUMPFUN_INNER_MIGRATE:
            ev = parse_migrate_from_data(inner, meta_d)
            return emit(ev if ev.is_valid() else None)
        return None

    if program_id_b58 == PUMPSWAP_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_pumpswap(filter):
            return None
        if disc16 == _PS_BUY:
            return emit(parse_ps_buy_from_data(inner, meta_d))
        if disc16 == _PS_SELL:
            return emit(parse_ps_sell_from_data(inner, meta_d))
        if disc16 == _PS_CREATE_POOL:
            return emit(parse_ps_create_pool_from_data(inner, meta_d))
        if disc16 == _PS_ADD_LIQ:
            return emit(parse_ps_add_liq_from_data(inner, meta_d))
        if disc16 == _PS_REMOVE_LIQ:
            return emit(parse_ps_remove_liq_from_data(inner, meta_d))
        return None

    if program_id_b58 == PUMP_FEES_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_pump_fees(filter):
            return None
        event_disc = _event_cpi_disc8(disc16)
        if event_disc == PUMP_FEES_CREATE_FEE_SHARING_CONFIG:
            return emit(parse_pump_fees_create_fee_sharing_config_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_INITIALIZE_FEE_CONFIG:
            return emit(parse_pump_fees_initialize_fee_config_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_RESET_FEE_SHARING_CONFIG:
            return emit(parse_pump_fees_reset_fee_sharing_config_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY:
            return emit(parse_pump_fees_revoke_fee_sharing_authority_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY:
            return emit(parse_pump_fees_transfer_fee_sharing_authority_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_UPDATE_ADMIN:
            return emit(parse_pump_fees_update_admin_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_UPDATE_FEE_CONFIG:
            return emit(parse_pump_fees_update_fee_config_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_UPDATE_FEE_SHARES:
            return emit(parse_pump_fees_update_fee_shares_from_data(inner, meta_d))
        if event_disc == PUMP_FEES_UPSERT_FEE_TIERS:
            return emit(parse_pump_fees_upsert_fee_tiers_from_data(inner, meta_d))
        return None

    if program_id_b58 == RAYDIUM_CLMM_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_raydium_clmm(filter):
            return None
        if disc16 == _CLMM_SWAP:
            return emit(parse_clmm_swap_from_data(inner, meta_d))
        if disc16 == _CLMM_INC:
            return emit(parse_clmm_inc_from_data(inner, meta_d))
        if disc16 == _CLMM_DEC:
            return emit(parse_clmm_dec_from_data(inner, meta_d))
        if disc16 == _CLMM_LIQUIDITY_CHANGE:
            return emit(parse_clmm_liquidity_change_from_data(inner, meta_d))
        if disc16 == _CLMM_CONFIG_CHANGE:
            return emit(parse_clmm_config_change_from_data(inner, meta_d))
        if disc16 == _CLMM_CREATE_PERSONAL_POSITION:
            return emit(parse_clmm_create_personal_position_from_data(inner, meta_d))
        if disc16 == _CLMM_LIQUIDITY_CALCULATE:
            return emit(parse_clmm_liquidity_calculate_from_data(inner, meta_d))
        if disc16 == _CLMM_OPEN_LIMIT_ORDER:
            return emit(parse_clmm_open_limit_order_from_data(inner, meta_d))
        if disc16 == _CLMM_INCREASE_LIMIT_ORDER:
            return emit(parse_clmm_increase_limit_order_from_data(inner, meta_d))
        if disc16 == _CLMM_DECREASE_LIMIT_ORDER:
            return emit(parse_clmm_decrease_limit_order_from_data(inner, meta_d))
        if disc16 == _CLMM_SETTLE_LIMIT_ORDER:
            return emit(parse_clmm_settle_limit_order_from_data(inner, meta_d))
        if disc16 == _CLMM_UPDATE_REWARD_INFOS:
            return emit(parse_clmm_update_reward_infos_from_data(inner, meta_d))
        if disc16 == _CLMM_CREATE_POOL:
            return emit(parse_clmm_create_from_data(inner, meta_d))
        if disc16 == _CLMM_COLLECT_PERSONAL_FEE:
            return emit(parse_clmm_collect_personal_from_data(inner, meta_d))
        if disc16 == _CLMM_COLLECT_PROTOCOL_FEE:
            return emit(parse_clmm_collect_protocol_from_data(inner, meta_d))
        return None

    if program_id_b58 == RAYDIUM_CPMM_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_raydium_cpmm(filter):
            return None
        if disc16 == _CPMM_SWAP_IN:
            return emit(parse_cpmm_swap_in_from_data(inner, meta_d))
        if disc16 == _CPMM_SWAP_OUT:
            return emit(parse_cpmm_swap_out_from_data(inner, meta_d))
        if disc16 == _CPMM_CREATE_POOL:
            return emit(parse_cpmm_create_from_data(inner, meta_d))
        if disc16 == _CPMM_DEP:
            return emit(parse_cpmm_deposit_from_data(inner, meta_d))
        if disc16 == _CPMM_WIT:
            return emit(parse_cpmm_withdraw_from_data(inner, meta_d))
        return None

    if program_id_b58 == RAYDIUM_AMM_V4_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_raydium_amm_v4(filter):
            return None
        if disc16 == _AMM_SWAP_IN:
            return emit(parse_amm_swap_in_from_data(inner, meta_d))
        if disc16 == _AMM_SWAP_OUT:
            return emit(parse_amm_swap_out_from_data(inner, meta_d))
        if disc16 == _AMM_DEP:
            return emit(parse_amm_deposit_from_data(inner, meta_d))
        if disc16 == _AMM_WIT:
            return emit(parse_amm_withdraw_from_data(inner, meta_d))
        if disc16 == _AMM_INIT2:
            return emit(parse_amm_init2_from_data(inner, meta_d))
        if disc16 == _AMM_WITHDRAW_PNL:
            return emit(parse_amm_withdraw_pnl_from_data(inner, meta_d))
        return None

    if program_id_b58 == ORCA_WHIRLPOOL_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_orca_whirlpool(filter):
            return None
        if disc16 == _ORCA_TRADED:
            return emit(parse_orca_traded_from_data(inner, meta_d))
        if disc16 == _ORCA_LIQ_INC:
            return emit(parse_orca_liq_inc_from_data(inner, meta_d))
        if disc16 == _ORCA_LIQ_DEC:
            return emit(parse_orca_liq_dec_from_data(inner, meta_d))
        if disc16 == _ORCA_POOL_INITIALIZED:
            return emit(parse_orca_pool_init_from_data(inner, meta_d))
        return None

    if program_id_b58 == METEORA_POOLS_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_meteora_pools(filter):
            return None
        if disc16 == _MP_SWAP:
            return emit(parse_meteora_swap_from_data(inner, meta_d) or _meteora_pools_swap_inner(inner, meta_d))
        if disc16 == _MP_ADD:
            return emit(parse_meteora_add_from_data(inner, meta_d))
        if disc16 == _MP_REM:
            return emit(parse_meteora_remove_from_data(inner, meta_d))
        if disc16 == _MP_BOOTSTRAP:
            return emit(parse_meteora_bootstrap_from_data(inner, meta_d))
        if disc16 == _MP_POOL_CREATED:
            return emit(parse_meteora_pool_created_from_data(inner, meta_d))
        if disc16 == _MP_SET_POOL_FEES:
            return emit(parse_meteora_pools_set_pool_fees_from_data(inner, meta_d))
        return None

    if program_id_b58 == METEORA_DAMM_V2_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_meteora_damm_v2(filter):
            return None
        return emit(parse_meteora_damm_from_buf(_damm_buf_from_inner(disc16, inner), meta_d))

    if program_id_b58 == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_raydium_launchlab(filter):
            return None
        if disc16 == _RAYDIUM_LAUNCHLAB_TRADE:
            return emit(_raydium_launchlab_trade_inner(inner, meta_d))
        if disc16 == _RAYDIUM_LAUNCHLAB_POOL_CREATE:
            return emit(_raydium_launchlab_pool_create_inner(inner, meta_d))
        return None

    if program_id_b58 == METEORA_DLMM_PROGRAM_ID:
        if filter is not None and not event_type_filter_includes_meteora_dlmm(filter):
            return None
        return emit(parse_dlmm_from_program_data(_dlmm_buf_from_inner(disc16, inner), meta_d))

    return None
