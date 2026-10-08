"""Explicit simulateTransaction evidence adapter; no RPC or wire reserialization."""

from __future__ import annotations
import re
import struct
import base58
from .wire_transaction import decode_wire_transaction
from .transaction_route import analyze_rpc_transaction_routes, TOKEN, TOKEN_2022, ZERO


def _unsigned(value, bits):
    if type(value) not in (str, int) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError("Invalid simulation integer")
    n = int(value)
    if not 0 <= n < 1 << bits:
        raise ValueError("Simulation integer outside range")
    return n


def analyze_simulation_routes(wire, response, graduated_pools=()):
    """Original wire plus simulateTransaction response. SPL transfers and ATA setup.

    Unsupported parsed CPI fail explicitly. Raw/compiled CPI are preserved.
    V0 requires caller-resolved addresses in result.value.loadedAddresses.
    """
    tx, _ = decode_wire_transaction(wire)
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        raise ValueError("Simulation response missing execution metadata")
    value = response["result"].get("value")
    if (
        response.get("error")
        or not isinstance(value, dict)
        or "err" not in value
        or "innerInstructions" not in value
    ):
        raise ValueError("Simulation response missing execution metadata")
    groups = value["innerInstructions"]
    if groups is None:
        groups = []
    if not isinstance(groups, list):
        raise ValueError("Invalid simulation inner instructions")
    lookups = tx["message"]["addressTableLookups"]
    loaded = value.get("loadedAddresses")
    if loaded is None:
        if lookups:
            raise ValueError("V0 ALT addresses unavailable; provide loadedAddresses")
        loaded = {"writable": [], "readonly": []}
    if not isinstance(loaded, dict):
        raise ValueError("Invalid simulation loaded addresses")
    for side in ("writable", "readonly"):
        addresses = loaded.get(side)
        expected = sum(len(lookup[side + "Indexes"]) for lookup in lookups)
        if not isinstance(addresses, list) or len(addresses) != expected:
            raise ValueError("Simulation loaded address count does not match wire lookups")
        for address in addresses:
            if not isinstance(address, str) or len(base58.b58decode(address)) != 32:
                raise ValueError("Invalid simulation loaded public key")
    keys = tx["message"]["accountKeys"] + loaded["writable"] + loaded["readonly"]

    def index(key):
        if not isinstance(key, str) or key not in keys:
            raise ValueError("Simulation account absent from transaction")
        return keys.index(key)

    def valid_index(n):
        if type(n) is not int or not 0 <= n < len(keys):
            raise ValueError("Invalid simulation account index")
        return n

    def instruction(ix):
        if not isinstance(ix, dict):
            raise ValueError("Invalid simulation instruction")
        height = ix.get("stackHeight")
        if height is not None and (type(height) is not int or height < 2):
            raise ValueError("Invalid simulation stack height")
        if "programIdIndex" in ix:
            if (
                "parsed" in ix
                or not isinstance(ix.get("data"), str)
                or not isinstance(ix.get("accounts"), list)
            ):
                raise ValueError("Invalid compiled simulation instruction")
            base58.b58decode(ix["data"])
            return dict(
                programIdIndex=valid_index(ix["programIdIndex"]),
                accounts=[valid_index(i) for i in ix["accounts"]],
                data=ix["data"],
                stackHeight=height,
            )
        program = index(ix.get("programId"))
        if "parsed" not in ix:
            if not isinstance(ix.get("data"), str) or not isinstance(
                ix.get("accounts"), list
            ):
                raise ValueError("Invalid raw simulation instruction")
            base58.b58decode(ix["data"])
            return dict(
                programIdIndex=program,
                accounts=[index(k) for k in ix["accounts"]],
                data=ix["data"],
                stackHeight=height,
            )
        parsed = ix["parsed"]
        if not isinstance(parsed, dict) or not isinstance(parsed.get("info"), dict):
            raise ValueError("Unsupported parsed simulation instruction")
        setup = _account_setup(ix["programId"], parsed.get("type"), parsed["info"])
        if setup is not None:
            accounts, data = setup
            return dict(
                programIdIndex=program,
                accounts=[index(k) for k in accounts],
                data=base58.b58encode(data).decode(),
                stackHeight=height,
            )
        if ix["programId"] not in (TOKEN, TOKEN_2022):
            raise ValueError("Unsupported parsed simulation program")
        kind, info = ix["parsed"].get("type"), ix["parsed"].get("info")
        if not isinstance(info, dict) or kind not in (
            "transfer",
            "transferChecked",
            "transferCheckedWithFee",
        ):
            raise ValueError("Unsupported parsed simulation instruction")
        authority = info.get("authority", info.get("multisigAuthority"))
        signers = info.get("signers", [])
        if not isinstance(signers, list):
            raise ValueError("Invalid simulation signers")
        if kind == "transfer":
            accounts = [
                info.get("source"),
                info.get("destination"),
                authority,
            ] + signers
            data = struct.pack("<BQ", 3, _unsigned(info.get("amount"), 64))
        else:
            with_fee = kind == "transferCheckedWithFee"
            if with_fee and ix["programId"] != TOKEN_2022:
                raise ValueError("Transfer fee requires Token-2022")
            amount = info.get("tokenAmount")
            if not isinstance(amount, dict):
                raise ValueError("Invalid simulation token amount")
            n, decimals = _unsigned(amount.get("amount"), 64), _unsigned(
                amount.get("decimals"), 8
            )
            accounts = [
                info.get("source"),
                info.get("mint"),
                info.get("destination"),
                authority,
            ] + signers
            data = (
                struct.pack(
                    "<BBQBQ", 26, 1, n, decimals, _unsigned(info.get("feeAmount"), 64)
                )
                if with_fee
                else struct.pack("<BQB", 12, n, decimals)
            )
        return dict(
            programIdIndex=program,
            accounts=[index(k) for k in accounts],
            data=base58.b58encode(data).decode(),
            stackHeight=height,
        )

    converted, seen = [], set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Invalid simulation instruction group")
        outer = group.get("index")
        if (
            type(outer) is not int
            or not 0 <= outer < len(tx["message"]["instructions"])
            or outer in seen
            or not isinstance(group.get("instructions"), list)
        ):
            raise ValueError("Invalid simulation instruction group")
        seen.add(outer)
        converted.append(
            dict(
                index=outer,
                instructions=[instruction(ix) for ix in group["instructions"]],
            )
        )
    return analyze_rpc_transaction_routes(
        dict(transaction=tx, meta={**value, "innerInstructions": converted}),
        graduated_pools,
    )


