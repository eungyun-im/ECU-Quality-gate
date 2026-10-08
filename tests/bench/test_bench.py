"""Sanity checks of the virtual bench: application behavior and the fuzzer."""

from bench.fuzz import DiagFuzzer
from protocol import uds


def latest_brake(bench):
    message = bench.network.by_name("BrakeCommand")
    frame = next(f for f in reversed(bench.bus.trace) if f.can_id == message.can_id)
    return message.decode(frame.data)


def test_brake_request_follows_speed_and_distance(bench):
    bench.sensor.speed_kph, bench.sensor.distance_m = 40.0, 10.0
    bench.bus.advance(100)
    assert latest_brake(bench)["brake_request"] == 1
    bench.sensor.speed_kph = 29.9
    bench.bus.advance(100)
    assert latest_brake(bench)["brake_request"] == 0


def test_written_threshold_changes_behavior(bench):
    bench.sensor.speed_kph, bench.sensor.distance_m = 40.0, 10.0
    bench.client.unlock()
    bench.client.write_did(0x0101, list((500).to_bytes(2, "big")))  # 50.0 km/h
    bench.bus.advance(100)
    assert latest_brake(bench)["brake_request"] == 0


def test_frame_helpers_round_trip():
    payload = [uds.READ_DATA_BY_IDENTIFIER, 0xF1, 0x90]
    assert uds.from_frame(uds.to_frame(payload)) == payload
    assert uds.from_frame(bytes([0x09, 0x22])) is None
    assert uds.from_frame(bytes([0x00, 0x22])) is None


def test_fuzzer_is_reproducible(bench):
    first = DiagFuzzer(bench.client, 7).random_frames(20)
    second = DiagFuzzer(bench.client, 7).random_frames(20)
    assert first == second


def test_mutations_cover_every_strategy(bench):
    frames = DiagFuzzer(bench.client, 7).mutated_frames([0x3E, 0x00], 12)
    assert any(f[0] == 0 for f in frames)
    assert any(f[0] > len(f) - 1 for f in frames)
    assert any(len(f) > 8 for f in frames)
