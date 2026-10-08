"""Gate report: verdict first, then per-requirement results and defects."""

PENDING = "PENDING (gate/verdict.py not implemented)"


def _by_requirement(results, requirements):
    table = {req: {"pass": 0, "fail": 0, "blocked": 0, "not_run": 0} for req in requirements}
    for result in results:
        table.setdefault(result.requirement, {"pass": 0, "fail": 0, "blocked": 0, "not_run": 0})
        table[result.requirement][result.outcome] += 1
    return table


def render(build_version, verdict, results, defects, requirements, coverage=None):
    """Markdown report. verdict is a gate.model.Verdict, or None while undecided."""
    lines = [f"# Gate report: build {build_version}", ""]
    lines.append(f"**Verdict: {verdict.verdict if verdict else PENDING}**")
    if verdict and verdict.failed_criteria:
        lines.append("")
        lines.append("Failed criteria: " + ", ".join(verdict.failed_criteria))
    lines.append("")

    counts = {o: sum(r.outcome == o for r in results) for o in ("pass", "fail", "blocked", "not_run")}
    lines.append(
        f"Tests: {len(results)} total, {counts['pass']} passed, {counts['fail']} failed, "
        f"{counts['blocked']} blocked, {counts['not_run']} not run"
    )
    if coverage is not None:
        lines.append(f"Requirement coverage: {coverage:.0%}")
    lines.append(f"Open defects: {sum(d.status != 'closed' for d in defects)}")
    lines += ["", "## Requirements", "", "| Requirement | Tests | Passed | Failed | Result |", "|---|---|---|---|---|"]
    for requirement, row in _by_requirement(results, requirements).items():
        executed = row["pass"] + row["fail"]
        if executed == 0:
            state = "NOT COVERED"
        else:
            state = "FAIL" if row["fail"] else "PASS"
        total = sum(row.values())
        lines.append(f"| {requirement} | {total} | {row['pass']} | {row['fail']} | {state} |")

    lines += ["", "## Defects", ""]
    if not defects:
        lines.append("None.")
    else:
        lines += ["| ID | Severity | Requirement | Summary | Evidence |", "|---|---|---|---|---|"]
        for defect in defects:
            evidence = defect.trace_path or ""
            lines.append(
                f"| {defect.defect_id} | {defect.severity} | {defect.requirement} | "
                f"{defect.summary} | {evidence} |"
            )
    lines.append("")
    return "\n".join(lines)
