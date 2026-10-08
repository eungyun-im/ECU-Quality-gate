"""Network definition loaded from network/messages.yaml."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MESSAGES_YAML = ROOT / "network" / "messages.yaml"


@dataclass(frozen=True)
class Signal:
    name: str
    size: int
    scale: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class Message:
    name: str
    can_id: int
    sender: str
    receivers: tuple
    cycle_ms: int
    signals: tuple

    @property
    def length(self):
        return sum(s.size for s in self.signals)

    def encode(self, values):
        data = bytearray()
        for signal in self.signals:
            limit = (1 << (8 * signal.size)) - 1
            raw = round(values[signal.name] / signal.scale)
            data += min(max(raw, 0), limit).to_bytes(signal.size, "big")
        return bytes(data)

    def decode(self, data):
        values, offset = {}, 0
        for signal in self.signals:
            raw = int.from_bytes(data[offset : offset + signal.size], "big")
            values[signal.name] = raw * signal.scale
            offset += signal.size
        return values


@dataclass(frozen=True)
class Network:
    messages: tuple
    diagnostics: dict

    def by_id(self, can_id):
        return next((m for m in self.messages if m.can_id == can_id), None)

    def by_name(self, name):
        return next(m for m in self.messages if m.name == name)


def load_network(path=MESSAGES_YAML):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    messages = tuple(
        Message(
            name=m["name"],
            can_id=m["id"],
            sender=m["sender"],
            receivers=tuple(m["receivers"]),
            cycle_ms=m["cycle_ms"],
            signals=tuple(
                Signal(s["name"], s["bytes"], s["scale"], s["min"], s["max"])
                for s in m["signals"]
            ),
        )
        for m in raw["messages"]
    )
    return Network(messages=messages, diagnostics=raw["diagnostics"])
