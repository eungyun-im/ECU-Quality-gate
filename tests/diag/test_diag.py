import pytest

from bench.uds import nrc
from protocol import uds

pytestmark = pytest.mark.diag

THRESHOLD_DID = 0x0101
SW_VERSION_DID = 0xF195
VIN_DID = 0xF190
STORED_DTC = 0xD00100


@pytest.mark.req("DIAG-01")
def test_starts_in_default_session(bench):
    # SecurityAccess exists only in the extended session.
    response = bench.client.request([uds.SECURITY_ACCESS, uds.REQUEST_SEED])
    assert nrc(response) == uds.NRC_NOT_SUPPORTED_IN_SESSION


@pytest.mark.req("DIAG-01")
def test_enter_extended_session(bench):
    assert bench.client.enter_session(uds.EXTENDED_SESSION) == [0x50, 0x03]
    assert isinstance(bench.client.request_seed(), int)


@pytest.mark.req("DIAG-01")
def test_unsupported_session_is_rejected(bench):
    assert nrc(bench.client.enter_session(0x7E)) == uds.NRC_SUB_FUNCTION_NOT_SUPPORTED


@pytest.mark.req("DIAG-02")
def test_session_survives_just_under_s3(bench):
    bench.client.enter_session(uds.EXTENDED_SESSION)
    bench.bus.advance(4999)
    assert isinstance(bench.client.request_seed(), int)


@pytest.mark.req("DIAG-02")
def test_session_falls_back_at_s3(bench):
    bench.client.enter_session(uds.EXTENDED_SESSION)
    bench.bus.advance(5000)
    response = bench.client.request([uds.SECURITY_ACCESS, uds.REQUEST_SEED])
    assert nrc(response) == uds.NRC_NOT_SUPPORTED_IN_SESSION


@pytest.mark.req("DIAG-02")
def test_tester_present_keeps_session_alive(bench):
    bench.client.enter_session(uds.EXTENDED_SESSION)
    for _ in range(3):
        bench.bus.advance(4000)
        assert bench.client.tester_present() == [0x7E, 0x00]
    assert isinstance(bench.client.request_seed(), int)


@pytest.mark.req("DIAG-03")
def test_read_known_dids(bench):
    version = bench.client.read_did(SW_VERSION_DID)
    assert version == [0x62, 0xF1, 0x95, *bench.build.version_bytes]
    vin = bench.client.read_did(VIN_DID)
    assert vin[:3] == [0x62, 0xF1, 0x90]
    assert len(vin) == 3 + 17


@pytest.mark.req("DIAG-03")
def test_read_unknown_did(bench):
    assert nrc(bench.client.read_did(0xFFFF)) == uds.NRC_REQUEST_OUT_OF_RANGE


@pytest.mark.req("DIAG-03")
def test_read_with_wrong_length(bench):
    response = bench.client.request([uds.READ_DATA_BY_IDENTIFIER, 0x01])
    assert nrc(response) == uds.NRC_INCORRECT_LENGTH


@pytest.mark.req("DIAG-04")
def test_write_rejected_in_default_session(bench):
    response = bench.client.write_did(THRESHOLD_DID, [0x01, 0x90])
    assert nrc(response) == uds.NRC_NOT_SUPPORTED_IN_SESSION


@pytest.mark.req("DIAG-04")
def test_write_rejected_when_locked(bench):
    bench.client.enter_session(uds.EXTENDED_SESSION)
    response = bench.client.write_did(THRESHOLD_DID, [0x01, 0x90])
    assert nrc(response) == uds.NRC_SECURITY_ACCESS_DENIED


@pytest.mark.req("DIAG-04")
def test_write_accepted_when_unlocked(bench):
    assert bench.client.unlock() == [0x67, 0x02]
    assert bench.client.write_did(THRESHOLD_DID, [0x01, 0x90]) == [0x6E, 0x01, 0x01]
    assert bench.client.read_did(THRESHOLD_DID) == [0x62, 0x01, 0x01, 0x01, 0x90]


@pytest.mark.req("DIAG-04")
def test_write_validates_did_and_length(bench):
    bench.client.unlock()
    assert nrc(bench.client.write_did(SW_VERSION_DID, [1, 2, 3])) == uds.NRC_REQUEST_OUT_OF_RANGE
    assert nrc(bench.client.write_did(THRESHOLD_DID, [0x01])) == uds.NRC_INCORRECT_LENGTH


@pytest.mark.req("DIAG-05")
def test_read_and_clear_dtcs(bench):
    assert bench.client.read_dtcs() == []
    bench.brake.dtcs.add(STORED_DTC)  # precondition: one stored DTC
    assert bench.client.read_dtcs() == [STORED_DTC]
    assert bench.client.clear_dtcs() == [0x54]
    assert bench.client.read_dtcs() == []


@pytest.mark.req("DIAG-05")
def test_dtc_requests_with_wrong_length(bench):
    assert nrc(bench.client.request([uds.READ_DTC_INFORMATION, 0x02])) == uds.NRC_INCORRECT_LENGTH
    assert nrc(bench.client.request([uds.CLEAR_DIAGNOSTIC_INFORMATION, 0xFF])) == uds.NRC_INCORRECT_LENGTH


@pytest.mark.req("DIAG-06")
def test_reset_returns_to_default_and_locks(bench):
    bench.client.unlock()
    assert bench.client.reset() == [0x51, 0x01]
    response = bench.client.request([uds.SECURITY_ACCESS, uds.REQUEST_SEED])
    assert nrc(response) == uds.NRC_NOT_SUPPORTED_IN_SESSION
    bench.client.enter_session(uds.EXTENDED_SESSION)
    response = bench.client.write_did(THRESHOLD_DID, [0x01, 0x90])
    assert nrc(response) == uds.NRC_SECURITY_ACCESS_DENIED


@pytest.mark.req("DIAG-06")
def test_unsupported_reset_type(bench):
    response = bench.client.request([uds.ECU_RESET, 0x7E])
    assert nrc(response) == uds.NRC_SUB_FUNCTION_NOT_SUPPORTED
