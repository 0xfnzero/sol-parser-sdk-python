"""指令解析器 - 对齐 Rust 实现"""

from __future__ import annotations

import struct
from typing import List, Optional, Sequence

import base58

from .grpc_types import (
    EventMetadata,
    EventType,
    EventTypeFilter,
    ExcludeFilter,
    IncludeOnlyFilter,
    METEORA_DAMM_V2_FILTER_TYPES,
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
    event_type_filter_allows_instruction_parsing,
)
from .dex_parsers import Z, normalize_pumpfun_ix_name, read_pump_fees_fee_tiers_vec, read_pump_fees_shareholders_vec
from .event_types import (
    DexEvent,
    PumpFeesCreateFeeSharingConfigEvent,
    PumpFeesFees,
    PumpFeesInitializeFeeConfigEvent,
    PumpFeesResetFeeSharingConfigEvent,
    PumpFeesRevokeFeeSharingAuthorityEvent,
    PumpFeesTransferFeeSharingAuthorityEvent,
    PumpFeesUpdateAdminEvent,
    PumpFeesUpdateFeeConfigEvent,
    PumpFeesUpdateFeeSharesEvent,
    PumpFeesUpsertFeeTiersEvent,
    PumpFunCreateEvent,
    PumpFunCreateV2TokenEvent,
    PumpFunTradeEvent,
    PumpSwapBuyEvent,
    PumpSwapSellEvent,
    MeteoraDlmmAddLiquidityEvent,
    MeteoraDlmmClaimFeeEvent,
    MeteoraDlmmClosePositionEvent,
    MeteoraDlmmCreatePositionEvent,
    MeteoraDlmmInitializeBinArrayEvent,
    MeteoraDlmmInitializePoolEvent,
    MeteoraDlmmRemoveLiquidityEvent,
    MeteoraDlmmSwapEvent,
    MeteoraPoolsAddLiquidityEvent,
    MeteoraPoolsPoolCreatedEvent,
    MeteoraPoolsRemoveLiquidityEvent,
    MeteoraPoolsSwapEvent,
    legacy_dict_to_dex_event,
)

# 程序 ID 常量（与 Rust ``instr::program_ids`` 一致，用于 inner / outer 路由）
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
METEORA_DAMM_V2_PROGRAM_ID = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
RAYDIUM_CPMM_PROGRAM_ID = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
RAYDIUM_AMM_V4_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_WHIRLPOOL_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
METEORA_POOLS_PROGRAM_ID = "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"
METEORA_DLMM_PROGRAM_ID = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
METEORA_DBC_PROGRAM_ID = "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"
RAYDIUM_LAUNCHLAB_PROGRAM_ID = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"
PUMPSWAP_FEES_PROGRAM_ID = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
PUMP_FEES_PROGRAM_ID = PUMPSWAP_FEES_PROGRAM_ID


def _d(*xs: int) -> int:
    return struct.unpack("<Q", bytes(xs))[0]


# Discriminator 常量
_DISC_PUMPSWAP_BUY = _d(102, 6, 61, 18, 1, 218, 235, 234)
_DISC_PUMPSWAP_SELL = _d(51, 230, 133, 164, 1, 127, 131, 173)
_DISC_PUMPSWAP_BUY_EXACT_QUOTE_IN = _d(198, 46, 21, 82, 180, 217, 232, 112)

_DISC_DAMM_SWAP    = _d(27, 60, 21, 213, 138, 170, 187, 147)
_DISC_DAMM_SWAP2   = _d(189, 66, 51, 168, 38, 80, 117, 153)
_DISC_DAMM_ADD_LIQ = _d(175, 242, 8, 157, 30, 247, 185, 169)
_DISC_DAMM_REM_LIQ = _d(87, 46, 88, 98, 175, 96, 34, 91)
_DISC_DAMM_CREATE  = _d(156, 15, 119, 198, 29, 181, 221, 55)
_DISC_DAMM_CLOSE   = _d(20, 145, 144, 68, 143, 142, 214, 178)
_DISC_DAMM_INIT    = _d(228, 50, 246, 85, 203, 66, 134, 37)

_DISC_METEORA_POOLS_SWAP = _d(248, 198, 158, 145, 225, 117, 135, 200)
_DISC_METEORA_POOLS_ADD_LIQUIDITY = _d(181, 157, 89, 67, 143, 182, 52, 72)
_DISC_METEORA_POOLS_REMOVE_LIQUIDITY = _d(80, 85, 209, 72, 24, 206, 177, 108)
_DISC_METEORA_POOLS_CREATE_POOL = _d(95, 180, 10, 172, 84, 174, 232, 40)

_DISC_DLMM_ADD_LIQUIDITY = _d(181, 157, 89, 67, 143, 182, 52, 72)
_DISC_DLMM_ADD_LIQUIDITY2 = _d(228, 162, 78, 28, 70, 219, 116, 115)
_DISC_DLMM_CLAIM_FEE = _d(169, 32, 79, 137, 136, 232, 70, 137)
_DISC_DLMM_CLAIM_FEE2 = _d(112, 191, 101, 171, 28, 144, 127, 187)
_DISC_DLMM_CLOSE_POSITION = _d(123, 134, 81, 0, 49, 68, 98, 98)
_DISC_DLMM_CLOSE_POSITION2 = _d(174, 90, 35, 115, 186, 40, 147, 226)
_DISC_DLMM_INITIALIZE_BIN_ARRAY = _d(35, 86, 19, 185, 78, 212, 75, 211)
_DISC_DLMM_INITIALIZE_LB_PAIR = _d(45, 154, 237, 210, 221, 15, 166, 92)
_DISC_DLMM_INITIALIZE_LB_PAIR2 = _d(73, 59, 36, 120, 237, 83, 108, 198)
_DISC_DLMM_INITIALIZE_POSITION = _d(219, 192, 234, 71, 190, 191, 102, 80)
_DISC_DLMM_INITIALIZE_POSITION2 = _d(143, 19, 242, 145, 213, 15, 104, 115)
_DISC_DLMM_INITIALIZE_POSITION_PDA = _d(46, 82, 125, 146, 85, 141, 228, 153)
_DISC_DLMM_REMOVE_LIQUIDITY = _d(80, 85, 209, 72, 24, 206, 177, 108)
_DISC_DLMM_REMOVE_LIQUIDITY2 = _d(230, 215, 82, 127, 241, 101, 227, 146)
_DISC_DLMM_SWAP = _d(248, 198, 158, 145, 225, 117, 135, 200)
_DISC_DLMM_SWAP2 = _d(65, 75, 63, 76, 235, 91, 91, 136)
_DISC_DLMM_SWAP_EXACT_OUT = _d(250, 73, 101, 33, 38, 207, 75, 184)
_DISC_DLMM_SWAP_EXACT_OUT2 = _d(43, 215, 247, 132, 137, 60, 243, 81)
_DISC_DLMM_SWAP_WITH_PRICE_IMPACT = _d(56, 173, 230, 208, 173, 228, 156, 205)
_DISC_DLMM_SWAP_WITH_PRICE_IMPACT2 = _d(74, 98, 192, 214, 177, 51, 75, 51)

_DLMM_INSTRUCTION_DISCS = (
    _DISC_DLMM_INITIALIZE_LB_PAIR,
    _DISC_DLMM_INITIALIZE_LB_PAIR2,
    _DISC_DLMM_INITIALIZE_BIN_ARRAY,
    _DISC_DLMM_ADD_LIQUIDITY,
    _DISC_DLMM_ADD_LIQUIDITY2,
    _DISC_DLMM_REMOVE_LIQUIDITY,
    _DISC_DLMM_REMOVE_LIQUIDITY2,
    _DISC_DLMM_INITIALIZE_POSITION,
    _DISC_DLMM_INITIALIZE_POSITION2,
    _DISC_DLMM_INITIALIZE_POSITION_PDA,
    _DISC_DLMM_SWAP,
    _DISC_DLMM_SWAP2,
    _DISC_DLMM_SWAP_EXACT_OUT,
    _DISC_DLMM_SWAP_EXACT_OUT2,
    _DISC_DLMM_SWAP_WITH_PRICE_IMPACT,
    _DISC_DLMM_SWAP_WITH_PRICE_IMPACT2,
    _DISC_DLMM_CLAIM_FEE,
    _DISC_DLMM_CLAIM_FEE2,
    _DISC_DLMM_CLOSE_POSITION,
    _DISC_DLMM_CLOSE_POSITION2,
)

_DISC_CLMM_SWAP    = _d(248, 198, 158, 145, 225, 117, 135, 200)
_DISC_CLMM_SWAP_V2 = _d(43, 4, 237, 11, 26, 201, 30, 98)
_DISC_CLMM_INC_LIQ = _d(133, 29, 89, 223, 69, 238, 176, 10)
_DISC_CLMM_DEC_LIQ = _d(58, 127, 188, 62, 79, 82, 196, 96)
_DISC_CLMM_CREATE  = _d(233, 146, 209, 142, 207, 104, 64, 188)
_DISC_CLMM_CREATE_CUSTOMIZABLE_POOL = _d(43, 68, 212, 167, 89, 47, 164, 1)
_DISC_CLMM_OPEN_POSITION = _d(135, 128, 47, 77, 15, 152, 240, 49)
_DISC_CLMM_OPEN_POSITION_V2 = _d(77, 184, 74, 214, 112, 86, 241, 199)
_DISC_CLMM_OPEN_POSITION_WITH_TOKEN_22_NFT = _d(77, 255, 174, 82, 125, 29, 201, 46)
_DISC_CLMM_CLOSE_POSITION = _d(123, 134, 81, 0, 49, 68, 98, 98)

