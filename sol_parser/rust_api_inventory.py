"""Rust ``sol-parser-sdk`` 公开 API 与 Python 映射（维护对照，非运行时依赖）。

本模块仅作文档与静态清单；实际导出见 ``sol_parser.__init__`` 及各子包。
"""

# crate 根: sol-parser-sdk/src/lib.rs
CRATE_ROOT_EXPORTS = {
    "parse_logs_only": "sol_parser.parser.parse_logs_only",
    "parse_logs_streaming": "sol_parser.parser.parse_logs_streaming",
    "parse_transaction_events": "sol_parser.parser.parse_transaction_events",
    "parse_transaction_events_streaming": "sol_parser.parser.parse_transaction_events_streaming",
    "parse_transaction_with_listener": "sol_parser.parser.parse_transaction_with_listener",
    "parse_transaction_with_streaming_listener": "sol_parser.parser.parse_transaction_with_streaming_listener",
    "DexEvent": "sol_parser.dex_parsers.DexEvent (dict 形态) / event_types.TypedDexEvent",
    "EventListener": "sol_parser.parser.EventListener",
    "EventMetadata": "sol_parser.grpc_types.EventMetadata",
    "ParsedEvent": "同 DexEvent",
    "StreamingEventListener": "sol_parser.parser.StreamingEventListener",
    "warmup_parser": "sol_parser.parser.warmup_parser",
    "convert_rpc_to_grpc": "sol_parser.rpc_parser.convert_rpc_to_grpc",
    "parse_rpc_transaction": "sol_parser.rpc_parser.parse_rpc_transaction",
    "parse_transaction_from_rpc": "sol_parser.rpc_parser.parse_transaction_from_rpc",
    "ParseError": "sol_parser.rpc_parser.ParseError",
    "rpc_resolve_user_wallet_pubkey": "sol_parser.accounts.rpc_wallet.rpc_resolve_user_wallet_pubkey",
    "user_wallet_pubkey_for_onchain_account": "sol_parser.accounts.utils.user_wallet_pubkey_for_onchain_account",
}

SUBMODULES = {
    "accounts": "sol_parser.accounts",
    "common": "sol_parser.common (见 common 子模块或常量分散)",
    "core": "sol_parser.parser / merger / dex_parsers / event_types",
    "instr": "sol_parser.instructions",
    "logs": "sol_parser.logs",
    "utils": "sol_parser.json_util 等",
    "warmup": "sol_parser.parser.warmup_parser",
    "grpc": "sol_parser.grpc",
    "shredstream": "sol_parser.shredstream_client / shredstream 配置",
    "rpc_parser": "sol_parser.rpc_parser",
    "parser": "sol_parser.parser (core 别名)",
}

__all__ = ["CRATE_ROOT_EXPORTS", "SUBMODULES"]
