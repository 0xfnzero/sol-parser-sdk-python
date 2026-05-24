import base58

from sol_parser.dex_parsers import parse_trade_from_data
from sol_parser.event_types import DexEvent, PumpFunTradeEvent, to_typed_event
from sol_parser.grpc_types import EventType
from sol_parser.merger import merge_dex_events


def _pk(seed: int) -> bytes:
    return bytes((seed + i) & 0xFF for i in range(32))


def _u16(v: int) -> bytes:
    return v.to_bytes(2, "little")


def _u32(v: int) -> bytes:
    return v.to_bytes(4, "little")


def _u64(v: int) -> bytes:
    return v.to_bytes(8, "little")


def _i64(v: int) -> bytes:
    return v.to_bytes(8, "little", signed=True)


def _str(s: str) -> bytes:
    b = s.encode()
    return _u32(len(b)) + b


def test_pumpfun_trade_parser_keeps_quote_tail_fields() -> None:
    quote_mint = _pk(90)
    shareholder = _pk(120)
    data = b"".join(
        [
            _pk(1),
            _u64(10),
            _u64(20),
            b"\x01",
            _pk(2),
            _i64(30),
            _u64(40),
            _u64(50),
            _u64(60),
            _u64(70),
            _pk(3),
            _u64(80),
            _u64(90),
            _pk(4),
            _u64(100),
            _u64(110),
            b"\x00",
            _u64(120),
            _u64(130),
            _u64(140),
            _i64(150),
            _str("buy_exact_quote_in_v2"),
            b"\x00",
            _u64(30),
            _u64(170),
            _u64(500),
            _u64(600),
            _u32(1),
            shareholder,
            _u16(2500),
            quote_mint,
            _u64(700),
            _u64(800),
            _u64(900),
        ]
    )

    ev = parse_trade_from_data(data, {"signature": "sig", "slot": 1}, False)

    assert ev.type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN
    t = ev.data
    assert t.quote_mint == base58.b58encode(quote_mint).decode()
    assert t.quote_amount == 700
    assert t.virtual_quote_reserves == 800
    assert t.real_quote_reserves == 900
    assert t.buyback_fee_basis_points == 500
    assert t.buyback_fee == 600
    assert t.shareholders[0].address == base58.b58encode(shareholder).decode()
    assert t.shareholders[0].share_bps == 2500


def test_merge_does_not_clobber_quote_tail_with_defaults() -> None:
    base = DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            quote_mint="USDC_MINT",
            quote_amount=10,
            virtual_quote_reserves=20,
            real_quote_reserves=30,
        ),
    )
    inner = DexEvent(type=EventType.PUMP_FUN_TRADE, data=PumpFunTradeEvent())

    merge_dex_events(base, inner)

    assert base.data.quote_mint == "USDC_MINT"
    assert base.data.quote_amount == 10
    assert base.data.virtual_quote_reserves == 20
    assert base.data.real_quote_reserves == 30


def test_to_typed_event_preserves_trade_shareholders() -> None:
    typed = to_typed_event(
        {
            "PumpFunTrade": {
                "shareholders": [{"address": "holder", "share_bps": 2500}],
                "quote_mint": "quote",
                "quote_amount": 123,
            }
        }
    )

    assert typed is not None
    assert typed.shareholders[0].address == "holder"
    assert typed.shareholders[0].share_bps == 2500
    assert typed.quote_mint == "quote"
    assert typed.quote_amount == 123
