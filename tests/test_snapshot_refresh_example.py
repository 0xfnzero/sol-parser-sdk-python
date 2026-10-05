import importlib.util
from pathlib import Path
from types import SimpleNamespace
import base64
import pytest

spec = importlib.util.spec_from_file_location(
    "snapshot_refresh",
    Path(__file__).parents[1] / "examples/stonkfun_snapshot_refresh.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_order_conflict_replay_and_closed_snapshot():
    old = {
        "pubkey": "key",
        "owner": "owner",
        "data": base64.b64encode(b"one").decode(),
        "slot": "100",
        "write_version": "1",
    }

    def event(data=b"one", slot=100, version=1, lamports=1):
        return SimpleNamespace(
            metadata=SimpleNamespace(slot=slot),
            write_version=version,
            account=SimpleNamespace(
                pubkey="key", owner="owner", data=data, lamports=lamports
            ),
        )

    assert module.apply_raw_snapshot(old, event()) is old
    assert module.apply_raw_snapshot(old, event(b"stale", 99, 999)) is old
    with pytest.raises(ValueError, match="Conflicting"):
        module.apply_raw_snapshot(old, event(b"bad"))
    closed = module.apply_raw_snapshot(old, event(b"stale bytes", 101, 0, 0))
    assert closed["data"] == "" and closed["slot"] == "101"


def test_route_grpc_refresh_waits_for_all_pools_and_updates_array_index_zero(
    tmp_path, monkeypatch
):
    import asyncio, json

    clock = module.CLOCK
    old = lambda key: {
        "pubkey": key,
        "owner": "owner",
        "data": base64.b64encode(b"old").decode(),
        "slot": "100",
        "write_version": "0",
    }
    value = {
        "accounts": [old("pool1"), old("pool2"), old(clock)],
        "legs": [{"pool": "pool1"}, {"pool": "pool2"}],
    }
    path = tmp_path / "route.json"
    path.write_text(json.dumps(value))
    data = bytearray(40)
    data[:8] = (101).to_bytes(8, "little")
    data[16:24] = (4).to_bytes(8, "little")
    data[32:40] = (123).to_bytes(8, "little")

    def event(key, content):
        return SimpleNamespace(
            type=module.EventType.ACCOUNT_RAW_SNAPSHOT,
            data=SimpleNamespace(
                metadata=SimpleNamespace(slot=101),
                write_version=1,
                account=SimpleNamespace(
                    pubkey=key, owner="owner", data=bytes(content), lamports=1
                ),
            ),
        )

    class Client:
        closed = False

        async def subscribe_dex_events(self, transactions, accounts, filter):
            assert set(accounts[0].account) == {clock, "pool1", "pool2"}
            queue = asyncio.Queue()
            for e in [
                event("pool1", b"new1"),
                event(clock, data),
                event("pool2", b"new2"),
            ]:
                queue.put_nowait(e)
            return queue

        async def get_latest_blockhash(self, commitment):
            return SimpleNamespace(blockhash="hash", slot=101)

        async def disconnect(self):
            self.closed = True

    client = Client()
    monkeypatch.setenv("GRPC_URL", "http://example.invalid")
    monkeypatch.setattr(module.YellowstoneGrpc, "new", lambda *args: client)
    asyncio.run(module.refresh(path, 1, True))
    saved = json.loads(path.read_text())
    assert [a["slot"] for a in saved["accounts"]] == ["101", "101", "101"]
    assert base64.b64decode(saved["accounts"][0]["data"]) == b"new1"
    assert base64.b64decode(saved["accounts"][1]["data"]) == b"new2"
    assert (
        saved["epoch"] == "4"
        and saved["unix_timestamp"] == "123"
        and saved["read_slot"] == "101"
    )
    assert client.closed


@pytest.mark.parametrize('blocked_phase', ['subscription', 'updates', 'blockhash'])
def test_deadline_cancels_all_refresh_phases_without_saving_partial_state(
    blocked_phase, tmp_path, monkeypatch
):
    import asyncio
    import json

    old = lambda key: dict(pubkey=key, owner='owner', data='', slot='100', write_version='0')
    original = json.dumps(dict(accounts=[old('pool'), old(module.CLOCK)], legs=[dict(pool='pool')]))
    path = tmp_path/'snapshot.json'
    path.write_text(original)
    clock = bytearray(40)
    clock[:8] = (101).to_bytes(8, 'little')

    def event(key, data):
        return SimpleNamespace(type=module.EventType.ACCOUNT_RAW_SNAPSHOT, data=SimpleNamespace(
            metadata=SimpleNamespace(slot=101), write_version=1,
            account=SimpleNamespace(pubkey=key, owner='owner', data=data, lamports=1)))

    class Client:
        closed = False
        cancelled = False

        async def block(self):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

        async def subscribe_dex_events(self, *args):
            if blocked_phase == 'subscription':
                await self.block()
            queue = asyncio.Queue()
            if blocked_phase == 'blockhash':
                queue.put_nowait(event('pool', b'new'))
                queue.put_nowait(event(module.CLOCK, bytes(clock)))
            return queue

        async def get_latest_blockhash(self, *args):
            await self.block()

        async def disconnect(self):
            self.closed = True

    client = Client()
    monkeypatch.setenv('GRPC_URL', 'http://example.invalid')
    monkeypatch.setattr(module.YellowstoneGrpc, 'new', lambda *args: client)
    with pytest.raises(TimeoutError, match='deadline exceeded'):
        asyncio.run(module.refresh(path, .01, True))
    assert client.closed and path.read_text() == original
    if blocked_phase != 'updates':
        assert client.cancelled
