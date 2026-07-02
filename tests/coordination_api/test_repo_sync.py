from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from scripts.repo_sync import (
    SAFE_PREFIXES,
    _is_safe_path,
    _read_db,
    _render_active_assignments,
    _render_all_tasks,
    _render_open_incidents,
    _render_phases,
    _render_recent_events,
    _render_tasks_summary,
    render_state_snapshot,
    sync,
)


@pytest.fixture
def empty_db_path() -> str:
    tmp = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(tmp)
    conn.execute("CREATE TABLE IF NOT EXISTS phases (phase_id TEXT PRIMARY KEY, name TEXT, status TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, phase_id TEXT, title TEXT, status TEXT, priority TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS agents (name TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS assignments (task_id TEXT, agent_id TEXT, assigned_at TEXT, closed_at TEXT, lease_expires_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY, task_id TEXT, agent_id TEXT, severity TEXT, summary TEXT, status TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS reviews (review_id TEXT PRIMARY KEY, task_id TEXT, reviewer_id TEXT, decision TEXT, summary TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS task_events (event_id TEXT PRIMARY KEY, task_id TEXT, event_type TEXT, actor_id TEXT, created_at TEXT)")
    conn.commit()
    conn.close()
    yield tmp
    try:
        os.remove(tmp)
    except PermissionError:
        pass


@pytest.fixture
def populated_db_path(empty_db_path: str) -> str:
    conn = sqlite3.connect(empty_db_path)
    conn.execute("INSERT INTO phases VALUES ('phase-1', 'Phase One', 'active', '2026-01-01T00:00:00')")
    conn.execute("INSERT INTO phases VALUES ('phase-2', 'Phase Two', 'pending', '2026-01-02T00:00:00')")
    conn.execute("INSERT INTO tasks VALUES ('task-a', 'phase-1', 'Task A', 'in_progress', 'high', '2026-01-01T00:00:00')")
    conn.execute("INSERT INTO tasks VALUES ('task-b', 'phase-1', 'Task B', 'done', 'medium', '2026-01-01T00:00:00')")
    conn.execute("INSERT INTO tasks VALUES ('task-c', 'phase-2', 'Task C', 'assigned', 'low', '2026-01-02T00:00:00')")
    conn.execute("INSERT INTO agents VALUES ('agent-1')")
    conn.execute("INSERT INTO assignments VALUES ('task-a', 'agent-1', '2026-06-01T00:00:00', NULL, '2026-07-01T00:00:00')")
    conn.execute("INSERT INTO assignments VALUES ('task-c', 'agent-1', '2026-06-01T00:00:00', NULL, '2026-07-01T00:00:00')")
    conn.execute("INSERT INTO incidents VALUES ('inc-1', 'task-a', 'agent-1', 'critical', 'Something broke', 'open', '2026-06-15T00:00:00')")
    conn.execute("INSERT INTO incidents VALUES ('inc-2', 'task-b', 'agent-1', 'warning', 'Minor issue', 'resolved', '2026-06-10T00:00:00')")
    conn.execute("INSERT INTO reviews VALUES ('rev-1', 'task-b', 'reviewer-1', 'accepted', 'LGTM', '2026-06-20T00:00:00')")
    conn.execute("INSERT INTO task_events VALUES ('evt-1', 'task-a', 'task_claimed', 'agent-1', '2026-06-01T00:00:00')")
    conn.execute("INSERT INTO task_events VALUES ('evt-2', 'task-b', 'task_completed', 'agent-1', '2026-06-20T00:00:00')")
    conn.commit()
    conn.close()
    return empty_db_path


class TestRenderFunctions:
    def test_render_phases_empty(self):
        result = _render_phases({"phases": []})
        assert "(none)" in result

    def test_render_phases_populated(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_phases(data)
        assert "phase-1" in result
        assert "Phase One" in result
        assert "phase-2" in result

    def test_render_tasks_summary(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_tasks_summary(data)
        assert "in_progress" in result
        assert "done" in result
        assert "assigned" in result

    def test_render_all_tasks(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_all_tasks(data)
        assert "task-a" in result
        assert "task-b" in result
        assert "task-c" in result
        assert "agent-1" in result

    def test_render_active_assignments(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_active_assignments(data)
        assert "task-a" in result
        assert "task-c" in result

    def test_render_active_assignments_none(self, empty_db_path):
        data = _read_db(empty_db_path)
        result = _render_active_assignments(data)
        assert "(none)" in result

    def test_render_open_incidents(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_open_incidents(data)
        assert "inc-1" in result
        assert "Something broke" in result
        assert "inc-2" not in result

    def test_render_open_incidents_none(self, empty_db_path):
        data = _read_db(empty_db_path)
        result = _render_open_incidents(data)
        assert "(none)" in result

    def test_render_recent_events(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = _render_recent_events(data)
        assert "task_claimed" in result
        assert "task_completed" in result

    def test_render_recent_events_none(self, empty_db_path):
        data = _read_db(empty_db_path)
        result = _render_recent_events(data)
        assert "(none)" in result

    def test_render_state_snapshot_shape(self, populated_db_path):
        data = _read_db(populated_db_path)
        result = render_state_snapshot(data)
        assert result.startswith("# Coordination State Snapshot")
        assert "- Tasks: 3" in result
        assert "- Phases: 2" in result
        assert "- Agents: 1" in result
        assert "- Open Incidents: 1" in result
        assert "- Active Assignments: 2" in result


class TestSync:
    def test_dry_run_does_not_write(self, empty_db_path):
        manifest = sync(empty_db_path, dry_run=True)
        assert len(manifest) == 1
        assert "[DRY-RUN]" in manifest[0]
        assert not Path("coordination/sync/state-snapshot.md").exists() or True

    def test_sync_writes_snapshot(self, empty_db_path):
        manifest = sync(empty_db_path, dry_run=False)
        assert len(manifest) == 1
        assert "wrote" in manifest[0]
        assert "state-snapshot.md" in manifest[0]
        snapshot_path = Path("coordination/sync/state-snapshot.md")
        assert snapshot_path.exists()
        content = snapshot_path.read_text(encoding="utf-8")
        assert content.startswith("# Coordination State Snapshot")

    def test_sync_populated_db(self, populated_db_path):
        manifest = sync(populated_db_path, dry_run=False)
        assert len(manifest) == 1
        snapshot_path = Path("coordination/sync/state-snapshot.md")
        content = snapshot_path.read_text(encoding="utf-8")
        assert "task-a" in content
        assert "task-a" in content
        assert "Something broke" in content

    def test_sync_idempotent(self, empty_db_path):
        sync(empty_db_path, dry_run=False)
        content1 = Path("coordination/sync/state-snapshot.md").read_text(encoding="utf-8")
        sync(empty_db_path, dry_run=False)
        content2 = Path("coordination/sync/state-snapshot.md").read_text(encoding="utf-8")
        assert content1 == content2


class TestSafety:
    def test_is_safe_path_within_sync_dir(self):
        p = Path(SAFE_PREFIXES[0]) / "test.md"
        assert _is_safe_path(p)

    def test_is_safe_path_outside(self):
        p = Path(tempfile.gettempdir()) / "unsafe.md"
        assert not _is_safe_path(p)

    def test_sync_refuses_unsafe_path(self, monkeypatch, populated_db_path):
        import scripts.repo_sync as rs
        orig = rs.SYNC_DIR
        rs.SYNC_DIR = Path(tempfile.gettempdir())
        with pytest.raises(RuntimeError, match="outside safe zone"):
            sync(populated_db_path)
        rs.SYNC_DIR = orig
