import pytest

pytestmark = pytest.mark.network_behavior


@pytest.mark.skip(reason="not implemented: NET-01 cycle time")
def test_cycle_time_within_tolerance():
    pass


@pytest.mark.skip(reason="not implemented: NET-02 timeout DTC")
def test_timeout_dtc_when_message_stops():
    pass


@pytest.mark.skip(reason="not implemented: NET-03 signal range")
def test_signals_within_declared_range():
    pass
