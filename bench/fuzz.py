"""Diagnostic fuzzer. Seeded, so every failing case can be replayed.

It works at two levels:
- UDS payloads sent through ISO-TP, short and long. Oracle: every request is answered.
- Raw CAN frames on the request ID. Many are invalid ISO-TP and are rightly
  ignored, so the oracle is liveness: the ECU still answers afterwards.
"""

import random
from dataclasses import dataclass

from protocol import uds

MAX_RANDOM_PAYLOAD = 40


@dataclass(frozen=True)
class FuzzFinding:
    payload: bytes
    problem: str

    def __str__(self):
        return f"{self.payload.hex().upper()}: {self.problem}"


class DiagFuzzer:
    def __init__(self, client, seed):
        self.client = client
        self.rng = random.Random(seed)

    def _random_bytes(self, low, high):
        return bytes(self.rng.randrange(256) for _ in range(self.rng.randrange(low, high + 1)))

    def random_payloads(self, count):
        """UDS payloads of random length and content. Long ones need several frames."""
        return [self._random_bytes(1, MAX_RANDOM_PAYLOAD) for _ in range(count)]

    def mutated_payloads(self, valid_payload, count):
        """Variants of a valid request. The strategies are cycled so each is used."""
        strategies = [self._bit_flip, self._truncate, self._extend, self._other_service, self._repeat]
        base = bytes(valid_payload)
        return [strategies[i % len(strategies)](bytearray(base)) for i in range(count)]

    def _bit_flip(self, payload):
        index = self.rng.randrange(len(payload))
        payload[index] ^= 1 << self.rng.randrange(8)
        return bytes(payload)

    def _truncate(self, payload):
        return bytes(payload[: self.rng.randrange(1, len(payload))]) if len(payload) > 1 else bytes(payload)

    def _extend(self, payload):
        return bytes(payload) + self._random_bytes(1, 30)

    def _other_service(self, payload):
        payload[0] = self.rng.randrange(256)
        return bytes(payload)

    def _repeat(self, payload):
        return bytes(payload) * self.rng.randrange(2, 8)

    def random_frames(self, count):
        """Raw CAN frames of random length and content."""
        return [self._random_bytes(1, 8) for _ in range(count)]

    def run(self, payloads, timeout_ms=50):
        """Send every payload and return the ones the ECU handled wrongly.

        Oracle: every request gets a response, and a service the ECU does not
        support never gets a positive one.
        """
        findings = []
        for payload in payloads:
            response = self.client.request(payload, timeout_ms)
            if response is None:
                findings.append(FuzzFinding(payload, "no response"))
            elif payload[0] not in uds.SUPPORTED_SERVICES and self._is_positive(payload[0], response):
                findings.append(FuzzFinding(payload, "positive response to unsupported service"))
        return findings

    @staticmethod
    def _is_positive(service, response):
        # Service 0x3F is the trap: 0x3F + 0x40 is 0x7F, the negative response marker.
        if response[0] == uds.NEGATIVE_RESPONSE and len(response) == 3 and response[1] == service:
            return False
        return response[0] == (service + uds.POSITIVE_OFFSET) & 0xFF

    def send_frames(self, frames, gap_ms=1):
        """Put raw frames on the bus. Returns nothing: check liveness afterwards."""
        for frame in frames:
            self.client.send_raw_frame(frame)
            self.client.bus.advance(gap_ms)
        self.client.flush()
