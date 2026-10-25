"""Validate versioned IDL method names against actual native instruction discriminators."""
import hashlib
import base58

def expected_pump_method(raw,legacy):
    message=raw["transaction"]["message"]
    loaded=raw["meta"].get("loadedAddresses") or {}
    keys=message["accountKeys"]+loaded.get("writable",[])+loaded.get("readonly",[])
    instructions=message["instructions"]+[i for g in raw["meta"].get("innerInstructions",[]) for i in g["instructions"]]
    for method in (legacy+"_v3", legacy+"_v2"):
        discriminator=hashlib.sha256(("global:"+method).encode()).digest()[:8]
        if any(keys[i["programIdIndex"]]=="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" and base58.b58decode(i["data"])[:8]==discriminator for i in instructions):
            return method
    return legacy
