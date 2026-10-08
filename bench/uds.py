"""Tester side of the diagnostic link.

UdsClient sends raw UDS payloads over ISO-TP. It is used where a test needs
full control of the bytes: malformed requests, fuzzing, exact response checks.
For well-formed requests there is also a standard udsoncan client, see
bench/tester.py.
"""

from protocol.isotp_link import IsoTpEndpoint
from protocol import uds


class UdsClient:
    def __init__(self, bus, request_id=0x7E0, response_id=0x7E8):
        self.bus = bus
        self.request_id = request_id
        self.response_id = response_id
        self.link = IsoTpEndpoint(bus, txid=request_id, rxid=response_id, owner=self)
        bus.attach(self)
        bus.add_transport(self.link)

    def on_frame(self, frame):
        self.link.on_frame(frame)

    def step(self, now_ms):
        pass

    def send(self, payload):
        """Send a UDS payload. Segmentation into CAN frames is done by ISO-TP."""
        self.link.send(payload)
        self.bus.settle()

    def wait_response(self, timeout_ms=1000):
        """Advance simulated time until a complete response arrives. None on timeout."""
        waited = 0
        while True:
            self.bus.settle()
            response = self.link.receive()
            if response is not None:
                return response
            if waited >= timeout_ms:
                return None
            self.bus.advance(1)
            waited += 1

    def flush(self):
        while self.link.receive() is not None:
            pass

    def request(self, payload, timeout_ms=1000):
        """Send a UDS payload and return the response payload, or None on timeout."""
        self.flush()
        self.send(payload)
        return self.wait_response(timeout_ms)

    def send_raw_frame(self, data):
        """Put one raw CAN frame on the request ID, bypassing ISO-TP. For transport fuzzing."""
        self.bus.send(self.request_id, bytes(data), sender=self)
        self.bus.settle()

    # Convenience wrappers used across the test suites.

    def enter_session(self, session):
        return self.request([uds.DIAGNOSTIC_SESSION_CONTROL, session])

    def tester_present(self):
        return self.request([uds.TESTER_PRESENT, 0x00])

    def read_did(self, did):
        return self.request([uds.READ_DATA_BY_IDENTIFIER, did >> 8, did & 0xFF])

    def write_did(self, did, data):
        return self.request([uds.WRITE_DATA_BY_IDENTIFIER, did >> 8, did & 0xFF, *data])

    def request_seed(self):
        """Return the seed as an int, or the raw response when it is negative."""
        response = self.request([uds.SECURITY_ACCESS, uds.REQUEST_SEED])
        if is_positive(response, uds.SECURITY_ACCESS):
            return (response[2] << 8) | response[3]
        return response

    def send_key(self, key):
        return self.request([uds.SECURITY_ACCESS, uds.SEND_KEY, key >> 8, key & 0xFF])

    def unlock(self):
        """Extended session plus a correct seed and key exchange."""
        self.enter_session(uds.EXTENDED_SESSION)
        return self.send_key(uds.compute_key(self.request_seed()))

    def read_dtcs(self, status_mask=0xFF):
        """Return the stored DTC codes as ints."""
        response = self.request(
            [uds.READ_DTC_INFORMATION, uds.REPORT_DTC_BY_STATUS_MASK, status_mask]
        )
        if not is_positive(response, uds.READ_DTC_INFORMATION):
            return response
        records = response[3:]
        return [
            (records[i] << 16) | (records[i + 1] << 8) | records[i + 2]
            for i in range(0, len(records) - 3, 4)
        ]

    def clear_dtcs(self):
        return self.request([uds.CLEAR_DIAGNOSTIC_INFORMATION, *uds.ALL_DTC_GROUP])

    def reset(self):
        return self.request([uds.ECU_RESET, uds.HARD_RESET])


def is_positive(response, service):
    return bool(response) and response[0] == service + uds.POSITIVE_OFFSET


def nrc(response):
    """Negative response code, or None when the response is not negative."""
    if response and len(response) >= 3 and response[0] == uds.NEGATIVE_RESPONSE:
        return response[2]
    return None
