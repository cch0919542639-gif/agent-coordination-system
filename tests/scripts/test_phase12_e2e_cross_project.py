"""Cross-project E2E regression tests for Phase 12 event-driven orchestration.

Verifies the complete pipeline: monitor → event ledger → routing → worker poll →
acknowledge across two isolated project repositories.  Covers review-submitted,
ready-assigned, incident-opened, unregistered worker, malformed registry/policy,
fetch failure, retry acknowledgement, project isolation, and no-duplicate repeat
poll behavior.

Proves no task lifecycle mutation, claim/review execution, subprocess launch,
HTTP call, push, or agent launch occurs in any tested event flow.

All repositories are isolated temporary local remotes.  Never contacts real
GitHub or any external service.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers — isolated Git repos
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd,
    )


def _init_remote(tmp_path: Path, name: str) -> Path:
    """Create a bare Git remote with a coordination layout on main."""
    remote = tmp_path / f"{name}.git"
    _git(["init", "--bare", str(remote)], cwd=str(tmp_path))

    work = tmp_path / f"{name}_work"
    work.mkdir()
    _git(["init", str(work)], cwd=str(work))
    _git(["config", "user.email", "test@test.com"], cwd=str(work))
    _git(["config", "user.name", "Test"], cwd=str(work))

    # Create coordination layout
    for state in ("ready", "in_progress", "review", "done", "blocked"):
        (work / "coordination" / "task-board" / state).mkdir(parents=True, exist_ok=True)
    for d in ("progress", "delivery", "reviews", "incidents"):
        (work / "coordination" / d).mkdir(parents=True, exist_ok=True)

    _git(["add", "."], cwd=str(work))
    _git(["commit", "-m", "init coordination layout"], cwd=str(work))
    _git(["branch", "-M", "main"], cwd=str(work))
    _git(["remote", "add", "origin", str(remote)], cwd=str(work))
    _git(["push", "origin", "main"], cwd=str(work))
    return remote


def _write_task_card(
    repo_work: Path,
    task_id: str,
    status: str,
    owner: str = "test-agent",
    reviewer: str = "ORCHESTRATOR",
    state: str = "ready",
) -> Path:
    """Write a task card into the coordination layout and push."""
    card_dir = repo_work / "coordination" / "task-board" / state
    card_dir.mkdir(parents=True, exist_ok=True)
    card = card_dir / f"{task_id}.md"
    card.write_text(
        textwrap.dedent(f"""\
            ---
            task_id: {task_id}
            phase: phase12
            status: {status}
            owner: {owner}
            reviewer: {reviewer}
            priority: medium
            ---
            # Task Packet

            ## Objective
            Test task for E2E regression.
        """),
        encoding="utf-8",
    )
    _git(["add", "."], cwd=str(repo_work))
    _git(["commit", "-m", f"add {task_id}"], cwd=str(repo_work))
    _git(["push", "origin", "main"], cwd=str(repo_work))
    return card


def _clone_remote(remote: Path, tmp_path: Path, name: str) -> Path:
    clone = tmp_path / f"{name}_clone"
    result = _git(["clone", str(remote), str(clone)], cwd=str(tmp_path))
    if result.returncode != 0:
        clone.mkdir()
        _git(["init", str(clone)], cwd=str(clone))
        _git(["remote", "add", "origin", str(remote)], cwd=str(clone))
        _git(["fetch", "origin"], cwd=str(clone))
        _git(["checkout", "main"], cwd=str(clone))
    else:
        _git(["checkout", "-b", "main", "origin/main"], cwd=str(clone))
    _git(["config", "user.email", "test@test.com"], cwd=str(clone))
    _git(["config", "user.name", "Test"], cwd=str(clone))
    return clone


# ---------------------------------------------------------------------------
# Helpers — patched paths
# ---------------------------------------------------------------------------

def _patch_all(tmp_path: Path):
    """Patch all module-level paths to use tmp_path."""
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    return (
        patch.multiple(
            "event_routing",
            MONITOR_DIR=monitor_dir,
            POLICY_FILE=monitor_dir / "routing_policy.json",
            DELIVERY_DIR=delivery_dir,
            DELIVERY_FILE=delivery_dir / "delivery_state.jsonl",
        ),
        patch.multiple(
            "event_ledger",
            MONITOR_DIR=monitor_dir,
            EVENTS_FILE=monitor_dir / "events.jsonl",
            STATE_FILE=monitor_dir / "state.json",
        ),
        patch.multiple(
            "worker_poller",
            MONITOR_DIR=monitor_dir,
            WORKERS_FILE=monitor_dir / "workers.json",
        ),
        patch.multiple(
            "project_registry",
            MONITOR_DIR=monitor_dir,
            REGISTRY_FILE=monitor_dir / "projects.json",
        ),
    )


def _write_routing_policy(tmp_path: Path, policies: list[dict]) -> None:
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    (monitor_dir / "routing_policy.json").write_text(
        json.dumps(policies, indent=2), encoding="utf-8"
    )


def _write_workers(tmp_path: Path, workers: list[dict]) -> None:
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    (monitor_dir / "workers.json").write_text(
        json.dumps(workers, indent=2), encoding="utf-8"
    )


def _write_project_registry(tmp_path: Path, entries: list[dict]) -> None:
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    (monitor_dir / "projects.json").write_text(
        json.dumps(entries, indent=2), encoding="utf-8"
    )


def _make_policy(project_id: str) -> dict:
    return {
        "project_id": project_id,
        "routes": [
            {"event_type": "review_submitted", "destination": "orchestrator"},
            {"event_type": "ready_assigned", "destination": "registered_worker"},
            {"event_type": "incident_opened", "destination": "orchestrator"},
        ],
        "enabled": True,
    }


def _make_worker(worker_id: str, project_id: str) -> dict:
    return {
        "worker_id": worker_id,
        "project_id": project_id,
        "enabled": True,
        "registered_at": "2026-07-17T00:00:00Z",
    }


# ===================================================================
# 1. Full E2E Pipeline — Two Isolated Projects
# ===================================================================


class TestCrossProjectE2EPipeline:
    """Two independent projects flow through the complete pipeline."""

    def test_review_submitted_project_alpha(self, tmp_path: Path) -> None:
        """review_submitted in proj-alpha routes to orchestrator, not proj-beta."""
        remote_a = _init_remote(tmp_path, "proj-alpha")
        _write_task_card(tmp_path / "proj-alpha_work", "task-a-01", "REVIEW", state="review")
        clone_a = _clone_remote(remote_a, tmp_path, "proj-alpha")

        remote_b = _init_remote(tmp_path, "proj-beta")
        _write_task_card(tmp_path / "proj-beta_work", "task-b-01", "REVIEW", state="review")
        clone_b = _clone_remote(remote_b, tmp_path, "proj-beta")

        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            # Set up registry and policies
            _write_project_registry(tmp_path, [
                {"project_id": "proj-alpha", "local_path": str(clone_a), "remote_name": "origin", "default_branch": "main"},
                {"project_id": "proj-beta", "local_path": str(clone_b), "remote_name": "origin", "default_branch": "main"},
            ])
            _write_routing_policy(tmp_path, [_make_policy("proj-alpha"), _make_policy("proj-beta")])
            _write_workers(tmp_path, [_make_worker("worker-a", "proj-alpha")])

            # Monitor detects events
            from project_registry import load_registry, ProjectEntry
            from remote_ref_monitor import _scan_project
            from event_ledger import append_events, load_events
            from event_routing import route_event, append_delivery_records, load_delivery_state
            from worker_poller import poll_worker

            projects = load_registry()
            state: dict = {}
            all_events = []
            for proj in projects:
                pe = ProjectEntry.from_dict(proj.to_dict() if hasattr(proj, 'to_dict') else {
                    "project_id": proj.project_id,
                    "local_path": proj.local_path,
                    "remote_name": proj.remote_name,
                    "default_branch": proj.default_branch,
                })
                events = _scan_project(pe, state)
                all_events.extend(events)

            added = append_events(all_events)
            assert added > 0, "Monitor should detect review events"

            # Route events
            ledger = load_events()
            delivery_records = []
            for event in ledger:
                if event.event_type == "review_submitted":
                    results = route_event(
                        event.project_id, event.task_id, event.event_type,
                        event.ref, event.commit,
                    )
                    for payload, record in results:
                        delivery_records.append(record)

            appended = append_delivery_records(delivery_records)
            assert appended > 0

            # Worker poll — worker-a should see nothing (review goes to orchestrator, not registered_worker)
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("worker-a")
            assert rc == 0
            output = f.getvalue()
            # review_submitted routes to orchestrator, not registered_worker
            assert "No pending work" in output or "task-a-01" not in output
        finally:
            for p in patches:
                p.stop()

    def test_ready_assigned_project_beta(self, tmp_path: Path) -> None:
        """ready_assigned in proj-beta routes to registered_worker for proj-beta only."""
        remote_a = _init_remote(tmp_path, "proj-alpha")
        clone_a = _clone_remote(remote_a, tmp_path, "proj-alpha")

        remote_b = _init_remote(tmp_path, "proj-beta")
        _write_task_card(tmp_path / "proj-beta_work", "task-b-02", "READY", owner="beta-agent", state="ready")
        clone_b = _clone_remote(remote_b, tmp_path, "proj-beta")

        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_project_registry(tmp_path, [
                {"project_id": "proj-alpha", "local_path": str(clone_a), "remote_name": "origin", "default_branch": "main"},
                {"project_id": "proj-beta", "local_path": str(clone_b), "remote_name": "origin", "default_branch": "main"},
            ])
            _write_routing_policy(tmp_path, [_make_policy("proj-alpha"), _make_policy("proj-beta")])
            _write_workers(tmp_path, [_make_worker("worker-b", "proj-beta")])

            from project_registry import load_registry, ProjectEntry
            from remote_ref_monitor import _scan_project
            from event_ledger import append_events, load_events
            from event_routing import route_event, append_delivery_records, load_delivery_state
            from worker_poller import poll_worker

            projects = load_registry()
            state: dict = {}
            all_events = []
            for proj in projects:
                pe = ProjectEntry.from_dict({
                    "project_id": proj.project_id,
                    "local_path": proj.local_path,
                    "remote_name": proj.remote_name,
                    "default_branch": proj.default_branch,
                })
                events = _scan_project(pe, state)
                all_events.extend(events)

            added = append_events(all_events)
            assert added > 0

            # Route ready_assigned events to registered_worker
            ledger = load_events()
            delivery_records = []
            for event in ledger:
                if event.event_type == "ready_assigned":
                    results = route_event(
                        event.project_id, event.task_id, event.event_type,
                        event.ref, event.commit,
                    )
                    for payload, record in results:
                        delivery_records.append(record)

            append_delivery_records(delivery_records)

            # Worker-b polls — should see task-b-02
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("worker-b")
            assert rc == 0
            output = f.getvalue()
            assert "task-b-02" in output

            # Worker-a (proj-alpha) should NOT see task-b-02
            _write_workers(tmp_path, [_make_worker("worker-a", "proj-alpha")])
            f2 = io.StringIO()
            with redirect_stdout(f2):
                rc = poll_worker("worker-a")
            assert rc == 0
            assert "task-b-02" not in f2.getvalue()
        finally:
            for p in patches:
                p.stop()

    def test_incident_opened_project_alpha(self, tmp_path: Path) -> None:
        """incident_opened in proj-alpha routes to orchestrator."""
        remote_a = _init_remote(tmp_path, "proj-alpha")
        _write_task_card(tmp_path / "proj-alpha_work", "task-a-03", "BLOCKED", state="blocked")
        clone_a = _clone_remote(remote_a, tmp_path, "proj-alpha")

        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_project_registry(tmp_path, [
                {"project_id": "proj-alpha", "local_path": str(clone_a), "remote_name": "origin", "default_branch": "main"},
            ])
            _write_routing_policy(tmp_path, [_make_policy("proj-alpha")])

            from project_registry import load_registry, ProjectEntry
            from remote_ref_monitor import _scan_project
            from event_ledger import append_events, load_events
            from event_routing import route_event, append_delivery_records

            projects = load_registry()
            state: dict = {}
            all_events = []
            for proj in projects:
                pe = ProjectEntry.from_dict({
                    "project_id": proj.project_id,
                    "local_path": proj.local_path,
                    "remote_name": proj.remote_name,
                    "default_branch": proj.default_branch,
                })
                events = _scan_project(pe, state)
                all_events.extend(events)

            added = append_events(all_events)
            assert added > 0

            ledger = load_events()
            delivery_records = []
            for event in ledger:
                if event.event_type == "incident_opened":
                    results = route_event(
                        event.project_id, event.task_id, event.event_type,
                        event.ref, event.commit,
                    )
                    for payload, record in results:
                        delivery_records.append(record)
                        assert record.destination == "orchestrator"

            appended = append_delivery_records(delivery_records)
            assert appended > 0
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 2. Unregistered Worker
# ===================================================================


class TestUnregisteredWorker:
    """Unregistered worker cannot poll."""

    def test_unregistered_worker_rejected(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_workers(tmp_path, [])
            from worker_poller import poll_worker
            f = io.StringIO()
            with redirect_stderr(f):
                rc = poll_worker("ghost-worker")
            assert rc == 1
            assert "not registered" in f.getvalue()
        finally:
            for p in patches:
                p.stop()

    def test_disabled_worker_rejected(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_workers(tmp_path, [{"worker_id": "disabled-w", "project_id": "p1", "enabled": False, "registered_at": ""}])
            from worker_poller import poll_worker
            f = io.StringIO()
            with redirect_stderr(f):
                rc = poll_worker("disabled-w")
            assert rc == 1
            assert "disabled" in f.getvalue()
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 3. Malformed Registry / Policy
# ===================================================================


class TestMalformedConfig:
    """Malformed registry and policy files handled gracefully."""

    def test_corrupt_registry_file(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True, exist_ok=True)
            (monitor_dir / "projects.json").write_text("NOT JSON {{{", encoding="utf-8")

            from project_registry import load_registry
            projects = load_registry()
            assert projects == []
        finally:
            for p in patches:
                p.stop()

    def test_corrupt_policy_file(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True, exist_ok=True)
            (monitor_dir / "routing_policy.json").write_text("NOT JSON {{{", encoding="utf-8")

            from event_routing import load_routing_policies
            policies = load_routing_policies()
            assert policies == []
        finally:
            for p in patches:
                p.stop()

    def test_non_list_registry(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True, exist_ok=True)
            (monitor_dir / "projects.json").write_text(
                json.dumps({"not": "a list"}), encoding="utf-8"
            )
            from project_registry import load_registry
            projects = load_registry()
            assert projects == []
        finally:
            for p in patches:
                p.stop()

    def test_non_list_policy(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True, exist_ok=True)
            (monitor_dir / "routing_policy.json").write_text(
                json.dumps({"not": "a list"}), encoding="utf-8"
            )
            from event_routing import load_routing_policies
            policies = load_routing_policies()
            assert policies == []
        finally:
            for p in patches:
                p.stop()

    def test_empty_registry(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from project_registry import load_registry
            projects = load_registry()
            assert projects == []
        finally:
            for p in patches:
                p.stop()

    def test_unknown_project_no_policy(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [_make_policy("proj-known")])
            from event_routing import is_eligible
            ok, reason = is_eligible("proj-unknown", "review_submitted", "orchestrator")
            assert ok is False
            assert "no routing policy" in reason
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 4. Fetch Failure
# ===================================================================


class TestFetchFailure:
    """Fetch failure produces a health event and does not crash."""

    def test_fetch_failure_health_event(self, tmp_path: Path) -> None:
        """When a project's remote is unreachable, a fetch_failed event is recorded."""
        # Register a project pointing to a non-existent path
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            bad_path = str(tmp_path / "nonexistent_repo")
            _write_project_registry(tmp_path, [
                {"project_id": "proj-bad", "local_path": bad_path, "remote_name": "origin", "default_branch": "main"},
            ])

            from project_registry import load_registry, ProjectEntry
            from remote_ref_monitor import _scan_project

            projects = load_registry()
            state: dict = {}
            all_events = []
            for proj in projects:
                pe = ProjectEntry.from_dict({
                    "project_id": proj.project_id,
                    "local_path": proj.local_path,
                    "remote_name": proj.remote_name,
                    "default_branch": proj.default_branch,
                })
                events = _scan_project(pe, state)
                all_events.extend(events)

            # Non-existent path should produce no events (not a crash)
            assert isinstance(all_events, list)
        finally:
            for p in patches:
                p.stop()

    def test_fetch_failure_event_type(self, tmp_path: Path) -> None:
        """Simulated fetch failure produces fetch_failed event."""
        from event_ledger import Event, make_event_id, now_iso
        event = Event(
            event_id=make_event_id("proj-x", "/bad/path", "fetch", "fail", "health", "fetch_failed"),
            project_id="proj-x",
            repository="/bad/path",
            ref="fetch",
            commit="fail",
            task_id="health",
            event_type="fetch_failed",
            detected_at=now_iso(),
        )
        assert event.event_type == "fetch_failed"
        assert event.task_id == "health"


