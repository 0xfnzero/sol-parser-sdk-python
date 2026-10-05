"""Local BlockMeta adapter, matching Rust's saturated timestamp conversion."""

from dataclasses import dataclass
from .grpc_types import EventType, EventMetadata
from .event_types import DexEvent


@dataclass
class BlockMetaEvent:
    metadata: EventMetadata


def parse_block_meta_update(meta, grpc_recv_us, fallback_block_us=None):
    block_us = fallback_block_us or 0
    if meta.block_time is not None:
        block_us = max(-(1 << 63), min((1 << 63) - 1, meta.block_time * 1_000_000))
    return DexEvent(
        EventType.BLOCK_META,
        BlockMetaEvent(
            EventMetadata(
                signature="1" * 64,
                slot=meta.slot,
                tx_index=0,
                block_time_us=block_us,
                grpc_recv_us=grpc_recv_us,
                recent_blockhash=meta.blockhash,
            )
        ),
    )
