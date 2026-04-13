"""基础导入与 inner 路由烟测。"""

from __future__ import annotations

from sol_parser.inner_instruction_parser import parse_inner_instruction
from sol_parser.grpc_types import IncludeOnlyFilter
from sol_parser.instructions import PUMPFUN_PROGRAM_ID


def test_parse_inner_pumpfun_short_data() -> None:
    assert parse_inner_instruction(b"", PUMPFUN_PROGRAM_ID, {}, IncludeOnlyFilter([]), False) is None


def test_import_grpc_subscribe_builder() -> None:
    from sol_parser.grpc.subscribe_builder import build_subscribe_request_with_commitment

    from sol_parser.grpc_types import AccountFilter, CommitmentLevel, TransactionFilter

    tx = TransactionFilter(account_include=["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"])
    req = build_subscribe_request_with_commitment(
        [tx], [AccountFilter.new()], CommitmentLevel.PROCESSED
    )
    assert req is not None


def test_import_accounts_utils() -> None:
    from sol_parser.accounts.utils import user_wallet_pubkey_for_onchain_account

    assert (
        user_wallet_pubkey_for_onchain_account(
            "SoLAddRess1111111111111111111111111111111111",
            "11111111111111111111111111111111",
            b"",
            False,
        )
        == "SoLAddRess1111111111111111111111111111111111"
    )