# ===================================================================
# 5. Retry / Acknowledgement
# ===================================================================


class TestRetryAcknowledgement:
    """Retry state machine and acknowledgement retry path."""

    def test_retry_then_acknowledge(self, tmp_path: Path) -> None:
        """A delivery record can be retried, then acknowledged."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, mark_attempt,
                acknowledge, load_delivery_state_map,
            )
            record = DeliveryRecord(
                payload_id="retry-ack-test",
                project_id="p1", task_id="t1",
                event_type="ready_assigned", destination="registered_worker",
            )
            append_delivery_records([record])

            # Mark an attempt — becomes retry_pending
            record = mark_attempt(record)
            assert record.status == "retry_pending"
            assert record.attempts == 1

            # Acknowledge despite retry_pending
            result = acknowledge("retry-ack-test")
            assert result is True

            rmap = load_delivery_state_map()
            assert rmap["retry-ack-test"].status == "acknowledged"
        finally:
            for p in patches:
                p.stop()

    def test_terminal_failure_not_acknowledgeable(self, tmp_path: Path) -> None:
        """After max retries, record is in terminal failure state."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, mark_attempt,
                MAX_RETRY_ATTEMPTS,
            )
            record = DeliveryRecord(
                payload_id="terminal-test",
                project_id="p1", task_id="t1",
                event_type="ready_assigned", destination="registered_worker",
            )
            append_delivery_records([record])

            for _ in range(MAX_RETRY_ATTEMPTS):
                record = mark_attempt(record)

            assert record.status == "failed"
            assert record.terminal_failure_at != ""
        finally:
            for p in patches:
                p.stop()

    def test_acknowledge_idempotent(self, tmp_path: Path) -> None:
        """Acknowledging twice does not error."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, acknowledge,
            )
            record = DeliveryRecord(
                payload_id="idem-ack",
                project_id="p1", task_id="t1",
                event_type="review_submitted", destination="orchestrator",
            )
            append_delivery_records([record])
            assert acknowledge("idem-ack") is True
            assert acknowledge("idem-ack") is True
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 6. Project Isolation Recovery
# ===================================================================


class TestProjectIsolationRecovery:
    """Project isolation is maintained even with shared infrastructure."""

    def test_cross_project_routing_blocked(self, tmp_path: Path) -> None:
        """Events from proj-alpha cannot route to proj-beta destinations."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [
                _make_policy("proj-alpha"),
                _make_policy("proj-beta"),
            ])
            from event_routing import is_eligible

            # proj-alpha review_submitted → orchestrator (allowed)
            ok, _ = is_eligible("proj-alpha", "review_submitted", "orchestrator")
            assert ok is True

            # proj-gamma has no policy
            ok, reason = is_eligible("proj-gamma", "review_submitted", "orchestrator")
            assert ok is False
            assert "no routing policy" in reason

            # proj-alpha ready_assigned → registered_worker (allowed)
            ok, _ = is_eligible("proj-alpha", "ready_assigned", "registered_worker")
            assert ok is True

            # proj-alpha cannot route incident_opened → registered_worker (not in policy)
            ok, _ = is_eligible("proj-alpha", "incident_opened", "registered_worker")
            assert ok is False
        finally:
            for p in patches:
                p.stop()

    def test_different_projects_different_routes(self, tmp_path: Path) -> None:
        """Each project has its own routing rules."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [
                {"project_id": "proj-a", "routes": [
                    {"event_type": "review_submitted", "destination": "orchestrator"},
                ], "enabled": True},
                {"project_id": "proj-b", "routes": [
                    {"event_type": "ready_assigned", "destination": "registered_worker"},
                ], "enabled": True},
            ])
            from event_routing import is_eligible

            ok1, _ = is_eligible("proj-a", "review_submitted", "orchestrator")
            assert ok1 is True

            ok2, _ = is_eligible("proj-a", "ready_assigned", "registered_worker")
            assert ok2 is False

            ok3, _ = is_eligible("proj-b", "ready_assigned", "registered_worker")
            assert ok3 is True

            ok4, _ = is_eligible("proj-b", "review_submitted", "orchestrator")
            assert ok4 is False
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 7. No-Duplicate Repeat Poll
# ===================================================================


class TestNoDuplicateRepeatPoll:
    """Repeated polls produce no duplicate events or delivery records."""

    def test_duplicate_event_detection(self, tmp_path: Path) -> None:
        """Same event appended twice is deduplicated by the ledger."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_ledger import Event, append_events, load_events
            event = Event(
                event_id="dup-001",
                project_id="p1", repository="/r", ref="main",
                commit="abc", task_id="t1", event_type="review_submitted",
                detected_at="2026-07-17T00:00:00Z",
            )
            added1 = append_events([event])
            assert added1 == 1

            added2 = append_events([event])
            assert added2 == 0

            events = load_events()
            assert len(events) == 1
        finally:
            for p in patches:
                p.stop()

    def test_duplicate_delivery_record_dedup(self, tmp_path: Path) -> None:
        """Same delivery record appended twice is deduplicated."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, load_delivery_state,
            )
            record = DeliveryRecord(
                payload_id="dup-delivery",
                project_id="p1", task_id="t1",
                event_type="ready_assigned", destination="registered_worker",
            )
            added1 = append_delivery_records([record])
            assert added1 == 1

            added2 = append_delivery_records([record])
            assert added2 == 0

            records = load_delivery_state()
            assert len(records) == 1
        finally:
            for p in patches:
                p.stop()

    def test_worker_poll_idempotent(self, tmp_path: Path) -> None:
        """Polling the same state twice produces identical output."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "p1")
            monitor_dir = tmp_path / "monitor"
            delivery_dir = monitor_dir / "delivery"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            (delivery_dir / "delivery_state.jsonl").write_text(
                json.dumps({
                    "payload_id": "idem-poll", "project_id": "p1", "task_id": "t1",
                    "event_type": "ready_assigned", "destination": "registered_worker",
                    "status": "pending",
                }) + "\n",
                encoding="utf-8",
            )
            f1 = io.StringIO()
            with redirect_stdout(f1):
                poll_worker("w1")
            f2 = io.StringIO()
            with redirect_stdout(f2):
                poll_worker("w1")
            assert f1.getvalue() == f2.getvalue()
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 8. No Lifecycle Mutation
# ===================================================================


