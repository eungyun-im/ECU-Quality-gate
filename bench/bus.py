"""In-process CAN bus with a simulated clock and trace recording.

Time only moves when a test calls advance(), one millisecond per tick. A 10 s
security lockout therefore runs in milliseconds of real time and gives the
same result on every machine.
"""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Frame:
    ts_ms: int
    can_id: int
    data: bytes


class VirtualBus:
    def __init__(self):
        self.now_ms = 0
        self.trace = []
        self.nodes = []
        self.transports = []
        self.injector = None
        self._delayed = []

    def attach(self, node):
        """A node needs on_frame(frame) and step(now_ms). Nodes step in attach order."""
        self.nodes.append(node)

    def add_transport(self, transport):
        """A transport needs pump(), returning True while it still has work to do."""
        self.transports.append(transport)

    def send(self, can_id, data, sender=None):
        data = bytes(data)
        if self.injector is None:
            deliveries = [(self.now_ms, data)]
        else:
            deliveries = self.injector.process(can_id, data, self.now_ms)
        for deliver_at, payload in deliveries:
            if deliver_at <= self.now_ms:
                self._deliver(can_id, payload, sender)
            else:
                self._delayed.append((deliver_at, can_id, payload, sender))

    def _deliver(self, can_id, data, sender):
        frame = Frame(self.now_ms, can_id, data)
        self.trace.append(frame)
        for node in self.nodes:
            if node is not sender:
                node.on_frame(frame)

    def settle(self, limit=10000):
        """Run the transport layers until no frame is waiting to be handled.

        A segmented diagnostic message is several frames in both directions.
        They are all exchanged within the current millisecond.
        """
        for _ in range(limit):
            if not any([transport.pump() for transport in self.transports]):
                return
        raise RuntimeError("transport layers did not settle")

    def advance(self, ms):
        for _ in range(ms):
            self.now_ms += 1
            due = [d for d in self._delayed if d[0] <= self.now_ms]
            self._delayed = [d for d in self._delayed if d[0] > self.now_ms]
            for _, can_id, payload, sender in due:
                self._deliver(can_id, payload, sender)
            for node in list(self.nodes):
                node.step(self.now_ms)
            self.settle()

    def save_trace(self, path):
        save_trace(self.trace, path)


def save_trace(trace, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ts_ms", "can_id", "data"])
        for frame in trace:
            writer.writerow([frame.ts_ms, f"{frame.can_id:03X}", frame.data.hex().upper()])


def load_trace(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [
            Frame(int(row["ts_ms"]), int(row["can_id"], 16), bytes.fromhex(row["data"]))
            for row in csv.DictReader(f)
        ]
