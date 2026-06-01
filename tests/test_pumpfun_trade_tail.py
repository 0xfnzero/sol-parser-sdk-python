import base58

from sol_parser.dex_parsers import parse_create_from_data, parse_trade_from_data
from sol_parser.event_types import DexEvent, PumpFunCreateEvent, PumpFunCreateV2TokenEvent, PumpFunTradeEvent, to_typed_event
from sol_parser.grpc_types import EventType
from sol_parser.merger import merge_dex_events
from sol_parser.pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge


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

    assert ev.type == EventType.PUMP_FUN_BUY
    t = ev.data
    assert t.quote_mint == base58.b58encode(quote_mint).decode()
    assert t.quote_amount == 700
    assert t.virtual_quote_reserves == 800
    assert t.real_quote_reserves == 900
    assert t.buyback_fee_basis_points == 500
    assert t.buyback_fee == 600
    assert t.shareholders[0].address == base58.b58encode(shareholder).decode()
    assert t.shareholders[0].share_bps == 2500


def test_pumpfun_create_parser_keeps_quote_tail_fields() -> None:
    quote_mint = _pk(90)
    data = b"".join(
        [
            _str("Name"),
            _str("SYM"),
            _str("https://example.invalid/meta.json"),
            _pk(1),
            _pk(2),
            _pk(3),
            _pk(4),
            _i64(123),
            _u64(1_073_000_000_000_000),
            _u64(30_000_000_000),
            _u64(793_100_000_000_000),
            _u64(1_000_000_000_000_000),
            _pk(5),
            b"\x00",
            b"\x01",
            quote_mint,
            _u64(4_292_000_000),
        ]
    )

    ev = parse_create_from_data(data, {"signature": "sig", "slot": 1})

    assert ev.type == EventType.PUMP_FUN_CREATE
    create = ev.data
    assert create.quote_mint == base58.b58encode(quote_mint).decode()
    assert create.virtual_quote_reserves == 4_292_000_000
    assert create.is_cashback_enabled is True


def test_post_merge_enriches_create_v2_from_create_event() -> None:
    events = [
        DexEvent(
            type=EventType.PUMP_FUN_CREATE_V2,
            data=PumpFunCreateV2TokenEvent(
                name="ix-name",
                mint="mint",
            ),
        ),
        DexEvent(
            type=EventType.PUMP_FUN_CREATE,
            data=PumpFunCreateEvent(
                name="event-name",
                symbol="EVT",
                uri="uri",
                mint="mint",
                bonding_curve="curve",
                user="user",
                creator="creator",
                timestamp=123,
                virtual_token_reserves=1,
                virtual_sol_reserves=30_000_000_000,
                real_token_reserves=2,
                token_total_supply=3,
                token_program="token-program",
                is_mayhem_mode=True,
                is_cashback_enabled=True,
                quote_mint="USDC",
                virtual_quote_reserves=4_292_000_000,
            ),
        ),
    ]

    enrich_pumpfun_same_tx_post_merge(events)

    create_v2 = events[0].data
    assert create_v2.name == "ix-name"
    assert create_v2.quote_mint == "USDC"
    assert create_v2.virtual_quote_reserves == 4_292_000_000
    assert create_v2.virtual_sol_reserves == 30_000_000_000
    assert create_v2.is_cashback_enabled is True
    assert create_v2.is_mayhem_mode is True


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
