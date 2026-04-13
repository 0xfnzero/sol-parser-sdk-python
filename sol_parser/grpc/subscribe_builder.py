"""对齐 Rust ``grpc/subscribe_builder.rs``：构造 Yellowstone ``SubscribeRequest``。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

from ..grpc_types import AccountFilter, CommitmentLevel, TransactionFilter

try:
    from .. import geyser_pb2
except ImportError:
    geyser_pb2 = None  # type: ignore


def _tx_filter_to_proto(f: TransactionFilter) -> Any:
    if geyser_pb2 is None:
        raise ImportError("需要 geyser_pb2")
    tx = geyser_pb2.SubscribeRequestFilterTransactions(
        vote=False,
        failed=False,
        account_include=list(f.account_include),
        account_exclude=list(f.account_exclude),
        account_required=list(f.account_required),
    )
    if f.vote is not None:
        tx.vote = f.vote
    if f.failed is not None:
        tx.failed = f.failed
    if f.signature:
        tx.signature = f.signature
    return tx


def _acc_filter_to_proto(f: AccountFilter) -> Any:
    if geyser_pb2 is None:
        raise ImportError("需要 geyser_pb2")
    flist = []
    for sub in f.filters:
        one = geyser_pb2.SubscribeRequestFilterAccountsFilter()
        if sub.memcmp is not None:
            m = sub.memcmp
            mc = geyser_pb2.SubscribeRequestFilterAccountsFilterMemcmp(offset=m.offset)
            if m.bytes is not None:
                mc.bytes = bytes(m.bytes)
            elif m.base58:
                mc.base58 = m.base58
            elif m.base64:
                mc.base64 = m.base64
            one.memcmp.CopyFrom(mc)
        if sub.datasize is not None:
            one.datasize = sub.datasize
        if sub.token_account_state is not None:
            one.token_account_state = sub.token_account_state
        if sub.lamports is not None:
            lp = geyser_pb2.SubscribeRequestFilterAccountsFilterLamports()
            if sub.lamports.eq is not None:
                lp.eq = sub.lamports.eq
            if sub.lamports.ne is not None:
                lp.ne = sub.lamports.ne
            if sub.lamports.lt is not None:
                lp.lt = sub.lamports.lt
            if sub.lamports.gt is not None:
                lp.gt = sub.lamports.gt
            one.lamports.CopyFrom(lp)
        flist.append(one)
    return geyser_pb2.SubscribeRequestFilterAccounts(
        account=list(f.account),
        owner=list(f.owner),
        filters=flist,
    )


def _finalize(
    transactions: Dict[str, Any],
    accounts: Dict[str, Any],
    commitment: CommitmentLevel,
) -> Any:
    if geyser_pb2 is None:
        raise ImportError("需要 geyser_pb2")
    return geyser_pb2.SubscribeRequest(
        slots={},
        accounts=accounts,
        transactions=transactions,
        transactions_status={},
        blocks={},
        blocks_meta={},
        entry={},
        commitment=commitment.value,
        accounts_data_slice=[],
        ping=None,
    )


def build_subscribe_request(
    tx_filters: List[TransactionFilter],
    acc_filters: List[AccountFilter],
) -> Any:
    """对齐 Rust ``build_subscribe_request``（commitment = Processed）。"""
    return build_subscribe_request_with_commitment(
        tx_filters, acc_filters, CommitmentLevel.PROCESSED
    )


def build_subscribe_request_with_commitment(
    tx_filters: List[TransactionFilter],
    acc_filters: List[AccountFilter],
    commitment: CommitmentLevel,
) -> Any:
    if geyser_pb2 is None:
        raise ImportError("需要 geyser_pb2")
    transactions = {f"tx_{i}": _tx_filter_to_proto(f) for i, f in enumerate(tx_filters)}
    accounts = {f"acc_{i}": _acc_filter_to_proto(f) for i, f in enumerate(acc_filters)}
    return _finalize(transactions, accounts, commitment)


def build_subscribe_transaction_filters_named(
    named_tx_filters: List[Tuple[str, TransactionFilter]],
    acc_filters: List[AccountFilter],
    commitment: CommitmentLevel,
) -> Any:
    """对齐 Rust ``build_subscribe_transaction_filters_named``。"""
    if geyser_pb2 is None:
        raise ImportError("需要 geyser_pb2")
    transactions = {name: _tx_filter_to_proto(f) for name, f in named_tx_filters}
    accounts = {f"acc_{i}": _acc_filter_to_proto(f) for i, f in enumerate(acc_filters)}
    return _finalize(transactions, accounts, commitment)


__all__ = [
    "build_subscribe_request",
    "build_subscribe_request_with_commitment",
    "build_subscribe_transaction_filters_named",
]
