"""Yellowstone gRPC 客户端实现

参考实现:
- https://github.com/chainstacklabs/grpc-geyser-tutorial
- https://github.com/rpcpool/yellowstone-grpc
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass

import grpc
from grpc import aio

from .grpc_types import (
    ClientConfig,
    TransactionFilter,
    SubscribeCallbacks,
    SubscribeUpdate,
    SubscribeUpdateAccount,
    SubscribeUpdateAccountInfo,
    SubscribeUpdateSlot,
    SubscribeUpdateTransaction,
    SubscribeUpdateTransactionInfo,
    SubscribeUpdateBlock,
    SubscribeUpdateBlockMeta,
    SubscribeUpdatePing,
    SubscribeUpdatePong,
    CommitmentLevel,
    SlotStatus,
    GetLatestBlockhashRequest,
    GetLatestBlockhashResponse,
    GetBlockHeightRequest,
    GetBlockHeightResponse,
    GetSlotRequest,
    GetSlotResponse,
    GetVersionRequest,
    GetVersionResponse,
    IsBlockhashValidRequest,
    IsBlockhashValidResponse,
    PingRequest,
    PongResponse,
    SubscribeReplayInfoRequest,
    SubscribeReplayInfoResponse,
)

# 尝试导入生成的 protobuf 代码
try:
    from . import geyser_pb2
    from . import geyser_pb2_grpc
    HAS_PROTO = True
except ImportError:
    HAS_PROTO = False


@dataclass
class Subscription:
    """订阅句柄"""
    id: str
    filter: TransactionFilter
    cancel: Callable[[], None]
    callbacks: SubscribeCallbacks


class YellowstoneGrpc:
    """Yellowstone gRPC 客户端"""

    def __init__(self, endpoint: str, config: Optional[ClientConfig] = None):
        self.endpoint = endpoint
        self.config = config or ClientConfig.default()
        self._x_token: Optional[str] = None
        self._connected = False
        self._subscribers: Dict[str, Subscription] = {}
        self._channel: Optional[aio.Channel] = None
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()

    @classmethod
    def new(cls, endpoint: str, token: Optional[str] = None) -> YellowstoneGrpc:
        """对齐 Rust ``YellowstoneGrpc::new``。"""
        from .parser import warmup_parser

        warmup_parser()
        inst = cls(endpoint)
        if token:
            inst.set_x_token(token)
        return inst

    @classmethod
    def new_with_config(
        cls, endpoint: str, token: Optional[str], config: ClientConfig
    ) -> YellowstoneGrpc:
        """对齐 Rust ``YellowstoneGrpc::new_with_config``。"""
        from .parser import warmup_parser

        warmup_parser()
        inst = cls(endpoint, config)
        if token:
            inst.set_x_token(token)
        return inst

    async def subscribe_dex_events(
        self,
        transaction_filters: List[TransactionFilter],
        account_filters: List[Any],
        event_type_filter: Optional[Any] = None,
    ) -> Any:
        """对齐 Rust API 名称：完整多路合并订阅尚未实现；请使用 ``connect`` + ``subscribe_transactions``。"""
        _ = transaction_filters
        _ = account_filters
        _ = event_type_filter
        raise NotImplementedError(
            "subscribe_dex_events: 请使用 connect() 与 subscribe_transactions()；"
            "多过滤器请在业务层合并为 TransactionFilter"
        )

    async def update_subscription(
        self,
        transaction_filters: List[TransactionFilter],
        account_filters: List[Any],
    ) -> None:
        """对齐 Rust 名称：动态更新需重建流。"""
        _ = transaction_filters
        _ = account_filters
        raise NotImplementedError("请取消订阅后重新 subscribe_transactions")

    def set_x_token(self, token: str) -> None:
        """设置 X-Token 认证"""
        self._x_token = token

    def _get_channel_options(self) -> list:
        """获取 gRPC 通道选项

        参考: https://github.com/chainstacklabs/grpc-geyser-tutorial
        """
        return [
            ('grpc.keepalive_time_ms', self.config.keep_alive_interval_ms),
            ('grpc.keepalive_timeout_ms', self.config.keep_alive_timeout_ms),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.min_time_between_pings_ms', 10000),
        ]

    def _create_auth_credentials(self):
        """创建认证凭证

        参考: https://github.com/chainstacklabs/grpc-geyser-tutorial/main.py
        """
        if not self._x_token:
            return None

        def auth_callback(context, callback):
            callback((('x-token', self._x_token),), None)

        return grpc.metadata_call_credentials(auth_callback)

    def _get_metadata(self) -> Optional[list]:
        """获取认证元数据（用于流式调用）"""
        if self._x_token:
            return [('x-token', self._x_token)]
        return None

    async def connect(self) -> None:
        """连接到 gRPC 服务器

        参考实现:
        - https://github.com/chainstacklabs/grpc-geyser-tutorial/main.py
        - https://github.com/rpcpool/yellowstone-grpc/examples/python
        """
        if self._connected:
            return

        if not HAS_PROTO:
            raise ImportError(
                "YellowstoneGrpc.connect: 需要 protobuf 生成的代码。\n"
                "请执行以下步骤:\n"
                "1. 克隆 https://github.com/rpcpool/yellowstone-grpc\n"
                "2. 使用 protoc 生成 Python 代码:\n"
                "   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. geyser.proto\n"
                "3. 将生成的 geyser_pb2.py 和 geyser_pb2_grpc.py 放入 sol_parser 目录"
            )

        async with self._lock:
            if self._connected:
                return

            channel_options = self._get_channel_options()

            if self.config.enable_tls:
                # 创建 SSL 凭证
                ssl_creds = grpc.ssl_channel_credentials()

                # 添加认证
                auth_creds = self._create_auth_credentials()
                if auth_creds:
                    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
                else:
                    composite_creds = ssl_creds

                self._channel = aio.secure_channel(
                    self.endpoint,
                    composite_creds,
                    options=channel_options
                )
            else:
                self._channel = aio.insecure_channel(
                    self.endpoint,
                    options=channel_options
                )

            self._client = geyser_pb2_grpc.GeyserStub(self._channel)
            self._connected = True

    async def disconnect(self) -> None:
        """断开连接"""
        if not self._connected:
            return

        async with self._lock:
            # 取消所有订阅
            for sub in list(self._subscribers.values()):
                sub.cancel()
            self._subscribers.clear()

            # 关闭通道
            if self._channel:
                await self._channel.close()
                self._channel = None

            self._client = None
            self._connected = False

    def _build_subscribe_request(self, filter: TransactionFilter) -> Any:
        """构建订阅请求"""
        tx_filter = geyser_pb2.SubscribeRequestFilterTransactions(
            account_include=filter.account_include,
            account_exclude=filter.account_exclude,
            account_required=filter.account_required,
        )

        if filter.vote is not None:
            tx_filter.vote = filter.vote
        if filter.failed is not None:
            tx_filter.failed = filter.failed
        if filter.signature:
            tx_filter.signature = filter.signature

        return geyser_pb2.SubscribeRequest(
            transactions={"client": tx_filter}
        )

    def _convert_update(self, pb_update: Any) -> SubscribeUpdate:
        """转换 protobuf 更新到本地类型"""
        update = SubscribeUpdate(filters=list(pb_update.filters))

        # 转换账户更新
        if pb_update.HasField('account'):
            acc = pb_update.account
            update.account = SubscribeUpdateAccount(
                slot=acc.slot,
                is_startup=acc.is_startup
            )
            if acc.account:
                update.account.account = SubscribeUpdateAccountInfo(
                    pubkey=bytes(acc.account.pubkey),
                    lamports=acc.account.lamports,
                    owner=bytes(acc.account.owner),
                    executable=acc.account.executable,
                    rent_epoch=acc.account.rent_epoch,
                    data=bytes(acc.account.data),
                    write_version=acc.account.write_version,
                    txn_signature=bytes(acc.account.txn_signature) if acc.account.txn_signature else None
                )

        # 转换 slot 更新
        if pb_update.HasField('slot'):
            slot = pb_update.slot
            update.slot = SubscribeUpdateSlot(
                slot=slot.slot,
                status=SlotStatus(slot.status)
            )
            if slot.HasField('parent'):
                update.slot.parent = slot.parent
            if slot.HasField('dead_error'):
                update.slot.dead_error = slot.dead_error

        # 转换交易更新
        if pb_update.HasField('transaction'):
            tx = pb_update.transaction
            update.transaction = SubscribeUpdateTransaction(slot=tx.slot)
            if tx.transaction:
                # 直接从 proto 对象提取 log_messages，避免反序列化
                log_msgs = list(tx.transaction.meta.log_messages) if tx.transaction.meta else []
                update.transaction.transaction = SubscribeUpdateTransactionInfo(
                    signature=bytes(tx.transaction.signature),
                    is_vote=tx.transaction.is_vote,
                    transaction_raw=tx.transaction.transaction.SerializeToString() if tx.transaction.transaction else b"",
                    meta_raw=tx.transaction.meta.SerializeToString() if tx.transaction.meta else b"",
                    index=tx.transaction.index,
                    log_messages=log_msgs,
                )

        # 转换区块更新
        if pb_update.HasField('block'):
            block = pb_update.block
            update.block = SubscribeUpdateBlock(
                slot=block.slot,
                blockhash=block.blockhash,
                parent_slot=block.parent_slot,
                parent_blockhash=block.parent_blockhash,
                executed_transaction_count=block.executed_transaction_count
            )

        # 转换区块元数据更新
        if pb_update.HasField('block_meta'):
            meta = pb_update.block_meta
            update.block_meta = SubscribeUpdateBlockMeta(
                slot=meta.slot,
                blockhash=meta.blockhash,
                parent_slot=meta.parent_slot,
                parent_blockhash=meta.parent_blockhash,
                executed_transaction_count=meta.executed_transaction_count
            )

        # 转换 Ping
        if pb_update.HasField('ping'):
            update.ping = SubscribeUpdatePing()

        # 转换 Pong
        if pb_update.HasField('pong'):
            update.pong = SubscribeUpdatePong(id=pb_update.pong.id)

        return update

    async def subscribe_transactions(
        self,
        filter: TransactionFilter,
        callbacks: SubscribeCallbacks,
    ) -> Subscription:
        """订阅交易"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected, call connect() first")

        if not HAS_PROTO:
            raise ImportError(
                "YellowstoneGrpc.subscribe_transactions: 需要 protobuf 生成的代码。"
                "请从 https://github.com/rpcpool/yellowstone-grpc 获取 proto 文件并生成 Python 代码。"
            )

        sub_id = str(uuid.uuid4())

        # 创建取消事件
        cancel_event = asyncio.Event()

        def cancel():
            cancel_event.set()

        sub = Subscription(
            id=sub_id,
            filter=filter,
            cancel=cancel,
            callbacks=callbacks,
        )

        self._subscribers[sub_id] = sub

        # 构建订阅请求
        req = self._build_subscribe_request(filter)

        # 启动处理任务
        asyncio.create_task(self._handle_stream(sub, req, cancel_event))

        return sub

    async def _handle_stream(
        self, sub: Subscription, req: Any, cancel_event: asyncio.Event
    ) -> None:
        """处理流式响应。

        Geyser 会周期性下发 ``SubscribeUpdate.ping``；必须在同一 Subscribe 双向流上回写
        ``SubscribeRequest.ping``（与 Rust / TypeScript / Go 一致），否则公共节点或 LB 可能断开。
        """
        outgoing: asyncio.Queue = asyncio.Queue()

        async def request_iterator():
            yield req
            while True:
                if cancel_event.is_set():
                    return
                ping_req = await outgoing.get()
                if ping_req is None:
                    return
                yield ping_req

        try:
            metadata = self._get_metadata()
            async for update in self._client.Subscribe(request_iterator(), metadata=metadata):
                if cancel_event.is_set():
                    break
                if update.HasField("ping"):
                    await outgoing.put(
                        geyser_pb2.SubscribeRequest(
                            ping=geyser_pb2.SubscribeRequestPing(id=1)
                        )
                    )
                    continue
                if sub.callbacks.on_update:
                    converted = self._convert_update(update)
                    sub.callbacks.on_update(converted)
        except Exception as e:
            if sub.callbacks.on_error:
                sub.callbacks.on_error(e)
        finally:
            await outgoing.put(None)
            self._subscribers.pop(sub.id, None)
            if sub.callbacks.on_end:
                sub.callbacks.on_end()

    async def unsubscribe(self, sub_id: str) -> None:
        """取消订阅"""
        sub = self._subscribers.pop(sub_id, None)
        if sub is None:
            raise ValueError(f"Subscription {sub_id} not found")
        sub.cancel()

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def get_config(self) -> ClientConfig:
        """获取客户端配置"""
        return self.config

    async def get_latest_blockhash(
        self, commitment: Optional[CommitmentLevel] = None
    ) -> GetLatestBlockhashResponse:
        """获取最新区块哈希"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.GetLatestBlockhashRequest()
        if commitment is not None:
            req.commitment = commitment.value

        metadata = self._get_metadata()
        resp = await self._client.get_latest_blockhash(req, metadata=metadata)

        return GetLatestBlockhashResponse(
            slot=resp.slot,
            blockhash=resp.blockhash,
            last_valid_block_height=resp.last_valid_block_height
        )

    async def get_block_height(
        self, commitment: Optional[CommitmentLevel] = None
    ) -> GetBlockHeightResponse:
        """获取区块高度"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.GetBlockHeightRequest()
        if commitment is not None:
            req.commitment = commitment.value

        metadata = self._get_metadata()
        resp = await self._client.get_block_height(req, metadata=metadata)

        return GetBlockHeightResponse(block_height=resp.block_height)

    async def get_slot(
        self, commitment: Optional[CommitmentLevel] = None
    ) -> GetSlotResponse:
        """获取当前 Slot"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.GetSlotRequest()
        if commitment is not None:
            req.commitment = commitment.value

        metadata = self._get_metadata()
        resp = await self._client.get_slot(req, metadata=metadata)

        return GetSlotResponse(slot=resp.slot)

    async def get_version(self) -> GetVersionResponse:
        """获取服务器版本"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.GetVersionRequest()
        metadata = self._get_metadata()
        resp = await self._client.get_version(req, metadata=metadata)

        return GetVersionResponse(version=resp.version)

    async def is_blockhash_valid(
        self, blockhash: str, commitment: Optional[CommitmentLevel] = None
    ) -> IsBlockhashValidResponse:
        """验证区块哈希是否有效"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.IsBlockhashValidRequest(blockhash=blockhash)
        if commitment is not None:
            req.commitment = commitment.value

        metadata = self._get_metadata()
        resp = await self._client.is_blockhash_valid(req, metadata=metadata)

        return IsBlockhashValidResponse(slot=resp.slot, valid=resp.valid)

    async def ping(self, count: int) -> PongResponse:
        """发送 Ping 请求"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.PingRequest(count=count)
        metadata = self._get_metadata()
        resp = await self._client.ping(req, metadata=metadata)

        return PongResponse(count=resp.count)

    async def subscribe_replay_info(self) -> SubscribeReplayInfoResponse:
        """订阅重放信息"""
        if not self._connected or not self._client:
            raise RuntimeError("Client not connected")

        if not HAS_PROTO:
            raise ImportError("需要 protobuf 生成的代码")

        req = geyser_pb2.SubscribeReplayInfoRequest()
        metadata = self._get_metadata()
        resp = await self._client.subscribe_replay_info(req, metadata=metadata)

        result = SubscribeReplayInfoResponse()
        if resp.HasField('first_available'):
            result.first_available = resp.first_available

        return result


def parse_commitment_level(s: str) -> CommitmentLevel:
    """解析承诺级别字符串"""
    s_lower = s.lower()
    if s_lower == "confirmed":
        return CommitmentLevel.CONFIRMED
    elif s_lower == "finalized":
        return CommitmentLevel.FINALIZED
    else:
        return CommitmentLevel.PROCESSED
