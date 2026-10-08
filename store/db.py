"""SQLite results store: create schema, record runs, run the named queries."""

from pathlib import Path

SCHEMA = Path(__file__).parent / "schema.sql"
QUERIES = Path(__file__).parent / "queries"


def connect(path):
    # TODO: open with sqlite3, enable foreign keys, apply schema on first use
    raise NotImplementedError


def record_run(conn, build_version, results, defects):
    raise NotImplementedError


def run_query(conn, name, **params):
    # TODO: load queries/<name>.sql and execute with named parameters
    raise NotImplementedError
