import pytest

pytestmark = pytest.mark.security


@pytest.mark.skip(reason="not implemented: SEC-01 wrong key, lockout, delay")
def test_lockout_after_three_wrong_keys():
    pass


@pytest.mark.skip(reason="not implemented: SEC-02 write while locked")
def test_write_rejected_while_locked():
    pass


@pytest.mark.skip(reason="not implemented: SEC-03 seed changes on every request")
def test_seed_is_not_reused():
    pass


@pytest.mark.skip(reason="not implemented: SEC-03 captured seed and key pair")
def test_replayed_key_is_rejected():
    pass


@pytest.mark.skip(reason="not implemented: SEC-04 lockout survives ECU reset")
def test_reset_does_not_clear_attempt_counter():
    pass


@pytest.mark.skip(reason="not implemented: SEC-05 random requests")
def test_ecu_survives_random_requests():
    pass


@pytest.mark.skip(reason="not implemented: SEC-05 mutated valid requests")
def test_ecu_survives_mutated_requests():
    pass
