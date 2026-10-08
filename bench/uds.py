"""UDS tester client."""

NEGATIVE_RESPONSE = 0x7F

NRC = {
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceededNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x7F: "serviceNotSupportedInActiveSession",
}


class UdsClient:
    def __init__(self, bus, request_id=0x7E0, response_id=0x7E8):
        self.bus = bus
        self.request_id = request_id
        self.response_id = response_id

    def request(self, payload, timeout_ms=1000):
        # TODO: send, wait for the response frame, return its payload
        raise NotImplementedError
