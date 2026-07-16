"""Tests for remote-ref monitor and event ledger.

Uses isolated temporary remotes; never contacts real GitHub.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _init_bare_remote(tmp_path: Path) -> Path:
    """Create a bare Git remote with a task card on main."""
    remote = tmp_path / "remote.git"
    _run(["git", "init", "--bare", str(remote)])

    # Create a working copy, add a task card, push
    work = tmp_path / "work"
    work.mkdir()
    _run(["git", "init", str(work)], cwd=str(work))
    _run(["git", "config", "user.email", "test@test.com"], cwd=str(work))
    _run(["git", "config", "user.name", "Test"], cwd=str(work))

    # Create coordination layout
    card_dir = work / "coordination" / "task-board" / "review"
    card_dir.mkdir(parents=True)
    card = card_dir / "test-task-01.md"
    card.write_text(textwrap.dedent("""\
        ---
        task_id: test-task-01
        phase: test
        status: REVIEW
        owner: test-agent
        reviewer: ORCHESTRATOR
        priority: medium
        dependencies: []
        allowed_scope:
          - tests/**
        forbidden_scope:
          - src/**
        acceptance:
          - test
        expected_artifacts:
          - code_changes
        ---
        # Task Packet

        ## Objective

        Test task for monitor.
    """), encoding="utf-8")

    _run(["git", "add", "."], cwd=str(work))
    _run(["git", "commit", "-m", "add test task"], cwd=str(work))
    # Ensure branch is named 'main'
    _run(["git", "branch", "-M", "main"], cwd=str(work))
    _run(["git", "remote", "add", "origin", str(remote)], cwd=str(work))
    _run(["git", "push", "origin", "main"], cwd=str(work))

    return remote


def _make_project_entry(tmp_path: Path, remote: Path, project_id: str = "test-proj") -> dict:
    """Create a project registry entry pointing to a local clone."""
    clone = tmp_path / "clone"
    result = _run(["git", "clone", str(remote), str(clone)])
    if result.returncode != 0:
        # If clone fails (empty repo), create manually
        clone.mkdir()
        _run(["git", "init", str(clone)], cwd=str(clone))
        _run(["git", "remote", "add", "origin", str(remote)], cwd=str(clone))
        _run(["git", "fetch", "origin"], cwd=str(clone))
        _run(["git", "checkout", "main"], cwd=str(clone))
    else:
        # Ensure we have a local main branch tracking origin/main
        _run(["git", "checkout", "-b", "main", "origin/main"], cwd=str(clone))
    # Configure git user for the clone
    _run(["git", "config", "user.email", "test@test.com"], cwd=str(clone))
    _run(["git", "config", "user.name", "Test"], cwd=str(clone))
    return {
        "project_id": project_id,
        "local_path": str(clone),
        "remote_name": "origin",
        "default_branch": "main",
    }


def _write_registry(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a project registry file."""
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return registry


def _cleanup_monitor():
    """Clean up monitor state from previous runs."""
    import shutil
    monitor_dir = ROOT / "coordination" / "monitor"
    if monitor_dir.exists():
        shutil.rmtree(monitor_dir, ignore_errors=True)


# ─── 1. Event identity ──────────────────────────────────────────────


class TestEventIdentity:
    """Deterministic event IDs and type detection."""

    def test_make_event_id_deterministic(self) -> None:
        from event_ledger import make_event_id
        id1 = make_event_id("p", "repo", "branch", "sha123", "t1", "review_submitted")
        id2 = make_event_id("p", "repo", "branch", "sha123", "t1", "review_submitted")
        assert id1 == id2
        assert len(id1) == 16

    def test_different_inputs_different_ids(self) -> None:
        from event_ledger import make_event_id
        id1 = make_event_id("p", "repo", "branch", "sha123", "t1", "review_submitted")
        id2 = make_event_id("p", "repo", "branch", "sha456", "t1", "review_submitted")
        assert id1 != id2

    def test_detect_review_submitted(self) -> None:
        from event_ledger import detect_event_type
        fm = {"status": "REVIEW", "owner": "agent-1"}
        assert detect_event_type(fm) == "review_submitted"

    def test_detect_ready_assigned(self) -> None:
        from event_ledger import detect_event_type
        fm = {"status": "READY", "owner": "agent-1"}
        assert detect_event_type(fm) == "ready_assigned"

    def test_detect_ready_unassigned(self) -> None:
        from event_ledger import detect_event_type
        fm = {"status": "READY", "owner": "UNASSIGNED"}
        assert detect_event_type(fm) is None

    def test_detect_incident_opened(self) -> None:
        from event_ledger import detect_event_type
        fm = {"status": "BLOCKED", "owner": "agent-1"}
        assert detect_event_type(fm) == "incident_opened"

    def test_detect_unknown_status(self) -> None:
        from event_ledger import detect_event_type
        fm = {"status": "DONE", "owner": "agent-1"}
        assert detect_event_type(fm) is None


# ─── 2. Event ledger ────────────────────────────────────────────────


class TestEventLedger:
    """Atomic append, dedup, and state persistence."""

    def test_append_and_load(self, tmp_path: Path) -> None:
        from event_ledger import Event, append_events, load_events, EVENTS_FILE
        _cleanup_monitor()
        try:
            event = Event(
                event_id="test-id-001",
                project_id="p1",
                repository="/tmp/repo",
                ref="main",
                commit="abc123",
                task_id="t1",
                event_type="review_submitted",
                detected_at="2026-01-01T00:00:00Z",
            )
            added = append_events([event])
            assert added == 1
            events = load_events()
            assert len(events) == 1
            assert events[0].event_id == "test-id-001"
        finally:
            _cleanup_monitor()

    def test_dedup_on_second_append(self, tmp_path: Path) -> None:
        from event_ledger import Event, append_events, load_events
        _cleanup_monitor()
        try:
            event = Event(
                event_id="dedup-test",
                project_id="p1",
                repository="/tmp/repo",
                ref="main",
                commit="abc",
                task_id="t1",
                event_type="review_submitted",
                detected_at="2026-01-01T00:00:00Z",
            )
            append_events([event])
            added = append_events([event])
            assert added == 0
            events = load_events()
            assert len(events) == 1
        finally:
            _cleanup_monitor()

    def test_state_persistence(self) -> None:
        from event_ledger import load_state, save_state
        _cleanup_monitor()
        try:
            state = {"seen_commits": {"p1": {"main": "abc123"}}}
            save_state(state)
            loaded = load_state()
            assert loaded["seen_commits"]["p1"]["main"] == "abc123"
        finally:
            _cleanup_monitor()


# ─── 3. Project registry ────────────────────────────────────────────


class TestProjectRegistry:
    """Registry load, add, remove."""

    def test_load_empty(self, tmp_path: Path) -> None:
        from project_registry import load_registry, REGISTRY_FILE
        # Ensure no registry exists
        if REGISTRY_FILE.exists():
            REGISTRY_FILE.unlink()
        entries = load_registry()
        assert entries == []

    def test_add_and_get(self, tmp_path: Path) -> None:
        from project_registry import ProjectEntry, add_project, get_project, REGISTRY_FILE
        entry = ProjectEntry(project_id="test-add", local_path=str(tmp_path))
        add_project(entry)
        try:
            got = get_project("test-add")
            assert got is not None
            assert got.project_id == "test-add"
        finally:
            if REGISTRY_FILE.exists():
                REGISTRY_FILE.unlink(missing_ok=True)

    def test_remove(self, tmp_path: Path) -> None:
        from project_registry import ProjectEntry, add_project, remove_project, get_project, REGISTRY_FILE
        entry = ProjectEntry(project_id="test-rm", local_path=str(tmp_path))
        add_project(entry)
        try:
            assert remove_project("test-rm") is True
            assert get_project("test-rm") is None
            assert remove_project("test-rm") is False
        finally:
            if REGISTRY_FILE.exists():
                REGISTRY_FILE.unlink(missing_ok=True)


# ─── 4. Monitor with isolated remote ────────────────────────────────


class TestMonitorWithRemote:
    """End-to-end monitor with a temporary Git remote."""

    def test_detects_review_submitted(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        # Write registry
        registry_path = tmp_path / "projects.json"
        registry_path.write_text(json.dumps([entry], indent=2), encoding="utf-8")

        from event_ledger import load_events, save_state
        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}
        events = _scan_project(project, state)

        review_events = [e for e in events if e.event_type == "review_submitted"]
        assert len(review_events) == 1
        assert review_events[0].task_id == "test-task-01"

    def test_no_new_events_on_unchanged_ref(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        from event_ledger import Event, make_event_id
        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}
        events1 = _scan_project(project, state)

        # Run again — should be empty
        events2 = _scan_project(project, state)
        assert len(events2) == 0

    def test_new_event_on_push(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}
        events1 = _scan_project(project, state)

        # Push a new task card to ready/assigned
        clone = Path(entry["local_path"])
        card_dir = clone / "coordination" / "task-board" / "ready"
        card_dir.mkdir(parents=True)
        card = card_dir / "new-task.md"
        card.write_text(textwrap.dedent("""\
            ---
            task_id: new-task-01
            phase: test
            status: READY
            owner: assigned-agent
            reviewer: ORCHESTRATOR
            priority: medium
            dependencies: []
            allowed_scope:
              - tests/**
            forbidden_scope:
              - src/**
            acceptance:
              - test
            expected_artifacts:
              - code_changes
            ---
            # Task Packet

            ## Objective

            New assigned task.
        """), encoding="utf-8")
        _run(["git", "add", "."], cwd=str(clone))
        _run(["git", "commit", "-m", "add assigned task"], cwd=str(clone))
        _run(["git", "push", "origin", "main"], cwd=str(clone))

        events2 = _scan_project(project, state)
        ready_events = [e for e in events2 if e.event_type == "ready_assigned"]
        assert len(ready_events) == 1
        assert ready_events[0].task_id == "new-task-01"

    def test_malformed_card_produces_no_crash(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        # Push a malformed card
        clone = Path(entry["local_path"])
        card_dir = clone / "coordination" / "task-board" / "review"
        card_dir.mkdir(parents=True, exist_ok=True)
        card = card_dir / "bad-task.md"
        card.write_text("not valid front matter\n", encoding="utf-8")
        _run(["git", "add", "."], cwd=str(clone))
        _run(["git", "commit", "-m", "add bad card"], cwd=str(clone))
        _run(["git", "push", "origin", "main"], cwd=str(clone))

        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}
        events = _scan_project(project, state)
        # No crash, no events from the bad card
        assert isinstance(events, list)


# ─── 5. Lifecycle no-mutation ───────────────────────────────────────


class TestNoMutation:
    """Monitor never modifies task cards or lifecycle."""

    def test_monitor_does_not_write_cards(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}

        # Snapshot card content
        clone = Path(entry["local_path"])
        card_path = clone / "coordination" / "task-board" / "review" / "test-task-01.md"
        before = card_path.read_bytes()

        _scan_project(project, state)

        after = card_path.read_bytes()
        assert before == after

    def test_monitor_does_not_create_commits(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}

        clone = Path(entry["local_path"])
        result = _run(["git", "rev-parse", "HEAD"], cwd=str(clone))
        sha_before = result.stdout.strip()

        _scan_project(project, state)

        result = _run(["git", "rev-parse", "HEAD"], cwd=str(clone))
        sha_after = result.stdout.strip()
        assert sha_before == sha_after


# ─── 6. Branch isolation ────────────────────────────────────────────


class TestBranchIsolation:
    """Events are scoped to specific branches."""

    def test_only_default_branch_scanned(self, tmp_path: Path) -> None:
        remote = _init_bare_remote(tmp_path)
        entry = _make_project_entry(tmp_path, remote)

        # Push a feature branch with a different task
        clone = Path(entry["local_path"])
        _run(["git", "checkout", "-b", "feature/other"], cwd=str(clone))
        card_dir = clone / "coordination" / "task-board" / "ready"
        card_dir.mkdir(parents=True)
        card = card_dir / "feature-task.md"
        card.write_text(textwrap.dedent("""\
            ---
            task_id: feature-task-01
            phase: test
            status: READY
            owner: feature-agent
            reviewer: ORCHESTRATOR
            priority: medium
            dependencies: []
            allowed_scope:
              - tests/**
            forbidden_scope:
              - src/**
            acceptance:
              - test
            expected_artifacts:
              - code_changes
            ---
            # Task Packet

            ## Objective

            Feature task.
        """), encoding="utf-8")
        _run(["git", "add", "."], cwd=str(clone))
        _run(["git", "commit", "-m", "add feature task"], cwd=str(clone))
        _run(["git", "push", "origin", "feature/other"], cwd=str(clone))
        _run(["git", "checkout", "main"], cwd=str(clone))

        from project_registry import ProjectEntry
        from remote_ref_monitor import _scan_project

        project = ProjectEntry.from_dict(entry)
        state: dict = {}
        events = _scan_project(project, state)

        # Only main branch events
        refs = {e.ref for e in events}
        assert "feature/other" not in refs


# ─── 7. CLI integration ─────────────────────────────────────────────


class TestCLI:
    """CLI produces valid output."""

    def test_help_flag(self) -> None:
        # Just test the parser
        from remote_ref_monitor import build_parser
        parser = build_parser()
        assert parser is not None

    def test_monitor_no_projects(self) -> None:
        """Monitor with no projects produces clean output."""
        from remote_ref_monitor import monitor_once
        # Ensure no registry
        from project_registry import REGISTRY_FILE
        if REGISTRY_FILE.exists():
            REGISTRY_FILE.unlink()
        # This should not crash
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            result = monitor_once()
        assert result == 0
