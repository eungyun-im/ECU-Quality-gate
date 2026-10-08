"""Tests of the analyzer itself, on hand-made traces and on injected faults."""

from analyzer.checks import check_cycle_time, check_signal_ranges, check_timeouts
from bench.bus import Frame, load_trace
from bench.network import load_network

NETWORK = load_network()
SPEED = NETWORK.by_name("VehicleSpeed")


def speed_frames(times, kph=40.0):
    return [Frame(t, SPEED.can_id, SPEED.encode({"speed_kph": kph})) for t in times]


def test_clean_trace_has_no_findings():
    trace = speed_frames(range(10, 200, 10))
    assert check_cycle_time(trace, NETWORK) == []
    assert check_timeouts(trace, NETWORK) == []
    assert check_signal_ranges(trace, NETWORK) == []


def test_cycle_check_tolerates_ten_percent():
    assert check_cycle_time(speed_frames([10, 21, 30]), NETWORK) == []


def test_cycle_check_flags_drift():
    findings = check_cycle_time(speed_frames([10, 20, 32]), NETWORK)
    assert [(f.requirement, f.ts_ms) for f in findings] == [("NET-01", 32)]


def test_timeout_check_uses_three_cycles():
    assert check_timeouts(speed_frames([10, 40]), NETWORK) == []
    findings = check_timeouts(speed_frames([10, 41]), NETWORK)
    assert [(f.requirement, f.ts_ms) for f in findings] == [("NET-02", 40)]


def test_timeout_check_sees_silence_at_the_end():
    assert check_timeouts(speed_frames([10, 20]), NETWORK, end_ms=100) != []


def test_range_check_flags_out_of_range_value():
    findings = check_signal_ranges(speed_frames([10], kph=300.0), NETWORK)
    assert [f.requirement for f in findings] == ["NET-03"]


def test_injected_corruption_is_found(bench):
    bench.injector.corrupt(SPEED.can_id, byte_index=0, value=0xFF)
    bench.bus.advance(50)
    assert check_signal_ranges(bench.bus.trace, bench.network) != []


def test_injected_delay_is_found(bench):
    bench.bus.advance(100)
    bench.injector.delay(SPEED.can_id, extra_ms=4, start_ms=bench.bus.now_ms, duration_ms=20)
    bench.bus.advance(100)
    assert check_cycle_time(bench.bus.trace, bench.network) != []


def test_trace_round_trip(bench, tmp_path):
    bench.bus.advance(50)
    path = tmp_path / "trace.csv"
    bench.bus.save_trace(path)
    assert load_trace(path) == bench.bus.trace
