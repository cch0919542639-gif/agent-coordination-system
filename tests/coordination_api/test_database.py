import os
import tempfile

import pytest

from services.coordination_api.database import (
    SCHEMA_VERSION,
    create_connection,
    get_db_path,
    run_migrations,
)


@pytest.fixture
def db_path() -> str:
    tmp = tempfile.mktemp(suffix=".db")
    yield tmp
    try:
        os.remove(tmp)
    except PermissionError:
        pass


class TestSchemaInit:
    def test_migrations_run_on_fresh_db(self, db_path: str) -> None:
        run_migrations(db_path)
        conn = create_connection(db_path)
        cursor = conn.execute("SELECT COALESCE(MAX(version), 0) FROM _migrations")
        assert cursor.fetchone()[0] == SCHEMA_VERSION

    def test_all_tables_exist_after_migration(self, db_path: str) -> None:
        run_migrations(db_path)
        conn = create_connection(db_path)
        expected = [
            "agents",
            "phases",
            "tasks",
            "assignments",
            "task_events",
            "incidents",
            "reviews",
            "artifacts",
        ]
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_migrations' AND name NOT LIKE 'sqlite_%'"
        )
        actual = {row["name"] for row in cursor.fetchall()}
        for table in expected:
            assert table in actual, f"Missing table: {table}"

    def test_migrations_idempotent(self, db_path: str) -> None:
        run_migrations(db_path)
        run_migrations(db_path)
        run_migrations(db_path)
        conn = create_connection(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM _migrations")
        assert cursor.fetchone()[0] == SCHEMA_VERSION

    def test_schema_version_constant(self, db_path: str) -> None:
        run_migrations(db_path)
        conn = create_connection(db_path)
        cursor = conn.execute("SELECT MAX(version) FROM _migrations")
        assert cursor.fetchone()[0] == SCHEMA_VERSION

    def test_default_db_path(self) -> None:
        path = get_db_path()
        assert isinstance(path, str)
        assert len(path) > 0
        assert path == "coordination.db"

    def test_empty_tables_after_fresh_migration(self, db_path: str) -> None:
        run_migrations(db_path)
        conn = create_connection(db_path)
        tables = ["agents", "phases", "tasks", "assignments", "task_events", "incidents", "reviews", "artifacts"]
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            assert cursor.fetchone()[0] == 0, f"Table {table} should be empty"

    def test_migration_tracks_version(self, db_path: str) -> None:
        run_migrations(db_path)
        conn = create_connection(db_path)
        cursor = conn.execute("SELECT version, applied_at FROM _migrations ORDER BY version")
        rows = cursor.fetchall()
        assert len(rows) == SCHEMA_VERSION
        for i, row in enumerate(rows):
            assert row["version"] == i + 1
            assert row["applied_at"] is not None