_DISC_CPMM_SWAP    = _d(143, 190, 90, 218, 196, 30, 51, 222)
_DISC_CPMM_SWAP_OUT = _d(55, 217, 98, 86, 163, 74, 180, 173)
_DISC_CPMM_INITIALIZE = _d(175, 175, 109, 31, 13, 152, 155, 237)
_DISC_CPMM_DEP     = _d(242, 35, 198, 137, 82, 225, 242, 182)
_DISC_CPMM_WIT     = _d(183, 18, 70, 156, 148, 109, 161, 34)

_DISC_ORCA_SWAP    = _d(248, 198, 158, 145, 225, 117, 135, 200)
_DISC_ORCA_SWAP_V2 = _d(43, 4, 237, 11, 26, 201, 30, 98)
_DISC_ORCA_INC_LIQ = _d(46, 156, 243, 118, 13, 205, 251, 178)
_DISC_ORCA_DEC_LIQ = _d(160, 38, 208, 111, 104, 91, 44, 1)
_DISC_ORCA_INIT_POOL = _d(17, 43, 80, 74, 168, 202, 6, 113)

_DISC_RAYDIUM_LAUNCHLAB_TRADE       = _d(189, 219, 127, 211, 78, 230, 97, 238)
_DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE = _d(151, 215, 226, 9, 118, 161, 115, 174)
_IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_IN = _d(250, 234, 13, 123, 213, 156, 19, 236)
_IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_OUT = _d(24, 211, 116, 40, 105, 3, 153, 56)
_IX_RAYDIUM_LAUNCHLAB_INITIALIZE = _d(175, 175, 109, 31, 13, 152, 155, 237)
_IX_RAYDIUM_LAUNCHLAB_INITIALIZE_V2 = _d(67, 153, 175, 39, 218, 16, 38, 32)
_IX_RAYDIUM_LAUNCHLAB_INITIALIZE_WITH_TOKEN_2022 = _d(37, 190, 126, 222, 44, 154, 171, 17)
_IX_RAYDIUM_LAUNCHLAB_MIGRATE_TO_AMM = _d(207, 82, 192, 145, 254, 207, 145, 223)
_IX_RAYDIUM_LAUNCHLAB_MIGRATE_TO_CPSWAP = _d(136, 92, 200, 103, 28, 218, 144, 140)
_IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_IN = _d(149, 39, 222, 155, 211, 124, 152, 26)
_IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_OUT = _d(95, 200, 71, 34, 8, 9, 11, 166)

_DISC_PFEES_CREATE_FEE_SHARING = _d(195, 78, 86, 76, 111, 52, 251, 213)
_DISC_PFEES_INITIALIZE_FEE_CONFIG = _d(62, 162, 20, 133, 121, 65, 145, 27)
_DISC_PFEES_RESET_FEE_SHARING = _d(10, 2, 182, 95, 16, 127, 129, 186)
_DISC_PFEES_RESET_FEE_SHARING_V2 = _d(169, 245, 17, 209, 94, 91, 248, 128)
_DISC_PFEES_REVOKE_FEE_SHARING = _d(18, 233, 158, 39, 185, 207, 58, 104)
_DISC_PFEES_TRANSFER_FEE_SHARING = _d(202, 10, 75, 200, 164, 34, 210, 96)
_DISC_PFEES_UPDATE_ADMIN = _d(161, 176, 40, 213, 60, 184, 179, 228)
_DISC_PFEES_UPDATE_FEE_CONFIG = _d(104, 184, 103, 242, 88, 151, 107, 20)
_DISC_PFEES_UPDATE_FEE_SHARES = _d(189, 13, 136, 99, 187, 164, 237, 35)
_DISC_PFEES_UPDATE_FEE_SHARES_V2 = _d(111, 251, 49, 6, 78, 78, 106, 18)
_DISC_PFEES_UPSERT_FEE_TIERS = _d(227, 23, 150, 12, 77, 86, 94, 4)

_DISC_PUMPFUN_CREATE = _d(24, 30, 200, 40, 5, 28, 7, 119)
_DISC_PUMPFUN_CREATE_V2 = _d(214, 144, 76, 236, 95, 139, 49, 180)
_DISC_PUMPFUN_BUY = _d(102, 6, 61, 18, 1, 218, 235, 234)
_DISC_PUMPFUN_SELL = _d(51, 230, 133, 164, 1, 127, 131, 173)
_DISC_PUMPFUN_BUY_EXACT_SOL_IN = _d(56, 252, 116, 8, 158, 223, 205, 95)
_DISC_PUMPFUN_BUY_V2 = _d(184, 23, 238, 97, 103, 197, 211, 61)
_DISC_PUMPFUN_SELL_V2 = _d(93, 246, 130, 60, 231, 233, 64, 178)
_DISC_PUMPFUN_BUY_EXACT_QUOTE_IN_V2 = _d(194, 171, 28, 70, 104, 77, 91, 47)


def _get_account_safe(accounts: List[str], index: int) -> str:
    """安全获取账户地址"""
    if index < 0 or index >= len(accounts):
        return Z
    return accounts[index]


