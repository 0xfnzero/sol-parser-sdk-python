"""对齐 Rust ``grpc/geyser_connect.rs``：Geyser gRPC 连接配置（Python 侧用 ``grpc`` + aio）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class GeyserConnectConfig:
    """对齐 Rust ``GeyserConnectConfig``。"""
    connect_timeout_s: float = 8.0
    max_decoding_message_size: int = 1024 * 1024 * 1024
    x_token: Optional[str] = None


async def connect_yellowstone_geyser(endpoint: str, config: Optional[GeyserConnectConfig] = None) -> Any:
    """建立 gRPC channel + Geyser stub（对齐 Rust 连接语义；返回 ``(channel, stub)`` 元组）。"""
    import grpc
    from grpc import aio

    cfg = config or GeyserConnectConfig()
    opts = [
        ("grpc.max_receive_message_length", cfg.max_decoding_message_size),
        ("grpc.max_send_message_length", cfg.max_decoding_message_size),
    ]
    if endpoint.startswith("https://"):
        creds = grpc.ssl_channel_credentials()
        channel = aio.secure_channel(endpoint.replace("https://", "", 1), creds, options=opts)
    else:
        ep = endpoint.replace("http://", "", 1) if "://" in endpoint else endpoint
        channel = aio.insecure_channel(ep, options=opts)
    try:
        from .. import geyser_pb2_grpc
    except ImportError as e:
        raise ImportError("需要 geyser_pb2_grpc") from e
    return channel, geyser_pb2_grpc.GeyserStub(channel)


__all__ = ["GeyserConnectConfig", "connect_yellowstone_geyser"]
