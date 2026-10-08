"""Virtual ECU: periodic transmit, receive monitoring, UDS server."""

DEFAULT_SESSION = 0x01
EXTENDED_SESSION = 0x03


class VirtualEcu:
    def __init__(self, name, bus, build):
        self.name = name
        self.bus = bus
        self.build = build
        self.session = DEFAULT_SESSION
        self.unlocked = False
        self.dtcs = []

    def step(self, now_ms):
        # TODO: send periodic messages, check receive timeouts, run S3 timer
        raise NotImplementedError

    def handle_request(self, payload):
        # TODO: dispatch on service ID, return positive or negative response
        raise NotImplementedError
