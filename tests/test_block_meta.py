from sol_parser.grpc_types import (
    SubscribeUpdateBlockMeta,
    EventType,
    event_type_filter_include_only,
    event_type_filter_exclude,
)
from sol_parser.block_meta import parse_block_meta_update
from sol_parser.grpc.subscribe_builder import build_subscribe_request_with_event_filter


def test_block_metadata():
    e = parse_block_meta_update(
        SubscribeUpdateBlockMeta(
            slot=452558748, blockhash="observed", block_time=1790928211
        ),
        123,
        456,
    )
    assert e.type == EventType.BLOCK_META
    assert vars(e.data.metadata) == dict(
        signature="1" * 64,
        slot=452558748,
        tx_index=0,
        block_time_us=1790928211000000,
        grpc_recv_us=123,
        recent_blockhash="observed",
        is_created_buy=False,
    )
    assert (
        parse_block_meta_update(
            SubscribeUpdateBlockMeta(), 123, 456
        ).data.metadata.block_time_us
        == 456
    )
    assert (
        parse_block_meta_update(
            SubscribeUpdateBlockMeta(block_time=2**63 - 1), 0
        ).data.metadata.block_time_us
        == 2**63 - 1
    )
    assert parse_block_meta_update(
        SubscribeUpdateBlockMeta(block_time=-(2**63)), 0
    ).data.metadata.block_time_us == -(2**63)


def test_block_meta_subscription_opt_in():
    assert not build_subscribe_request_with_event_filter([], []).blocks_meta
    assert not build_subscribe_request_with_event_filter(
        [], [], event_type_filter_include_only([EventType.PUMP_FUN_TRADE])
    ).blocks_meta
    assert (
        "block_meta"
        in build_subscribe_request_with_event_filter(
            [], [], event_type_filter_include_only([EventType.BLOCK_META])
        ).blocks_meta
    )
    assert not build_subscribe_request_with_event_filter(
        [], [], event_type_filter_exclude([EventType.BLOCK_META])
    ).blocks_meta
