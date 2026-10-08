import pytest

from analyzer.checks import check_cycle_time, check_signal_ranges, check_timeouts

pytestmark = pytest.mark.network_behavior

SPEED_ID = 0x100
SPEED_TIMEOUT_DTC = 0xD00100


def latest(bench, name):
    message = bench.network.by_name(name)
    frame = next(f for f in reversed(bench.bus.trace) if f.can_id == message.can_id)
    return message.decode(frame.data)


@pytest.mark.req("NET-01")
def test_cycle_times_within_tolerance(bench):
    bench.bus.advance(2000)
    assert [str(f) for f in check_cycle_time(bench.bus.trace, bench.network)] == []


@pytest.mark.req("NET-01")
def test_every_periodic_message_is_present(bench):
    bench.bus.advance(200)
    seen = {f.can_id for f in bench.bus.trace}
    assert {m.can_id for m in bench.network.messages} <= seen


@pytest.mark.req("NET-02")
def test_timeout_dtc_when_message_stops(bench):
    bench.bus.advance(200)
    bench.injector.drop(SPEED_ID, start_ms=bench.bus.now_ms, duration_ms=100)
    bench.bus.advance(60)
    assert latest(bench, "BrakeCommand")["fault"] == 1
    bench.bus.advance(90)
    assert bench.client.read_dtcs() == [SPEED_TIMEOUT_DTC]
    assert check_timeouts(bench.bus.trace, bench.network) != []


@pytest.mark.req("NET-02")
def test_no_dtc_for_two_missing_frames(bench):
    bench.bus.advance(205)
    bench.injector.drop(SPEED_ID, start_ms=bench.bus.now_ms, duration_ms=20)
    bench.bus.advance(100)
    assert bench.client.read_dtcs() == []


@pytest.mark.req("NET-02")
def test_dtc_for_three_missing_frames(bench):
    bench.bus.advance(205)
    bench.injector.drop(SPEED_ID, start_ms=bench.bus.now_ms, duration_ms=30)
    bench.bus.advance(100)
    assert bench.client.read_dtcs() == [SPEED_TIMEOUT_DTC]


@pytest.mark.req("NET-03")
def test_signals_stay_in_range_across_the_operating_range(bench):
    for speed, distance in [(0.0, 0.0), (100.0, 20.0), (250.0, 200.0)]:
        bench.sensor.speed_kph = speed
        bench.sensor.distance_m = distance
        bench.bus.advance(100)
    assert [str(f) for f in check_signal_ranges(bench.bus.trace, bench.network)] == []
