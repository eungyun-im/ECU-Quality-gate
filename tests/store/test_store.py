"""Tests of the results store and of the gate queries.

A query test is skipped while its .sql file is still a TODO.
"""

import pytest

from gate.model import Defect, TestResult
from store import db


def needs_query(name):
    return pytest.mark.skipif(not db.is_written(name), reason=f"store/queries/{name}.sql not written yet")


@pytest.fixture
def conn():
    connection = db.connect()
    yield connection
    connection.close()


def result(test_id, requirement, outcome):
    return TestResult(test_id=test_id, requirement=requirement, outcome=outcome)


def test_schema_and_requirements_are_created(conn):
    count = conn.execute("SELECT COUNT(*) AS n FROM requirements").fetchone()["n"]
    assert count == len(db.load_requirements())


def test_record_run_stores_results_and_defects(conn):
    results = [result("t1", "DIAG-01", "pass"), result("t2", "SEC-01", "fail")]
    defects = [Defect("DEF-001", "SEC-01", "critical", "no lockout")]
    build_id, run_id = db.record_run(conn, "1.0.0", results, defects)
    assert conn.execute("SELECT COUNT(*) AS n FROM test_results WHERE run_id = ?", (run_id,)).fetchone()["n"] == 2
    assert conn.execute("SELECT COUNT(*) AS n FROM defects WHERE build_id = ?", (build_id,)).fetchone()["n"] == 1


def test_rerun_replaces_the_defects_of_a_build(conn):
    defect = [Defect("DEF-001", "SEC-01", "critical", "no lockout")]
    db.record_run(conn, "1.0.0", [result("t1", "SEC-01", "fail")], defect)
    db.record_run(conn, "1.0.0", [result("t1", "SEC-01", "pass")], [])
    assert conn.execute("SELECT COUNT(*) AS n FROM defects").fetchone()["n"] == 0


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(Exception):
        db.record_run(conn, "1.0.0", [result("t1", "NOPE-99", "pass")], [])


def test_requirement_coverage(conn):
    total = len(db.load_requirements())
    results = [
        result("t1", "DIAG-01", "pass"),
        result("t2", "DIAG-01", "fail"),
        result("t3", "DIAG-02", "blocked"),
    ]
    _, run_id = db.record_run(conn, "1.0.0", results, [])
    row = db.run_query(conn, "requirement_coverage", run_id=run_id)[0]
    assert row["requirements_total"] == total
    assert row["requirements_covered"] == 1
    assert row["coverage"] == pytest.approx(1 / total)


@needs_query("open_defects_by_severity")
def test_open_defects_by_severity(conn):
    defects = [
        Defect("DEF-001", "SEC-01", "critical", "a"),
        Defect("DEF-002", "SEC-02", "critical", "b"),
        Defect("DEF-003", "NET-01", "major", "c", status="closed"),
        Defect("DEF-004", "NET-03", "minor", "d"),
    ]
    build_id, _ = db.record_run(conn, "1.0.0", [], defects)
    rows = db.run_query(conn, "open_defects_by_severity", build_id=build_id)
    assert {r["severity"]: r["open_count"] for r in rows} == {"critical": 2, "minor": 1}


@needs_query("regression_between_builds")
def test_regression_between_builds(conn):
    _, previous = db.record_run(
        conn, "1.0.0", [result("t1", "DIAG-01", "pass"), result("t2", "SEC-01", "pass")], []
    )
    _, current = db.record_run(
        conn, "1.1.0", [result("t1", "DIAG-01", "pass"), result("t2", "SEC-01", "fail")], []
    )
    rows = db.run_query(
        conn, "regression_between_builds", previous_run_id=previous, current_run_id=current
    )
    assert [(r["test_id"], r["previous_outcome"], r["current_outcome"]) for r in rows] == [
        ("t2", "pass", "fail")
    ]


@needs_query("pass_rate_trend")
def test_pass_rate_trend(conn):
    db.record_run(conn, "1.0.0", [result("t1", "DIAG-01", "pass"), result("t2", "DIAG-02", "pass")], [])
    db.record_run(conn, "1.1.0", [result("t1", "DIAG-01", "pass"), result("t2", "DIAG-02", "fail")], [])
    rows = db.run_query(conn, "pass_rate_trend")
    assert [(r["version"], r["category"], r["tests"], r["passed"]) for r in rows] == [
        ("1.0.0", "DIAG", 2, 2),
        ("1.1.0", "DIAG", 2, 1),
    ]
    assert rows[1]["pass_rate"] == pytest.approx(0.5)
