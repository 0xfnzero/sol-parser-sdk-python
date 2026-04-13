"""gRPC ShredStream ``Entry.entries`` 负载解码（对齐 Node ``entries_decode.ts`` / Go ``DecodeEntriesBincode``）。"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Optional

MAX_VEC_ENTRIES = 100_000


def read_u64_le(buf: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", buf, offset)[0]


def bincode_vec_entry_count(entries_bytes: bytes) -> int:
    if len(entries_bytes) < 8:
        raise ValueError("shredstream: entries payload too short for vec length")
    n = read_u64_le(entries_bytes, 0)
    if n > MAX_VEC_ENTRIES:
        raise ValueError(f"shredstream: corrupt entry_count {n} exceeds limit")
    return n


def decode_compact_u16(buf: bytes, pos: int) -> Optional[tuple[int, int]]:
    if pos >= len(buf):
        return None
    b0 = buf[pos]
    if b0 < 0x80:
        return (b0, 1)
    if pos + 1 >= len(buf):
        return None
    b1 = buf[pos + 1]
    if b1 < 0x80:
        return ((b0 & 0x7F) | (b1 << 7), 2)
    if pos + 2 >= len(buf):
        return None
    b2 = buf[pos + 2]
    return ((b0 & 0x7F) | ((b1 & 0x7F) << 7) | (b2 << 14), 3)


@dataclass
class _ParsedTx:
    tx_len: int
    signatures: List[bytes]


def parse_transaction_wire(buf: bytes, pos: int) -> Optional[_ParsedTx]:
    start = pos
    if pos >= len(buf):
        return None
    sig_count_enc = decode_compact_u16(buf, pos)
    if not sig_count_enc:
        return None
    p = pos + sig_count_enc[1]
    sig_count = sig_count_enc[0]
    sigs_end = p + sig_count * 64
    if sigs_end > len(buf):
        return None
    sigs: List[bytes] = []
    for _ in range(sig_count):
        sigs.append(buf[p : p + 64])
        p += 64
    if p >= len(buf):
        return None
    msg_first = buf[p]
    is_v0 = msg_first >= 0x80
    if is_v0:
        p += 1
    p += 3
    if p > len(buf):
        return None
    acct_enc = decode_compact_u16(buf, p)
    if not acct_enc:
        return None
    p += acct_enc[1]
    p += acct_enc[0] * 32
    if p > len(buf):
        return None
    ix_count_enc = decode_compact_u16(buf, p)
    if not ix_count_enc:
        return None
    p += ix_count_enc[1]
    ix_count = ix_count_enc[0]
    for _ in range(ix_count):
        p += 1
        if p > len(buf):
            return None
        acct_len_enc = decode_compact_u16(buf, p)
        if not acct_len_enc:
            return None
        p += acct_len_enc[1]
        p += acct_len_enc[0]
        if p > len(buf):
            return None
        data_len_enc = decode_compact_u16(buf, p)
        if not data_len_enc:
            return None
        p += data_len_enc[1]
        p += data_len_enc[0]
        if p > len(buf):
            return None
    if is_v0:
        if p >= len(buf):
            return None
        atl_count_enc = decode_compact_u16(buf, p)
        if not atl_count_enc:
            return None
        p += atl_count_enc[1]
        atl_count = atl_count_enc[0]
        for _ in range(atl_count):
            p += 32
            if p > len(buf):
                return None
            w_len_enc = decode_compact_u16(buf, p)
            if not w_len_enc:
                return None
            p += w_len_enc[1]
            p += w_len_enc[0]
            if p > len(buf):
                return None
            r_len_enc = decode_compact_u16(buf, p)
            if not r_len_enc:
                return None
            p += r_len_enc[1]
            p += r_len_enc[0]
            if p > len(buf):
                return None
    return _ParsedTx(tx_len=p - start, signatures=sigs)


class _BatchDecoder:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.expected_entry_count = 0
        self.entries_yielded = 0
        self.cursor = 0

    def append(self, payload: bytes) -> None:
        self.buffer.extend(payload)

    def try_decode_entry(self) -> Optional[List[bytes]]:
        pos = self.cursor
        buf = self.buffer
        if pos + 48 > len(buf):
            return None
        p = pos + 8 + 32
        tx_count = read_u64_le(buf, p)
        p += 8
        txs: List[bytes] = []
        for _ in range(tx_count):
            tx_start = p
            parsed = parse_transaction_wire(buf, p)
            if not parsed:
                raise ValueError("shredstream: truncated transaction in entry")
            raw = bytes(buf[tx_start : tx_start + parsed.tx_len])
            txs.append(raw)
            p = tx_start + parsed.tx_len
        self.cursor = p
        return txs

    def push_flat(self, payload: bytes) -> List[bytes]:
        self.append(payload)
        if self.expected_entry_count == 0 and self.entries_yielded == 0 and self.cursor == 0:
            if len(self.buffer) < 8:
                raise ValueError("shredstream: entries payload too short for vec length")
            count = read_u64_le(self.buffer, 0)
            if count > MAX_VEC_ENTRIES:
                raise ValueError(f"shredstream: corrupt entry_count {count} exceeds limit")
            self.expected_entry_count = int(count)
            self.cursor = 8
        out: List[bytes] = []
        while self.entries_yielded < self.expected_entry_count:
            entry_txs = self.try_decode_entry()
            if entry_txs is None:
                raise ValueError(f"shredstream: incomplete entry at offset {self.cursor}")
            out.extend(entry_txs)
            self.entries_yielded += 1
        return out


def decode_entries_bincode_flat(entries_bytes: bytes) -> List[bytes]:
    if not entries_bytes:
        return []
    dec = _BatchDecoder()
    return dec.push_flat(entries_bytes)
