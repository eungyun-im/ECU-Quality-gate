"""UDS server of the brake ECU: sessions, data identifiers, DTCs, security access.

Simplifications against ISO 14229, all deliberate:
- Every message fits one frame (the diagnostic channel is treated as CAN FD),
  so there is no ISO-TP segmentation.
- Session control answers without the timing parameter record.
- suppressPosRspMsgIndicationBit is not supported.
"""

import random

from protocol import uds

FIXED_SEED = 0x1234


class UdsServer:
    def __init__(self, ecu, config, build):
        self.ecu = ecu
        self.build = build
        self.request_id = config["request_id"]
        self.response_id = config["response_id"]
        self.s3_ms = config["s3_server_ms"]
        self.max_attempts = config["security"]["max_attempts"]
        self.lockout_ms = config["security"]["lockout_ms"]
        self.dids = {d["id"]: d for d in config["dids"]}
        self._rng = random.Random(20261008)
        self._handlers = {
            uds.DIAGNOSTIC_SESSION_CONTROL: self._session_control,
            uds.ECU_RESET: self._ecu_reset,
            uds.CLEAR_DIAGNOSTIC_INFORMATION: self._clear_dtcs,
            uds.READ_DTC_INFORMATION: self._read_dtcs,
            uds.READ_DATA_BY_IDENTIFIER: self._read_did,
            uds.SECURITY_ACCESS: self._security_access,
            uds.WRITE_DATA_BY_IDENTIFIER: self._write_did,
            uds.TESTER_PRESENT: self._tester_present,
        }
        # Volatile state, lost on reset
        self.session = uds.DEFAULT_SESSION
        self.unlocked = False
        self.pending_seed = None
        self.last_request_ms = 0
        self.hung = False
        # Non-volatile state, kept across reset
        self.failed_attempts = 0
        self.lockout_until_ms = 0

    # Frame level

    def handle(self, data, now_ms):
        """Return the response frame for a request frame, or None for no response."""
        if self.hung:
            return None
        request = uds.from_frame(data)
        if request is None:
            if self.build.has("SEED-07") and data and data[0] > len(data) - 1:
                self.hung = True
                return None
            service = data[1] if len(data) > 1 else 0x00
            return uds.to_frame(self._negative(service, uds.NRC_INCORRECT_LENGTH))
        self.last_request_ms = now_ms
        handler = self._handlers.get(request[0])
        if handler is None:
            response = self._negative(request[0], uds.NRC_SERVICE_NOT_SUPPORTED)
        else:
            response = handler(request, now_ms)
        return uds.to_frame(response)

    def tick(self, now_ms):
        """S3 server timer: leave a non-default session after a quiet period."""
        if self.session != uds.DEFAULT_SESSION and now_ms - self.last_request_ms >= self.s3_ms:
            self._enter_session(uds.DEFAULT_SESSION)

    @staticmethod
    def _negative(service, code):
        return [uds.NEGATIVE_RESPONSE, service, code]

    def _enter_session(self, session):
        self.session = session
        self.unlocked = False
        self.pending_seed = None

    # Services

    def _session_control(self, request, now_ms):
        service = uds.DIAGNOSTIC_SESSION_CONTROL
        if len(request) != 2:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if request[1] not in (uds.DEFAULT_SESSION, uds.EXTENDED_SESSION):
            return self._negative(service, uds.NRC_SUB_FUNCTION_NOT_SUPPORTED)
        self._enter_session(request[1])
        return [service + uds.POSITIVE_OFFSET, request[1]]

    def _tester_present(self, request, now_ms):
        service = uds.TESTER_PRESENT
        if len(request) != 2:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if request[1] != 0x00:
            return self._negative(service, uds.NRC_SUB_FUNCTION_NOT_SUPPORTED)
        return [service + uds.POSITIVE_OFFSET, 0x00]

    def _ecu_reset(self, request, now_ms):
        service = uds.ECU_RESET
        if len(request) != 2:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if request[1] != uds.HARD_RESET:
            return self._negative(service, uds.NRC_SUB_FUNCTION_NOT_SUPPORTED)
        self._enter_session(uds.DEFAULT_SESSION)
        if self.build.has("SEED-06"):
            self.failed_attempts = 0
            self.lockout_until_ms = 0
        return [service + uds.POSITIVE_OFFSET, request[1]]

    def _read_did(self, request, now_ms):
        service = uds.READ_DATA_BY_IDENTIFIER
        if len(request) != 3:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        did = (request[1] << 8) | request[2]
        data = self.ecu.read_did(did)
        if data is None:
            return self._negative(service, uds.NRC_REQUEST_OUT_OF_RANGE)
        return [service + uds.POSITIVE_OFFSET, request[1], request[2], *data]

    def _write_did(self, request, now_ms):
        service = uds.WRITE_DATA_BY_IDENTIFIER
        seeded = self.build.has("SEED-02")
        if self.session == uds.DEFAULT_SESSION and not seeded:
            return self._negative(service, uds.NRC_NOT_SUPPORTED_IN_SESSION)
        if len(request) < 4:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        did = (request[1] << 8) | request[2]
        entry = self.dids.get(did)
        if entry is None or entry["access"] != "read_write":
            return self._negative(service, uds.NRC_REQUEST_OUT_OF_RANGE)
        if len(request) - 3 != entry["bytes"]:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        must_be_unlocked = self.session == uds.EXTENDED_SESSION if seeded else True
        if must_be_unlocked and not self.unlocked:
            return self._negative(service, uds.NRC_SECURITY_ACCESS_DENIED)
        self.ecu.write_did(did, request[3:])
        return [service + uds.POSITIVE_OFFSET, request[1], request[2]]

    def _read_dtcs(self, request, now_ms):
        service = uds.READ_DTC_INFORMATION
        if len(request) != 3:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if request[1] != uds.REPORT_DTC_BY_STATUS_MASK:
            return self._negative(service, uds.NRC_SUB_FUNCTION_NOT_SUPPORTED)
        response = [service + uds.POSITIVE_OFFSET, request[1], uds.DTC_STATUS_AVAILABILITY_MASK]
        if request[2] & uds.DTC_STATUS_CONFIRMED:
            for code in sorted(self.ecu.dtcs):
                response += [*code.to_bytes(3, "big"), uds.DTC_STATUS_CONFIRMED]
        return response

    def _clear_dtcs(self, request, now_ms):
        service = uds.CLEAR_DIAGNOSTIC_INFORMATION
        if len(request) != 4:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if tuple(request[1:]) != uds.ALL_DTC_GROUP:
            return self._negative(service, uds.NRC_REQUEST_OUT_OF_RANGE)
        self.ecu.dtcs.clear()
        return [service + uds.POSITIVE_OFFSET]

    def _security_access(self, request, now_ms):
        service = uds.SECURITY_ACCESS
        if self.session != uds.EXTENDED_SESSION:
            return self._negative(service, uds.NRC_NOT_SUPPORTED_IN_SESSION)
        if len(request) < 2:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if request[1] not in (uds.REQUEST_SEED, uds.SEND_KEY):
            return self._negative(service, uds.NRC_SUB_FUNCTION_NOT_SUPPORTED)
        if now_ms < self.lockout_until_ms:
            return self._negative(service, uds.NRC_TIME_DELAY_NOT_EXPIRED)
        if self.lockout_until_ms:
            self.lockout_until_ms = 0
            self.failed_attempts = 0
        if request[1] == uds.REQUEST_SEED:
            return self._request_seed(request)
        return self._send_key(request, now_ms)

    def _request_seed(self, request):
        service = uds.SECURITY_ACCESS
        if len(request) != 2:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if self.unlocked:
            seed = 0x0000
        elif self.build.has("SEED-05"):
            seed = FIXED_SEED
        else:
            seed = self._rng.randrange(1, 0x10000)
        self.pending_seed = None if self.unlocked else seed
        return [service + uds.POSITIVE_OFFSET, uds.REQUEST_SEED, seed >> 8, seed & 0xFF]

    def _send_key(self, request, now_ms):
        service = uds.SECURITY_ACCESS
        if len(request) != 4:
            return self._negative(service, uds.NRC_INCORRECT_LENGTH)
        if self.pending_seed is None:
            return self._negative(service, uds.NRC_REQUEST_SEQUENCE_ERROR)
        expected = uds.compute_key(self.pending_seed)
        self.pending_seed = None
        if ((request[2] << 8) | request[3]) == expected:
            self.unlocked = True
            self.failed_attempts = 0
            return [service + uds.POSITIVE_OFFSET, uds.SEND_KEY]
        if self.build.has("SEED-03"):
            return self._negative(service, uds.NRC_INVALID_KEY)
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_attempts:
            self.lockout_until_ms = now_ms + self.lockout_ms
            return self._negative(service, uds.NRC_EXCEEDED_ATTEMPTS)
        return self._negative(service, uds.NRC_INVALID_KEY)
