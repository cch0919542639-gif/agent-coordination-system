from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional


SCHEMA_VERSION = 1


class MigrationError(Exception):
    pass


def get_db_path() -> str:
    import os

    return os.environ.get("COORDINATION_DB_PATH", "coordination.db")


def create_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    path = db_path or get_db_path()
    with closing(create_connection(path)) as conn:
        yield conn


def run_migrations(db_path: Optional[str] = None) -> None:
    path = db_path or get_db_path()
    with closing(create_connection(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        cursor = conn.execute("SELECT COALESCE(MAX(version), 0) FROM _migrations")
        current = cursor.fetchone()[0]

        for version in range(current + 1, SCHEMA_VERSION + 1):
            migration = _get_migration(version)
            migration(conn)
            conn.execute(
                "INSERT INTO _migrations (version, applied_at) VALUES (?, ?)",
                (version, _now()),
            )
        conn.commit()


def _get_migration(version: int):
    migrations = {1: _migration_v1}
    fn = migrations.get(version)
    if fn is None:
        raise MigrationError(f"Unknown migration version {version}")
    return fn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migration_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agents (
            agent_id   TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS phases (
            phase_id       TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            objective      TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'planning',
            entry_criteria TEXT NOT NULL DEFAULT '[]',
            exit_criteria  TEXT NOT NULL DEFAULT '[]',
            frozen_spec_ref TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            task_id            TEXT PRIMARY KEY,
            phase_id           TEXT NOT NULL,
            title              TEXT NOT NULL DEFAULT '',
            objective          TEXT NOT NULL DEFAULT '',
            description        TEXT NOT NULL DEFAULT '',
            priority           TEXT NOT NULL DEFAULT 'medium',
            status             TEXT NOT NULL DEFAULT 'draft',
            allowed_scope      TEXT NOT NULL DEFAULT '[]',
            forbidden_scope    TEXT NOT NULL DEFAULT '[]',
            dependencies       TEXT NOT NULL DEFAULT '[]',
            acceptance_criteria TEXT NOT NULL DEFAULT '[]',
            expected_artifacts TEXT NOT NULL DEFAULT '[]',
            created_at         TEXT NOT NULL,
            updated_at         TEXT NOT NULL,
            FOREIGN KEY (phase_id) REFERENCES phases(phase_id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id      TEXT PRIMARY KEY,
            task_id            TEXT NOT NULL,
            agent_id           TEXT NOT NULL,
            assigned_at        TEXT NOT NULL,
            assignment_reason  TEXT NOT NULL DEFAULT '',
            closed_at          TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id),
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS task_events (
            event_id   TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id   TEXT NOT NULL,
            payload    TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id        TEXT PRIMARY KEY,
            task_id            TEXT NOT NULL,
            agent_id           TEXT NOT NULL,
            severity           TEXT NOT NULL,
            category           TEXT NOT NULL DEFAULT '',
            summary            TEXT NOT NULL DEFAULT '',
            details            TEXT NOT NULL DEFAULT '',
            proposed_resolution TEXT NOT NULL DEFAULT '',
            status             TEXT NOT NULL DEFAULT 'open',
            resolved_at        TEXT,
            resolution_summary TEXT NOT NULL DEFAULT '',
            resolver_id        TEXT NOT NULL DEFAULT '',
            created_at         TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id),
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            review_id        TEXT PRIMARY KEY,
            task_id          TEXT NOT NULL,
            reviewer_id      TEXT NOT NULL,
            decision         TEXT NOT NULL,
            summary          TEXT NOT NULL DEFAULT '',
            findings         TEXT NOT NULL DEFAULT '[]',
            required_changes TEXT NOT NULL DEFAULT '[]',
            created_at       TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id  TEXT PRIMARY KEY,
            task_id      TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            path_or_url  TEXT NOT NULL DEFAULT '',
            repo_ref     TEXT NOT NULL DEFAULT '',
            commit_hash  TEXT NOT NULL DEFAULT '',
            created_at   TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );
        """
    )
