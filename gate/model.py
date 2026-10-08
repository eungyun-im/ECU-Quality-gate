"""Records passed between the gate stages."""

from dataclasses import dataclass, field
from typing import Optional

OUTCOMES = ("pass", "fail", "blocked", "not_run")
SEVERITIES = ("critical", "major", "minor")


@dataclass(frozen=True)
class TestResult:
    __test__ = False  # not a pytest test class

    test_id: str
    requirement: str
    outcome: str
    duration_ms: int = 0
    message: str = ""
    trace_path: Optional[str] = None


@dataclass(frozen=True)
class Defect:
    defect_id: str
    requirement: str
    severity: str
    summary: str
    status: str = "open"
    trace_path: Optional[str] = None
    tests: tuple = ()


@dataclass(frozen=True)
class Verdict:
    verdict: str  # "PASS" or "HOLD"
    failed_criteria: tuple = field(default_factory=tuple)
