"""Generate the README figures from real bench runs.

    python -m tools.figures

Writes docs/img/*.svg in a light and a dark variant.
"""

from pathlib import Path

from bench.bench import make_bench
from gate.run import ROOT, run_suites
from store.db import load_requirements
from tools.svgfig import Figure, save_both, scale

IMG = ROOT / "docs" / "img"
REFERENCE = ROOT / "builds" / "v1.0.0.yaml"
SEEDED = ROOT / "builds" / "v1.1.0.yaml"
OBSTACLE_ID = 0x110
NOMINAL_MS, TOLERANCE = 20, 0.10


def obstacle_gaps(build_path, duration_ms=400):
    """(time, gap to the previous frame) for every ObstacleDistance frame."""
    bench = make_bench(build_path)
    bench.bus.advance(duration_ms)
    times = [f.ts_ms for f in bench.bus.trace if f.can_id == OBSTACLE_ID]
    return [(now, now - before) for before, now in zip(times, times[1:])]


def cycle_time_figure(mode):
    reference, seeded = obstacle_gaps(REFERENCE), obstacle_gaps(SEEDED)
    fig = Figure(
        760, 330, mode,
        "The seeded build sends ObstacleDistance every 26 ms, outside the allowed band",
        "Gap between consecutive frames on the simulated bus (NET-01: nominal 20 ms, tolerance 10 %)",
    )
    left, right, top, bottom = 64, 556, 84, 276
    x = scale((0, 400), (left, right))
    y = scale((14, 30), (bottom, top))

    low, high = NOMINAL_MS * (1 - TOLERANCE), NOMINAL_MS * (1 + TOLERANCE)
    fig.rect(left, y(high), right - left, y(low) - y(high), "series1", opacity=0.10)
    for tick in (14, 18, 22, 26, 30):
        fig.line(left, y(tick), right, y(tick))
        fig.text(left - 10, y(tick) + 4, tick, size=11, color="secondary", anchor="end")
    for tick in (0, 100, 200, 300, 400):
        fig.text(x(tick), bottom + 20, tick, size=11, color="secondary", anchor="middle")
    fig.text(left - 44, top - 14, "gap (ms)", size=11, color="secondary")
    fig.text(right, bottom + 38, "time on the bus (ms)", size=11, color="secondary", anchor="end")

    for series, role in ((reference, "series1"), (seeded, "series2")):
        points = [(x(t), y(gap)) for t, gap in series]
        fig.polyline(points, role)
        for px, py in points:
            fig.dot(px, py, role)

    # Direct labels at the line ends, plus the band label. Text stays in text colors.
    fig.text(right + 14, y(26) + 4, "build 1.1.0 (seeded): 26 ms", size=12)
    fig.text(right + 14, y(20) + 4, "build 1.0.0: 20 ms", size=12)
    fig.text(right + 14, y(22) - 18, "allowed band", size=11, color="secondary")
    fig.text(right + 14, y(22) - 4, "18 to 22 ms", size=11, color="secondary")

    # Legend
    legend_y = 306
    for offset, role, label in ((0, "series1", "Reference build 1.0.0"), (190, "series2", "Seeded build 1.1.0")):
        fig.line(left + offset, legend_y, left + offset + 18, legend_y, stroke=role, width=2)
        fig.dot(left + offset + 9, legend_y, role)
        fig.text(left + offset + 26, legend_y + 4, label, size=11, color="secondary")
    return fig


def requirement_rows(build_path):
    counts = {r["id"]: [0, 0] for r in load_requirements()}
    for result in run_suites(build_path):
        counts[result.requirement][0 if result.outcome == "pass" else 1] += 1
    return counts


def gate_results_figure(mode, counts):
    failing = sum(1 for passed, failed in counts.values() if failed)
    fig = Figure(
        760, 96 + 24 * len(counts) + 34, mode,
        f"Seeded build 1.1.0: {failing} of {len(counts)} requirements have failing tests",
        "Requirement tests on the build with seven planted defects, one row per requirement",
    )
    label_x, bar_x, unit, thickness, gap = 24, 112, 46, 14, 2
    for row, (requirement, (passed, failed)) in enumerate(counts.items()):
        y = 80 + 24 * row
        fig.text(label_x, y + 11, requirement, size=12)
        cursor = bar_x
        if passed:
            width = passed * unit - (gap if failed else 0)
            fig.bar(cursor, y, width, thickness, "good", round_end=not failed)
            cursor += passed * unit
        if failed:
            fig.bar(cursor, y, failed * unit, thickness, "critical")
        end = bar_x + (passed + failed) * unit
        fig.text(end + 12, y + 11, f"{passed} of {passed + failed} passed", size=11, color="secondary")
        # State is never color alone: a mark and a word.
        mark, word, role = ("✕", "FAIL", "critical") if failed else ("✓", "PASS", "good")
        fig.text(676, y + 11, mark, size=12, color=role, weight=700)
        fig.text(692, y + 11, word, size=11, weight=600)
    legend_y = 80 + 24 * len(counts) + 22
    for offset, role, label in ((0, "good", "tests passed"), (130, "critical", "tests failed")):
        fig.rect(bar_x + offset, legend_y - 9, 12, 12, role, rx=2)
        fig.text(bar_x + offset + 18, legend_y + 1, label, size=11, color="secondary")
    return fig


def main():
    save_both(IMG, "cycle-time", cycle_time_figure)
    counts = requirement_rows(SEEDED)
    save_both(IMG, "gate-results", lambda mode: gate_results_figure(mode, counts))


if __name__ == "__main__":
    main()
