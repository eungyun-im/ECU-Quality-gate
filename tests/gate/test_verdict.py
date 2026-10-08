"""Contract of gate.verdict.decide().

Skipped until decide() is implemented. Make these pass, then the gate prints
PASS or HOLD instead of PENDING.
"""

import pytest
import yaml

from gate.model import Defect, TestResult
from gate.run import CRITERIA_YAML
from gate.verdict import decide

REQUIREMENTS = ["DIAG-01", "NET-01", "SEC-01"]
CRITERIA = yaml.safe_load(CRITERIA_YAML.read_text(encoding="utf-8"))["criteria"]


def verdict(results, defects=()):
    try:
        return decide(list(results), list(defects), CRITERIA, REQUIREMENTS)
    except NotImplementedError:
        pytest.skip("gate/verdict.py is not implemented yet")


def all_passed():
    return [TestResult(f"t-{req}", req, "pass") for req in REQUIREMENTS]


def defect(severity, status="open", number=1):
    return Defect(f"DEF-{number:03d}", "SEC-01", severity, "summary", status=status)


def test_pass_when_everything_holds():
    decision = verdict(all_passed())
    assert decision.verdict == "PASS"
    assert tuple(decision.failed_criteria) == ()


def test_hold_on_one_critical_defect():
    decision = verdict(all_passed(), [defect("critical")])
    assert decision.verdict == "HOLD"
    assert "open_defects_max.critical" in decision.failed_criteria


def test_hold_on_one_major_defect():
    decision = verdict(all_passed(), [defect("major")])
    assert decision.verdict == "HOLD"
    assert "open_defects_max.major" in decision.failed_criteria


def test_three_minor_defects_are_tolerated():
    defects = [defect("minor", number=n) for n in range(1, 4)]
    assert verdict(all_passed(), defects).verdict == "PASS"


def test_four_minor_defects_hold():
    defects = [defect("minor", number=n) for n in range(1, 5)]
    decision = verdict(all_passed(), defects)
    assert decision.verdict == "HOLD"
    assert "open_defects_max.minor" in decision.failed_criteria


def test_closed_defects_do_not_count():
    assert verdict(all_passed(), [defect("critical", status="closed")]).verdict == "PASS"


def test_hold_when_a_requirement_has_no_executed_test():
    results = all_passed()[:-1]
    decision = verdict(results)
    assert decision.verdict == "HOLD"
    assert "requirement_coverage_min" in decision.failed_criteria


def test_blocked_test_does_not_count_as_coverage():
    results = all_passed()[:-1] + [TestResult("t-SEC-01", "SEC-01", "blocked")]
    decision = verdict(results)
    assert decision.verdict == "HOLD"
    assert "requirement_coverage_min" in decision.failed_criteria
    assert "tests_blocked_max" in decision.failed_criteria


def test_not_run_test_holds():
    results = all_passed() + [TestResult("t-extra", "SEC-01", "not_run")]
    decision = verdict(results)
    assert decision.verdict == "HOLD"
    assert "tests_not_run_max" in decision.failed_criteria


def test_every_failed_criterion_is_named():
    results = all_passed()[:-1]
    decision = verdict(results, [defect("critical"), defect("major", number=2)])
    assert set(decision.failed_criteria) == {
        "requirement_coverage_min",
        "open_defects_max.critical",
        "open_defects_max.major",
    }
