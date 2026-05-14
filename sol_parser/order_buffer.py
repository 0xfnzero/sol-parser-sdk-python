"""OrderMode buffers for low-latency DEX subscriptions."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from .event_types import DexEvent
from .grpc_types import ClientConfig, OrderMode


@dataclass
class _Batch:
    slot: int
    tx_index: int
    seq: int
    events: List[DexEvent]


def _event_slot_tx(events: List[DexEvent], fallback_slot: int, fallback_tx_index: int) -> Tuple[int, int]:
    if not events:
        return fallback_slot, fallback_tx_index
    meta = getattr(events[0].data, "metadata", None)
    slot = int(getattr(meta, "slot", fallback_slot) or fallback_slot)
    tx_index = int(getattr(meta, "tx_index", fallback_tx_index) or fallback_tx_index)
    return slot, tx_index


class OrderDispatcher:
    def __init__(self, config: ClientConfig):
        self.mode = config.order_mode
        self.timeout_s = max(0.001, float(config.order_timeout_ms or 100) / 1000.0)
        self.micro_batch_s = max(0.000001, float(config.micro_batch_us or 100) / 1_000_000.0)
        self.slots: Dict[int, List[_Batch]] = {}
        self.watermarks: Dict[int, int] = {}
        self.micro_batch: List[_Batch] = []
        self.micro_start = 0.0
        self.last_flush = time.monotonic()
        self.current_slot = 0
        self.seq = 0

    @property
    def needs_timer(self) -> bool:
        return self.mode != OrderMode.UNORDERED

    @property
    def interval_s(self) -> float:
        if self.mode == OrderMode.MICRO_BATCH:
            return self.micro_batch_s
        return max(0.001, self.timeout_s / 2.0)

    def push_transaction_events(
        self,
        events: List[DexEvent],
        fallback_slot: int,
        fallback_tx_index: int,
        emit: Callable[[DexEvent], None],
    ) -> None:
        if not events:
            return
        slot, tx_index = _event_slot_tx(events, fallback_slot, fallback_tx_index)
        batch = _Batch(slot=slot, tx_index=tx_index, seq=self.seq, events=events)
        self.seq += 1

        if self.mode == OrderMode.UNORDERED:
            self._emit_batch(batch, emit)
        elif self.mode == OrderMode.ORDERED:
            self._push_ordered(batch, emit)
        elif self.mode == OrderMode.STREAMING_ORDERED:
            self._push_streaming(batch, emit)
        elif self.mode == OrderMode.MICRO_BATCH:
            self._push_micro_batch(batch, emit)
        else:
            self._emit_batch(batch, emit)

    def flush_due(self, emit: Callable[[DexEvent], None]) -> None:
        now = time.monotonic()
        if self.mode in (OrderMode.ORDERED, OrderMode.STREAMING_ORDERED):
            if self.slots and now - self.last_flush > self.timeout_s:
                self._flush_all_slots(emit)
        if self.mode == OrderMode.MICRO_BATCH:
            if self.micro_batch and now - self.micro_start >= self.micro_batch_s:
                self._flush_micro_batch(emit)

    def flush_all(self, emit: Callable[[DexEvent], None]) -> None:
        self._flush_all_slots(emit)
        self._flush_micro_batch(emit)

    def _push_ordered(self, batch: _Batch, emit: Callable[[DexEvent], None]) -> None:
        if batch.slot > self.current_slot and self.current_slot > 0:
            self._flush_before(batch.slot, emit)
        if batch.slot > self.current_slot:
            self.current_slot = batch.slot
        self.slots.setdefault(batch.slot, []).append(batch)

    def _push_streaming(self, batch: _Batch, emit: Callable[[DexEvent], None]) -> None:
        if batch.slot > self.current_slot and self.current_slot > 0:
            self._flush_before(batch.slot, emit)
            for slot in list(self.watermarks):
                if slot < batch.slot:
                    self.watermarks.pop(slot, None)
        if batch.slot > self.current_slot:
            self.current_slot = batch.slot

        expected = self.watermarks.get(batch.slot, 0)
        if batch.tx_index == expected:
            self._emit_batch(batch, emit)
            watermark = expected + 1
            buffered = self.slots.get(batch.slot, [])
            buffered.sort(key=_batch_key)
            while True:
                pos = next((i for i, item in enumerate(buffered) if item.tx_index == watermark), -1)
                if pos < 0:
                    break
                self._emit_batch(buffered.pop(pos), emit)
                watermark += 1
            if buffered:
                self.slots[batch.slot] = buffered
            else:
                self.slots.pop(batch.slot, None)
            self.watermarks[batch.slot] = watermark
            self.last_flush = time.monotonic()
        elif batch.tx_index > expected:
            self.slots.setdefault(batch.slot, []).append(batch)

    def _push_micro_batch(self, batch: _Batch, emit: Callable[[DexEvent], None]) -> None:
        now = time.monotonic()
        if not self.micro_batch:
            self.micro_start = now
        self.micro_batch.append(batch)
        if now - self.micro_start >= self.micro_batch_s:
            self._flush_micro_batch(emit)

    def _flush_before(self, slot: int, emit: Callable[[DexEvent], None]) -> None:
        for s in sorted(k for k in self.slots if k < slot):
            batches = self.slots.pop(s)
            batches.sort(key=_batch_key)
            for batch in batches:
                self._emit_batch(batch, emit)
            self.watermarks.pop(s, None)
        self.last_flush = time.monotonic()

    def _flush_all_slots(self, emit: Callable[[DexEvent], None]) -> None:
        for s in sorted(self.slots):
            batches = self.slots[s]
            batches.sort(key=_batch_key)
            for batch in batches:
                self._emit_batch(batch, emit)
        self.slots.clear()
        self.watermarks.clear()
        self.last_flush = time.monotonic()

    def _flush_micro_batch(self, emit: Callable[[DexEvent], None]) -> None:
        if not self.micro_batch:
            return
        self.micro_batch.sort(key=_batch_key)
        for batch in self.micro_batch:
            self._emit_batch(batch, emit)
        self.micro_batch = []
        self.micro_start = 0.0
        self.last_flush = time.monotonic()

    @staticmethod
    def _emit_batch(batch: _Batch, emit: Callable[[DexEvent], None]) -> None:
        for event in batch.events:
            emit(event)


def _batch_key(batch: _Batch) -> Tuple[int, int, int]:
    return (batch.slot, batch.tx_index, batch.seq)
