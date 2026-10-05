from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sol_parser.grpc_client import YellowstoneGrpc
from sol_parser.grpc_types import CommitmentLevel


@pytest.mark.asyncio
async def test_generated_stub_method_names():
    client = YellowstoneGrpc.new("https://example.invalid:443")
    client._connected = True
    client._client = SimpleNamespace(
        GetLatestBlockhash=AsyncMock(
            return_value=SimpleNamespace(
                slot=42, blockhash="cached", last_valid_block_height=99
            )
        )
    )
    result = await client.get_latest_blockhash(CommitmentLevel.CONFIRMED)
    assert result.slot == 42 and result.blockhash == "cached"
    client._client.GetLatestBlockhash.assert_awaited_once()
    assert client._client.GetLatestBlockhash.call_args.args[0].commitment == 1
