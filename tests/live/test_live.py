"""The ECUs on a python-can bus in real time, talking to a stock udsoncan client.

Uses python-can's in-process "virtual" interface, so no CAN hardware or kernel
module is needed. On Linux the same code runs on vcan0 (see bench/live.py).
"""

import threading

import can
import pytest

from bench.live import make_live_tester, run_tester_session, start_ecus

pytestmark = pytest.mark.live
CHANNEL = "ecu-quality-gate-live-test"


@pytest.fixture
def live_ecus():
    ecu_can = can.Bus(interface="virtual", channel=CHANNEL)
    bus = start_ecus(ecu_can)
    stop = threading.Event()
    thread = threading.Thread(target=bus.run, kwargs={"stop": stop}, daemon=True)
    thread.start()
    yield bus
    stop.set()
    thread.join(timeout=2)
    ecu_can.shutdown()


def test_standard_tester_talks_to_the_ecus_in_real_time(live_ecus):
    tester_can = can.Bus(interface="virtual", channel=CHANNEL)
    client, notifier = make_live_tester(tester_can)
    try:
        result = run_tester_session(client)
    finally:
        notifier.stop()
        tester_can.shutdown()
    assert result == {
        "vin": "KMUECUGATE0000001",
        "sw_version": "1.0.0",
        "threshold_kph": 35.0,
        "dtcs": [],
    }
    periodic = {f.can_id for f in live_ecus.trace}
    assert {0x100, 0x110, 0x120} <= periodic
