"""Shared fixtures and the hooks that feed test results to the gate.

Environment variables (all optional, set by gate/run.py):
    ECU_BUILD     build file to test (default: builds/v1.0.0.yaml)
    GATE_RESULTS  JSON file to write one record per requirement test
    GATE_TRACES   directory for the bus trace of each failed test
"""

import json
import os
import re
from pathlib import Path

import pytest

from bench.bench import make_bench
from ecus.build import REFERENCE_BUILD

_records = {}
_traces = {}


@pytest.fixture
def bench(request):
    bench = make_bench(os.environ.get("ECU_BUILD", REFERENCE_BUILD))
    yield bench
    report = getattr(request.node, "rep_call", None)
    traces_dir = os.environ.get("GATE_TRACES")
    if traces_dir and report is not None and report.failed:
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", _test_id(request.node))
        path = Path(traces_dir) / f"{name}.csv"
        bench.bus.save_trace(path)
        _traces[request.node.nodeid] = str(path)


def _test_id(item):
    """File and test name. Test names alone repeat across suites."""
    return f"{item.path.stem}.{item.name}"


def _requirement(item):
    marker = item.get_closest_marker("req")
    return marker.args[0] if marker else None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.rep_call = report
    requirement = _requirement(item)
    if requirement is None:
        return
    if report.when == "call":
        message = ""
        if report.failed and call.excinfo is not None:
            message = str(call.excinfo.value).strip().splitlines()[0] if str(call.excinfo.value).strip() else call.excinfo.typename
        _records[item.nodeid] = {
            "test_id": _test_id(item),
            "requirement": requirement,
            "outcome": "pass" if report.passed else "fail",
            "duration_ms": round(report.duration * 1000),
            "message": message,
        }
    elif report.when == "setup" and not report.passed:
        _records[item.nodeid] = {
            "test_id": _test_id(item),
            "requirement": requirement,
            "outcome": "not_run" if report.skipped else "blocked",
            "duration_ms": 0,
            "message": "",
        }


def pytest_sessionfinish(session):
    results_file = os.environ.get("GATE_RESULTS")
    if not results_file:
        return
    rows = [dict(record, trace_path=_traces.get(nodeid)) for nodeid, record in _records.items()]
    Path(results_file).write_text(json.dumps(rows, indent=2), encoding="utf-8")
