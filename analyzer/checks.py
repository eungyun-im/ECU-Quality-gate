"""Offline checks on a recorded bus trace. Each returns a list of findings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    requirement: str
    message: str
    ts_ms: int
    detail: str

    def __str__(self):
        return f"[{self.requirement}] {self.message} @ {self.ts_ms} ms: {self.detail}"


def _frames_by_message(trace, network):
    grouped = {m.can_id: [] for m in network.messages}
    for frame in trace:
        if frame.can_id in grouped:
            grouped[frame.can_id].append(frame)
    return [(network.by_id(can_id), frames) for can_id, frames in grouped.items()]


def check_cycle_time(trace, network, tolerance=0.10):
    """NET-01: gap between consecutive frames within tolerance of the nominal cycle."""
    findings = []
    for message, frames in _frames_by_message(trace, network):
        limit = tolerance * message.cycle_ms
        for previous, current in zip(frames, frames[1:]):
            gap = current.ts_ms - previous.ts_ms
            if abs(gap - message.cycle_ms) > limit:
                findings.append(
                    Finding(
                        "NET-01",
                        message.name,
                        current.ts_ms,
                        f"gap {gap} ms, nominal {message.cycle_ms} ms",
                    )
                )
    return findings


def check_timeouts(trace, network, max_missing_cycles=3, end_ms=None):
    """NET-02: silences long enough that the receiver must store a timeout DTC."""
    findings = []
    for message, frames in _frames_by_message(trace, network):
        limit = max_missing_cycles * message.cycle_ms
        times = [f.ts_ms for f in frames]
        if end_ms is not None:
            times.append(end_ms)
        for previous, current in zip(times, times[1:]):
            if current - previous > limit:
                findings.append(
                    Finding(
                        "NET-02",
                        message.name,
                        previous + limit,
                        f"silent for {current - previous} ms, limit {limit} ms",
                    )
                )
    return findings


def check_signal_ranges(trace, network):
    """NET-03: every signal value inside its declared range."""
    findings = []
    for message, frames in _frames_by_message(trace, network):
        for frame in frames:
            values = message.decode(frame.data)
            for signal in message.signals:
                value = values[signal.name]
                if not signal.minimum <= value <= signal.maximum:
                    findings.append(
                        Finding(
                            "NET-03",
                            message.name,
                            frame.ts_ms,
                            f"{signal.name} = {value:g}, range {signal.minimum:g} to {signal.maximum:g}",
                        )
                    )
    return findings
