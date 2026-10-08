"""A standard udsoncan client connected to the bench.

udsoncan builds and parses the UDS messages. The connection class below
carries them over the bench's ISO-TP link and waits in simulated time, so a
request that times out costs no real time.
"""

import udsoncan
from udsoncan.client import Client
from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

from protocol import uds

VIN_DID = 0xF190
SW_VERSION_DID = 0xF195
THRESHOLD_DID = 0x0101
SECURITY_LEVEL = 1


class BenchConnection(BaseConnection):
    def __init__(self, uds_client, name=None):
        BaseConnection.__init__(self, name)
        self._client = uds_client
        self._opened = False

    def open(self):
        self._opened = True
        return self

    def close(self):
        self._opened = False

    def is_open(self):
        return self._opened

    def empty_rxqueue(self):
        self._client.flush()

    def specific_send(self, payload, timeout=None):
        self._client.send(payload)

    def specific_wait_frame(self, timeout=2):
        response = self._client.wait_response(timeout_ms=round(timeout * 1000))
        if response is None:
            raise TimeoutException(f"no response within {timeout} s of simulated time")
        return bytes(response)


def security_algorithm(level, seed, params=None):
    """Seed-to-key callback in the form udsoncan expects."""
    return uds.compute_key(int.from_bytes(seed, "big")).to_bytes(2, "big")


def client_config():
    config = dict(udsoncan.configs.default_client_config)
    config.update(
        exception_on_negative_response=True,
        exception_on_invalid_response=True,
        exception_on_unexpected_response=True,
        security_algo=security_algorithm,
        request_timeout=2,
        p2_timeout=1,
        p2_star_timeout=5,
        data_identifiers={
            VIN_DID: udsoncan.AsciiCodec(17),
            SW_VERSION_DID: ">BBB",
            THRESHOLD_DID: ">H",
        },
    )
    return config


def make_tester(uds_client, connection=None):
    """Return a udsoncan Client. Use it as a context manager, or call open()."""
    connection = connection or BenchConnection(uds_client)
    return Client(connection, config=client_config())
