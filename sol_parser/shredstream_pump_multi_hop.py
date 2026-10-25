"""Official multi_hop_swap curve inputs; no RPC or estimated execution amounts."""

from dataclasses import replace
import hashlib
import base58
from .event_types import DexEvent, PumpFunTradeEvent
from .grpc_types import EventType
from .instructions import PUMPFUN_PROGRAM_ID, PUMPSWAP_PROGRAM_ID
from .trade_source import RawInstructionPayload, TradeParseStatus
from .dex_parsers import Z

MULTI_HOP_SWAP = bytes([43, 100, 73, 19, 233, 246, 111, 148])
try:
    from solders.pubkey import Pubkey
except ImportError:
    Pubkey = None


def _curve_address(mint):
    seed = base58.b58decode(mint)
    if len(seed) != 32:
        raise ValueError("Invalid mint")
    if Pubkey is not None:
        return str(
            Pubkey.find_program_address(
                [b"bonding-curve", seed], Pubkey.from_string(PUMPFUN_PROGRAM_ID)
            )[0]
        )
    # Same off-curve test as Solana PDA derivation. Keep solders optional.
    p = 2**255 - 19
    d = -121665 * pow(121666, p - 2, p) % p
    program = base58.b58decode(PUMPFUN_PROGRAM_ID)
    for bump in range(255, -1, -1):
        key = hashlib.sha256(
            b"bonding-curve" + seed + bytes([bump]) + program + b"ProgramDerivedAddress"
        ).digest()
        y = (int.from_bytes(key, "little") & (2**255 - 1)) % p
        yy = y * y % p
        x_squared = (yy - 1) * pow(d * yy + 1, p - 2, p) % p
        if pow(x_squared, (p - 1) // 2, p) == p - 1:
            return base58.b58encode(key).decode()
    raise ValueError("No PDA bump")


def parse_curve_hops(data, indices, keys, index, metadata):
    if (
        len(data) != 24
        or not data.startswith(MULTI_HOP_SWAP)
        or len(indices) < 21
        or (len(indices) - 16) % 5
        or not any(data[8:16])
        or not any(data[16:24])
    ):
        return []

    def get(i):
        return keys[indices[i]] if indices[i] < len(keys) else None

    if get(11) != PUMPSWAP_PROGRAM_ID or get(12) != PUMPFUN_PROGRAM_ID or not get(0):
        return []
    hops = (len(indices) - 16) // 5

    def connected(buy):
        return hops > 1 and all(
            get(16 + i * 5 + int(not buy)) not in (None, Z)
            and get(16 + i * 5 + int(not buy)) == get(16 + (i + 1) * 5 + int(buy))
            for i in range(hops - 1)
        )

    buy, sell = connected(True), connected(False)
    known = buy != sell
    events = []
    for h in range(hops):
        start = 16 + h * 5
        mint, quote, curve = get(start), get(start + 1), get(start + 2)
        if (
            not mint
            or not quote
            or not curve
            or mint == Z
            or quote == Z
            or mint == quote
        ):
            continue
        try:
            if curve != _curve_address(mint):
                continue
        except ValueError:
            continue
        events.append(
            DexEvent(
                EventType.PUMP_FUN_TRADE,
                PumpFunTradeEvent(
                    metadata=replace(metadata),
                    ix_name="multi_hop_swap",
                    mint=mint,
                    quote_mint=quote,
                    user=get(0),
                    bonding_curve=curve,
                    associated_bonding_curve=get(start + 3) or Z,
                    associated_quote_bonding_curve=get(start + 4) or Z,
                    global_account=get(13) or Z,
                    fee_config=get(14) or Z,
                    event_authority=get(15) or Z,
                    program=PUMPFUN_PROGRAM_ID,
                    system_program=get(9) or Z,
                    is_buy=known and buy,
                    parse_status=(
                        TradeParseStatus.INSTRUCTION_DECODED
                        if known
                        else TradeParseStatus.UNRESOLVED
                    ),
                    third_program=RawInstructionPayload(
                        PUMPSWAP_PROGRAM_ID,
                        index,
                        [keys[i] if i < len(keys) else None for i in indices],
                        list(indices),
                        list(data),
                    ),
                ),
            )
        )
    return events
