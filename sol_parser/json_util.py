"""与 TS `dexEventToJsonString` 对应：将解析结果安全序列化为 JSON（`default=str` 覆盖非原生类型）。"""

from __future__ import annotations

import json
from typing import Any


def dex_event_json_dumps(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, default=str, **kwargs)
