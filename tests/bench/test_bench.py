"""Sanity checks of the virtual bench: application behavior, transport and the fuzzer."""

from bench.fuzz import DiagFuzzer

REQUEST_ID, RESPONSE_ID = 0x7E0, 0x7E8


def latest_brake(bench):
    message = bench.network.by_name("BrakeCommand")
    frame = next(f for f in reversed(bench.bus.trace) if f.can_id == message.can_id)
    return message.decode(frame.data)


def diagnostic_frames(bench):
    return [f for f in bench.bus.trace if f.can_id in (REQUEST_ID, RESPONSE_ID)]


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


def test_short_exchange_is_two_single_frames(bench):
    bench.client.tester_present()
    frames = diagnostic_frames(bench)
    assert [(f.can_id, f.data.hex()) for f in frames] == [
        (REQUEST_ID, "023e000000000000"),
        (RESPONSE_ID, "027e000000000000"),
    ]


def test_long_response_is_segmented_with_flow_control(bench):
    response = bench.client.read_did(0xF190)
    assert bytes(response[3:]) == b"KMUECUGATE0000001"
    frames = diagnostic_frames(bench)
    kinds = [(f.can_id, f.data[0] >> 4) for f in frames]
    assert kinds == [
        (REQUEST_ID, 0x0),   # single frame: request
        (RESPONSE_ID, 0x1),  # first frame: 20-byte response announced
        (REQUEST_ID, 0x3),   # flow control from the tester
        (RESPONSE_ID, 0x2),  # consecutive frame 1
        (RESPONSE_ID, 0x2),  # consecutive frame 2
    ]
    first = frames[1].data
    assert ((first[0] & 0x0F) << 8 | first[1]) == 20
    assert all(len(f.data) == 8 for f in frames)


def test_long_request_is_segmented_too(bench):
    payload = [0x22] + [0x00] * 19
    assert bench.client.request(payload) == [0x7F, 0x22, 0x13]
    requests = [f for f in diagnostic_frames(bench) if f.can_id == REQUEST_ID]
    assert [f.data[0] >> 4 for f in requests] == [0x1, 0x2, 0x2]


def test_transport_layers_report_no_errors_in_normal_use(bench):
    bench.client.unlock()
    bench.client.read_did(0xF190)
    assert bench.client.link.errors == []
    assert bench.brake.link.errors == []


def test_fuzzer_is_reproducible(bench):
    first = DiagFuzzer(bench.client, 7).random_payloads(20)
    second = DiagFuzzer(bench.client, 7).random_payloads(20)
    assert first == second


def test_fuzz_inputs_include_multi_frame_payloads(bench):
    fuzzer = DiagFuzzer(bench.client, 7)
    assert any(len(p) > 7 for p in fuzzer.random_payloads(50))
    assert any(len(p) > 16 for p in fuzzer.mutated_payloads([0x3E, 0x00], 10))


def test_fuzz_oracle_knows_service_3f(bench):
    # 0x3F + 0x40 equals 0x7F, so a rejection of service 0x3F starts like a positive response.
    fuzzer = DiagFuzzer(bench.client, 7)
    assert fuzzer.run([bytes([0x3F, 0x01])]) == []
