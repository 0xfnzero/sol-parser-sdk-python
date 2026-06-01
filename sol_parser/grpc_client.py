"""Yellowstone gRPC 客户端实现

参考实现:
- https://github.com/chainstacklabs/grpc-geyser-tutorial
- https://github.com/rpcpool/yellowstone-grpc
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

import base58
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


def normalize_grpc_endpoint(endpoint: str, default_tls_from_config: bool) -> Tuple[str, bool]:
    """将 ``https://host:443`` / ``http://host`` 转为 gRPC 可用的 ``host:port``，并决定是否走 TLS。

    ``grpc.aio.secure_channel`` / ``insecure_channel`` 的 *target* 不能包含 scheme，否则会出现
    DNS 报错 ``Misformatted domain name``。
    """
    s = (endpoint or "").strip()
    if not s:
        return s, default_tls_from_config
    if "://" not in s:
        return s, default_tls_from_config
    parsed = urlparse(s)
    host = parsed.hostname or ""
    if not host:
        return s, default_tls_from_config
    port = parsed.port
    if port is not None:
        target = f"{host}:{port}"
    else:
        if parsed.scheme == "https":
            target = f"{host}:443"
        elif parsed.scheme == "http":
            target = f"{host}:80"
        else:
            target = host
    use_tls = parsed.scheme == "https"
    return target, use_tls


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
        self._dex_event_queue: Optional[asyncio.Queue] = None
        self._dex_event_filter: Optional[Any] = None
        self._dex_cancel_event: Optional[asyncio.Event] = None
        self._dex_task: Optional[asyncio.Task] = None
        self._dex_request_queue: Optional[asyncio.Queue] = None
        self._dex_current_req: Optional[Any] = None

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
    ) -> asyncio.Queue:
        """订阅 DEX 事件并返回低延迟 ``asyncio.Queue``。

        与 Rust ``YellowstoneGrpc::subscribe_dex_events`` 语义对齐：方法负责启动后台流，
        将解析后的 ``DexEvent`` 推入队列；调用方从返回队列消费事件。
        """
        if not self._connected:
            await self.connect()
        if not self._client:
            raise RuntimeError("Client not connected")

        from .grpc.subscribe_builder import build_subscribe_request

        req = build_subscribe_request(transaction_filters, account_filters)
        queue: asyncio.Queue = asyncio.Queue(maxsize=max(1, int(self.config.buffer_size or 100_000)))

        if self._dex_cancel_event is not None:
            self._dex_cancel_event.set()
        if self._dex_task is not None and not self._dex_task.done():
            self._dex_task.cancel()

        cancel_event = asyncio.Event()
        request_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._dex_event_queue = queue
        self._dex_event_filter = event_type_filter
        self._dex_cancel_event = cancel_event
        self._dex_request_queue = request_queue
        self._dex_current_req = req
        self._dex_task = asyncio.create_task(
            self._handle_dex_stream(req, queue, cancel_event, event_type_filter, request_queue)
        )
        return queue

    async def update_subscription(
        self,
        transaction_filters: List[TransactionFilter],
        account_filters: List[Any],
    ) -> None:
        """动态更新 DEX 订阅。

        Python gRPC runtime 不暴露当前双向流的发送端给外部 API；这里保留原队列，
        取消旧后台流并用新过滤器立即重建，调用方无需替换消费队列。
        """
        if self._dex_event_queue is None:
            raise RuntimeError("No active DEX subscription")
        if not self._connected:
            await self.connect()
        if not self._client:
            raise RuntimeError("Client not connected")

        from .grpc.subscribe_builder import build_subscribe_request

        req = build_subscribe_request(transaction_filters, account_filters)
        self._dex_current_req = req
        if self._dex_request_queue is None:
            raise RuntimeError("No active DEX subscription")
        await self._dex_request_queue.put(req)

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

            target, use_tls = normalize_grpc_endpoint(
                self.endpoint, self.config.enable_tls
            )

            if use_tls:
                # 创建 SSL 凭证
                ssl_creds = grpc.ssl_channel_credentials()

                # 添加认证
                auth_creds = self._create_auth_credentials()
                if auth_creds:
                    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
                else:
                    composite_creds = ssl_creds

                self._channel = aio.secure_channel(
                    target,
                    composite_creds,
                    options=channel_options
                )
            else:
                self._channel = aio.insecure_channel(
                    target,
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
            if self._dex_cancel_event is not None:
                self._dex_cancel_event.set()
            if self._dex_task is not None and not self._dex_task.done():
                self._dex_task.cancel()
            self._dex_cancel_event = None
            self._dex_task = None
            self._dex_event_queue = None
            self._dex_request_queue = None
            self._dex_current_req = None

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
        if hasattr(pb_update, "created_at") and pb_update.HasField("created_at"):
            ts = pb_update.created_at
            update.created_at = int(ts.seconds) * 1_000_000 + int(ts.nanos) // 1_000

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

    @staticmethod
    def _queue_event_nowait(queue: asyncio.Queue, event: Any) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # 与 Rust 有界 ArrayQueue 的低延迟取舍一致：消费端落后时丢弃新事件，避免阻塞 gRPC 流。
            pass

    async def _enqueue_transaction_dex_events(
        self,
        queue: asyncio.Queue,
        info: SubscribeUpdateTransactionInfo,
        slot: int,
        event_type_filter: Optional[Any],
        grpc_recv_us: int,
        block_time_us: Optional[int],
        order_dispatcher: Optional[Any] = None,
    ) -> None:
        if not info:
            return
        signature = base58.b58encode(bytes(info.signature)).decode("ascii") if info.signature else ""

        from .grpc_instruction_parser import (
            enrich_dex_events_with_subscribe_tx_info,
            parse_instructions_enhanced_from_subscribe_tx_info,
        )
        from .parser import parse_invoke_info, parse_log_optimized_with_program_id, parse_program_complete_info
        from .log_instr_dedup import dedupe_log_instruction_events
        from .pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge
        from .grpc_types import EventType

        instruction_events = parse_instructions_enhanced_from_subscribe_tx_info(
            info,
            slot,
            event_type_filter,
            block_time_us,
            grpc_recv_us,
        )

        log_events = []
        is_created_buy = False
        active_program_stack = []
        for log in info.log_messages:
            invoke = parse_invoke_info(log)
            if invoke is not None:
                program_id, depth = invoke
                del active_program_stack[max(0, depth - 1):]
                active_program_stack.append(program_id)

            ev = parse_log_optimized_with_program_id(
                log,
                signature,
                slot,
                int(info.index),
                block_time_us,
                grpc_recv_us,
                event_type_filter,
                is_created_buy,
                "",
                active_program_stack[-1] if active_program_stack else None,
            )
            if ev is None:
                completed = parse_program_complete_info(log)
                if completed is not None:
                    for i in range(len(active_program_stack) - 1, -1, -1):
                        if active_program_stack[i] == completed:
                            del active_program_stack[i:]
                            break
                continue
            if ev.type in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
                is_created_buy = True
            log_events.append(ev)
            completed = parse_program_complete_info(log)
            if completed is not None:
                for i in range(len(active_program_stack) - 1, -1, -1):
                    if active_program_stack[i] == completed:
                        del active_program_stack[i:]
                        break

        enrich_dex_events_with_subscribe_tx_info(instruction_events, info)
        enrich_dex_events_with_subscribe_tx_info(log_events, info)
        events = dedupe_log_instruction_events(log_events, instruction_events)
        enrich_pumpfun_same_tx_post_merge(events)
        if order_dispatcher is not None:
            order_dispatcher.push_transaction_events(
                events,
                slot,
                int(info.index),
                lambda ev: self._queue_event_nowait(queue, ev),
            )
        else:
            for ev in events:
                self._queue_event_nowait(queue, ev)

    async def _enqueue_account_dex_event(
        self,
        queue: asyncio.Queue,
        update: SubscribeUpdate,
        event_type_filter: Optional[Any],
        grpc_recv_us: int,
        block_time_us: Optional[int],
    ) -> None:
        if update.account is None or update.account.account is None:
            return
        acc = update.account.account

        from .accounts import AccountData, parse_account_unified
        from .grpc_types import EventMetadata

        signature = (
            base58.b58encode(bytes(acc.txn_signature)).decode("ascii")
            if acc.txn_signature
            else ""
        )
        account = AccountData(
            pubkey=base58.b58encode(bytes(acc.pubkey)).decode("ascii"),
            executable=bool(acc.executable),
            lamports=int(acc.lamports),
            owner=base58.b58encode(bytes(acc.owner)).decode("ascii"),
            rent_epoch=int(acc.rent_epoch),
            data=bytes(acc.data),
        )
        metadata = EventMetadata(
            signature=signature,
            slot=int(update.account.slot),
            tx_index=0,
            block_time_us=0 if block_time_us is None else block_time_us,
            grpc_recv_us=grpc_recv_us,
        )
        ev = parse_account_unified(account, metadata, event_type_filter)
        if ev is not None:
            self._queue_event_nowait(queue, ev)

    async def _handle_dex_stream(
        self,
        req: Any,
        queue: asyncio.Queue,
        cancel_event: asyncio.Event,
        event_type_filter: Optional[Any],
        request_queue: asyncio.Queue,
    ) -> None:
        delay = 1.0
        from .order_buffer import OrderDispatcher

        order_dispatcher = OrderDispatcher(self.config)

        async def flush_loop() -> None:
            while not cancel_event.is_set():
                await asyncio.sleep(order_dispatcher.interval_s)
                order_dispatcher.flush_due(lambda ev: self._queue_event_nowait(queue, ev))

        flush_task: Optional[asyncio.Task] = None
        if order_dispatcher.needs_timer:
            flush_task = asyncio.create_task(flush_loop())

        try:
            while not cancel_event.is_set():
                outgoing: asyncio.Queue = asyncio.Queue()

                async def request_iterator():
                    yield self._dex_current_req or req
                    while True:
                        if cancel_event.is_set():
                            return
                        ping_req = await outgoing.get()
                        if ping_req is None:
                            return
                        yield ping_req

                async def request_pump() -> None:
                    while not cancel_event.is_set():
                        next_req = await request_queue.get()
                        self._dex_current_req = next_req
                        await outgoing.put(next_req)

                pump_task = asyncio.create_task(request_pump())
                try:
                    metadata = self._get_metadata()
                    async for pb_update in self._client.Subscribe(request_iterator(), metadata=metadata):
                        if cancel_event.is_set():
                            break
                        if pb_update.HasField("ping"):
                            await outgoing.put(
                                geyser_pb2.SubscribeRequest(
                                    ping=geyser_pb2.SubscribeRequestPing(id=1)
                                )
                            )
                            continue

                        grpc_recv_us = int(time.time() * 1_000_000)
                        update = self._convert_update(pb_update)
                        block_time_us = update.created_at
                        if update.transaction and update.transaction.transaction:
                            await self._enqueue_transaction_dex_events(
                                queue,
                                update.transaction.transaction,
                                int(update.transaction.slot),
                                event_type_filter,
                                grpc_recv_us,
                                block_time_us,
                                order_dispatcher,
                            )
                        if update.account:
                            await self._enqueue_account_dex_event(
                                queue,
                                update,
                                event_type_filter,
                                grpc_recv_us,
                                block_time_us,
                            )
                    delay = 1.0
                except asyncio.CancelledError:
                    break
                except Exception:
                    order_dispatcher.flush_all(lambda ev: self._queue_event_nowait(queue, ev))
                    if cancel_event.is_set():
                        break
                    await asyncio.sleep(delay)
                    delay = min(delay * 2.0, 60.0)
                finally:
                    pump_task.cancel()
                    await outgoing.put(None)
        finally:
            if flush_task is not None:
                flush_task.cancel()
            order_dispatcher.flush_all(lambda ev: self._queue_event_nowait(queue, ev))

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
