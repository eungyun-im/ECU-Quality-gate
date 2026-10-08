import pytest

pytestmark = pytest.mark.diag


@pytest.mark.skip(reason="not implemented: DIAG-01 session control")
def test_enter_extended_session():
    pass


@pytest.mark.skip(reason="not implemented: DIAG-02 S3 timeout")
def test_session_falls_back_without_tester_present():
    pass


@pytest.mark.skip(reason="not implemented: DIAG-03 read DID, NRC 0x31, NRC 0x13")
def test_read_data_by_identifier():
    pass


@pytest.mark.skip(reason="not implemented: DIAG-04 write preconditions")
def test_write_rejected_in_default_session():
    pass


@pytest.mark.skip(reason="not implemented: DIAG-05 read and clear DTC")
def test_read_and_clear_dtc():
    pass


@pytest.mark.skip(reason="not implemented: DIAG-06 ECU reset")
def test_reset_returns_to_default_session():
    pass
