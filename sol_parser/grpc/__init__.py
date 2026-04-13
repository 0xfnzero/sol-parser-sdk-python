"""对齐 Rust ``sol_parser_sdk::grpc`` 子模块的 Python 入口。"""

from .subscribe_builder import (
    build_subscribe_request,
    build_subscribe_request_with_commitment,
    build_subscribe_transaction_filters_named,
)
from .transaction_meta import (
    collect_account_keys_bs58,
    collect_watch_transfer_counterparty_pairs,
    heuristic_sol_counterparties_for_watched_keys,
    lamport_balance_deltas,
    pubkey_bytes_to_bs58,
    spl_token_counterparty_by_owner,
    token_balance_raw_amount,
    try_yellowstone_signature,
)
from .geyser_connect import GeyserConnectConfig, connect_yellowstone_geyser

# 与 Rust 一致：从 types 再导出常用名（grpc/mod.rs）
from ..grpc_types import (
    AccountFilter,
    ClientConfig,
    EventType as StreamingEventType,
    EventTypeFilter,
    OrderMode,
    Protocol,
    SlotFilter,
    TransactionFilter,
    account_filter_memcmp,
)

EventType = StreamingEventType

__all__ = [
    "build_subscribe_request",
    "build_subscribe_request_with_commitment",
    "build_subscribe_transaction_filters_named",
    "pubkey_bytes_to_bs58",
    "collect_account_keys_bs58",
    "lamport_balance_deltas",
    "heuristic_sol_counterparties_for_watched_keys",
    "spl_token_counterparty_by_owner",
    "token_balance_raw_amount",
    "collect_watch_transfer_counterparty_pairs",
    "try_yellowstone_signature",
    "GeyserConnectConfig",
    "connect_yellowstone_geyser",
    "YellowstoneGrpc",
    "Subscription",
]

# 延迟导入避免循环依赖
def __getattr__(name: str):
    if name == "YellowstoneGrpc":
        from ..grpc_client import YellowstoneGrpc
        return YellowstoneGrpc
    if name == "Subscription":
        from ..grpc_client import Subscription
        return Subscription
    raise AttributeError(name)
