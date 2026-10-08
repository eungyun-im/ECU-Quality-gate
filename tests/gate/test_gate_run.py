"""The suites must pass the reference build and catch every planted defect.

Each test runs the requirement suites in a subprocess against one build.
"""

from pathlib import Path

import pytest
import yaml

from gate.run import ROOT, derive_defects, execute, run_suites

pytestmark = pytest.mark.gate

REFERENCE = ROOT / "builds" / "v1.0.0.yaml"
SEEDED = ROOT / "builds" / "v1.1.0.yaml"
SEEDS = yaml.safe_load(SEEDED.read_text(encoding="utf-8"))["seeded_defects"]


def failed_requirements(results):
    return {r.requirement for r in results if r.outcome == "fail"}


def test_reference_build_passes_every_requirement_test():
    results = run_suites(REFERENCE)
    assert results, "no requirement tests were collected"
    assert failed_requirements(results) == set()


@pytest.mark.parametrize("seed", SEEDS, ids=[s["id"] for s in SEEDS])
def test_each_planted_defect_is_caught_alone(seed, tmp_path):
    build = tmp_path / "single.yaml"
    build.write_text(
        yaml.safe_dump({"version": "9.9.9", "seeded_defects": [seed]}), encoding="utf-8"
    )
    assert seed["violates"] in failed_requirements(run_suites(build))


def test_seeded_build_report_names_every_violated_requirement(tmp_path):
    decision, results, defects, text = execute(SEEDED, out_dir=tmp_path)
    violated = {s["violates"] for s in SEEDS}
    assert violated <= {d.requirement for d in defects}
    assert derive_defects(results) == defects
    for requirement in violated:
        assert requirement in text
    assert Path(tmp_path / "gate_1.1.0.md").exists()
    assert all(d.trace_path and Path(tmp_path / d.trace_path).exists() for d in defects)
    if decision is not None:
        assert decision.verdict == "HOLD"