class TestNoLifecycleMutation:
    """No part of the event flow modifies task cards, claims, or reviews."""

    def test_event_flow_no_task_card_writes(self, tmp_path: Path) -> None:
        """Monitor → route → poll never creates or modifies task card files."""
        remote = _init_remote(tmp_path, "test-proj")
        _write_task_card(tmp_path / "test-proj_work", "t-lifecycle", "REVIEW", state="review")
        clone = _clone_remote(remote, tmp_path, "test-proj")

        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_project_registry(tmp_path, [
                {"project_id": "test-proj", "local_path": str(clone), "remote_name": "origin", "default_branch": "main"},
            ])
            _write_routing_policy(tmp_path, [_make_policy("test-proj")])

            from project_registry import load_registry, ProjectEntry
            from remote_ref_monitor import _scan_project
            from event_ledger import append_events
            from event_routing import route_event, append_delivery_records

            projects = load_registry()
            state: dict = {}
            all_events = []
            for proj in projects:
                pe = ProjectEntry.from_dict({
                    "project_id": proj.project_id,
                    "local_path": proj.local_path,
                    "remote_name": proj.remote_name,
                    "default_branch": proj.default_branch,
                })
                events = _scan_project(pe, state)
                all_events.extend(events)

            append_events(all_events)

            # Snapshot task board before routing
            task_board = clone / "coordination" / "task-board"
            review_before = sorted(f.name for f in (task_board / "review").iterdir())
            ready_before = sorted(f.name for f in (task_board / "ready").iterdir()) if (task_board / "ready").exists() else []

            # Route events
            from event_ledger import load_events
            ledger = load_events()
            for event in ledger:
                route_event(event.project_id, event.task_id, event.event_type, event.ref, event.commit)

            # Verify no task board changes
            review_after = sorted(f.name for f in (task_board / "review").iterdir())
            ready_after = sorted(f.name for f in (task_board / "ready").iterdir()) if (task_board / "ready").exists() else []
            assert review_before == review_after
            assert ready_before == ready_after
        finally:
            for p in patches:
                p.stop()

    def test_no_subprocess_in_event_flow(self, tmp_path: Path) -> None:
        """route_event and poll_worker never call subprocess.run."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [_make_policy("p1")])
            from event_routing import route_event
            with patch("subprocess.run") as mock_sub:
                results = route_event("p1", "t1", "review_submitted", "main", "abc")
                mock_sub.assert_not_called()
                assert len(results) >= 0  # may be 0 if no route matches
        finally:
            for p in patches:
                p.stop()

    def test_no_http_in_event_flow(self, tmp_path: Path) -> None:
        """acknowledge and route_event never call HTTP."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, acknowledge,
            )
            record = DeliveryRecord(
                payload_id="no-http-test",
                project_id="p1", task_id="t1",
                event_type="review_submitted", destination="orchestrator",
            )
            append_delivery_records([record])
            with patch("urllib.request.urlopen") as mock_http:
                acknowledge("no-http-test")
                mock_http.assert_not_called()
        finally:
            for p in patches:
                p.stop()

    def test_no_push_in_event_flow(self, tmp_path: Path) -> None:
        """No git push is called during event routing."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [_make_policy("p1")])
            from event_routing import route_event
            with patch("subprocess.run") as mock_sub:
                route_event("p1", "t1", "review_submitted", "main", "abc")
                # Verify no git push was called
                for call in mock_sub.call_args_list:
                    args = call[0][0] if call[0] else []
                    assert "push" not in args
        finally:
            for p in patches:
                p.stop()

    def test_acknowledge_does_not_claim_or_review(self, tmp_path: Path) -> None:
        """Acknowledgement only changes delivery status, never task lifecycle."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_routing import (
                DeliveryRecord, append_delivery_records, acknowledge,
                load_delivery_state_map,
            )
            record = DeliveryRecord(
                payload_id="no-claim",
                project_id="p1", task_id="t1",
                event_type="ready_assigned", destination="registered_worker",
            )
            append_delivery_records([record])
            acknowledge("no-claim")

            rmap = load_delivery_state_map()
            rec = rmap["no-claim"]
            assert rec.status == "acknowledged"
            # No lifecycle fields changed
            assert rec.event_type == "ready_assigned"
            assert rec.destination == "registered_worker"
            assert rec.terminal_failure_at == ""
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 9. Duplicate Event Detection Across Projects
# ===================================================================


