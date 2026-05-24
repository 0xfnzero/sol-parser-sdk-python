import struct

from sol_parser.event_types import DexEvent, PumpSwapBuyEvent
from sol_parser.grpc_types import EventType
from sol_parser.instructions import parse_pumpswap_instruction
from sol_parser.merger import merge_dex_events


def ix(disc: bytes, first: int, second: int) -> bytes:
    return disc + struct.pack("<QQ", first, second)


def accounts(n: int) -> list[str]:
    return [f"Account{i:02d}" for i in range(n)]


def test_pumpswap_buy_instruction_maps_non_cashback_tail_and_args():
    ev = parse_pumpswap_instruction(
        ix(bytes([102, 6, 61, 18, 1, 218, 235, 234]), 100, 200),
        accounts(26),
        "sig",
        1,
        0,
        None,
        0,
    )

    assert ev is not None
    assert ev.type == EventType.PUMP_SWAP_BUY
    buy = ev.data
    assert buy.base_amount_out == 100
    assert buy.max_quote_amount_in == 200
    assert buy.pool == "Account00"
    assert buy.coin_creator == ""
    assert buy.pool_v2 == "Account23"
    assert buy.fee_recipient == "Account24"
    assert buy.fee_recipient_quote_token_account == "Account25"


def test_pumpswap_buy_exact_quote_instruction_reverses_args_and_maps_cashback_tail():
    ev = parse_pumpswap_instruction(
        ix(bytes([198, 46, 21, 82, 180, 217, 232, 112]), 300, 400),
        accounts(27),
        "sig",
        1,
        0,
        None,
        0,
    )

    assert ev is not None
    buy = ev.data
    assert buy.base_amount_out == 400
    assert buy.max_quote_amount_in == 300
    assert buy.pool_v2 == "Account24"
    assert buy.fee_recipient == "Account25"
    assert buy.fee_recipient_quote_token_account == "Account26"


def test_pumpswap_sell_instruction_maps_cashback_tail_and_args():
    ev = parse_pumpswap_instruction(
        ix(bytes([51, 230, 133, 164, 1, 127, 131, 173]), 500, 600),
        accounts(26),
        "sig",
        1,
        0,
        None,
        0,
    )

    assert ev is not None
    assert ev.type == EventType.PUMP_SWAP_SELL
    sell = ev.data
    assert sell.base_amount_in == 500
    assert sell.min_quote_amount_out == 600
    assert sell.pool_v2 == "Account23"
    assert sell.fee_recipient == "Account24"
    assert sell.fee_recipient_quote_token_account == "Account25"


def test_pumpswap_merge_preserves_instruction_upgrade_tail():
    base = DexEvent(
        type=EventType.PUMP_SWAP_BUY,
        data=PumpSwapBuyEvent(
            pool="Pool111111111111111111111111111111111111",
            user="User111111111111111111111111111111111111",
            pool_v2="PoolV2111111111111111111111111111111111",
            fee_recipient="Fee1111111111111111111111111111111111111",
            fee_recipient_quote_token_account="FeeAta111111111111111111111111111111111",
        ),
    )
    inner = DexEvent(
        type=EventType.PUMP_SWAP_BUY,
        data=PumpSwapBuyEvent(
            pool="Pool111111111111111111111111111111111111",
            user="User111111111111111111111111111111111111",
            base_amount_out=123,
            max_quote_amount_in=456,
        ),
    )

    merge_dex_events(base, inner)

    assert base.data.base_amount_out == 123
    assert base.data.max_quote_amount_in == 456
    assert base.data.pool_v2 == "PoolV2111111111111111111111111111111111"
    assert base.data.fee_recipient == "Fee1111111111111111111111111111111111111"
    assert base.data.fee_recipient_quote_token_account == "FeeAta111111111111111111111111111111111"
