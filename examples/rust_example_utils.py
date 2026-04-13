"""与 Rust ``sol-parser-sdk/examples/*.rs`` 中 publicnode 默认配置一致（文档与本地快速试跑）。

实际解析仍使用 :func:`sol_parser.env_config.parse_grpc_credentials`，其已支持
``GRPC_AUTH_TOKEN``、``GRPC_ENDPOINT`` 等与 Rust 相同的环境变量名。
"""

# 对齐 pumpfun_trade_filter.rs / meteora_damm_grpc.rs 等内联常量
DEFAULT_GRPC_ENDPOINT = "https://solana-yellowstone-grpc.publicnode.com:443"
DEFAULT_GRPC_AUTH_TOKEN = (
    "cd1c3642f88c86f9f8e7f15831faf9f067b997c6ac2b72c81d115e8d071af77a"
)
