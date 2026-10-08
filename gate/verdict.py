"""Reduce test results and defects to PASS or HOLD.

Not implemented yet. The contract is fixed by tests/gate/test_verdict.py,
which is skipped until decide() stops raising NotImplementedError.

Inputs
    results       list of gate.model.TestResult (outcome: pass, fail, blocked, not_run)
    defects       list of gate.model.Defect (severity: critical, major, minor; status)
    criteria      the "criteria" mapping of requirements/gate_criteria.yaml
    requirements  list of every requirement ID that must be covered

Output
    gate.model.Verdict("PASS") when every criterion holds, otherwise
    gate.model.Verdict("HOLD", failed_criteria=(...)) naming each criterion
    that failed, using the key names of gate_criteria.yaml.

Criteria
    requirement_coverage_min   share of requirements with at least one test
                               whose outcome is pass or fail
    open_defects_max           per severity, counting defects not yet closed
    tests_blocked_max          tests with outcome blocked
    tests_not_run_max          tests with outcome not_run
"""


def decide(results, defects, criteria, requirements):
    raise NotImplementedError("gate/verdict.py: decide() is not implemented yet")
