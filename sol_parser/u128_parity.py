"""u128 小端十进制字符串与 Go `u128LEDecimalString` 语义一致性的自检（不依赖 Go 运行时）。"""

from __future__ import annotations

import struct
import sys

from .dex_parsers import DLMM_SWAP, _u128le_int, parse_dlmm_from_program_data, parse_orca_traded_from_data


def verify_u128_le_decimal() -> int:
    """断言 `_u128le_int` → `str` 与无符号 128 位小端整数值一致。"""
    cases = [
        0,
        1,
        255,
        256,
        10**18,
        2**64 - 1,
        2**127 - 1,
        2**128 - 1,
    ]
    buf = bytearray(32)
    for n in cases:
        le = n.to_bytes(16, "little")
        buf[:16] = le
        got = str(_u128le_int(bytes(buf), 0))
        if got != str(n):
            print(
                f"[u128-parity] 失败: 期望十进制 {n!s}, 得到 {got!s}",
                file=sys.stderr,
            )
            return 1
    print("[u128-parity] OK：小端 u128 十进制与 Go u128LEDecimalString 一致")
    return 0


def verify_orca_swap_sqrt_decimal_strings() -> int:
    """合成 OrcaWhirlpoolSwap 载荷，确认 `pre_sqrt_price` / `post_sqrt_price` 为十进制字符串。"""
    meta = {
        "signature": "",
        "slot": 0,
        "tx_index": 0,
        "block_time_us": 0,
        "grpc_recv_us": 0,
    }
    whirlpool = bytes(32)
    pre = (1000).to_bytes(16, "little")
    post = (2000).to_bytes(16, "little")
    tail = b"".join((0).to_bytes(8, "little") for _ in range(6))
    data = whirlpool + b"\x00" + pre + post + tail
    ev = parse_orca_traded_from_data(data, meta)
    if ev is None:
        print("[u128-parity] Orca 合成载荷解析失败", file=sys.stderr)
        return 1
    inner = ev.get("OrcaWhirlpoolSwap") or {}
    if inner.get("pre_sqrt_price") != "1000" or inner.get("post_sqrt_price") != "2000":
        print(f"[u128-parity] Orca sqrt 字段不符: {inner!r}", file=sys.stderr)
        return 1
    print("[u128-parity] OK：OrcaWhirlpoolSwap u128 字段为十进制字符串")
    return 0


def verify_dlmm_swap_fee_bps_decimal_string() -> int:
    """合成 MeteoraDlmmSwap 载荷，确认 `fee_bps` 为十进制字符串。"""
    meta = {
        "signature": "",
        "slot": 0,
        "tx_index": 0,
        "block_time_us": 0,
        "grpc_recv_us": 0,
    }
    fee_bps_val = 4242
    data = (
        bytes(64)
        + struct.pack("<ii", 0, 0)
        + struct.pack("<QQ", 0, 0)
        + b"\x00"
        + struct.pack("<QQ", 0, 0)
        + fee_bps_val.to_bytes(16, "little")
        + struct.pack("<Q", 0)
    )
    buf = struct.pack("<Q", DLMM_SWAP) + data
    ev = parse_dlmm_from_program_data(buf, meta)
    if ev is None:
        print("[u128-parity] DLMM 合成载荷解析失败", file=sys.stderr)
        return 1
    inner = ev.get("MeteoraDlmmSwap") or {}
    if inner.get("fee_bps") != str(fee_bps_val):
        print(f"[u128-parity] DLMM fee_bps 不符: {inner!r}", file=sys.stderr)
        return 1
    print("[u128-parity] OK：MeteoraDlmmSwap fee_bps 为十进制字符串")
    return 0


def run_all_u128_checks() -> int:
    if verify_u128_le_decimal() != 0:
        return 1
    if verify_orca_swap_sqrt_decimal_strings() != 0:
        return 1
    return verify_dlmm_swap_fee_bps_decimal_string()


def main() -> None:
    sys.exit(run_all_u128_checks())


if __name__ == "__main__":
    main()
