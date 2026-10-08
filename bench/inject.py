"""Bus-level fault injection: drop, delay or corrupt frames of one CAN ID."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class _Rule:
    kind: str
    can_id: int
    start_ms: int
    end_ms: Optional[int]
    extra_ms: int = 0
    byte_index: int = 0
    value: int = 0

    def active(self, can_id, now_ms):
        if can_id != self.can_id or now_ms < self.start_ms:
            return False
        return self.end_ms is None or now_ms < self.end_ms


class FaultInjector:
    def __init__(self):
        self.rules = []

    def _add(self, kind, can_id, start_ms, duration_ms, **extra):
        end_ms = None if duration_ms is None else start_ms + duration_ms
        self.rules.append(_Rule(kind, can_id, start_ms, end_ms, **extra))

    def drop(self, can_id, start_ms, duration_ms):
        """Frames sent in [start_ms, start_ms + duration_ms) never reach the bus."""
        self._add("drop", can_id, start_ms, duration_ms)

    def delay(self, can_id, extra_ms, start_ms=0, duration_ms=None):
        self._add("delay", can_id, start_ms, duration_ms, extra_ms=extra_ms)

    def corrupt(self, can_id, byte_index, value, start_ms=0, duration_ms=None):
        self._add("corrupt", can_id, start_ms, duration_ms, byte_index=byte_index, value=value)

    def clear(self):
        self.rules.clear()

    def process(self, can_id, data, now_ms):
        """Return the (deliver_at_ms, data) pairs that actually reach the bus."""
        deliver_at = now_ms
        for rule in self.rules:
            if not rule.active(can_id, now_ms):
                continue
            if rule.kind == "drop":
                return []
            if rule.kind == "delay":
                deliver_at += rule.extra_ms
            elif rule.kind == "corrupt" and rule.byte_index < len(data):
                data = data[: rule.byte_index] + bytes([rule.value]) + data[rule.byte_index + 1 :]
        return [(deliver_at, data)]
