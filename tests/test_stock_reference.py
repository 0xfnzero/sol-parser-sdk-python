from sol_parser import StockPriceTracker
from sol_parser.stock_prices import STOCK_USDC, STOCK_WSOL, DEFAULT_STOCK_SOL_USDC_POOL
from sol_parser.event_types import DexEvent,RaydiumCpmmSwapEvent
from sol_parser.grpc_types import EventType,EventMetadata
from sol_parser.trade_source import TradeParseStatus
import base58
import pytest
MINT=base58.b58encode(bytes([21])*32).decode()
POOL=base58.b58encode(bytes([22])*32).decode()
def swap(reference,index):
    return DexEvent(EventType.RAYDIUM_CPMM_SWAP,RaydiumCpmmSwapEvent(
        metadata=EventMetadata(slot=100,tx_index=index,grpc_recv_us=1000),
        parse_status=TradeParseStatus.EXECUTION_CONFIRMED,
        pool_id=DEFAULT_STOCK_SOL_USDC_POOL if reference else POOL,
        input_mint=STOCK_WSOL if reference else MINT,output_mint=STOCK_USDC,
        input_amount=1_000_000_000 if reference else 1_000_000,
        output_amount=100_000_000 if reference else 10_000_000,
        input_vault_before=1,output_vault_before=1))
def test_reference_order_and_reset():
    catalog={"tokens":[{"mint":MINT,"symbol":"TEST","decimals":6}],"pools":[{"pool":POOL,"mint":MINT,"quote_mint":STOCK_USDC,"dex_type":"raydium_cpmm"}]}
    tracker=StockPriceTracker(catalog,sol_usdc_dex="raydium_cpmm")
    tracker.process(swap(True,1),1000)
    assert tracker.process(swap(False,1),1000).price_sol is None
    tracker.update_liquidity(dict(pool=POOL,slot=100,observed_us=1000,source="coherent-test",tvl_usdc=500))
    for impact in (10000, 65535):
        with pytest.raises(ValueError):
            tracker.update_liquidity(dict(pool=POOL, slot=100, observed_us=1000, source="test", depth_max_price_impact_bps=impact))
    with pytest.raises(ValueError):
        tracker.update_liquidity(dict(pool=POOL, slot=100, observed_us=1000, source=" \t\n"))
    price=tracker.process(swap(False,2),1000)
    assert price.price_sol==0.1 and price.liquidity["tvl_usdc"]==500
    price.liquidity["tvl_usdc"]=1
    assert tracker.process(swap(False,3),1000).liquidity["tvl_usdc"]==500
    tracker.reset()
    assert tracker.process(swap(False,4),1000).price_sol is None
    assert tracker.process(swap(False,5),1000).liquidity is None
