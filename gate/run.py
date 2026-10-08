"""Run the quality gate on one build.

    python -m gate.run builds/v1.0.0.yaml
    python -m gate.run builds/v1.1.0.yaml --out reports

Exit code: 0 = PASS, 1 = HOLD, 2 = verdict not implemented yet.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from ecus.build import load_build
from gate import report, verdict as verdict_module
from gate.model import Defect, TestResult
from store import db

ROOT = Path(__file__).resolve().parent.parent
SUITES = ["tests/diag", "tests/network", "tests/security"]
CRITERIA_YAML = ROOT / "requirements" / "gate_criteria.yaml"


def run_suites(build_path, traces_dir=None):
    """Run the requirement suites against a build and return the test results."""
    with tempfile.TemporaryDirectory() as tmp:
        results_file = Path(tmp) / "results.json"
        env = dict(os.environ, ECU_BUILD=str(Path(build_path).resolve()), GATE_RESULTS=str(results_file))
        if traces_dir:
            env["GATE_TRACES"] = str(Path(traces_dir).resolve())
        subprocess.run(
            [sys.executable, "-m", "pytest", *SUITES, "-q", "-p", "no:cacheprovider"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if not results_file.exists():
            raise RuntimeError("the test run produced no results file")
        return [TestResult(**row) for row in json.loads(results_file.read_text(encoding="utf-8"))]


def derive_defects(results):
    """One defect per violated requirement, listing the tests that failed."""
    severity = {r["id"]: r["severity"] for r in db.load_requirements()}
    failed = {}
    for result in results:
        if result.outcome == "fail":
            failed.setdefault(result.requirement, []).append(result)
    defects = []
    for number, (requirement, tests) in enumerate(sorted(failed.items()), start=1):
        first = tests[0]
        check = first.test_id.removeprefix("test_").replace("_", " ")
        summary = f"Check failed: {check}"
        if len(tests) > 1:
            summary += f" (+{len(tests) - 1} more)"
        defects.append(
            Defect(
                defect_id=f"DEF-{number:03d}",
                requirement=requirement,
                severity=severity.get(requirement, "major"),
                summary=summary,
                trace_path=first.trace_path,
                tests=tuple(t.test_id for t in tests),
            )
        )
    return defects


def _relative_traces(results, out_dir):
    """Store trace paths relative to the report directory so the report can move."""
    relative = []
    for result in results:
        path = result.trace_path
        if path:
            path = Path(path).resolve().relative_to(Path(out_dir).resolve()).as_posix()
        relative.append(TestResult(**{**result.__dict__, "trace_path": path}))
    return relative


def execute(build_path, out_dir=None, db_path=None):
    """Full gate run. Returns (verdict or None, results, defects, report text)."""
    build = load_build(build_path)
    out_dir = Path(out_dir) if out_dir else None
    traces_dir = out_dir / "traces" / build.version if out_dir else None
    results = run_suites(build_path, traces_dir)
    if out_dir:
        results = _relative_traces(results, out_dir)
    defects = derive_defects(results)
    requirement_ids = [r["id"] for r in db.load_requirements()]

    conn = db.connect(str(db_path) if db_path else ":memory:")
    _, run_id = db.record_run(conn, build.version, results, defects)
    coverage = db.run_query(conn, "requirement_coverage", run_id=run_id)[0]["coverage"]
    conn.close()

    criteria = yaml.safe_load(CRITERIA_YAML.read_text(encoding="utf-8"))["criteria"]
    try:
        decision = verdict_module.decide(results, defects, criteria, requirement_ids)
    except NotImplementedError:
        decision = None
    text = report.render(build.version, decision, results, defects, requirement_ids, coverage)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"gate_{build.version}.md").write_text(text, encoding="utf-8")
    return decision, results, defects, text


def main():
    parser = argparse.ArgumentParser(description="Run the quality gate on one build.")
    parser.add_argument("build", help="path to a build file, e.g. builds/v1.0.0.yaml")
    parser.add_argument("--out", default="reports", help="directory for the report and traces")
    parser.add_argument("--db", default=None, help="SQLite file (default: <out>/results.db)")
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    decision, _, _, text = execute(args.build, out_dir, args.db or out_dir / "results.db")
    print(text)
    if decision is None:
        return 2
    return 0 if decision.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
