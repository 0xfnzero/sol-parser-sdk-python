import struct
from sol_parser.dex_parsers import parse_cpmm_swap_event_from_data,parse_dlmm_from_program_data

def test_cpmm_current_and_legacy_layouts():
    b=bytearray(162);b[81:113]=bytes([1])*32;b[113:145]=bytes([2])*32
    struct.pack_into('<QQ',b,145,9007199254740993,77);b[161]=1
    e=parse_cpmm_swap_event_from_data(b,{}).data
    assert e.trade_fee==9007199254740993 and e.creator_fee==77 and e.creator_fee_on_input
    assert e.input_mint!=e.output_mint
    assert parse_cpmm_swap_event_from_data(b[:81],{}) is not None
    for n in range(162):
        if n!=81:assert parse_cpmm_swap_event_from_data(b[:n],{}) is None
    b[161]=2;assert parse_cpmm_swap_event_from_data(b,{}) is None

def test_dlmm_current_components_and_bounds():
    b=bytearray(bytes([46,116,82,215,148,27,84,77])+bytes(147))
    struct.pack_into('<Q',b,8+97,9007199254740993)
    struct.pack_into('<QQ',b,8+113,17531,1947);b[8+145]=1
    e=parse_dlmm_from_program_data(b,{}).data
    assert e.fee==19478 and e.mm_fee==17531 and e.amount_left==9007199254740993
    assert e.fees_on_input and not e.fees_on_token_x
    for n in range(len(b)):assert parse_dlmm_from_program_data(b[:n],{}) is None
    struct.pack_into('<Q',b,8+113,(1<<64)-1);assert parse_dlmm_from_program_data(b,{}) is None
    struct.pack_into('<Q',b,8+113,3);b[8+146]=2;assert parse_dlmm_from_program_data(b,{}) is None
