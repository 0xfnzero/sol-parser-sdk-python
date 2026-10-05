"""Native canonical Solana Legacy, V0 and V1 wire decoding (SIMD-0385)."""

from __future__ import annotations
import base58


class _Reader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data, self.pos = data, offset

    def take(self, n: int) -> bytes:
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError("Truncated transaction")
        value = self.data[self.pos : self.pos + n]
        self.pos += n
        return value

    def uint(self, n: int = 1) -> int:
        return int.from_bytes(self.take(n), "little")

    def short(self) -> int:
        value = 0
        for i in range(3):
            b = self.uint()
            if i == 2 and b > 3:
                raise ValueError("Invalid short-u16")
            value |= (b & 127) << (7 * i)
            if not b & 128:
                if i and b == 0:
                    raise ValueError("Noncanonical short-u16")
                return value
        raise ValueError("Invalid short-u16")


def decode_wire_transaction(
    data: bytes, offset: int = 0, require_complete: bool = True
) -> tuple[dict, int]:
    if not isinstance(offset, int) or offset < 0 or offset >= len(data):
        raise ValueError("Invalid wire offset")
    r = _Reader(data, offset)
    version, signatures, config, lookups = "legacy", [], None, []
    if r.data[r.pos : r.pos + 1] == bytes([129]):
        r.take(1)
        version = 1
        header = r.take(3)
        mask = r.uint(4)
        blockhash = r.take(32)
        if mask & ~31 or mask & 3 not in (0, 3):
            raise ValueError("Invalid V1 config mask")
        count, keys_count = r.uint(), r.uint()
        if count > 64 or keys_count > 64 or header[0] > 12:
            raise ValueError("V1 transaction limit exceeded")
        keys = [r.take(32) for _ in range(keys_count)]
        config = {}
        for bit, key, size in [
            (3, "priorityFee", 8),
            (4, "computeUnitLimit", 4),
            (8, "loadedAccountsDataSizeLimit", 4),
            (16, "heapSize", 4),
        ]:
            if mask & bit:
                config[key] = r.uint(size)
        if "heapSize" in config and (
            not 32768 <= config["heapSize"] <= 262144 or config["heapSize"] % 1024
        ):
            raise ValueError("Invalid heap size")
        headers = [(r.uint(), r.uint(), r.uint(2)) for _ in range(count)]
        instructions = [
            {
                "programIdIndex": program,
                "accounts": list(r.take(accounts)),
                "data": base58.b58encode(r.take(length)).decode(),
            }
            for program, accounts, length in headers
        ]
        signatures = [r.take(64) for _ in range(header[0])]
        if r.pos - offset > 4096:
            raise ValueError("V1 transaction exceeds 4096 bytes")
    else:
        signature_count = r.short()
        if signature_count > 127:
            raise ValueError("Too many signatures")
        signatures = [r.take(64) for _ in range(signature_count)]
        first = r.uint()
        if first & 128:
            if first != 128:
                raise ValueError("Unknown transaction version")
            version = 0
            header = r.take(3)
        else:
            header = bytes([first]) + r.take(2)
        keys_count = r.short()
        if keys_count > 256:
            raise ValueError("Too many account keys")
        keys = [r.take(32) for _ in range(keys_count)]
        blockhash = r.take(32)
        instructions = []
        for _ in range(r.short()):
            program = r.uint()
            accounts = list(r.take(r.short()))
            payload = r.take(r.short())
            instructions.append(
                {
                    "programIdIndex": program,
                    "accounts": accounts,
                    "data": base58.b58encode(payload).decode(),
                }
            )
        if version == 0:
            for _ in range(r.short()):
                key = r.take(32)
                writable = list(r.take(r.short()))
                readonly = list(r.take(r.short()))
                lookups.append(
                    {
                        "accountKey": base58.b58encode(key).decode(),
                        "writableIndexes": writable,
                        "readonlyIndexes": readonly,
                    }
                )
        if len(signatures) != header[0]:
            raise ValueError("Signature count does not match header")
    if (
        header[0] > len(keys)
        or header[1] > header[0]
        or header[2] > len(keys) - header[0]
    ):
        raise ValueError("Invalid message header")
    if version == 1:
        if header[1] >= header[0]:
            raise ValueError("V1 requires a writable fee payer")
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate V1 accounts")
        for ix in instructions:
            if (
                ix["programIdIndex"] == 0
                or ix["programIdIndex"] >= len(keys)
                or any(i >= len(keys) for i in ix["accounts"])
            ):
                raise ValueError("Invalid V1 instruction index")
    account_count = len(keys) + sum(
        len(l["writableIndexes"]) + len(l["readonlyIndexes"]) for l in lookups
    )
    if account_count > 256:
        raise ValueError("Too many resolved account keys")
    if any(ix["programIdIndex"] >= len(keys) or any(i >= account_count for i in ix["accounts"]) for ix in instructions):
        raise ValueError("Invalid instruction index")
    if require_complete and r.pos != len(data):
        raise ValueError("Trailing transaction bytes")
    message = {
        "header": dict(
            zip(
                (
                    "numRequiredSignatures",
                    "numReadonlySignedAccounts",
                    "numReadonlyUnsignedAccounts",
                ),
                header,
            )
        ),
        "accountKeys": [base58.b58encode(key).decode() for key in keys],
        "recentBlockhash": base58.b58encode(blockhash).decode(),
        "instructions": instructions,
        "addressTableLookups": lookups,
    }
    if config is not None:
        message["config"] = config
    return {
        "signatures": [base58.b58encode(s).decode() for s in signatures],
        "message": message,
        "version": version,
    }, r.pos - offset
