"""The same requirements, exercised with a standard UDS client (udsoncan).

udsoncan builds every request and parses every response. A negative response
arrives as NegativeResponseException with the response code attached.
"""

from contextlib import contextmanager

import pytest
from udsoncan.exceptions import NegativeResponseException

from bench.tester import SECURITY_LEVEL, SW_VERSION_DID, THRESHOLD_DID, VIN_DID, make_tester
from protocol import uds

pytestmark = pytest.mark.diag

STORED_DTC = 0xD00100


@pytest.fixture
def tester(bench):
    with make_tester(bench.client) as client:
        yield client


@contextmanager
def rejected_with(code):
    """The request inside the block must be rejected with this response code."""
    with pytest.raises(NegativeResponseException) as info:
        yield
    assert info.value.response.code == code


@pytest.mark.req("DIAG-01")
def test_session_change_reports_server_timing(tester):
    response = tester.change_session(uds.EXTENDED_SESSION)
    assert response.positive
    assert response.service_data.p2_server_max == pytest.approx(0.050)
    assert response.service_data.p2_star_server_max == pytest.approx(5.0)


@pytest.mark.req("DIAG-03")
def test_read_vin_over_multiple_frames(tester):
    response = tester.read_data_by_identifier(VIN_DID)
    assert response.service_data.values[VIN_DID] == "KMUECUGATE0000001"


@pytest.mark.req("DIAG-03")
def test_read_software_version(tester, bench):
    response = tester.read_data_by_identifier(SW_VERSION_DID)
    assert list(response.service_data.values[SW_VERSION_DID]) == bench.build.version_bytes


@pytest.mark.req("DIAG-03")
def test_read_unknown_did_is_rejected(tester):
    tester.config["data_identifiers"][0xFFFF] = ">H"
    with rejected_with(uds.NRC_REQUEST_OUT_OF_RANGE):
        tester.read_data_by_identifier(0xFFFF)


@pytest.mark.req("DIAG-04")
def test_write_needs_extended_session(tester):
    with rejected_with(uds.NRC_NOT_SUPPORTED_IN_SESSION):
        tester.write_data_by_identifier(THRESHOLD_DID, 400)


@pytest.mark.req("DIAG-04")
def test_write_needs_unlocked_security(tester):
    tester.change_session(uds.EXTENDED_SESSION)
    with rejected_with(uds.NRC_SECURITY_ACCESS_DENIED):
        tester.write_data_by_identifier(THRESHOLD_DID, 400)


@pytest.mark.req("DIAG-04")
def test_unlock_then_write_and_read_back(tester):
    tester.change_session(uds.EXTENDED_SESSION)
    tester.unlock_security_access(SECURITY_LEVEL)
    tester.write_data_by_identifier(THRESHOLD_DID, 400)
    response = tester.read_data_by_identifier(THRESHOLD_DID)
    assert response.service_data.values[THRESHOLD_DID] == (400,)


@pytest.mark.req("DIAG-05")
def test_read_and_clear_dtcs(tester, bench):
    bench.brake.dtcs.add(STORED_DTC)  # precondition: one stored DTC
    response = tester.get_dtc_by_status_mask(0xFF)
    assert [dtc.id for dtc in response.service_data.dtcs] == [STORED_DTC]
    tester.clear_dtc(0xFFFFFF)
    assert tester.get_dtc_by_status_mask(0xFF).service_data.dtcs == []


@pytest.mark.req("DIAG-06")
def test_reset_locks_the_ecu_again(tester):
    tester.change_session(uds.EXTENDED_SESSION)
    tester.unlock_security_access(SECURITY_LEVEL)
    tester.ecu_reset(uds.HARD_RESET)
    with rejected_with(uds.NRC_NOT_SUPPORTED_IN_SESSION):
        tester.request_seed(SECURITY_LEVEL)


@pytest.mark.req("SEC-01")
def test_three_wrong_keys_lock_access(tester):
    tester.change_session(uds.EXTENDED_SESSION)
    for expected in (uds.NRC_INVALID_KEY, uds.NRC_INVALID_KEY, uds.NRC_EXCEEDED_ATTEMPTS):
        tester.request_seed(SECURITY_LEVEL)
        with rejected_with(expected):
            tester.send_key(SECURITY_LEVEL, b"\x00\x00")
    with rejected_with(uds.NRC_TIME_DELAY_NOT_EXPIRED):
        tester.request_seed(SECURITY_LEVEL)


@pytest.mark.req("DIAG-02")
def test_tester_present_is_answered(tester):
    assert tester.tester_present().positive
