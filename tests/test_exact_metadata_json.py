import json
import pytest
from sol_parser.grpc_types import EventMetadata
from sol_parser.json_util import dex_event_json_dumps

def test_full_integer_range_json():
    metadata=EventMetadata(slot=str(2**64-1),tx_index=2**64-1,block_time_us=-(2**63),grpc_recv_us=2**63-1)
    encoded=json.loads(dex_event_json_dumps(metadata))
    for k in ('slot','tx_index','block_time_us','grpc_recv_us'):assert encoded[k]==str(getattr(metadata,k))

@pytest.mark.parametrize('values',[{'slot':2**64},{'slot':-1},{'slot':True},{'slot':1.0},{'slot':'1e3'},{'block_time_us':2**63}])
def test_invalid_metadata(values):
    with pytest.raises(ValueError):EventMetadata(**values)
