import base64,json,copy
from pathlib import Path
import pytest
from sol_parser.inner_instruction_parser import parse_inner_instruction
from sol_parser.event_types import EventMetadata
from sol_parser.grpc_types import EventType,event_type_filter_include_only
from sol_parser.log_instr_dedup import dedupe_log_instruction_events
F=json.loads((Path(__file__).parent/'fixtures/dbc_swap2.json').read_text())
@pytest.mark.parametrize('case',F['cases'])
def test_current_dbc_cpi(case):
    data=bytes([228,69,165,46,81,203,154,29])+base64.b64decode(case['data'])
    def parse(data):return parse_inner_instruction(data,'dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN',{'signature':'sig','slot':1},event_type_filter_include_only([EventType.METEORA_DBC_SWAP]),False)
    event=parse(data);e=event.data;mode=case['mode']
    assert e.event_version==2 and e.swap_mode==mode
    assert e.amount_in==(100000 if mode==0 else 90000)
    assert e.actual_input_amount==e.amount_in-1000
    assert e.minimum_amount_out==(0 if mode==2 else 79000)
    assert e.maximum_amount_in==(100000 if mode==2 else 0)
    assert e.amount_left==(10000 if mode==1 else 0)
    assert e.output_amount==80000 and e.next_sqrt_price==(1<<100)+7
    assert e.quote_reserve_amount==9007199254740993
    assert e.has_transfer_hook==(case['name']=='EvtSwap2WithTransferHook')
    for size in range(len(data)):assert parse(data[:size]) is None
    invalid=bytearray(data);invalid[16+82]=3;assert parse(bytes(invalid)) is None
    old=copy.deepcopy(event);old.data.event_version=0
    assert len(dedupe_log_instruction_events([], [old,event]))==1
    assert len(dedupe_log_instruction_events([], [old,old,event,event]))==2
    assert len(dedupe_log_instruction_events([], [old,old,event]))==3
