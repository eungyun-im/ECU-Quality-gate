"""UDS tester client. It is a bus node that sends requests and collects responses."""

from protocol import uds


class UdsClient:
    def __init__(self, bus, request_id=0x7E0, response_id=0x7E8):
        self.bus = bus
        self.request_id = request_id
        self.response_id = response_id
        self._inbox = []
        bus.attach(self)

    def on_frame(self, frame):
        if frame.can_id == self.response_id:
            self._inbox.append(frame)

    def step(self, now_ms):
        pass

    def request(self, payload, timeout_ms=1000):
        """Send a UDS payload and return the response payload, or None on timeout."""
        return self.request_raw(uds.to_frame(payload), timeout_ms)

    def request_raw(self, frame_data, timeout_ms=1000):
        """Send raw frame bytes, including the length byte. Used by the fuzzer."""
        self._inbox.clear()
        self.bus.send(self.request_id, frame_data, sender=self)
        waited = 0
        while not self._inbox and waited < timeout_ms:
            self.bus.advance(1)
            waited += 1
        if not self._inbox:
            return None
        return uds.from_frame(self._inbox[0].data)

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
