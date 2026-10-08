"""Offline checks on a recorded bus trace. Each returns a list of findings."""


def check_cycle_time(trace, messages, tolerance=0.10):
    # NET-01
    raise NotImplementedError


def check_timeouts(trace, messages, max_missing_cycles=3):
    # NET-02
    raise NotImplementedError


def check_signal_ranges(trace, messages):
    # NET-03
    raise NotImplementedError
