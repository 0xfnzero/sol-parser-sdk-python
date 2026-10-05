"""与 TS `dexEventToJsonString` 对应：将解析结果安全序列化为 JSON（`default=str` 覆盖非原生类型）。"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from .event_types import DexEvent
from .grpc_types import EventType


def dex_event_json_dumps(obj: Any, **kwargs: Any) -> str:
    return json.dumps(_precise_metadata(dex_event_to_jsonable(obj)), default=str, **kwargs)


def dex_event_to_jsonable(ev: Any) -> Any:
    """将 :class:`~sol_parser.event_types.DexEvent` 转为可 JSON 化的 ``{"type","data"}`` 结构。

    ``data`` 内嵌 dataclass（含 ``metadata``）用 :func:`dataclasses.asdict` 递归展开，
    便于 ``indent`` 后一行一个字段阅读。
    """
    if isinstance(ev, DexEvent):
        t = ev.type.value if isinstance(ev.type, EventType) else str(ev.type)
        if ev.data is None:
            return {"type": t, "data": None}
        if is_dataclass(ev.data):
            return {"type": t, "data": asdict(ev.data)}
        return {"type": t, "data": ev.data}
    if is_dataclass(ev):
        return asdict(ev)
    return ev


def format_dex_event_json(ev: Any, *, indent: int = 2, ensure_ascii: bool = False) -> str:
    """将事件格式化为缩进 JSON 字符串（默认每字段一行，对齐常见日志阅读习惯）。"""
    return dex_event_json_dumps(
        dex_event_to_jsonable(ev),
        indent=indent,
        ensure_ascii=ensure_ascii,
    )


def _precise_metadata(obj):
    """Match Node exact metadata JSON without changing floating latency metrics."""
    if isinstance(obj,dict):
        result={k:_precise_metadata(v) for k,v in obj.items()}
        if "signature" in obj and all(k in obj for k in ("slot","tx_index","block_time_us","grpc_recv_us")):
            from .grpc_types import EventMetadata
            validated=EventMetadata(**{k:obj[k] for k in ("signature","slot","tx_index","block_time_us","grpc_recv_us")})
            for k in ("slot","tx_index","block_time_us","grpc_recv_us"):result[k]=str(getattr(validated,k))
        return result
    if isinstance(obj,(tuple,list)):return [_precise_metadata(v) for v in obj]
    if is_dataclass(obj):return _precise_metadata(asdict(obj))
    return obj
