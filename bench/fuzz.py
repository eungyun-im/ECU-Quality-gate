"""Diagnostic request fuzzer. Seeded, so every failing case can be replayed."""

import random
from dataclasses import dataclass

from protocol import uds


@dataclass(frozen=True)
class FuzzFinding:
    frame: bytes
    problem: str

    def __str__(self):
        return f"{self.frame.hex().upper()}: {self.problem}"


class DiagFuzzer:
    def __init__(self, client, seed):
        self.client = client
        self.rng = random.Random(seed)

    def random_frames(self, count):
        """Frames of random length and content, including the length byte."""
        return [
            bytes(self.rng.randrange(256) for _ in range(self.rng.randrange(1, 9)))
            for _ in range(count)
        ]

    def mutated_frames(self, valid_payload, count):
        """Variants of a valid request. The strategies are cycled so each is used."""
        strategies = [
            self._bit_flip,
            self._truncate,
            self._length_too_long,
            self._length_zero,
            self._extend,
            self._other_service,
        ]
        base = uds.to_frame(valid_payload)
        return [strategies[i % len(strategies)](bytearray(base)) for i in range(count)]

    def _bit_flip(self, frame):
        index = self.rng.randrange(len(frame))
        frame[index] ^= 1 << self.rng.randrange(8)
        return bytes(frame)

    def _truncate(self, frame):
        return bytes(frame[: self.rng.randrange(1, len(frame))])

    def _length_too_long(self, frame):
        frame[0] = self.rng.randrange(len(frame), 256)
        return bytes(frame)

    def _length_zero(self, frame):
        frame[0] = 0
        return bytes(frame)

    def _extend(self, frame):
        extra = bytes(self.rng.randrange(256) for _ in range(self.rng.randrange(1, 9)))
        return bytes(frame) + extra

    def _other_service(self, frame):
        frame[1] = self.rng.randrange(256)
        return bytes(frame)

    def run(self, frames, timeout_ms=50):
        """Send every frame and return the ones the ECU handled wrongly.

        Oracle: every request gets a response, and a service the ECU does not
        support never gets a positive one.
        """
        findings = []
        for frame in frames:
            response = self.client.request_raw(frame, timeout_ms)
            if response is None:
                findings.append(FuzzFinding(frame, "no response"))
                continue
            request = uds.from_frame(frame)
            if request and request[0] not in uds.SUPPORTED_SERVICES:
                if response[0] == (request[0] + uds.POSITIVE_OFFSET) & 0xFF:
                    findings.append(FuzzFinding(frame, "positive response to unsupported service"))
        return findings
