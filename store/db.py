"""SQLite results store: create the schema, record runs, run the named queries."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

STORE = Path(__file__).resolve().parent
SCHEMA = STORE / "schema.sql"
QUERIES = STORE / "queries"
REQUIREMENTS_YAML = STORE.parent / "requirements" / "requirements.yaml"


def load_requirements(path=REQUIREMENTS_YAML):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["requirements"]


def connect(path=":memory:"):
    """Open the database, creating the schema and the requirement rows on first use."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'builds'"
    ).fetchone()
    if not exists:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        conn.executemany(
            "INSERT INTO requirements (id, category, text) VALUES (:id, :category, :text)",
            load_requirements(),
        )
        conn.commit()
    return conn


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_run(conn, build_version, results, defects):
    """Store one gate run and return (build_id, run_id).

    A rerun of the same build replaces that build's defects, so the defect
    table always reflects the latest run of each build.
    """
    conn.execute(
        "INSERT OR IGNORE INTO builds (version, created_at) VALUES (?, ?)",
        (build_version, _now()),
    )
    build_id = conn.execute(
        "SELECT id FROM builds WHERE version = ?", (build_version,)
    ).fetchone()["id"]
    run_id = conn.execute(
        "INSERT INTO test_runs (build_id, started_at) VALUES (?, ?)", (build_id, _now())
    ).lastrowid
    conn.executemany(
        "INSERT INTO test_results (run_id, test_id, requirement_id, outcome, duration_ms, trace_path)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (run_id, r.test_id, r.requirement, r.outcome, r.duration_ms, r.trace_path)
            for r in results
        ],
    )
    conn.execute("DELETE FROM defects WHERE build_id = ?", (build_id,))
    conn.executemany(
        "INSERT INTO defects (id, build_id, requirement_id, severity, status, summary, trace_path)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (f"{build_version}/{d.defect_id}", build_id, d.requirement, d.severity, d.status,
             d.summary, d.trace_path)
            for d in defects
        ],
    )
    conn.commit()
    return build_id, run_id


def query_text(name):
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


def is_written(name):
    """False while a query file holds only comments."""
    lines = [line.strip() for line in query_text(name).splitlines()]
    return any(line and not line.startswith("--") for line in lines)


def run_query(conn, name, **params):
    """Run store/queries/<name>.sql with named parameters and return the rows."""
    if not is_written(name):
        raise NotImplementedError(f"store/queries/{name}.sql is not written yet")
    return conn.execute(query_text(name), params).fetchall()
