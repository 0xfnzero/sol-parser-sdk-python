"""Native instruction-level route analysis, aligned with Rust parser 0.7.7.

Accepts JSON-encoded RPC transactions. This is execution evidence, not a quote
or automatic route selector. Unknown invocations and failed intent remain visible.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Optional
import base58
import base64
from .wire_transaction import decode_wire_transaction

ZERO = "11111111111111111111111111111111"
TOKEN = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
WSOL = "So11111111111111111111111111111111111111112"
PROGRAMS = {
    'PumpFun': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
    "MeteoraDammV2": "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG",
    "RaydiumClmm": "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "RaydiumCpmm": "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    "RaydiumAmmV4": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "LaunchLab": "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj",
    "OrcaWhirlpool": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "MeteoraDlmm": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
    "PumpSwap": "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
}
STANDARD = "4E876qZTE9FJMrBzgVtBrSrzz2TLivB5Y5QXPjB4gZL7"
REWARD = "6BwHHDg3u1854jC8PDLXvR4spTcLNaoBxLJNGC4nTESt"
U64_MAX = (1 << 64) - 1


def stonkfun_mode_from_platform_config(key: str) -> Optional[str]:
    return "Standard" if key == STANDARD else "Reward" if key == REWARD else None


@dataclass(frozen=True)
class InstructionPosition:
    outer_index: int
    inner_index: Optional[int]
    stack_height: Optional[int]


@dataclass
class RouteSwapLeg:
    position: InstructionPosition
    program: str
    protocol: str
    pool: str
    trader: str
    input_account: str
    output_account: str
    input_mint: Optional[str]
    output_mint: Optional[str]
    amount_specified_is_input: bool
    specified_amount: int
    other_amount_threshold: int
    actual_input_amount: Optional[int] = None
    actual_output_amount: Optional[int] = None
    stonkfun_mode: Optional[str] = None
    stonkfun_graduated: bool = False


@dataclass
class RouteTokenTransfer:
    position: InstructionPosition
    program: str
    source: str
    destination: str
    mint: Optional[str]
    amount: int
    withheld_fee: Optional[int]


@dataclass
class RouteUnknownInvocation:
    position: InstructionPosition
    program: str
    has_token_transfers: bool
    has_known_swap_descendants: bool


@dataclass
class RouteNativeTokenAction:
    position: InstructionPosition
    account: str
    action: Any


@dataclass
class TransactionRoute:
    signature: str
    succeeded: bool
    legs: list[RouteSwapLeg] = field(default_factory=list)
    transfers: list[RouteTokenTransfer] = field(default_factory=list)
    native_token_actions: list[RouteNativeTokenAction] = field(default_factory=list)
    unknown_invocations: list[RouteUnknownInvocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Invocation:
    position: InstructionPosition
    program: str
    accounts: list[str]
    data: bytes

    def a(self, i: int) -> str:
        return self.accounts[i] if 0 <= i < len(self.accounts) else ZERO


def _disc(values: list[int]) -> bytes:
    return bytes(values)


def _pumpfun_native_debit(ix, children, leg):
    # Only immediate protocol payments count; exclude rent and wrapping.
    if leg.protocol!='PumpFun' or len(ix.accounts)<17 or ix.a(2)!=WSOL or leg.input_account!=leg.trader:
        return None
    recipients={ix.a(i) for i in (6,8,10,16)}
    depth=ix.position.stack_height
    if depth is None:return None
    total=0;paid_pool=False
    for child in children:
        if child.program!=ZERO or len(child.data)!=12 or child.data[:4]!=bytes([2,0,0,0]) or len(child.accounts)<2 or child.a(0)!=leg.trader:
            continue
        if child.position.stack_height!=depth+1:return None
        if child.a(1) not in recipients:return None
        paid_pool=paid_pool or child.a(1)==leg.pool
        total+=int.from_bytes(child.data[4:12],'little')
        if total>U64_MAX:return None
    return total if paid_pool else None


SWAP = _disc([248, 198, 158, 145, 225, 117, 135, 200])
SWAP_V2 = _disc([43, 4, 237, 11, 26, 201, 30, 98])
CP_IN = _disc([143, 190, 90, 218, 196, 30, 51, 222])
CP_OUT = _disc([55, 217, 98, 86, 163, 74, 180, 173])
DL_IN = {SWAP, _disc([65, 75, 63, 76, 235, 91, 91, 136])}
DL_OUT = {
    _disc([250, 73, 101, 33, 38, 207, 75, 184]),
    _disc([43, 215, 247, 132, 137, 60, 243, 81]),
}
LAB = {
    _disc([250, 234, 13, 123, 213, 156, 19, 236]): (True, True),
    _disc([24, 211, 116, 40, 105, 3, 153, 56]): (True, False),
    _disc([149, 39, 222, 155, 211, 124, 152, 26]): (False, True),
    _disc([95, 200, 71, 34, 8, 9, 11, 166]): (False, False),
}
PUMP = {
    _disc([198, 46, 21, 82, 180, 217, 232, 112]): (True, True),
    _disc([102, 6, 61, 18, 1, 218, 235, 234]): (True, False),
    _disc([51, 230, 133, 164, 1, 127, 131, 173]): (False, True),
}
CURVE_V2={
    _disc([194,171,28,70,104,77,91,47]):(True,True),
    _disc([184,23,238,97,103,197,211,61]):(True,False),
    _disc([93,246,130,60,231,233,64,178]):(False,True),
}
CURVE_LEGACY={
    _disc([56,252,116,8,158,223,205,95]):(True,True),
    _disc([102,6,61,18,1,218,235,234]):(True,False),
    _disc([51,230,133,164,1,127,131,173]):(False,True),
}


def _swap(
    ix: _Invocation, mints: dict[str, str], graduated: set[str]
) -> Optional[RouteSwapLeg]:
    d, a, n = ix.data, ix.a, len(ix.accounts)
    disc, pair, mode = d[:8], None, None
    protocol = next((p for p, key in PROGRAMS.items() if key == ix.program), None)
    exact, offset, invert = True, 8, False
    if (
        protocol == "RaydiumClmm"
        and disc in (SWAP, SWAP_V2)
        and n >= 10
        and len(d) >= 41
    ):
        pool, user, source, dest = a(2), a(0), a(3), a(4)
        exact = d[40] != 0
        if disc == SWAP_V2 and n >= 13:
            pair = (a(11), a(12))
    elif protocol == "OrcaWhirlpool" and disc in (SWAP, SWAP_V2) and len(d) >= 42:
        v2, direction = disc == SWAP_V2, d[41] != 0
        if n < (15 if v2 else 11):
            return None
        pool, user = a(4 if v2 else 2), a(3 if v2 else 1)
        x, y = (7, 9) if v2 else (3, 5)
        source, dest, exact = (
            a(x if direction else y),
            a(y if direction else x),
            d[40] != 0,
        )
        if v2:
            pair = (a(5), a(6)) if direction else (a(6), a(5))
    elif protocol == "RaydiumCpmm" and disc in (CP_IN, CP_OUT) and n >= 13:
        pool, user, source, dest = a(3), a(0), a(4), a(5)
        pair, exact = (a(10), a(11)), disc == CP_IN
        invert = not exact
    elif protocol == "MeteoraDammV2" and disc in (SWAP, _disc([65,75,63,76,235,91,91,136])) and n >= 11:
        if len(d) < 24:
            return None
        if disc != SWAP:
            if len(d) < 25 or d[24] > 2:
                return None
            exact = d[24] != 2
        pool, user, source, dest = a(1), a(8), a(2), a(3)
        # Pool mint order does not determine direction; use user-account evidence.
    elif protocol == "MeteoraDlmm" and disc in DL_IN | DL_OUT and n >= 11:
        pool, user, source, dest = a(0), a(10), a(4), a(5)
        exact, invert = disc in DL_IN, disc in DL_OUT
    elif protocol in ("LaunchLab", "PumpSwap") and disc in (
        LAB if protocol == "LaunchLab" else PUMP
    ):
        buy, exact = (LAB if protocol == "LaunchLab" else PUMP)[disc]
        if n < (18 if protocol == "LaunchLab" else 21):
            return None
        source, dest = a(6 if buy else 5), a(5 if buy else 6)
        if protocol == "LaunchLab":
            pool, user = a(4), a(0)
            pair, mode = (
                (a(10), a(9)) if buy else (a(9), a(10))
            ), stonkfun_mode_from_platform_config(a(3))
        else:
            pool, user = a(0), a(1)
            pair = (a(4), a(3)) if buy else (a(3), a(4))
    elif protocol=='PumpFun' and disc in CURVE_V2 and n>=16:
        buy,exact=CURVE_V2[disc]
        pool,user,source,dest=a(10),a(13),a(15 if buy else 14),a(14 if buy else 15)
        pair=(a(2),a(1)) if buy else (a(1),a(2))
        if a(2)==WSOL:
            if buy: source=user
            else: dest=user
    elif protocol=='PumpFun' and disc in CURVE_LEGACY and n>=12:
        buy,exact=CURVE_LEGACY[disc]
        pool,user,source,dest=a(3),a(6),a(6 if buy else 5),a(5 if buy else 6)
        pair=(WSOL,a(2)) if buy else (a(2),WSOL)
    elif protocol == "RaydiumAmmV4" and len(d) >= 17 and d[0] in (9, 11, 16, 17):
        modern = d[0] in (16, 17)
        if n < (8 if modern else 17):
            return None
        pool, user = a(1), a(7 if modern else n - 1)
        source, dest = (a(5), a(6)) if modern else (a(n - 3), a(n - 2))
        offset, exact = 1, d[0] in (9, 16)
        invert = not exact
    else:
        return None
    if len(d) < offset + 16:
        return None
    first, second = int.from_bytes(d[offset : offset + 8], "little"), int.from_bytes(
        d[offset + 8 : offset + 16], "little"
    )
    source_mint = mints.get(source) or (pair[0] if pair and pair[0] != ZERO else None)
    dest_mint = mints.get(dest) or (pair[1] if pair and pair[1] != ZERO else None)
    return RouteSwapLeg(
        ix.position,
        ix.program,
        protocol,
        pool,
        user,
        source,
        dest,
        source_mint,
        dest_mint,
        exact,
        second if invert else first,
        first if invert else second,
        stonkfun_mode=mode,
        stonkfun_graduated=protocol == "RaydiumCpmm" and pool in graduated,
    )


def _checked(ix: _Invocation) -> bool:
    return (
        ix.program in (TOKEN, TOKEN_2022)
        and len(ix.data) >= 10
        and ix.data[0] == 12
        and len(ix.accounts) >= 4
    )


def _with_fee(ix: _Invocation) -> bool:
    return (
        ix.program == TOKEN_2022
        and len(ix.data) >= 19
        and ix.data[:2] == bytes([26, 1])
        and len(ix.accounts) >= 4
    )


def _transfer(ix: _Invocation, mints: dict[str, str]) -> Optional[RouteTokenTransfer]:
    if ix.program not in (TOKEN, TOKEN_2022) or not ix.data:
        return None
    if _checked(ix):
        dest, offset, fee = 2, 1, 0 if ix.program == TOKEN else None
    elif _with_fee(ix):
        dest, offset, fee = 2, 2, int.from_bytes(ix.data[11:19], "little")
    elif ix.data[0] == 3 and len(ix.data) >= 9 and len(ix.accounts) >= 3:
        dest, offset, fee = 1, 1, 0
    else:
        return None
    return RouteTokenTransfer(
        ix.position,
        ix.program,
        ix.a(0),
        ix.a(dest),
        mints.get(ix.a(0)),
        int.from_bytes(ix.data[offset : offset + 8], "little"),
        fee,
    )


def _descendant(parent: InstructionPosition, child: InstructionPosition) -> bool:
    if parent.outer_index != child.outer_index:
        return False
    if parent.inner_index is None:
        return child.inner_index is not None
    return (
        child.inner_index is not None
        and child.inner_index > parent.inner_index
        and parent.stack_height is not None
        and child.stack_height is not None
        and child.stack_height > parent.stack_height
    )


def analyze_rpc_transaction_routes(
    transaction: dict, graduated_stonkfun_pools: Iterable[str] = ()
) -> TransactionRoute:
    tx = transaction.get("result", transaction)
    if not isinstance(tx, dict) or not isinstance(tx.get("meta"), dict):
        raise ValueError("Transaction metadata missing")
    if "err" not in tx["meta"]:
        raise ValueError("Transaction execution status missing")
    body = tx["transaction"]
    if isinstance(body, list):
        if len(body) != 2 or body[1] != "base64":
            raise ValueError("Expected base64 wire encoding")
        body, _ = decode_wire_transaction(base64.b64decode(body[0], validate=True))
    message, meta = body["message"], tx["meta"]
    if not isinstance(message, dict):
        raise ValueError("Expected JSON-encoded compiled transaction")
    keys = [k if isinstance(k, str) else k["pubkey"] for k in message["accountKeys"]]
    loaded = meta.get("loadedAddresses") or {}
    keys += loaded.get("writable", []) + loaded.get("readonly", [])

    def key(i: int) -> str:
        if type(i) is not int or not 0 <= i < len(keys):
            raise ValueError("Invalid compiled account index")
        return keys[i]

    invocations: list[_Invocation] = []
    groups = meta.get("innerInstructions") or []
    if not isinstance(groups, list):
        raise ValueError("Invalid compiled instruction groups")
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Invalid compiled instruction group")
        index = group.get("index")
        if type(index) is not int or not 0 <= index < len(message["instructions"]) or index in seen or not isinstance(group.get("instructions"), list):
            raise ValueError("Invalid compiled instruction group")
        seen.add(index)
        for ix in group["instructions"]:
            if not isinstance(ix, dict) or (ix.get("stackHeight") is not None and (type(ix["stackHeight"]) is not int or ix["stackHeight"] < 2)):
                raise ValueError("Invalid compiled stack height")
    for i, outer in enumerate(message["instructions"]):
        batch = [(outer, InstructionPosition(i, None, 1))]
        for group in groups:
            if group["index"] == i:
                batch += [
                    (ix, InstructionPosition(i, j, ix.get("stackHeight")))
                    for j, ix in enumerate(group["instructions"])
                ]
        for ix, position in batch:
            if "programIdIndex" not in ix:
                raise ValueError("Expected compiled instructions, not jsonParsed")
            data = (
                base58.b58decode(ix["data"])
                if isinstance(ix["data"], str)
                else bytes(ix["data"])
            )
            invocations.append(
                _Invocation(
                    position,
                    key(ix["programIdIndex"]),
                    [key(k) for k in ix["accounts"]],
                    data,
                )
            )
    mints: dict[str, str] = {}
    for balance in (meta.get("preTokenBalances") or []) + (
        meta.get("postTokenBalances") or []
    ):
        # Reject malformed mints rather than inventing pool identity from a key.
        if len(base58.b58decode(balance["mint"])) == 32:
            mints[key(balance["accountIndex"])] = balance["mint"]
    for ix in invocations:
        if _checked(ix) or _with_fee(ix):
            mints[ix.a(0)] = mints[ix.a(2)] = ix.a(1)
        if (
            ix.program in (TOKEN, TOKEN_2022)
            and len(ix.accounts) >= 2
            and (
                (ix.data == bytes([1]))
                or (len(ix.data) == 33 and ix.data[0] in (16, 18))
            )
        ):
            mints[ix.a(0)] = ix.a(1)
    while True:
        before = len(mints)
        for ix in invocations:
            if (
                ix.program in (TOKEN, TOKEN_2022)
                and len(ix.data) >= 9
                and ix.data[0] == 3
                and len(ix.accounts) >= 3
            ):
                mint = mints.get(ix.a(0)) or mints.get(ix.a(1))
                if mint:
                    mints.setdefault(ix.a(0), mint)
                    mints.setdefault(ix.a(1), mint)
        if len(mints) == before:
            break
    mints.pop(ZERO, None)
    signatures = body.get("signatures", [])
    route = TransactionRoute(
        signatures[0] if signatures else base58.b58encode(bytes(64)).decode(),
        meta.get("err") is None,
    )
    graduated = set(graduated_stonkfun_pools)
    for i, ix in enumerate(invocations):
        own = _transfer(ix, mints)
        if own:
            route.transfers.append(own)
        children = []
        for child in invocations[i + 1 :]:
            if not _descendant(ix.position, child.position):
                break
            children.append(child)
        nested = [t for c in children if (t := _transfer(c, mints)) is not None]
        leg = _swap(ix, mints, graduated)
        if leg:
            if route.succeeded:
                inputs = [t.amount for t in nested if t.source == leg.input_account]
                outputs = [
                    (
                        None
                        if t.withheld_fee is None or t.withheld_fee > t.amount
                        else t.amount - t.withheld_fee
                    )
                    for t in nested
                    if t.destination == leg.output_account
                ]
                if inputs and sum(inputs) <= U64_MAX:
                    leg.actual_input_amount = sum(inputs)
                if leg.protocol=='PumpFun' and leg.input_mint==WSOL and leg.input_account==leg.trader:
                    leg.actual_input_amount=_pumpfun_native_debit(ix,children,leg)
                if (
                    outputs
                    and all(x is not None for x in outputs)
                    and sum(outputs) <= U64_MAX
                ):
                    leg.actual_output_amount = sum(outputs)
            route.legs.append(leg)
        elif ix.program not in (
            TOKEN,
            TOKEN_2022,
            ZERO,
            "ComputeBudget111111111111111111111111111111",
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        ):
            route.unknown_invocations.append(
                RouteUnknownInvocation(
                    ix.position,
                    ix.program,
                    bool(nested),
                    any(_swap(c, mints, graduated) for c in children),
                )
            )
        target, action = None, None
        if (
            ix.program == ZERO
            and len(ix.data) == 12
            and ix.data[:4] == bytes([2, 0, 0, 0])
            and len(ix.accounts) >= 2
        ):
            target, action = ix.a(1), {
                "Fund": {
                    "source": ix.a(0),
                    "lamports": int.from_bytes(ix.data[4:12], "little"),
                }
            }
        elif ix.program in (TOKEN, TOKEN_2022):
            if ix.data == bytes([17]) and ix.accounts:
                target, action = ix.a(0), "SyncNative"
            elif ix.data == bytes([9]) and len(ix.accounts) >= 3:
                target, action = ix.a(0), {
                    "Close": {"destination": ix.a(1), "authority": ix.a(2)}
                }
        if target and mints.get(target) == WSOL:
            route.native_token_actions.append(
                RouteNativeTokenAction(ix.position, target, action)
            )
    return route
