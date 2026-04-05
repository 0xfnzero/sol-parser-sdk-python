"""
校验本包 `dex_parsers.dispatch_program_data` 与 Go matcher 是否覆盖
`sol-parser-sdk-ts/scripts/program-log-discriminators.json` 中的字节序列。

用法（在仓库内任意目录均可，依赖 `__file__` 定位）::

    python3 -m sol_parser.verify_discriminators
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    # sol-parser-sdk-python/sol_parser/verify_discriminators.py -> parents[2] = monorepo root
    return Path(__file__).resolve().parents[2]


def _comma_seq(arr: list[int]) -> str:
    return ", ".join(str(b) for b in arr)


def main() -> int:
    root = _repo_root()
    snap_path = root / "sol-parser-sdk-ts/scripts/program-log-discriminators.json"
    py_path = root / "sol-parser-sdk-python/sol_parser/dex_parsers.py"
    go_dir = root / "sol-parser-sdk-golang/solparser"

    if not snap_path.is_file():
        print(f"[verify-discriminators] 缺少快照: {snap_path}", file=sys.stderr)
        return 1
    if not py_path.is_file():
        print(f"[verify-discriminators] 缺少: {py_path}", file=sys.stderr)
        return 1
    if not go_dir.is_dir():
        print(f"[verify-discriminators] 缺少: {go_dir}", file=sys.stderr)
        return 1

    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    py_text = py_path.read_text(encoding="utf-8")
    go_parts = [p.read_text(encoding="utf-8") for p in sorted(go_dir.glob("*.go"))]
    go_text = "\n".join(go_parts)

    entries: dict[str, list[int]] = {}
    for block in ("PROGRAM_LOG_DISC", "PUMPSWAP_DISC"):
        for k, arr in snap[block].items():
            if not isinstance(arr, list) or len(arr) != 8:
                print(f"[verify-discriminators] {block}.{k} 须为长度 8 的数组", file=sys.stderr)
                return 1
            entries[f"{block}.{k}"] = [int(x) for x in arr]

    failed = False
    for label, arr in sorted(entries.items()):
        seq = _comma_seq(arr)
        if seq not in py_text:
            print(f"[verify-discriminators] Python dex_parsers 未出现字节序列: {label} [{seq}]", file=sys.stderr)
            failed = True
        if seq not in go_text:
            print(f"[verify-discriminators] Go solparser 未出现字节序列: {label} [{seq}]", file=sys.stderr)
            failed = True

    if failed:
        print(
            "[verify-discriminators] 请同步 TS scripts/program-log-discriminators.json、"
            "Go matcher 与 Python dex_parsers。",
            file=sys.stderr,
        )
        return 1

    print(
        f"[verify-discriminators] OK：{len(entries)} 条字节序列在 Python dex_parsers 与 Go solparser 中均可找到"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
