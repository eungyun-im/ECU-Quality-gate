import pytest

from analyzer.checks import check_cycle_time
from bench.fuzz import DiagFuzzer
from bench.uds import nrc
from protocol import uds

pytestmark = pytest.mark.security

THRESHOLD_DID = 0x0101
FUZZ_SEED = 20261008


def wrong_key(seed):
    return uds.compute_key(seed) ^ 0xFFFF


def fail_once(client):
    return client.send_key(wrong_key(client.request_seed()))


def wait(bench, ms):
    """Let time pass while TesterPresent keeps the extended session open."""
    for _ in range(ms // 1000):
        bench.bus.advance(1000)
        bench.client.tester_present()
    bench.bus.advance(ms % 1000)


@pytest.mark.req("SEC-01")
def test_lockout_after_three_wrong_keys(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(fail_once(client)) == uds.NRC_INVALID_KEY
    assert nrc(fail_once(client)) == uds.NRC_INVALID_KEY
    assert nrc(fail_once(client)) == uds.NRC_EXCEEDED_ATTEMPTS
    assert nrc(client.request_seed()) == uds.NRC_TIME_DELAY_NOT_EXPIRED


@pytest.mark.req("SEC-01")
def test_lockout_lasts_ten_seconds(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    for _ in range(3):
        fail_once(client)
    wait(bench, 9999)
    assert nrc(client.request_seed()) == uds.NRC_TIME_DELAY_NOT_EXPIRED
    wait(bench, 1)
    seed = client.request_seed()
    assert isinstance(seed, int)
    assert client.send_key(uds.compute_key(seed)) == [0x67, 0x02]


@pytest.mark.req("SEC-01")
def test_correct_key_resets_the_attempt_counter(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    fail_once(client)
    fail_once(client)
    assert client.send_key(uds.compute_key(client.request_seed())) == [0x67, 0x02]
    client.enter_session(uds.EXTENDED_SESSION)  # locks again
    assert nrc(fail_once(client)) == uds.NRC_INVALID_KEY


@pytest.mark.req("SEC-02")
def test_write_rejected_while_locked(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(client.write_did(THRESHOLD_DID, [0x00, 0x00])) == uds.NRC_SECURITY_ACCESS_DENIED
    fail_once(client)
    assert nrc(client.write_did(THRESHOLD_DID, [0x00, 0x00])) == uds.NRC_SECURITY_ACCESS_DENIED
    assert client.read_did(THRESHOLD_DID) == [0x62, 0x01, 0x01, 0x01, 0x2C]


@pytest.mark.req("SEC-02")
def test_key_without_seed_is_rejected(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(client.send_key(0x0000)) == uds.NRC_REQUEST_SEQUENCE_ERROR


@pytest.mark.req("SEC-03")
def test_seed_is_not_reused(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    seeds = [client.request_seed() for _ in range(5)]
    assert len(set(seeds)) == len(seeds)


@pytest.mark.req("SEC-03")
def test_replayed_key_is_rejected(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    captured_key = uds.compute_key(client.request_seed())
    client.request_seed()  # a later attempt gets its own seed
    assert nrc(client.send_key(captured_key)) == uds.NRC_INVALID_KEY


@pytest.mark.req("SEC-04")
def test_reset_does_not_clear_attempt_counter(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    fail_once(client)
    fail_once(client)
    client.reset()
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(fail_once(client)) == uds.NRC_EXCEEDED_ATTEMPTS


@pytest.mark.req("SEC-04")
def test_session_change_does_not_clear_attempt_counter(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    fail_once(client)
    fail_once(client)
    client.enter_session(uds.DEFAULT_SESSION)
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(fail_once(client)) == uds.NRC_EXCEEDED_ATTEMPTS


@pytest.mark.req("SEC-04")
def test_reset_does_not_end_the_lockout(bench):
    client = bench.client
    client.enter_session(uds.EXTENDED_SESSION)
    for _ in range(3):
        fail_once(client)
    client.reset()
    client.enter_session(uds.EXTENDED_SESSION)
    assert nrc(client.request_seed()) == uds.NRC_TIME_DELAY_NOT_EXPIRED


@pytest.mark.req("SEC-05")
def test_ecu_survives_random_requests(bench):
    fuzzer = DiagFuzzer(bench.client, FUZZ_SEED)
    findings = fuzzer.run(fuzzer.random_frames(300))
    assert [str(f) for f in findings] == []
    assert bench.client.tester_present() == [0x7E, 0x00]


@pytest.mark.req("SEC-05")
def test_ecu_survives_mutated_requests(bench):
    fuzzer = DiagFuzzer(bench.client, FUZZ_SEED)
    valid = [uds.READ_DATA_BY_IDENTIFIER, 0xF1, 0x95]
    findings = fuzzer.run(fuzzer.mutated_frames(valid, 120))
    assert [str(f) for f in findings] == []
    assert bench.client.tester_present() == [0x7E, 0x00]


@pytest.mark.req("SEC-05")
def test_bus_timing_holds_after_fuzzing(bench):
    fuzzer = DiagFuzzer(bench.client, FUZZ_SEED)
    for frame in fuzzer.random_frames(100):
        bench.client.request_raw(frame, timeout_ms=5)
        bench.bus.advance(3)
    assert [str(f) for f in check_cycle_time(bench.bus.trace, bench.network)] == []
