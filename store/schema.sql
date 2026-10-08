-- Results store (SQLite). One row per build, run, test result and defect.

CREATE TABLE builds (
    id          INTEGER PRIMARY KEY,
    version     TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE requirements (
    id        TEXT PRIMARY KEY,              -- DIAG-01, NET-01, SEC-01
    category  TEXT NOT NULL CHECK (category IN ('DIAG', 'NET', 'SEC')),
    text      TEXT NOT NULL
);

CREATE TABLE test_runs (
    id          INTEGER PRIMARY KEY,
    build_id    INTEGER NOT NULL REFERENCES builds(id),
    started_at  TEXT NOT NULL
);

CREATE TABLE test_results (
    run_id          INTEGER NOT NULL REFERENCES test_runs(id),
    test_id         TEXT NOT NULL,
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    outcome         TEXT NOT NULL CHECK (outcome IN ('pass', 'fail', 'blocked', 'not_run')),
    duration_ms     INTEGER,
    trace_path      TEXT,
    PRIMARY KEY (run_id, test_id)
);

CREATE TABLE defects (
    id              TEXT PRIMARY KEY,        -- DEF-001
    build_id        INTEGER NOT NULL REFERENCES builds(id),
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    severity        TEXT NOT NULL CHECK (severity IN ('critical', 'major', 'minor')),
    status          TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'fixed', 'retest', 'closed', 'reopened')),
    summary         TEXT NOT NULL,
    root_cause      TEXT,
    trace_path      TEXT
);

CREATE INDEX idx_results_requirement ON test_results(requirement_id);
CREATE INDEX idx_defects_build ON defects(build_id, severity, status);