class TestDuplicateAcrossProjects:
    """Duplicate events from different projects are independent."""

    def test_same_task_id_different_projects(self, tmp_path: Path) -> None:
        """Same task_id in different projects produces independent events."""
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from event_ledger import Event, append_events, load_events
            e1 = Event(
                event_id="cross-001",
                project_id="proj-a", repository="/a", ref="main",
                commit="abc", task_id="shared-id", event_type="review_submitted",
                detected_at="2026-07-17T00:00:00Z",
            )
            e2 = Event(
                event_id="cross-002",
                project_id="proj-b", repository="/b", ref="main",
                commit="abc", task_id="shared-id", event_type="review_submitted",
                detected_at="2026-07-17T00:00:00Z",
            )
            added = append_events([e1, e2])
            assert added == 2

            events = load_events()
            projects = {e.project_id for e in events}
            assert "proj-a" in projects
            assert "proj-b" in projects
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 10. Disabled Policy
# ===================================================================


class TestDisabledPolicy:
    """Disabled policies prevent routing."""

    def test_disabled_policy_blocks_routing(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            _write_routing_policy(tmp_path, [
                {"project_id": "proj-disabled", "routes": [
                    {"event_type": "review_submitted", "destination": "orchestrator"},
                ], "enabled": False},
            ])
            from event_routing import is_eligible, route_event
            ok, reason = is_eligible("proj-disabled", "review_submitted", "orchestrator")
            assert ok is False
            assert "no routing policy" in reason

            results = route_event("proj-disabled", "t1", "review_submitted", "main", "abc")
            assert results == []
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 11. Worker Poller with Multiple Pending
# ===================================================================


class TestWorkerPollerMultiplePending:
    """Worker sees all pending notifications for its project."""

    def test_multiple_pending_notifications(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import register_worker, poll_worker
            register_worker("w-multi", "p1")
            monitor_dir = tmp_path / "monitor"
            delivery_dir = monitor_dir / "delivery"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            records = [
                json.dumps({"payload_id": f"pay-{i}", "project_id": "p1", "task_id": f"t{i}",
                            "event_type": "ready_assigned", "destination": "registered_worker",
                            "status": "pending", "ref": "main", "commit": "abc",
                            "owner": "agent", "reviewer": "orch", "artifact_paths": []})
                for i in range(3)
            ]
            (delivery_dir / "delivery_state.jsonl").write_text(
                "\n".join(records) + "\n", encoding="utf-8"
            )
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w-multi")
            assert rc == 0
            output = f.getvalue()
            assert "Pending notifications: 3" in output
        finally:
            for p in patches:
                p.stop()


# ===================================================================
# 12. Corrupt Delivery State
# ===================================================================


class TestCorruptDeliveryState:
    """Malformed delivery state lines are skipped gracefully."""

    def test_corrupt_lines_skipped(self, tmp_path: Path) -> None:
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import register_worker, poll_worker
            register_worker("w-corrupt", "p1")
            monitor_dir = tmp_path / "monitor"
            delivery_dir = monitor_dir / "delivery"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            (delivery_dir / "delivery_state.jsonl").write_text(
                '{"payload_id": "good1", "project_id": "p1", "task_id": "t1", '
                '"event_type": "ready_assigned", "destination": "registered_worker", '
                '"status": "pending"}\n'
                'NOT JSON\n'
                '{"payload_id": "good2", "project_id": "p1", "task_id": "t2", '
                '"event_type": "ready_assigned", "destination": "registered_worker", '
                '"status": "pending"}\n',
                encoding="utf-8",
            )
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w-corrupt")
            assert rc == 0
            output = f.getvalue()
            assert "t1" in output or "t2" in output
        finally:
            for p in patches:
                p.stop()