def _make_meta(
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> EventMetadata:
    return EventMetadata(
        signature=signature,
        slot=slot,
        tx_index=tx_index,
        block_time_us=block_time_us or 0,
        grpc_recv_us=grpc_recv_us,
    )


def parse_instruction_unified(
    instruction_data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    filter: Optional[EventTypeFilter],
    program_id: str,
) -> Optional[DexEvent]:
    """统一的指令解析入口

    对齐 Rust `parse_instruction_unified`
    """
    if not instruction_data:
        return None
    if isinstance(filter, IncludeOnlyFilter) and not event_type_filter_allows_instruction_parsing(
        filter.include_only
    ):
        return None

    if program_id == PUMPFUN_PROGRAM_ID:
        if not _filter_includes_pumpfun(filter):
            return None
        return _filter_parsed_event(
            parse_pumpfun_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == PUMPSWAP_PROGRAM_ID:
        if not _filter_includes_pumpswap(filter):
            return None
        return _filter_parsed_event(
            parse_pumpswap_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == METEORA_DAMM_V2_PROGRAM_ID:
        if not _filter_includes_meteora_damm_v2(filter):
            return None
        return _filter_parsed_event(
            parse_meteora_damm_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == METEORA_POOLS_PROGRAM_ID:
        if not _filter_includes_meteora_pools(filter):
            return None
        return _filter_parsed_event(
            parse_meteora_pools_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == METEORA_DLMM_PROGRAM_ID:
        if not _filter_includes_meteora_dlmm(filter):
            return None
        return _filter_parsed_event(
            parse_meteora_dlmm_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == PUMP_FEES_PROGRAM_ID:
        if not _filter_includes_pump_fees(filter):
            return None
        return _filter_parsed_event(
            parse_pump_fees_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == RAYDIUM_CLMM_PROGRAM_ID:
        if not _filter_includes_raydium_clmm(filter):
            return None
        return _filter_parsed_event(
            parse_raydium_clmm_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == RAYDIUM_CPMM_PROGRAM_ID:
        if not _filter_includes_raydium_cpmm(filter):
            return None
        return _filter_parsed_event(
            parse_raydium_cpmm_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == RAYDIUM_AMM_V4_PROGRAM_ID:
        if not _filter_includes_raydium_amm_v4(filter):
            return None
        return _filter_parsed_event(
            parse_raydium_amm_v4_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == ORCA_WHIRLPOOL_PROGRAM_ID:
        if not _filter_includes_orca_whirlpool(filter):
            return None
        return _filter_parsed_event(
            parse_orca_whirlpool_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    elif program_id == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
        if not _filter_includes_raydium_launchlab(filter):
            return None
        return _filter_parsed_event(
            parse_raydium_launchlab_instruction(
                instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
            ),
            filter,
        )

    return None


def _disc8(instruction_data: bytes) -> Optional[int]:
    if len(instruction_data) < 8:
        return None
    return struct.unpack_from("<Q", instruction_data, 0)[0]


def normal_instruction_data_may_parse(program_id: str, instruction_data: bytes) -> bool:
    if not instruction_data:
        return False
    if program_id == RAYDIUM_AMM_V4_PROGRAM_ID:
        return instruction_data[0] in (1, 3, 4, 7, 9, 11)
    if program_id == METEORA_DLMM_PROGRAM_ID:
        disc = _disc8(instruction_data)
        return disc in _DLMM_INSTRUCTION_DISCS if disc is not None else False
    disc = _disc8(instruction_data)
    if disc is None:
        return False
    if program_id == METEORA_DAMM_V2_PROGRAM_ID:
        return disc == _DISC_DAMM_INIT
    if program_id == PUMPFUN_PROGRAM_ID:
        return disc in (
            _DISC_PUMPFUN_CREATE,
            _DISC_PUMPFUN_CREATE_V2,
            _DISC_PUMPFUN_BUY,
            _DISC_PUMPFUN_SELL,
            _DISC_PUMPFUN_BUY_EXACT_SOL_IN,
            _DISC_PUMPFUN_BUY_V2,
            _DISC_PUMPFUN_BUY_EXACT_QUOTE_IN_V2,
            _DISC_PUMPFUN_SELL_V2,
        )
    if program_id == PUMPSWAP_PROGRAM_ID:
        return disc in (
            _DISC_PUMPSWAP_BUY,
            _DISC_PUMPSWAP_SELL,
            _d(233, 146, 209, 142, 207, 104, 64, 188),
            _DISC_PUMPSWAP_BUY_EXACT_QUOTE_IN,
            _d(242, 35, 198, 137, 82, 225, 242, 182),
            _d(183, 18, 70, 156, 148, 109, 161, 34),
        )
    if program_id == PUMP_FEES_PROGRAM_ID:
        return disc in (
            _DISC_PFEES_CREATE_FEE_SHARING,
            _DISC_PFEES_INITIALIZE_FEE_CONFIG,
            _DISC_PFEES_RESET_FEE_SHARING,
            _DISC_PFEES_RESET_FEE_SHARING_V2,
            _DISC_PFEES_REVOKE_FEE_SHARING,
            _DISC_PFEES_TRANSFER_FEE_SHARING,
            _DISC_PFEES_UPDATE_ADMIN,
            _DISC_PFEES_UPDATE_FEE_CONFIG,
            _DISC_PFEES_UPDATE_FEE_SHARES,
            _DISC_PFEES_UPDATE_FEE_SHARES_V2,
            _DISC_PFEES_UPSERT_FEE_TIERS,
        )
    if program_id == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
        return disc in (
            _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_IN,
            _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_OUT,
            _IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_IN,
            _IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_OUT,
            _IX_RAYDIUM_LAUNCHLAB_INITIALIZE,
            _IX_RAYDIUM_LAUNCHLAB_INITIALIZE_V2,
            _IX_RAYDIUM_LAUNCHLAB_INITIALIZE_WITH_TOKEN_2022,
        )
    if program_id == RAYDIUM_CPMM_PROGRAM_ID:
        return disc in (
            _DISC_CPMM_SWAP,
            _DISC_CPMM_SWAP_OUT,
            _DISC_CPMM_INITIALIZE,
            _DISC_CPMM_DEP,
            _DISC_CPMM_WIT,
        )
    if program_id == RAYDIUM_CLMM_PROGRAM_ID:
        return disc in (
            _DISC_CLMM_SWAP,
            _DISC_CLMM_SWAP_V2,
            _DISC_CLMM_INC_LIQ,
            _DISC_CLMM_DEC_LIQ,
            _DISC_CLMM_CREATE,
            _DISC_CLMM_CREATE_CUSTOMIZABLE_POOL,
            _DISC_CLMM_OPEN_POSITION,
            _DISC_CLMM_OPEN_POSITION_V2,
            _DISC_CLMM_OPEN_POSITION_WITH_TOKEN_22_NFT,
            _DISC_CLMM_CLOSE_POSITION,
        )
    if program_id == ORCA_WHIRLPOOL_PROGRAM_ID:
        return disc in (
            _DISC_ORCA_SWAP,
            _DISC_ORCA_SWAP_V2,
            _DISC_ORCA_INC_LIQ,
            _DISC_ORCA_DEC_LIQ,
            _DISC_ORCA_INIT_POOL,
        )
    if program_id == METEORA_POOLS_PROGRAM_ID:
        return disc in (
            _DISC_METEORA_POOLS_SWAP,
            _DISC_METEORA_POOLS_ADD_LIQUIDITY,
            _DISC_METEORA_POOLS_REMOVE_LIQUIDITY,
            _DISC_METEORA_POOLS_CREATE_POOL,
        )
    return False


def parse_inner_compiled_instruction_if_supported(
    instruction_data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    filter: Optional[EventTypeFilter],
    program_id: str,
) -> Optional[DexEvent]:
    if not normal_instruction_data_may_parse(program_id, instruction_data):
        return None
    return parse_instruction_unified(
        instruction_data,
        accounts,
        signature,
        slot,
        tx_index,
        block_time_us,
        grpc_recv_us,
        filter,
        program_id,
    )


def parse_pumpfun_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpFun 指令
    
    注意：legacy Buy/Sell 仍主要通过统一的 TRADE 日志事件捕获，
    这里也解析 legacy/v2 trade 外层指令，用于和 Rust instruction parser 保持一致。
    
    Discriminators（8字节小端）：
    - CREATE: [24, 30, 200, 40, 5, 28, 7, 119]
    - CREATE_V2: [214, 144, 76, 236, 95, 139, 49, 180]
    """
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    # PumpFun Create: [24, 30, 200, 40, 5, 28, 7, 119]
    if discriminator == _DISC_PUMPFUN_CREATE:
        return _parse_pumpfun_create(data, accounts, meta)

    # PumpFun CreateV2: [214, 144, 76, 236, 95, 139, 49, 180]
    if discriminator == _DISC_PUMPFUN_CREATE_V2:
        return _parse_pumpfun_create_v2(data, accounts, meta)

    if discriminator == _DISC_PUMPFUN_BUY:
        return _parse_pumpfun_legacy_buy("buy", data[8:], accounts, meta)

    if discriminator == _DISC_PUMPFUN_BUY_EXACT_SOL_IN:
        return _parse_pumpfun_legacy_buy("buy_exact_sol_in", data[8:], accounts, meta)

    if discriminator == _DISC_PUMPFUN_SELL:
        return _parse_pumpfun_legacy_sell(data[8:], accounts, meta)

    if discriminator == _DISC_PUMPFUN_BUY_V2:
        return _parse_pumpfun_trade_v2("buy_v2", data[8:], accounts, meta)

    if discriminator == _DISC_PUMPFUN_BUY_EXACT_QUOTE_IN_V2:
        return _parse_pumpfun_trade_v2("buy_exact_quote_in_v2", data[8:], accounts, meta)

    if discriminator == _DISC_PUMPFUN_SELL_V2:
        return _parse_pumpfun_trade_v2("sell_v2", data[8:], accounts, meta)

    return None


def _u64_payload(data: bytes, offset: int) -> int:
    if offset + 8 <= len(data):
        return struct.unpack_from("<Q", data, offset)[0]
    return 0


def _read_borsh_string(data: bytes, offset: int) -> tuple[str, int]:
    if offset + 4 > len(data):
        raise ValueError("short borsh string length")
    size = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    end = offset + size
    if end > len(data):
        raise ValueError("short borsh string data")
    return data[offset:end].decode("utf-8", errors="replace"), end


def _parse_pumpfun_legacy_buy(
    ix_name: str,
    payload: bytes,
    accounts: List[str],
    meta: EventMetadata,
) -> Optional[DexEvent]:
    if len(accounts) < 16:
        return None
    first = _u64_payload(payload, 0)
    second = _u64_payload(payload, 8)
    exact_sol_in = ix_name == "buy_exact_sol_in"
    buyback_fee_recipient = _get_account_safe(accounts, 17)

    return DexEvent(
        type=EventType.PUMP_FUN_BUY_EXACT_SOL_IN if exact_sol_in else EventType.PUMP_FUN_BUY,
        data=PumpFunTradeEvent(
            metadata=meta,
            mint=_get_account_safe(accounts, 2),
            global_account=_get_account_safe(accounts, 0),
            fee_recipient=_get_account_safe(accounts, 1),
            bonding_curve=_get_account_safe(accounts, 3),
            bonding_curve_v2=_get_account_safe(accounts, 16),
            associated_bonding_curve=_get_account_safe(accounts, 4),
            associated_user=_get_account_safe(accounts, 5),
            user=_get_account_safe(accounts, 6),
            system_program=_get_account_safe(accounts, 7),
            token_program=_get_account_safe(accounts, 8),
            creator_vault=_get_account_safe(accounts, 9),
            event_authority=_get_account_safe(accounts, 10),
            program=_get_account_safe(accounts, 11),
            global_volume_accumulator=_get_account_safe(accounts, 12),
            user_volume_accumulator=_get_account_safe(accounts, 13),
            fee_config=_get_account_safe(accounts, 14),
            fee_program=_get_account_safe(accounts, 15),
            buyback_fee_recipient=buyback_fee_recipient,
            is_buy=True,
            sol_amount=first if exact_sol_in else second,
            token_amount=second if exact_sol_in else first,
            amount=second if exact_sol_in else first,
            max_sol_cost=first if exact_sol_in else second,
            spendable_sol_in=first if exact_sol_in else 0,
            min_tokens_out=second if exact_sol_in else 0,
            track_volume=(payload[16] != 0) if len(payload) > 16 else False,
            ix_name=ix_name,
            extra_instruction_account=buyback_fee_recipient if buyback_fee_recipient != Z else "",
        ),
    )


def _parse_pumpfun_legacy_sell(
    payload: bytes,
    accounts: List[str],
    meta: EventMetadata,
) -> Optional[DexEvent]:
    if len(accounts) < 14:
        return None
    amount = _u64_payload(payload, 0)
    min_sol_output = _u64_payload(payload, 8)
    legacy_user_volume_accumulator = Z
    legacy_bonding_curve_v2 = _get_account_safe(accounts, 14)
    legacy_buyback_fee_recipient = Z
    if len(accounts) >= 17:
        legacy_user_volume_accumulator = _get_account_safe(accounts, 14)
        legacy_bonding_curve_v2 = _get_account_safe(accounts, 15)
        legacy_buyback_fee_recipient = _get_account_safe(accounts, 16)
    elif len(accounts) >= 16:
        legacy_bonding_curve_v2 = _get_account_safe(accounts, 14)
        legacy_buyback_fee_recipient = _get_account_safe(accounts, 15)

    return DexEvent(
        type=EventType.PUMP_FUN_SELL,
        data=PumpFunTradeEvent(
            metadata=meta,
            mint=_get_account_safe(accounts, 2),
            is_buy=False,
            global_account=_get_account_safe(accounts, 0),
            fee_recipient=_get_account_safe(accounts, 1),
            bonding_curve=_get_account_safe(accounts, 3),
            bonding_curve_v2=legacy_bonding_curve_v2,
            associated_bonding_curve=_get_account_safe(accounts, 4),
            associated_user=_get_account_safe(accounts, 5),
            user=_get_account_safe(accounts, 6),
            system_program=_get_account_safe(accounts, 7),
            creator_vault=_get_account_safe(accounts, 8),
            token_program=_get_account_safe(accounts, 9),
            event_authority=_get_account_safe(accounts, 10),
            program=_get_account_safe(accounts, 11),
            user_volume_accumulator=legacy_user_volume_accumulator,
            fee_config=_get_account_safe(accounts, 12),
            fee_program=_get_account_safe(accounts, 13),
            buyback_fee_recipient=legacy_buyback_fee_recipient,
            sol_amount=min_sol_output,
            token_amount=amount,
            amount=amount,
            min_sol_output=min_sol_output,
            ix_name="sell",
            extra_instruction_account=legacy_buyback_fee_recipient if legacy_buyback_fee_recipient != Z else "",
        ),
    )


def _parse_pumpfun_trade_v2(
    ix_name: str,
    payload: bytes,
    accounts: List[str],
    meta: EventMetadata,
) -> Optional[DexEvent]:
    min_accounts = 26 if ix_name == "sell_v2" else 27
    if len(accounts) < min_accounts:
        return None
    first = _u64_payload(payload, 0)
    second = _u64_payload(payload, 8)
    if ix_name == "buy_exact_quote_in_v2":
        sol_amount, token_amount = first, second
    else:
        token_amount, sol_amount = first, second

    if ix_name == "buy_v2":
        event_type = EventType.PUMP_FUN_BUY
    elif ix_name == "sell_v2":
        event_type = EventType.PUMP_FUN_SELL
    else:
        event_type = EventType.PUMP_FUN_BUY
    normalized_ix_name = normalize_pumpfun_ix_name(ix_name)

    return DexEvent(
        type=event_type,
        data=PumpFunTradeEvent(
            metadata=meta,
            mint=_get_account_safe(accounts, 1),
            quote_mint=_get_account_safe(accounts, 2),
            global_account=_get_account_safe(accounts, 0),
            bonding_curve=_get_account_safe(accounts, 10),
            user=_get_account_safe(accounts, 13),
            sol_amount=sol_amount,
            token_amount=token_amount,
            amount=second if ix_name == "buy_exact_quote_in_v2" else first,
            max_sol_cost=0 if ix_name == "buy_exact_quote_in_v2" else (0 if ix_name == "sell_v2" else second),
            min_sol_output=second if ix_name == "sell_v2" else 0,
            spendable_quote_in=first if ix_name == "buy_exact_quote_in_v2" else 0,
            min_tokens_out=second if ix_name == "buy_exact_quote_in_v2" else 0,
            quote_amount=first if ix_name == "buy_exact_quote_in_v2" else 0,
            fee_recipient=_get_account_safe(accounts, 6),
            is_buy=ix_name != "sell_v2",
            is_created_buy=False,
            ix_name=normalized_ix_name,
            associated_bonding_curve=_get_account_safe(accounts, 11),
            associated_user=_get_account_safe(accounts, 14),
            system_program=_get_account_safe(accounts, 23 if ix_name == "sell_v2" else 24),
            token_program=_get_account_safe(accounts, 3),
            quote_token_program=_get_account_safe(accounts, 4),
            associated_token_program=_get_account_safe(accounts, 5),
            creator_vault=_get_account_safe(accounts, 16),
            associated_quote_fee_recipient=_get_account_safe(accounts, 7),
            buyback_fee_recipient=_get_account_safe(accounts, 8),
            associated_quote_buyback_fee_recipient=_get_account_safe(accounts, 9),
            associated_quote_bonding_curve=_get_account_safe(accounts, 12),
            associated_quote_user=_get_account_safe(accounts, 15),
            associated_creator_vault=_get_account_safe(accounts, 17),
            sharing_config=_get_account_safe(accounts, 18),
            event_authority=_get_account_safe(accounts, 24 if ix_name == "sell_v2" else 25),
            program=_get_account_safe(accounts, 25 if ix_name == "sell_v2" else 26),
            global_volume_accumulator="" if ix_name == "sell_v2" else _get_account_safe(accounts, 19),
            user_volume_accumulator=_get_account_safe(accounts, 19 if ix_name == "sell_v2" else 20),
            associated_user_volume_accumulator=_get_account_safe(accounts, 20 if ix_name == "sell_v2" else 21),
            fee_config=_get_account_safe(accounts, 21 if ix_name == "sell_v2" else 22),
            fee_program=_get_account_safe(accounts, 22 if ix_name == "sell_v2" else 23),
        ),
    )


def _parse_pumpfun_create(data: bytes, accounts: List[str], meta: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpFun Create 指令"""
    offset = 8  # Skip discriminator
    try:
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        symbol_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        symbol = data[offset:offset + symbol_len].decode('utf-8')
        offset += symbol_len

        uri_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        uri = data[offset:offset + uri_len].decode('utf-8')
        offset += uri_len
    except Exception:
        return None

    creator = Z
    if offset + 32 <= len(data):
        creator = base58.b58encode(data[offset:offset + 32]).decode('ascii')

    return DexEvent(
        type=EventType.PUMP_FUN_CREATE,
        data=PumpFunCreateEvent(
            metadata=meta,
            name=name,
            symbol=symbol,
            uri=uri,
            mint=_get_account_safe(accounts, 0),
            bonding_curve=_get_account_safe(accounts, 2),
            user=_get_account_safe(accounts, 7),
            creator=creator,
            token_program=Z,
            timestamp=0,
            virtual_token_reserves=0,
            virtual_sol_reserves=0,
            real_token_reserves=0,
            token_total_supply=0,
            is_mayhem_mode=False,
            is_cashback_enabled=False,
            quote_mint=Z,
            virtual_quote_reserves=0,
        ),
    )


def _parse_pumpfun_create_v2(data: bytes, accounts: List[str], meta: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpFun CreateV2 指令
    
    对齐 TS pumpfun_ix.ts CREATE_V2 处理
    """
    if len(accounts) < 16:
        return None
        
    offset = 8  # Skip discriminator
    try:
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        symbol_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        symbol = data[offset:offset + symbol_len].decode('utf-8')
        offset += symbol_len

        uri_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        uri = data[offset:offset + uri_len].decode('utf-8')
        offset += uri_len
    except Exception:
        return None

    if offset + 33 > len(data):
        return None
    creator = base58.b58encode(data[offset:offset + 32]).decode('ascii')
    offset += 32
    is_mayhem_mode = data[offset] == 1
    offset += 1
    is_cashback_enabled = data[offset] == 1 if offset < len(data) else False

    return DexEvent(
        type=EventType.PUMP_FUN_CREATE_V2,
        data=PumpFunCreateV2TokenEvent(
            metadata=meta,
            name=name,
            symbol=symbol,
            uri=uri,
            mint=_get_account_safe(accounts, 0),
            mint_authority=_get_account_safe(accounts, 1),
            bonding_curve=_get_account_safe(accounts, 2),
            associated_bonding_curve=_get_account_safe(accounts, 3),
            global_account=_get_account_safe(accounts, 4),
            user=_get_account_safe(accounts, 5),
            system_program=_get_account_safe(accounts, 6),
            token_program=_get_account_safe(accounts, 7),
            associated_token_program=_get_account_safe(accounts, 8),
            mayhem_program_id=_get_account_safe(accounts, 9),
            global_params=_get_account_safe(accounts, 10),
            sol_vault=_get_account_safe(accounts, 11),
            mayhem_state=_get_account_safe(accounts, 12),
            mayhem_token_vault=_get_account_safe(accounts, 13),
            event_authority=_get_account_safe(accounts, 14),
            program=_get_account_safe(accounts, 15),
            creator=creator,
            timestamp=0,
            virtual_token_reserves=0,
            virtual_sol_reserves=0,
            real_token_reserves=0,
            token_total_supply=0,
            is_mayhem_mode=is_mayhem_mode,
            is_cashback_enabled=is_cashback_enabled,
            quote_mint=_get_account_safe(accounts, 16) or Z,
            quote_vault=_get_account_safe(accounts, 17),
            quote_token_program=_get_account_safe(accounts, 18),
            virtual_quote_reserves=0,
            observed_fee_recipient="",
        ),
    )


def parse_pumpswap_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpSwap 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)
    payload = data[8:]

    def read_args() -> tuple[int, int]:
        if len(payload) < 16:
            return 0, 0
        return struct.unpack_from("<QQ", payload, 0)

    def fill_buy_tail(ev: PumpSwapBuyEvent) -> None:
        if len(accounts) >= 27:
            ev.pool_v2 = _get_account_safe(accounts, 24)
            ev.fee_recipient = _get_account_safe(accounts, 25)
            ev.fee_recipient_quote_token_account = _get_account_safe(accounts, 26)
        elif len(accounts) >= 26:
            ev.pool_v2 = _get_account_safe(accounts, 23)
            ev.fee_recipient = _get_account_safe(accounts, 24)
            ev.fee_recipient_quote_token_account = _get_account_safe(accounts, 25)
        elif len(accounts) >= 24:
            ev.pool_v2 = _get_account_safe(accounts, 23)

    def fill_sell_tail(ev: PumpSwapSellEvent) -> None:
        if len(accounts) >= 26:
            ev.pool_v2 = _get_account_safe(accounts, 23)
            ev.fee_recipient = _get_account_safe(accounts, 24)
            ev.fee_recipient_quote_token_account = _get_account_safe(accounts, 25)
        elif len(accounts) >= 24:
            ev.pool_v2 = _get_account_safe(accounts, 21)
            ev.fee_recipient = _get_account_safe(accounts, 22)
            ev.fee_recipient_quote_token_account = _get_account_safe(accounts, 23)
        elif len(accounts) >= 22:
            ev.pool_v2 = _get_account_safe(accounts, 21)

    if discriminator in (_DISC_PUMPSWAP_BUY, _DISC_PUMPSWAP_BUY_EXACT_QUOTE_IN):
        if len(accounts) < 13:
            return None
        first, second = read_args()
        if discriminator == _DISC_PUMPSWAP_BUY_EXACT_QUOTE_IN:
            base_amount_out, max_quote_amount_in = second, first
        else:
            base_amount_out, max_quote_amount_in = first, second
        ev = PumpSwapBuyEvent(
            metadata=meta,
            base_amount_out=base_amount_out,
            max_quote_amount_in=max_quote_amount_in,
            pool=_get_account_safe(accounts, 0),
            user=_get_account_safe(accounts, 1),
            base_mint=_get_account_safe(accounts, 3),
            quote_mint=_get_account_safe(accounts, 4),
            user_base_token_account=_get_account_safe(accounts, 5),
            user_quote_token_account=_get_account_safe(accounts, 6),
            pool_base_token_account=_get_account_safe(accounts, 7),
            pool_quote_token_account=_get_account_safe(accounts, 8),
            protocol_fee_recipient=_get_account_safe(accounts, 9),
            protocol_fee_recipient_token_account=_get_account_safe(accounts, 10),
            coin_creator_vault_ata=_get_account_safe(accounts, 17) if len(accounts) >= 19 else Z,
            coin_creator_vault_authority=_get_account_safe(accounts, 18) if len(accounts) >= 19 else Z,
            base_token_program=_get_account_safe(accounts, 11),
            quote_token_program=_get_account_safe(accounts, 12),
        )
        fill_buy_tail(ev)
        return DexEvent(type=EventType.PUMP_SWAP_BUY, data=ev)
    if discriminator == _DISC_PUMPSWAP_SELL:
        if len(accounts) < 13:
            return None
        base_amount_in, min_quote_amount_out = read_args()
        ev = PumpSwapSellEvent(
            metadata=meta,
            base_amount_in=base_amount_in,
            min_quote_amount_out=min_quote_amount_out,
            pool=_get_account_safe(accounts, 0),
            user=_get_account_safe(accounts, 1),
            base_mint=_get_account_safe(accounts, 3),
            quote_mint=_get_account_safe(accounts, 4),
            user_base_token_account=_get_account_safe(accounts, 5),
            user_quote_token_account=_get_account_safe(accounts, 6),
            pool_base_token_account=_get_account_safe(accounts, 7),
            pool_quote_token_account=_get_account_safe(accounts, 8),
            protocol_fee_recipient=_get_account_safe(accounts, 9),
            protocol_fee_recipient_token_account=_get_account_safe(accounts, 10),
            coin_creator_vault_ata=_get_account_safe(accounts, 17) if len(accounts) >= 19 else Z,
            coin_creator_vault_authority=_get_account_safe(accounts, 18) if len(accounts) >= 19 else Z,
            base_token_program=_get_account_safe(accounts, 11),
            quote_token_program=_get_account_safe(accounts, 12),
        )
        fill_sell_tail(ev)
        return DexEvent(type=EventType.PUMP_SWAP_SELL, data=ev)

    return None


def parse_meteora_damm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Meteora DAMM V2 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator in (_DISC_DAMM_SWAP, _DISC_DAMM_SWAP2):
        return legacy_dict_to_dex_event({"MeteoraDammV2Swap": {"metadata": meta}})
    if discriminator == _DISC_DAMM_ADD_LIQ:
        return legacy_dict_to_dex_event({"MeteoraDammV2AddLiquidity": {"metadata": meta}})
    if discriminator == _DISC_DAMM_REM_LIQ:
        return legacy_dict_to_dex_event({"MeteoraDammV2RemoveLiquidity": {"metadata": meta}})
    if discriminator == _DISC_DAMM_CREATE:
        return legacy_dict_to_dex_event({"MeteoraDammV2CreatePosition": {"metadata": meta}})
    if discriminator == _DISC_DAMM_CLOSE:
        return legacy_dict_to_dex_event({"MeteoraDammV2ClosePosition": {"metadata": meta}})
    if discriminator == _DISC_DAMM_INIT:
        return legacy_dict_to_dex_event({"MeteoraDammV2InitializePool": {"metadata": meta}})

    return None


def parse_meteora_pools_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    if len(data) < 8:
        return None
    discriminator = struct.unpack_from("<Q", data, 0)[0]
    payload = data[8:]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_METEORA_POOLS_SWAP:
        if len(payload) < 16 or not accounts:
            return None
        return DexEvent(
            type=EventType.METEORA_POOLS_SWAP,
            data=MeteoraPoolsSwapEvent(
                metadata=meta,
                in_amount=struct.unpack_from("<Q", payload, 0)[0],
                out_amount=struct.unpack_from("<Q", payload, 8)[0],
                trade_fee=0,
                admin_fee=0,
                host_fee=0,
            ),
        )

    if discriminator == _DISC_METEORA_POOLS_ADD_LIQUIDITY:
        if len(payload) < 24 or not accounts:
            return None
        return DexEvent(
            type=EventType.METEORA_POOLS_ADD_LIQUIDITY,
            data=MeteoraPoolsAddLiquidityEvent(
                metadata=meta,
                lp_mint_amount=struct.unpack_from("<Q", payload, 0)[0],
                token_a_amount=struct.unpack_from("<Q", payload, 8)[0],
                token_b_amount=struct.unpack_from("<Q", payload, 16)[0],
            ),
        )

    if discriminator == _DISC_METEORA_POOLS_REMOVE_LIQUIDITY:
        if len(payload) < 24 or not accounts:
            return None
        return DexEvent(
            type=EventType.METEORA_POOLS_REMOVE_LIQUIDITY,
            data=MeteoraPoolsRemoveLiquidityEvent(
                metadata=meta,
                lp_unmint_amount=struct.unpack_from("<Q", payload, 0)[0],
                token_a_out_amount=struct.unpack_from("<Q", payload, 8)[0],
                token_b_out_amount=struct.unpack_from("<Q", payload, 16)[0],
            ),
        )

    if discriminator == _DISC_METEORA_POOLS_CREATE_POOL:
        if len(payload) < 1 + 6 * 8 or len(accounts) <= 9:
            return None
        return DexEvent(
            type=EventType.METEORA_POOLS_POOL_CREATED,
            data=MeteoraPoolsPoolCreatedEvent(
                metadata=meta,
                lp_mint=accounts[4],
                token_a_mint=accounts[8],
                token_b_mint=accounts[9],
                pool_type=payload[0],
                pool=accounts[0],
            ),
        )

    return None


def parse_meteora_dlmm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    if len(data) < 8 or not accounts:
        return None
    discriminator = struct.unpack_from("<Q", data, 0)[0]
    payload = data[8:]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_DLMM_INITIALIZE_LB_PAIR:
        if len(payload) < 6:
            return None
        pool = _get_account_safe(accounts, 0)
        return DexEvent(
            type=EventType.METEORA_DLMM_INITIALIZE_POOL,
            data=MeteoraDlmmInitializePoolEvent(
                metadata=meta,
                pool=pool,
                creator=_get_account_safe(accounts, 8),
                active_bin_id=struct.unpack_from("<i", payload, 0)[0],
                bin_step=struct.unpack_from("<H", payload, 4)[0],
            ),
        )

    if discriminator == _DISC_DLMM_INITIALIZE_LB_PAIR2:
        if len(payload) < 4:
            return None
        pool = _get_account_safe(accounts, 0)
        return DexEvent(
            type=EventType.METEORA_DLMM_INITIALIZE_POOL,
            data=MeteoraDlmmInitializePoolEvent(
                metadata=meta,
                pool=pool,
                creator=_get_account_safe(accounts, 8),
                active_bin_id=struct.unpack_from("<i", payload, 0)[0],
                bin_step=0,
            ),
        )

    if discriminator == _DISC_DLMM_INITIALIZE_BIN_ARRAY:
        if len(payload) < 8:
            return None
        pool = _get_account_safe(accounts, 0)
        return DexEvent(
            type=EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
            data=MeteoraDlmmInitializeBinArrayEvent(
                metadata=meta,
                pool=pool,
                bin_array=_get_account_safe(accounts, 1),
                index=struct.unpack_from("<q", payload, 0)[0],
            ),
        )

    if discriminator in (_DISC_DLMM_ADD_LIQUIDITY, _DISC_DLMM_ADD_LIQUIDITY2):
        pool = _get_account_safe(accounts, 1)
        sender_index = 9 if discriminator == _DISC_DLMM_ADD_LIQUIDITY2 else 11
        return DexEvent(
            type=EventType.METEORA_DLMM_ADD_LIQUIDITY,
            data=MeteoraDlmmAddLiquidityEvent(
                metadata=meta,
                pool=pool,
                from_addr=_get_account_safe(accounts, sender_index),
                position=_get_account_safe(accounts, 0),
                amounts=[0, 0],
                active_bin_id=0,
            ),
        )

    if discriminator in (_DISC_DLMM_REMOVE_LIQUIDITY, _DISC_DLMM_REMOVE_LIQUIDITY2):
        pool = _get_account_safe(accounts, 1)
        sender_index = 9 if discriminator == _DISC_DLMM_REMOVE_LIQUIDITY2 else 11
        return DexEvent(
            type=EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
            data=MeteoraDlmmRemoveLiquidityEvent(
                metadata=meta,
                pool=pool,
                from_addr=_get_account_safe(accounts, sender_index),
                position=_get_account_safe(accounts, 0),
                amounts=[0, 0],
                active_bin_id=0,
            ),
        )

    if discriminator in (
        _DISC_DLMM_INITIALIZE_POSITION,
        _DISC_DLMM_INITIALIZE_POSITION2,
        _DISC_DLMM_INITIALIZE_POSITION_PDA,
    ):
        if len(payload) < 8:
            return None
        lower_bin_id, width = struct.unpack_from("<ii", payload, 0)
        if width < 0:
            return None
        pda = discriminator == _DISC_DLMM_INITIALIZE_POSITION_PDA
        position_index, pool_index, owner_index = (2, 3, 4) if pda else (1, 2, 3)
        return DexEvent(
            type=EventType.METEORA_DLMM_CREATE_POSITION,
            data=MeteoraDlmmCreatePositionEvent(
                metadata=meta,
                pool=_get_account_safe(accounts, pool_index),
                position=_get_account_safe(accounts, position_index),
                owner=_get_account_safe(accounts, owner_index),
                lower_bin_id=lower_bin_id,
                width=width,
            ),
        )

    if discriminator in (_DISC_DLMM_SWAP, _DISC_DLMM_SWAP2):
        if len(payload) < 8:
            return None
        pool = _get_account_safe(accounts, 0)
        return DexEvent(
            type=EventType.METEORA_DLMM_SWAP,
            data=MeteoraDlmmSwapEvent(
                metadata=meta,
                pool=pool,
                from_addr=_get_account_safe(accounts, 10),
                start_bin_id=0,
                end_bin_id=0,
                amount_in=struct.unpack_from("<Q", payload, 0)[0],
                amount_out=0,
                swap_for_y=False,
                fee=0,
                protocol_fee=0,
                fee_bps="0",
                host_fee=0,
            ),
        )

    if discriminator in (
        _DISC_DLMM_SWAP_EXACT_OUT,
        _DISC_DLMM_SWAP_EXACT_OUT2,
        _DISC_DLMM_SWAP_WITH_PRICE_IMPACT,
        _DISC_DLMM_SWAP_WITH_PRICE_IMPACT2,
    ):
        exact_out = discriminator in (_DISC_DLMM_SWAP_EXACT_OUT, _DISC_DLMM_SWAP_EXACT_OUT2)
        if len(payload) < (16 if exact_out else 8):
            return None
        amount_out = 0
        if exact_out:
            amount_out = struct.unpack_from("<Q", payload, 8)[0]
        pool = _get_account_safe(accounts, 0)
        return DexEvent(
            type=EventType.METEORA_DLMM_SWAP,
            data=MeteoraDlmmSwapEvent(
                metadata=meta,
                pool=pool,
                from_addr=_get_account_safe(accounts, 10),
                start_bin_id=0,
                end_bin_id=0,
                amount_in=struct.unpack_from("<Q", payload, 0)[0],
                amount_out=amount_out,
                swap_for_y=False,
                fee=0,
                protocol_fee=0,
                fee_bps="0",
                host_fee=0,
            ),
        )

    if discriminator in (_DISC_DLMM_CLAIM_FEE, _DISC_DLMM_CLAIM_FEE2):
        pool = _get_account_safe(accounts, 0)
        owner_index = 2 if discriminator == _DISC_DLMM_CLAIM_FEE2 else 4
        return DexEvent(
            type=EventType.METEORA_DLMM_CLAIM_FEE,
            data=MeteoraDlmmClaimFeeEvent(
                metadata=meta,
                pool=pool,
                position=_get_account_safe(accounts, 1),
                owner=_get_account_safe(accounts, owner_index),
                fee_x=0,
                fee_y=0,
            ),
        )

    if discriminator in (_DISC_DLMM_CLOSE_POSITION, _DISC_DLMM_CLOSE_POSITION2):
        position = _get_account_safe(accounts, 0)
        v2 = discriminator == _DISC_DLMM_CLOSE_POSITION2
        return DexEvent(
            type=EventType.METEORA_DLMM_CLOSE_POSITION,
            data=MeteoraDlmmClosePositionEvent(
                metadata=meta,
                pool=Z if v2 else _get_account_safe(accounts, 1),
                position=position,
                owner=_get_account_safe(accounts, 1 if v2 else 4),
            ),
        )

    return None


def _read_pump_fees_fees_at(data: bytes, o: List[int]) -> Optional[PumpFeesFees]:
    if o[0] + 24 > len(data):
        return None
    lp_fee_bps = struct.unpack_from("<Q", data, o[0])[0]
    o[0] += 8
    protocol_fee_bps = struct.unpack_from("<Q", data, o[0])[0]
    o[0] += 8
    creator_fee_bps = struct.unpack_from("<Q", data, o[0])[0]
    o[0] += 8
    return PumpFeesFees(
        lp_fee_bps=lp_fee_bps,
        protocol_fee_bps=protocol_fee_bps,
        creator_fee_bps=creator_fee_bps,
    )


def parse_pump_fees_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Pump Fees 外层指令（对齐 Rust `pump_fees::parse_instruction`）"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_PFEES_CREATE_FEE_SHARING:
        admin = _get_account_safe(accounts, 2)
        mint = _get_account_safe(accounts, 4)
        if admin == Z or mint == Z:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_CREATE_FEE_SHARING_CONFIG,
            data=PumpFeesCreateFeeSharingConfigEvent(
                metadata=meta,
                timestamp=0,
                mint=mint,
                bonding_curve=_get_account_safe(accounts, 7),
                pool=accounts[10] if len(accounts) > 10 else "",
                sharing_config=_get_account_safe(accounts, 5),
                admin=admin,
                initial_shareholders=[],
                status="Active",
            ),
        )

    if discriminator in (_DISC_PFEES_UPDATE_FEE_SHARES, _DISC_PFEES_UPDATE_FEE_SHARES_V2):
        if len(accounts) < 8:
            return None
        o = [8]
        shareholders = read_pump_fees_shareholders_vec(data, o)
        if shareholders is None or o[0] != len(data):
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_UPDATE_FEE_SHARES,
            data=PumpFeesUpdateFeeSharesEvent(
                metadata=meta,
                timestamp=0,
                mint=_get_account_safe(accounts, 4),
                sharing_config=_get_account_safe(accounts, 5),
                admin=_get_account_safe(accounts, 2),
                bonding_curve=_get_account_safe(accounts, 6),
                pump_creator_vault=_get_account_safe(accounts, 7),
                new_shareholders=shareholders,
            ),
        )

    if discriminator == _DISC_PFEES_INITIALIZE_FEE_CONFIG:
        if len(accounts) < 2:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_INITIALIZE_FEE_CONFIG,
            data=PumpFeesInitializeFeeConfigEvent(
                metadata=meta,
                timestamp=0,
                admin=accounts[0],
                fee_config=accounts[1],
            ),
        )

    if discriminator in (_DISC_PFEES_RESET_FEE_SHARING, _DISC_PFEES_RESET_FEE_SHARING_V2):
        if len(accounts) < 7:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_RESET_FEE_SHARING_CONFIG,
            data=PumpFeesResetFeeSharingConfigEvent(
                metadata=meta,
                timestamp=0,
                mint=accounts[5],
                sharing_config=accounts[6],
                old_admin=accounts[3],
                old_shareholders=[],
                new_admin=accounts[0],
                new_shareholders=[],
            ),
        )

    if discriminator == _DISC_PFEES_REVOKE_FEE_SHARING:
        if len(accounts) < 4:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_REVOKE_FEE_SHARING_AUTHORITY,
            data=PumpFeesRevokeFeeSharingAuthorityEvent(
                metadata=meta,
                timestamp=0,
                mint=accounts[2],
                sharing_config=accounts[3],
                admin=accounts[0],
            ),
        )

    if discriminator == _DISC_PFEES_TRANSFER_FEE_SHARING:
        if len(accounts) < 5:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_TRANSFER_FEE_SHARING_AUTHORITY,
            data=PumpFeesTransferFeeSharingAuthorityEvent(
                metadata=meta,
                timestamp=0,
                mint=accounts[2],
                sharing_config=accounts[3],
                old_admin=accounts[0],
                new_admin=accounts[4],
            ),
        )

    if discriminator == _DISC_PFEES_UPDATE_ADMIN:
        if len(accounts) < 3:
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_UPDATE_ADMIN,
            data=PumpFeesUpdateAdminEvent(
                metadata=meta,
                timestamp=0,
                old_admin=accounts[0],
                new_admin=accounts[2],
            ),
        )

    if discriminator == _DISC_PFEES_UPDATE_FEE_CONFIG:
        if len(accounts) < 2:
            return None
        o = [8]
        fee_tiers = read_pump_fees_fee_tiers_vec(data, o)
        if fee_tiers is None:
            return None
        flat_fees = _read_pump_fees_fees_at(data, o)
        if flat_fees is None or o[0] != len(data):
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_UPDATE_FEE_CONFIG,
            data=PumpFeesUpdateFeeConfigEvent(
                metadata=meta,
                timestamp=0,
                admin=accounts[1],
                fee_config=accounts[0],
                fee_tiers=fee_tiers,
                flat_fees=flat_fees,
            ),
        )

    if discriminator == _DISC_PFEES_UPSERT_FEE_TIERS:
        if len(accounts) < 2:
            return None
        o = [8]
        fee_tiers = read_pump_fees_fee_tiers_vec(data, o)
        if fee_tiers is None or o[0] >= len(data):
            return None
        offset = data[o[0]]
        o[0] += 1
        if o[0] != len(data):
            return None
        return DexEvent(
            type=EventType.PUMP_FEES_UPSERT_FEE_TIERS,
            data=PumpFeesUpsertFeeTiersEvent(
                metadata=meta,
                timestamp=0,
                admin=accounts[1],
                fee_config=accounts[0],
                fee_tiers=fee_tiers,
                offset=offset,
            ),
        )

    return None


def parse_raydium_clmm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium CLMM 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator in (_DISC_CLMM_SWAP, _DISC_CLMM_SWAP_V2):
        if len(data) < 8 + 8 + 8 + 16 + 1:
            return None
        sqrt_price_x64 = int.from_bytes(data[24:40], "little")
        is_base_input = data[40] == 1
        return legacy_dict_to_dex_event({"RaydiumClmmSwap": {
            "metadata": meta,
            "pool_state": _get_account_safe(accounts, 2),
            "sender": _get_account_safe(accounts, 0),
            "token_account_0": _get_account_safe(accounts, 3), "token_account_1": _get_account_safe(accounts, 4),
            "amount_0": 0, "amount_1": 0, "zero_for_one": is_base_input,
            "sqrt_price_x64": str(sqrt_price_x64), "liquidity": "0",
            "transfer_fee_0": 0, "transfer_fee_1": 0, "tick": 0,
        }})
    if discriminator == _DISC_CLMM_INC_LIQ:
        if len(data) < 8 + 16 + 8 + 8:
            return None
        liquidity = int.from_bytes(data[8:24], "little")
        amount0_max, amount1_max = struct.unpack_from("<QQ", data, 24)
        return legacy_dict_to_dex_event({"RaydiumClmmIncreaseLiquidity": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 2),
            "position_nft_mint": _get_account_safe(accounts, 1),
            "user": _get_account_safe(accounts, 0),
            "liquidity": str(liquidity),
            "amount_0": 0, "amount_1": 0,
            "amount_0_transfer_fee": 0, "amount_1_transfer_fee": 0,
            "amount0_max": amount0_max, "amount1_max": amount1_max,
        }})
    if discriminator == _DISC_CLMM_DEC_LIQ:
        if len(data) < 8 + 16 + 8 + 8:
            return None
        liquidity = int.from_bytes(data[8:24], "little")
        amount0_min, amount1_min = struct.unpack_from("<QQ", data, 24)
        return legacy_dict_to_dex_event({"RaydiumClmmDecreaseLiquidity": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 3),
            "position_nft_mint": _get_account_safe(accounts, 1),
            "user": _get_account_safe(accounts, 0),
            "liquidity": str(liquidity),
            "decrease_amount_0": 0, "decrease_amount_1": 0,
            "fee_amount_0": 0, "fee_amount_1": 0,
            "reward_amounts": [0, 0, 0],
            "transfer_fee_0": 0, "transfer_fee_1": 0,
            "amount0_min": amount0_min, "amount1_min": amount1_min,
        }})
    if discriminator == _DISC_CLMM_CREATE:
        if len(data) < 8 + 16 + 8:
            return None
        sqrt_price_x64 = int.from_bytes(data[8:24], "little")
        open_time = struct.unpack_from("<Q", data, 24)[0]
        return legacy_dict_to_dex_event({"RaydiumClmmCreatePool": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 2),
            "creator": _get_account_safe(accounts, 0),
            "token_0_mint": _get_account_safe(accounts, 3),
            "token_1_mint": _get_account_safe(accounts, 4),
            "tick_spacing": 0, "fee_rate": 0, "sqrt_price_x64": str(sqrt_price_x64),
            "tick": 0, "token_vault_0": _get_account_safe(accounts, 5), "token_vault_1": _get_account_safe(accounts, 6),
            "open_time": open_time,
        }})
    if discriminator == _DISC_CLMM_CREATE_CUSTOMIZABLE_POOL:
        if len(data) < 8 + 16:
            return None
        sqrt_price_x64 = int.from_bytes(data[8:24], "little")
        return legacy_dict_to_dex_event({"RaydiumClmmCreatePool": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 2),
            "creator": _get_account_safe(accounts, 0),
            "token_0_mint": _get_account_safe(accounts, 3),
            "token_1_mint": _get_account_safe(accounts, 4),
            "tick_spacing": 0, "fee_rate": 0, "sqrt_price_x64": str(sqrt_price_x64),
            "tick": 0, "token_vault_0": _get_account_safe(accounts, 5), "token_vault_1": _get_account_safe(accounts, 6),
            "open_time": 0,
        }})
    if discriminator in (
        _DISC_CLMM_OPEN_POSITION,
        _DISC_CLMM_OPEN_POSITION_V2,
        _DISC_CLMM_OPEN_POSITION_WITH_TOKEN_22_NFT,
    ):
        if len(data) < 8 + 4 + 4 + 4 + 4 + 16 + 8 + 8:
            return None
        tick_lower_index, tick_upper_index = struct.unpack_from("<ii", data, 8)
        liquidity = int.from_bytes(data[24:40], "little")
        pool_index = 4 if discriminator == _DISC_CLMM_OPEN_POSITION_WITH_TOKEN_22_NFT else 5
        return legacy_dict_to_dex_event({"RaydiumClmmOpenPosition": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, pool_index),
            "user": _get_account_safe(accounts, 1),
            "position_nft_mint": _get_account_safe(accounts, 2),
            "tick_lower_index": tick_lower_index,
            "tick_upper_index": tick_upper_index,
            "liquidity": str(liquidity),
        }})
    if discriminator == _DISC_CLMM_CLOSE_POSITION:
        return legacy_dict_to_dex_event({"RaydiumClmmClosePosition": {
            "metadata": meta,
            "pool": Z,
            "user": _get_account_safe(accounts, 0),
            "position_nft_mint": _get_account_safe(accounts, 1),
        }})

    return None


def parse_raydium_cpmm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium CPMM 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_CPMM_SWAP:
        if len(data) < 8 + 8 + 8:
            return None
        return legacy_dict_to_dex_event({"RaydiumCpmmSwap": {
            "metadata": meta,
            "pool_id": _get_account_safe(accounts, 3),
            "input_amount": 0, "output_amount": 0,
            "input_vault_before": 0, "output_vault_before": 0,
            "input_transfer_fee": 0, "output_transfer_fee": 0,
            "base_input": True,
        }})
    if discriminator == _DISC_CPMM_SWAP_OUT:
        if len(data) < 8 + 8 + 8:
            return None
        return legacy_dict_to_dex_event({"RaydiumCpmmSwap": {
            "metadata": meta,
            "pool_id": _get_account_safe(accounts, 3),
            "input_amount": 0, "output_amount": 0,
            "input_vault_before": 0, "output_vault_before": 0,
            "input_transfer_fee": 0, "output_transfer_fee": 0,
            "base_input": False,
        }})
    if discriminator == _DISC_CPMM_INITIALIZE:
        if len(data) < 8 + 8 + 8:
            return None
        return legacy_dict_to_dex_event({"RaydiumCpmmInitialize": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 0),
            "creator": _get_account_safe(accounts, 1),
            "init_amount0": struct.unpack_from("<Q", data, 8)[0],
            "init_amount1": struct.unpack_from("<Q", data, 16)[0],
        }})
    if discriminator == _DISC_CPMM_DEP:
        if len(data) < 8 + 8 + 8 + 8:
            return None
        return legacy_dict_to_dex_event({"RaydiumCpmmDeposit": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 0),
            "user": _get_account_safe(accounts, 1),
            "lp_token_amount": struct.unpack_from("<Q", data, 8)[0],
            "token0_amount": struct.unpack_from("<Q", data, 16)[0],
            "token1_amount": struct.unpack_from("<Q", data, 24)[0],
        }})
    if discriminator == _DISC_CPMM_WIT:
        if len(data) < 8 + 8 + 8 + 8:
            return None
        return legacy_dict_to_dex_event({"RaydiumCpmmWithdraw": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 0),
            "user": _get_account_safe(accounts, 1),
            "lp_token_amount": struct.unpack_from("<Q", data, 8)[0],
            "token0_amount": struct.unpack_from("<Q", data, 16)[0],
            "token1_amount": struct.unpack_from("<Q", data, 24)[0],
        }})

    return None


def parse_raydium_amm_v4_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium AMM V4 指令（单字节 discriminator）"""
    if len(data) < 1:
        return None

    instr_type = data[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if instr_type in (9, 11):  # SwapBaseIn / SwapBaseOut
        if len(data) < 17:
            return None
        first, second = struct.unpack_from("<QQ", data, 1)
        shift = 1 if len(accounts) == 17 else 0
        def g(index: int) -> str:
            return _get_account_safe(accounts, index - shift if index >= 5 else index)
        return legacy_dict_to_dex_event({"RaydiumAmmV4Swap": {
            "metadata": meta,
            "amm": _get_account_safe(accounts, 1),
            "user_source_owner": g(17),
            "amount_in": first if instr_type == 9 else 0,
            "minimum_amount_out": second if instr_type == 9 else 0,
            "max_amount_in": first if instr_type == 11 else 0,
            "amount_out": second if instr_type == 11 else 0,
            "token_program": g(0), "amm_authority": g(2), "amm_open_orders": g(3),
            "pool_coin_token_account": g(5), "pool_pc_token_account": g(6),
            "serum_program": g(7), "serum_market": g(8), "serum_bids": g(9),
            "serum_asks": g(10), "serum_event_queue": g(11),
            "serum_coin_vault_account": g(12), "serum_pc_vault_account": g(13),
            "serum_vault_signer": g(14),
            "user_source_token_account": g(15),
            "user_destination_token_account": g(16),
        }})

    return None


def parse_orca_whirlpool_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Orca Whirlpool 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator in (_DISC_ORCA_SWAP, _DISC_ORCA_SWAP_V2):
        if len(data) < 8 + 8 + 8 + 16 + 1 + 1:
            return None
        amount = struct.unpack_from("<Q", data, 8)[0]
        other_amount_threshold = struct.unpack_from("<Q", data, 16)[0]
        sqrt_price_limit = int.from_bytes(data[24:40], "little")
        amount_specified_is_input = data[40] != 0
        a_to_b = data[41] != 0
        whirlpool_index = 4 if discriminator == _DISC_ORCA_SWAP_V2 else 2
        return legacy_dict_to_dex_event({"OrcaWhirlpoolSwap": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, whirlpool_index),
            "a_to_b": a_to_b,
            "pre_sqrt_price": str(sqrt_price_limit), "post_sqrt_price": "0",
            "input_amount": amount if amount_specified_is_input else 0,
            "output_amount": other_amount_threshold if amount_specified_is_input else amount,
            "input_transfer_fee": 0, "output_transfer_fee": 0,
            "lp_fee": 0, "protocol_fee": 0,
        }})
    if discriminator == _DISC_ORCA_INC_LIQ:
        if len(data) < 8 + 16 + 8 + 8:
            return None
        liquidity = int.from_bytes(data[8:24], "little")
        token_max_a = struct.unpack_from("<Q", data, 24)[0]
        token_max_b = struct.unpack_from("<Q", data, 32)[0]
        return legacy_dict_to_dex_event({"OrcaWhirlpoolLiquidityIncreased": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 1),
            "position": _get_account_safe(accounts, 3),
            "tick_lower_index": 0, "tick_upper_index": 0,
            "liquidity": str(liquidity),
            "token_a_amount": token_max_a, "token_b_amount": token_max_b,
            "token_a_transfer_fee": 0, "token_b_transfer_fee": 0,
        }})
    if discriminator == _DISC_ORCA_DEC_LIQ:
        if len(data) < 8 + 16 + 8 + 8:
            return None
        liquidity = int.from_bytes(data[8:24], "little")
        token_min_a = struct.unpack_from("<Q", data, 24)[0]
        token_min_b = struct.unpack_from("<Q", data, 32)[0]
        return legacy_dict_to_dex_event({"OrcaWhirlpoolLiquidityDecreased": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 1),
            "position": _get_account_safe(accounts, 3),
            "tick_lower_index": 0, "tick_upper_index": 0,
            "liquidity": str(liquidity),
            "token_a_amount": token_min_a, "token_b_amount": token_min_b,
            "token_a_transfer_fee": 0, "token_b_transfer_fee": 0,
        }})
    if discriminator == _DISC_ORCA_INIT_POOL:
        if len(data) < 8 + 2 + 16:
            return None
        tick_spacing = struct.unpack_from("<H", data, 8)[0]
        initial_sqrt_price = int.from_bytes(data[10:26], "little")
        return legacy_dict_to_dex_event({"OrcaWhirlpoolPoolInitialized": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 1),
            "whirlpools_config": _get_account_safe(accounts, 2),
            "token_mint_a": _get_account_safe(accounts, 3),
            "token_mint_b": _get_account_safe(accounts, 4),
            "tick_spacing": tick_spacing,
            "token_program_a": _get_account_safe(accounts, 8),
            "token_program_b": _get_account_safe(accounts, 9),
            "decimals_a": 0,
            "decimals_b": 0,
            "initial_sqrt_price": str(initial_sqrt_price),
        }})

    return None


def parse_raydium_launchlab_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium LaunchLab 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)
    payload = data[8:]

    if discriminator == _DISC_RAYDIUM_LAUNCHLAB_TRADE:
        if len(payload) < 139:
            return None
        return legacy_dict_to_dex_event({"RaydiumLaunchlabTrade": {
            "metadata": meta,
            "pool_state": base58.b58encode(payload[0:32]).decode("ascii"),
            "user": Z,
            "amount_in": _u64_payload(payload, 88),
            "amount_out": _u64_payload(payload, 96),
            "is_buy": payload[136] == 0,
            "trade_direction": "Buy" if payload[136] == 0 else "Sell",
            "exact_in": payload[138] == 1,
        }})
    if discriminator == _DISC_RAYDIUM_LAUNCHLAB_POOL_CREATE:
        if len(payload) < 97:
            return None
        try:
            offset = 97
            name, offset = _read_borsh_string(payload, offset)
            symbol, offset = _read_borsh_string(payload, offset)
            uri, _ = _read_borsh_string(payload, offset)
        except ValueError:
            return None
        return legacy_dict_to_dex_event({"RaydiumLaunchlabPoolCreate": {
            "metadata": meta,
            "base_mint_param": {"symbol": symbol, "name": name, "uri": uri, "decimals": payload[96]},
            "pool_state": base58.b58encode(payload[0:32]).decode("ascii"),
            "creator": base58.b58encode(payload[32:64]).decode("ascii"),
        }})
    if discriminator in (
        _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_IN,
        _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_OUT,
        _IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_IN,
        _IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_OUT,
    ):
        first = _u64_payload(payload, 0)
        second = _u64_payload(payload, 8)
        exact_in = discriminator in (
            _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_IN,
            _IX_RAYDIUM_LAUNCHLAB_SELL_EXACT_IN,
        )
        is_buy = discriminator in (
            _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_IN,
            _IX_RAYDIUM_LAUNCHLAB_BUY_EXACT_OUT,
        )
        amount_in, amount_out = (first, second) if exact_in else (second, first)
        return legacy_dict_to_dex_event({"RaydiumLaunchlabTrade": {
            "metadata": meta,
            "pool_state": _get_account_safe(accounts, 4),
            "user": _get_account_safe(accounts, 0),
            "amount_in": amount_in,
            "amount_out": amount_out,
            "is_buy": is_buy,
            "trade_direction": "Buy" if is_buy else "Sell",
            "exact_in": exact_in,
        }})
    if discriminator in (
        _IX_RAYDIUM_LAUNCHLAB_INITIALIZE,
        _IX_RAYDIUM_LAUNCHLAB_INITIALIZE_V2,
        _IX_RAYDIUM_LAUNCHLAB_INITIALIZE_WITH_TOKEN_2022,
    ):
        if not payload:
            return None
        try:
            offset = 1
            name, offset = _read_borsh_string(payload, offset)
            symbol, offset = _read_borsh_string(payload, offset)
            uri, _ = _read_borsh_string(payload, offset)
        except ValueError:
            return None
        return legacy_dict_to_dex_event({"RaydiumLaunchlabPoolCreate": {
            "metadata": meta,
            "base_mint_param": {"symbol": symbol, "name": name, "uri": uri, "decimals": payload[0]},
            "pool_state": _get_account_safe(accounts, 5),
            "creator": _get_account_safe(accounts, 1),
        }})
    if discriminator in (
        _IX_RAYDIUM_LAUNCHLAB_MIGRATE_TO_AMM,
        _IX_RAYDIUM_LAUNCHLAB_MIGRATE_TO_CPSWAP,
    ):
        return None

    return None


# --- 过滤器辅助函数 ---

def _types_intersect(left: Sequence[EventType], right: Sequence[EventType]) -> bool:
    return any(t in right for t in left)


def _filter_includes_any(
    filter: Optional[EventTypeFilter],
    types: Sequence[EventType],
) -> bool:
    if filter is None:
        return True
    if isinstance(filter, IncludeOnlyFilter):
        return _types_intersect(filter.include_only, types)
    if isinstance(filter, ExcludeFilter):
        return any(filter.should_include(t) for t in types)
    return any(filter.should_include(t) for t in types)


def _filter_parsed_event(
    ev: Optional[DexEvent],
    filter: Optional[EventTypeFilter],
) -> Optional[DexEvent]:
    if ev is None or filter is None:
        return ev
    return ev if filter.should_include(ev.type) else None


def _filter_includes_pumpfun(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, PUMPFUN_FILTER_TYPES)


def _filter_includes_pump_fees(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, PUMP_FEES_EVENT_TYPES)


def _filter_includes_pumpswap(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, PUMPSWAP_FILTER_TYPES)


def _filter_includes_meteora_damm_v2(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, METEORA_DAMM_V2_FILTER_TYPES)


def _filter_includes_meteora_pools(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, METEORA_POOLS_FILTER_TYPES)


def _filter_includes_meteora_dlmm(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, METEORA_DLMM_FILTER_TYPES)


def _filter_includes_raydium_clmm(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, RAYDIUM_CLMM_FILTER_TYPES)


def _filter_includes_raydium_cpmm(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, RAYDIUM_CPMM_FILTER_TYPES)


def _filter_includes_raydium_amm_v4(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, RAYDIUM_AMM_V4_FILTER_TYPES)


def _filter_includes_orca_whirlpool(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, ORCA_WHIRLPOOL_FILTER_TYPES)


def _filter_includes_raydium_launchlab(filter: Optional[EventTypeFilter]) -> bool:
    return _filter_includes_any(filter, RAYDIUM_LAUNCHLAB_FILTER_TYPES)


__all__ = [
    "parse_instruction_unified",
    "parse_pumpfun_instruction",
    "parse_pumpswap_instruction",
    "parse_meteora_damm_instruction",
    "parse_meteora_pools_instruction",
    "parse_meteora_dlmm_instruction",
    "parse_pump_fees_instruction",
    "parse_raydium_clmm_instruction",
    "parse_raydium_cpmm_instruction",
    "parse_raydium_amm_v4_instruction",
    "parse_orca_whirlpool_instruction",
    "parse_raydium_launchlab_instruction",
]
