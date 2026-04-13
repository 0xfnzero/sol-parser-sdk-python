"""简单基准：纯 Python ``parse_log_optimized`` 耗时（原 bench_native 已废弃）。"""

from __future__ import annotations

import time

from sol_parser.parser import parse_log_optimized


def main() -> None:
    log = "Program log: noop"
    sig = "1111111111111111111111111111111111111111111111111111111111111111"
    n = 5000
    t0 = time.perf_counter()
    for _ in range(n):
        parse_log_optimized(log, sig, 1, 0, 0, 0)
    dt = time.perf_counter() - t0
    print(f"parse_log_optimized x{n}: {dt*1000:.2f} ms total, {dt/n*1e6:.2f} µs/call")


if __name__ == "__main__":
    main()