def _account_setup(program, kind, info):
    def pubkey(key):
        if not isinstance(key, str):
            raise ValueError("Invalid simulation public key")
        data = base58.b58decode(key)
        if len(data) != 32:
            raise ValueError("Invalid simulation public key")
        return data

    if program == ZERO and kind == "createAccount":
        return [info.get("source"), info.get("newAccount")], struct.pack(
            "<IQQ",
            0,
            _unsigned(info.get("lamports"), 64),
            _unsigned(info.get("space"), 64),
        ) + pubkey(info.get("owner"))
    if program == ZERO and kind in ("transfer", "allocate"):
        return ([info.get("source"), info.get("destination")] if kind == "transfer" else [info.get("account")]), struct.pack("<IQ", 2 if kind == "transfer" else 8, _unsigned(info.get("lamports" if kind == "transfer" else "space"), 64))
    if program == ZERO and kind == "assign":
        return [info.get("account")], struct.pack("<I", 1) + pubkey(info.get("owner"))
    if program not in (TOKEN, TOKEN_2022):
        return None
    if kind in ("mintTo", "mintToChecked", "burn", "burnChecked"):
        minting = kind.startswith("mintTo")
        checked = kind.endswith("Checked")
        authority_key = "mintAuthority" if minting else "authority"
        multisig_key = "multisigMintAuthority" if minting else "multisigAuthority"
        authority = info.get(authority_key)
        if authority is None:
            authority = info.get(multisig_key)
        signers = info.get("signers", [])
        if not isinstance(signers, list):
            raise ValueError("Invalid simulation signers")
        amount = info.get("tokenAmount") if checked else info
        if not isinstance(amount, dict):
            raise ValueError("Invalid simulation token amount")
        data = struct.pack("<BQ", (14 if minting else 15) if checked else (7 if minting else 8),
                           _unsigned(amount.get("amount"), 64))
        if checked:
            data += bytes([_unsigned(amount.get("decimals"), 8)])
        accounts = [info.get("mint"), info.get("account")] if minting else [info.get("account"), info.get("mint")]
        return accounts + [authority] + signers, data
    if kind == "initializeImmutableOwner":
        return [info.get("account")], bytes([22])
    if kind == "initializeAccount3":
        return [info.get("account"), info.get("mint")], bytes([18]) + pubkey(
            info.get("owner")
        )
    if kind == "getAccountDataSize":
        extensions = info.get("extensionTypes")
        if not isinstance(extensions, list):
            raise ValueError("Invalid simulation extension types")
        if any(ext != "immutableOwner" for ext in extensions):
            raise ValueError("Unsupported simulation extension type")
        return [info.get("mint")], bytes([21]) + struct.pack("<H", 7) * len(extensions)
    return None
