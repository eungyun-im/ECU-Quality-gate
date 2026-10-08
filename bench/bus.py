"""In-process CAN bus with a simulated clock and trace recording."""


class VirtualBus:
    def __init__(self):
        self.now_ms = 0
        self.trace = []

    def send(self, can_id, data):
        # TODO: timestamp, record, deliver to subscribers (through fault injection)
        raise NotImplementedError

    def advance(self, ms):
        # TODO: step every attached ECU
        raise NotImplementedError

    def save_trace(self, path):
        # TODO: one frame per line: timestamp_ms, id, data
        raise NotImplementedError
