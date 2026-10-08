import pytest

pytestmark = pytest.mark.security


@pytest.mark.skip(reason="not implemented: SEC-01 wrong key, lockout, delay")
def test_lockout_after_three_wrong_keys():
    pass


@pytest.mark.skip(reason="not implemented: SEC-02 write while locked")
def test_write_rejected_while_locked():
    pass
