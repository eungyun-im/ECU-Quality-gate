"""Virtual ECU: periodic transmit and receive-timeout monitoring."""


class VirtualEcu:
    def __init__(self, name, bus, network, build):
        self.name = name
        self.bus = bus
        self.network = network
        self.build = build
        self.tx = [m for m in network.messages if m.sender == name]
        self.rx = [m for m in network.messages if name in m.receivers]
        self.timeout_cycles = network.diagnostics["timeout_cycles"]
        self._next_tx = {m.can_id: self.cycle_ms(m) for m in self.tx}
        self._last_rx = {m.can_id: 0 for m in self.rx}
        self.signals = {}
        bus.attach(self)

    def cycle_ms(self, message):
        return message.cycle_ms

    def tx_values(self, message):
        """Signal values for a transmit message. Subclasses provide them."""
        raise NotImplementedError

    def timed_out(self, message, now_ms):
        return now_ms - self._last_rx[message.can_id] > self.timeout_cycles * message.cycle_ms

    def on_timeout(self, message):
        pass

    def on_frame(self, frame):
        message = self.network.by_id(frame.can_id)
        if message in self.rx:
            self._last_rx[frame.can_id] = frame.ts_ms
            self.signals.update(message.decode(frame.data))

    def step(self, now_ms):
        for message in self.rx:
            if self.timed_out(message, now_ms):
                self.on_timeout(message)
        for message in self.tx:
            if now_ms >= self._next_tx[message.can_id]:
                self.bus.send(message.can_id, message.encode(self.tx_values(message)), sender=self)
                self._next_tx[message.can_id] += self.cycle_ms(message)
