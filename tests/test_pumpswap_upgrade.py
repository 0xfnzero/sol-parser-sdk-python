from __future__ import annotations

import struct

from sol_parser.accounts import AccountData, parse_pumpswap_pool
from sol_parser.dex_parsers import (
    parse_ps_buy_from_data,
    parse_ps_create_pool_from_data,
    parse_ps_sell_from_data,
)
from sol_parser.event_types import PumpSwapBuyEvent, to_typed_event
from sol_parser.grpc_types import EventMetadata, EventType


POOL_DISC = bytes([241, 154, 109, 4, 17, 177, 109, 188])


def _current_tail() -> bytes:
    return b"".join(
        [
            struct.pack("<QQQQ", 177, 188, 199, 211),
            (-987_654_321).to_bytes(16, "little", signed=True),
            b"\x01",
            struct.pack("<Q", 222),
            struct.pack("<QQ", 233, 244),
        ]
    )


def _buy_payload(include_tail: bool) -> bytes:
    data = bytearray(393)
    data[352] = 1
    struct.pack_into("<Q", data, 385, 22)
    data += struct.pack("<I", 3) + b"buy"
    if include_tail:
        data += _current_tail()
    return bytes(data)


def test_pumpswap_current_trade_tail_fields() -> None:
    buy = parse_ps_buy_from_data(_buy_payload(True), {})
    assert buy is not None and buy.type == EventType.PUMP_SWAP_BUY
    assert buy.data.min_base_amount_out == 22
    assert buy.data.ix_name == "buy"
    assert buy.data.cashback_fee_basis_points == 177
    assert buy.data.cashback == 188
    assert buy.data.buyback_fee_basis_points == 199
    assert buy.data.buyback_fee == 211
    assert buy.data.virtual_quote_reserves == -987_654_321
    assert buy.data.can_boost is True
    assert buy.data.base_supply == 222
    assert buy.data.holder_rewards_bps == 233
    assert buy.data.holder_rewards == 244

    sell = parse_ps_sell_from_data(bytes(352) + _current_tail(), {})
    assert sell is not None and sell.type == EventType.PUMP_SWAP_SELL
    assert sell.data.cashback_fee_basis_points == 177
    assert sell.data.buyback_fee_basis_points == 199
    assert sell.data.virtual_quote_reserves == -987_654_321
    assert sell.data.can_boost is True
    assert sell.data.base_supply == 222
    assert sell.data.holder_rewards_bps == 233
    assert sell.data.holder_rewards == 244


def test_pumpswap_trade_layout_validation() -> None:
    assert parse_ps_buy_from_data(bytes(385), {}) is not None
    assert parse_ps_buy_from_data(bytes(396), {}) is None
    assert parse_ps_buy_from_data(bytes(397), {}) is not None
    assert parse_ps_sell_from_data(bytes(352), {}) is not None

    for tail_len in range(81):
        expected = tail_len in (0, 16, 32, 57) or tail_len == 73 or tail_len >= 81
        parsed = parse_ps_sell_from_data(bytes(352 + tail_len), {})
        assert (parsed is not None) is expected, tail_len

    for partial_len in (1, 15, 17, 31, 33, 56):
        assert parse_ps_buy_from_data(_buy_payload(False) + bytes(partial_len), {}) is None
        assert parse_ps_sell_from_data(bytes(352 + partial_len), {}) is None

    invalid_track = bytearray(_buy_payload(False))
    invalid_track[352] = 2
    assert parse_ps_buy_from_data(bytes(invalid_track), {}) is None

    invalid_utf8 = bytearray(_buy_payload(False))
    invalid_utf8[397] = 0xFF
    assert parse_ps_buy_from_data(bytes(invalid_utf8), {}) is None

    invalid_boost = bytearray(bytes(352) + _current_tail())
    invalid_boost[400] = 2
    assert parse_ps_sell_from_data(bytes(invalid_boost), {}) is None


def test_pumpswap_signed_i128_extremes_and_dict_compatibility() -> None:
    for value in (-(1 << 127), -1, (1 << 127) - 1):
        tail = bytearray(_current_tail())
        tail[32:48] = value.to_bytes(16, "little", signed=True)
        sell = parse_ps_sell_from_data(bytes(352) + tail, {})
        assert sell is not None
        assert sell.data.virtual_quote_reserves == value

    restored = to_typed_event(
        {"PumpSwapBuy": {"metadata": {}, "virtual_quote_reserves": "-987654321"}}
    )
    assert isinstance(restored, PumpSwapBuyEvent)
    assert restored.virtual_quote_reserves == -987_654_321
    assert restored.buyback_fee_basis_points == 0
    assert restored.can_boost is False


def test_pumpswap_pool_virtual_quote_reserves() -> None:
    def account(body: bytes) -> AccountData:
        return AccountData(
            pubkey="pool",
            executable=False,
            lamports=0,
            owner="owner",
            rent_epoch=0,
            data=POOL_DISC + body,
        )

    legacy = parse_pumpswap_pool(account(bytes(244)), EventMetadata())
    assert legacy is not None
    assert legacy.data["pool"]["virtual_quote_reserves"] == 0

    boost_body = bytearray(253)
    boost_body[237:253] = (-987_654_321).to_bytes(16, "little", signed=True)
    boost = parse_pumpswap_pool(account(bytes(boost_body)), EventMetadata())
    assert boost is not None
    assert boost.data["pool"]["virtual_quote_reserves"] == -987_654_321
    assert boost.data["pool"]["creator_fee_bps"] == 0

    current_body = bytearray(263)
    current_body[237:253] = (-987_654_321).to_bytes(16, "little", signed=True)
    current_body[253:261] = (250).to_bytes(8, "little")
    current_body[261] = 1
    current_body[262] = 1
    current = parse_pumpswap_pool(account(bytes(current_body)), EventMetadata())
    assert current is not None
    assert current.data["pool"]["virtual_quote_reserves"] == -987_654_321
    assert current.data["pool"]["creator_fee_bps"] == 250
    assert current.data["pool"]["can_edit_creator_fee"] is True
    assert current.data["pool"]["is_holder_reward"] is True

    for body_len in (*range(245, 253), *range(254, 262)):
        assert parse_pumpswap_pool(account(bytes(body_len)), EventMetadata()) is None
    assert parse_pumpswap_pool(account(bytes(262)), EventMetadata()) is not None


def test_pumpswap_create_pool_event_creator_fee_fields() -> None:
    data = bytearray(336)
    struct.pack_into("<H", data, 8, 42)
    data[325] = 1
    struct.pack_into("<Q", data, 326, 250)
    data[334] = 1
    data[335] = 1

    event = parse_ps_create_pool_from_data(bytes(data), {})
    assert event is not None and event.type == EventType.PUMP_SWAP_CREATE_POOL
    assert event.data.index == 42
    assert event.data.is_mayhem_mode is True
    assert event.data.creator_fee_bps == 250
    assert event.data.can_edit_creator_fee is True
    assert event.data.is_holder_reward is True

    for body_len in range(326, 337):
        expected = body_len == 326 or body_len >= 335
        parsed = parse_ps_create_pool_from_data(bytes(body_len), {})
        assert (parsed is not None) is expected, body_len
