"""高性能时间源（对齐 Rust ``sol_parser_sdk::core::now_micros`` 语义）。"""

from __future__ import annotations

import time


def now_micros() -> int:
    """当前时间（微秒），单调性与 ``time.time_ns()`` 一致。"""
    return time.time_ns() // 1000
