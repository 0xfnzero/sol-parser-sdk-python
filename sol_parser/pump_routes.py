"""Program-bound offline route intents. These are never confirmed fills."""
from dataclasses import dataclass, field
from typing import Optional
from .event_types import DexEvent, DexEventBase
from .grpc_types import EventType

PUMP='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
AMM='pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
RAPID='rapidV5DAKtecYzetwCNoxXWHpezjeg4hGt9BGiVcGW'
DELTA='J7pourVwqP1VtRNBiFNqbdGxwkx7ta2LHAURURRRJqmd'
TOKEN='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
TOKEN22='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
SYSTEM='11111111111111111111111111111111'
ATA='ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
GLOBAL='4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf'
EVENT='Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1'
FEES='pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ'
MULTI=bytes([43,100,73,19,233,246,111,148])
CURVE=bytes([225,154,117,22,215,86,246,103])

@dataclass
class PumpRouteHop:
    base_mint: str
    quote_mint: str
    venue: str
    base_vault: str
    quote_vault: str

@dataclass
class PumpRouteIntentEvent(DexEventBase):
    kind: str = ''
    program: str = ''
    instruction_index: int = 0
    user: str = ''
    input_account: str = ''
    output_account: str = ''
    amount_in: Optional[int] = None
    min_amount_out: Optional[int] = None
    hops: list[PumpRouteHop] = field(default_factory=list)
    instruction_data: list[int] = field(default_factory=list)
    # Intended direction relative to the wrapper hop's base mint, not a fill.
    is_buy: Optional[bool] = None
    # Official underlying instruction name encoded in the wrapper; unknown is None.
    ix_name: Optional[str] = None


def allows_route(filter, program):
    if filter is None:
        return True
    excluded=getattr(filter,'exclude_types',())
    if EventType.PUMP_ROUTE_INTENT in excluded or EventType.PUMP_FUN_TRADE in excluded or (program==AMM and EventType.PUMP_SWAP_TRADE in excluded):
        return False
    included=getattr(filter,'include_only',None)
    if included is not None:
        return any(k in included for k in (EventType.PUMP_ROUTE_INTENT,EventType.PUMP_FUN_TRADE)) or (program==AMM and EventType.PUMP_SWAP_TRADE in included)
    return filter.should_include(EventType.PUMP_ROUTE_INTENT)


def may_parse_route(program, data):
    return ((program==AMM and data[:8]==MULTI) or (program==PUMP and data[:8]==CURVE)
        or (program==DELTA and len(data)==28 and data[:8]==bytes([122,28,94,147,180,45,240,97]))
        or (program==RAPID and len(data)==41 and data[0]==0 and data[9:17]==bytes([1,0,0,27,15,14,8,24]) and data[17:25]==bytes([194,171,28,70,104,77,91,47]) and data[25:33]==bytes(8)))


def multi_hop_args(program,data,a):
    if program!=AMM or len(data)!=24 or data[:8]!=MULTI or len(a)<21 or (len(a)-16)%5 or any(a[i]!=v for i,v in {7:TOKEN,8:TOKEN22,9:SYSTEM,11:AMM,12:PUMP}.items()):
        return None
    amount=int.from_bytes(data[8:16],'little')
    return (amount,int.from_bytes(data[16:24],'little')) if amount else None


def parse_route(program,data,a,metadata,index,filter=None):
    if not may_parse_route(program,data) or not allows_route(filter,program):
        return None
    u=lambda at:int.from_bytes(data[at:at+8],'little')
    if program==AMM:
        args=multi_hop_args(program,data,a)
        if args is None:return None
        kind,fixed,user,source,dest,amount,minimum='MultiHopSwap',16,0,1,2,*args
    elif program==PUMP:
        if len(data)<20:return None
        count=int.from_bytes(data[16:20],'little')
        if not count or len(data)!=20+count or len(a)!=13+count*5 or any(a[i]!=v for i,v in {8:TOKEN,9:TOKEN22,10:SYSTEM,11:EVENT,12:PUMP}.items()):return None
        kind,fixed,user,source,dest,amount,minimum='MultiHopCurveSwap',13,3,5,6,u(8),None
    elif program==RAPID:
        if len(a)!=33 or a[0]!=a[19] or a[2]!=a[8] or a[9] not in (TOKEN,TOKEN22) or any(a[i]!=v for i,v in {3:TOKEN,4:SYSTEM,5:PUMP,6:GLOBAL,10:TOKEN,11:ATA,29:FEES,30:SYSTEM,31:EVENT,32:PUMP}.items()):return None
        kind,fixed,user,source,dest,amount,minimum='RapidBuy',0,0,21,20,u(1),u(33)
    else:
        if len(a)!=30 or a[0]!=a[14] or a[4] not in (TOKEN,TOKEN22) or a[5] not in (TOKEN,TOKEN22) or any(a[i]!=v for i,v in {1:GLOBAL,6:ATA,24:FEES,25:SYSTEM,26:EVENT,27:PUMP}.items()):return None
        kind,fixed,user,source,dest,amount,minimum='BuyPumpDelta',0,0,16,15,None,None
    if amount==0:return None
    hops=[PumpRouteHop(*a[i:i+5]) for i in range(fixed,len(a),5)] if fixed else [PumpRouteHop(*(a[i] for i in ((7,2,16,17,18) if program==RAPID else (2,3,11,12,13))))]
    return DexEvent(EventType.PUMP_ROUTE_INTENT,PumpRouteIntentEvent(
        metadata,kind,program,index,a[user],a[source],a[dest],amount,minimum,hops,list(data),
        is_buy=True if kind in ('RapidBuy', 'BuyPumpDelta') else None,
        ix_name='buy_exact_quote_in_v2' if kind == 'RapidBuy' else None))
