"""Inner instruction 解析（16 字节 discriminator），对齐 Rust ``grpc/instruction_parser::parse_inner_instruction``。"""

from __future__ import annotations

import struct
from typing import Optional

from .dex_parsers import (
    _parse_bonk_trade,
    parse_amm_deposit_from_data,
    parse_amm_swap_in_from_data,
    parse_amm_swap_out_from_data,
    parse_amm_withdraw_from_data,
    parse_clmm_collect_from_data,
    parse_clmm_create_from_data,
    parse_clmm_dec_from_data,
    parse_clmm_inc_from_data,
    parse_clmm_swap_from_data,
    parse_cpmm_deposit_from_data,
    parse_cpmm_swap_in_from_data,
    parse_cpmm_swap_out_from_data,
    parse_cpmm_withdraw_from_data,
    parse_dlmm_from_program_data,
    parse_meteora_damm_from_buf,
    parse_orca_liq_dec_from_data,
    parse_orca_liq_inc_from_data,
    parse_orca_traded_from_data,
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
from .grpc_types import EventType, EventTypeFilter, IncludeOnlyFilter
from .grpc_types import (
    event_type_filter_includes_meteora_damm_v2,
    event_type_filter_includes_pumpfun,
    event_type_filter_includes_pumpswap,
)
from .instructions import (
    BONK_LAUNCHPAD_PROGRAM_ID,
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    PUMPFUN_PROGRAM_ID,
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
_CLMM_SWAP = bytes([248, 198, 158, 145, 225, 117, 135, 200, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_INC = bytes([133, 29, 89, 223, 69, 238, 176, 10, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_DEC = bytes([160, 38, 208, 111, 104, 91, 44, 1, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_CREATE_POOL = bytes([233, 146, 209, 142, 207, 104, 64, 188, 155, 167, 108, 32, 122, 76, 173, 64])
_CLMM_COLLECT_FEE = bytes([164, 152, 207, 99, 187, 104, 171, 119, 155, 167, 108, 32, 122, 76, 173, 64])

# Raydium CPMM（all_inner::raydium_cpmm::discriminators）
_CPMM_SWAP_IN = bytes([143, 190, 90, 218, 196, 30, 51, 222, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_SWAP_OUT = bytes([55, 217, 98, 86, 163, 74, 180, 173, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_DEP = bytes([242, 35, 198, 137, 82, 225, 242, 182, 155, 167, 108, 32, 122, 76, 173, 64])
_CPMM_WIT = bytes([183, 18, 70, 156, 148, 109, 161, 34, 155, 167, 108, 32, 122, 76, 173, 64])

# Raydium AMM V4
_AMM_SWAP_IN = bytes([0, 0, 0, 0, 0, 0, 0, 9, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_SWAP_OUT = bytes([0, 0, 0, 0, 0, 0, 0, 11, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_DEP = bytes([0, 0, 0, 0, 0, 0, 0, 3, 155, 167, 108, 32, 122, 76, 173, 64])
_AMM_WIT = bytes([0, 0, 0, 0, 0, 0, 0, 4, 155, 167, 108, 32, 122, 76, 173, 64])

# Orca
_ORCA_TRADED = bytes([225, 202, 73, 175, 147, 43, 160, 150, 155, 167, 108, 32, 122, 76, 173, 64])
_ORCA_LIQ_INC = bytes([30, 7, 144, 181, 102, 254, 155, 161, 155, 167, 108, 32, 122, 76, 173, 64])
_ORCA_LIQ_DEC = bytes([166, 1, 36, 71, 112, 202, 181, 171, 155, 167, 108, 32, 122, 76, 173, 64])

# Meteora Pools AMM
_MP_SWAP = bytes([81, 108, 227, 190, 205, 208, 10, 196, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_ADD = bytes([31, 94, 125, 90, 227, 52, 61, 186, 155, 167, 108, 32, 122, 76, 173, 64])
_MP_REM = bytes([116, 244, 97, 232, 103, 31, 152, 58, 155, 167, 108, 32, 122, 76, 173, 64])

# Meteora DAMM V2（inner 16 字节：magic + 8 字节 event disc，与 ``parse_meteora_damm_from_buf`` 的 disc 一致）
def _damm_buf_from_inner(disc16: bytes, inner: bytes) -> bytes:
    return disc16[8:16] + inner

# Bonk inner
_BONK_TRADE = bytes([80, 120, 100, 200, 150, 75, 60, 40, 155, 167, 108, 32, 122, 76, 173, 64])

# DLMM（8 字节 event disc + payload）
def _dlmm_buf_from_inner(disc16: bytes, inner: bytes) -> bytes:
    return disc16[8:16] + inner


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


def _bonk_trade_inner(data: bytes, meta_d: dict) -> Optional[DexEvent]:
    if len(data) < 81:
        return None
    return _parse_bonk_trade(data, meta_d)


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
    f: EventTypeFilter = filter if filter is not None else IncludeOnlyFilter([])

    if program_id_b58 == PUMPFUN_PROGRAM_ID:
        if not event_type_filter_includes_pumpfun(f):
            return None
        if disc16 == _PUMPFUN_INNER_TRADE:
            ev = parse_trade_from_data(inner, meta_d, is_created_buy)
            return ev if ev.is_valid() else None
        if disc16 == _PUMPFUN_INNER_CREATE:
            ev = parse_create_from_data(inner, meta_d)
            return ev if ev.is_valid() else None
        if disc16 == _PUMPFUN_INNER_MIGRATE:
            ev = parse_migrate_from_data(inner, meta_d)
            return ev if ev.is_valid() else None
        return None

    if program_id_b58 == PUMPSWAP_PROGRAM_ID:
        if not event_type_filter_includes_pumpswap(f):
            return None
        if disc16 == _PS_BUY:
            return parse_ps_buy_from_data(inner, meta_d)
        if disc16 == _PS_SELL:
            return parse_ps_sell_from_data(inner, meta_d)
        if disc16 == _PS_CREATE_POOL:
            return parse_ps_create_pool_from_data(inner, meta_d)
        if disc16 == _PS_ADD_LIQ:
            return parse_ps_add_liq_from_data(inner, meta_d)
        if disc16 == _PS_REMOVE_LIQ:
            return parse_ps_remove_liq_from_data(inner, meta_d)
        return None

    if program_id_b58 == RAYDIUM_CLMM_PROGRAM_ID:
        if disc16 == _CLMM_SWAP:
            return parse_clmm_swap_from_data(inner, meta_d)
        if disc16 == _CLMM_INC:
            return parse_clmm_inc_from_data(inner, meta_d)
        if disc16 == _CLMM_DEC:
            return parse_clmm_dec_from_data(inner, meta_d)
        if disc16 == _CLMM_CREATE_POOL:
            return parse_clmm_create_from_data(inner, meta_d)
        if disc16 == _CLMM_COLLECT_FEE:
            return parse_clmm_collect_from_data(inner, meta_d)
        return None

    if program_id_b58 == RAYDIUM_CPMM_PROGRAM_ID:
        if disc16 == _CPMM_SWAP_IN:
            return parse_cpmm_swap_in_from_data(inner, meta_d)
        if disc16 == _CPMM_SWAP_OUT:
            return parse_cpmm_swap_out_from_data(inner, meta_d)
        if disc16 == _CPMM_DEP:
            return parse_cpmm_deposit_from_data(inner, meta_d)
        if disc16 == _CPMM_WIT:
            return parse_cpmm_withdraw_from_data(inner, meta_d)
        return None

    if program_id_b58 == RAYDIUM_AMM_V4_PROGRAM_ID:
        if disc16 == _AMM_SWAP_IN:
            return parse_amm_swap_in_from_data(inner, meta_d)
        if disc16 == _AMM_SWAP_OUT:
            return parse_amm_swap_out_from_data(inner, meta_d)
        if disc16 == _AMM_DEP:
            return parse_amm_deposit_from_data(inner, meta_d)
        if disc16 == _AMM_WIT:
            return parse_amm_withdraw_from_data(inner, meta_d)
        return None

    if program_id_b58 == ORCA_WHIRLPOOL_PROGRAM_ID:
        if disc16 == _ORCA_TRADED:
            return parse_orca_traded_from_data(inner, meta_d)
        if disc16 == _ORCA_LIQ_INC:
            return parse_orca_liq_inc_from_data(inner, meta_d)
        if disc16 == _ORCA_LIQ_DEC:
            return parse_orca_liq_dec_from_data(inner, meta_d)
        return None

    if program_id_b58 == METEORA_POOLS_PROGRAM_ID:
        if disc16 == _MP_SWAP:
            return _meteora_pools_swap_inner(inner, meta_d)
        if disc16 == _MP_ADD:
            return _meteora_pools_add_inner(inner, meta_d)
        if disc16 == _MP_REM:
            return _meteora_pools_rem_inner(inner, meta_d)
        return None

    if program_id_b58 == METEORA_DAMM_V2_PROGRAM_ID:
        if not event_type_filter_includes_meteora_damm_v2(f):
            return None
        return parse_meteora_damm_from_buf(_damm_buf_from_inner(disc16, inner), meta_d)

    if program_id_b58 == BONK_LAUNCHPAD_PROGRAM_ID:
        if disc16 == _BONK_TRADE:
            return _bonk_trade_inner(inner, meta_d)
        return None

    if program_id_b58 == METEORA_DLMM_PROGRAM_ID:
        return parse_dlmm_from_program_data(_dlmm_buf_from_inner(disc16, inner), meta_d)

    return None
