#!/usr/bin/env python3
"""Focused tests for the Phase 14 worker activation command.

Covers:
  - Owner-strict activation: only matching worker receives payload
  - Two-worker isolation: worker A cannot see B's delivery
  - Duplicate activation is idempotent (no duplicate payload)
  - Fail-closed: missing, empty, mismatched, malformed, acknowledged,
    retry-pending, and failed records all rejected
  - No task-card mutation
  - No subprocess, HTTP, or agent launch
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_delivery_state(tmp_path: Path, records: list[dict]) -> Path:
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    dfile = delivery_dir / "delivery_state.jsonl"
    lines = "\n".join(json.dumps(r) for r in records) + "\n"
    dfile.write_text(lines, encoding="utf-8")
    return dfile


def _patch_all(tmp_path: Path):
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    workers_file = monitor_dir / "workers.json"
    return (
        patch("worker_poller.MONITOR_DIR", monitor_dir),
        patch("worker_poller.WORKERS_FILE", workers_file),
        patch("event_routing.MONITOR_DIR", monitor_dir),
        patch("event_routing.DELIVERY_DIR", delivery_dir),
        patch("event_routing.DELIVERY_FILE", delivery_dir / "delivery_state.jsonl"),
    )


def _register(tmp_path: Path, worker_id: str, project_id: str = "proj-a"):
    from worker_poller import register_worker
    with patch("worker_poller.MONITOR_DIR", tmp_path / "monitor"), \
         patch("worker_poller.WORKERS_FILE", tmp_path / "monitor" / "workers.json"):
        register_worker(worker_id, project_id)


def _delivery_record(
    payload_id: str = "pay-001",
    project_id: str = "proj-a",
    task_id: str = "task-01",
    event_type: str = "ready_assigned",
    destination: str = "registered_worker",
    status: str = "pending",
    owner: str = "worker-a",
    reviewer: str = "ORCHESTRATOR",
    ref: str = "main",
    commit: str = "abc123def456",
) -> dict:
    return {
        "payload_id": payload_id,
        "project_id": project_id,
        "task_id": task_id,
        "event_type": event_type,
        "destination": destination,
        "status": status,
        "owner": owner,
        "reviewer": reviewer,
        "ref": ref,
        "commit": commit,
        "artifact_paths": [],
    }


# ---------------------------------------------------------------------------
# 1. Basic activation
# ---------------------------------------------------------------------------

class TestBasicActivation:
    """Activation succeeds for owner-matching pending delivery."""

    def test_activate_emits_payload(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["action"] == "ready_task_available"
            assert data["worker_id"] == "worker-a"
            assert data["task_id"] == "task-01"
            assert data["project_id"] == "proj-a"
        finally:
            for p in patches:
                p.stop()

    def test_activate_acknowledges_after_emit(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                activate_worker("worker-a", output_json=True)
            # Verify acknowledgement was written
            from event_routing import load_delivery_state_map
            records = load_delivery_state_map()
            rec = records["pay-001"]
            assert rec.status == "acknowledged"
            assert rec.acknowledged_at != ""
        finally:
            for p in patches:
                p.stop()

    def test_activate_idempotent(self, tmp_path: Path):
        """Second activation finds no pending work (already acknowledged)."""
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f1 = io.StringIO()
            with redirect_stdout(f1):
                rc1 = activate_worker("worker-a", output_json=True)
            assert rc1 == 0
            data1 = json.loads(f1.getvalue())
            assert data1["activated"] is True

            f2 = io.StringIO()
            with redirect_stdout(f2):
                rc2 = activate_worker("worker-a", output_json=True)
            assert rc2 == 0
            data2 = json.loads(f2.getvalue())
            assert data2["activated"] is False
            assert data2["reason"] == "no eligible delivery"
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 2. Two-worker isolation
# ---------------------------------------------------------------------------

class TestTwoWorkerIsolation:
    """Two workers on the same machine only see their own deliveries."""

    def test_worker_a_sees_only_a(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _register(tmp_path, "worker-b", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(payload_id="pay-a", task_id="task-a", owner="worker-a"),
            _delivery_record(payload_id="pay-b", task_id="task-b", owner="worker-b"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["task_id"] == "task-a"
            assert data["worker_id"] == "worker-a"
        finally:
            for p in patches:
                p.stop()

    def test_worker_b_sees_only_b(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _register(tmp_path, "worker-b", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(payload_id="pay-a", task_id="task-a", owner="worker-a"),
            _delivery_record(payload_id="pay-b", task_id="task-b", owner="worker-b"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-b", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["task_id"] == "task-b"
            assert data["worker_id"] == "worker-b"
        finally:
            for p in patches:
                p.stop()

    def test_worker_b_cannot_activate_a(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _register(tmp_path, "worker-b", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(payload_id="pay-a", task_id="task-a", owner="worker-a"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-b", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 3. Fail-closed cases
# ---------------------------------------------------------------------------

class TestFailClosed:
    """Missing, empty, mismatched, malformed, and non-pending records rejected."""

    def test_unregistered_worker(self, tmp_path: Path):
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                rc = activate_worker("ghost")
            assert rc == 1
            assert "not registered" in stderr_capture.getvalue()
        finally:
            for p in patches:
                p.stop()

    def test_empty_owner_rejected(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(owner=""),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()

    def test_mismatched_owner_rejected(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(owner="worker-b"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()

    def test_acknowledged_record_rejected(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(status="acknowledged"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()

    def test_retry_pending_record_rejected(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(status="retry_pending"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()

    def test_failed_record_rejected(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [
            _delivery_record(status="failed"),
        ])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["activated"] is False
        finally:
            for p in patches:
                p.stop()

    def test_malformed_record_skipped(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        monitor_dir = tmp_path / "monitor"
        delivery_dir = monitor_dir / "delivery"
        delivery_dir.mkdir(parents=True, exist_ok=True)
        (delivery_dir / "delivery_state.jsonl").write_text(
            "NOT JSON\n"
            '{"payload_id": "good", "project_id": "proj-a", "task_id": "t1", '
            '"event_type": "ready_assigned", "destination": "registered_worker", '
            '"status": "pending", "owner": "worker-a"}\n',
            encoding="utf-8",
        )
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                rc = activate_worker("worker-a", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["task_id"] == "t1"
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 4. No task-card mutation
# ---------------------------------------------------------------------------

class TestNoTaskCardMutation:
    """Activation never writes to task-board directories."""

    def test_no_files_written(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        task_board = tmp_path / "coordination" / "task-board"
        task_board.mkdir(parents=True)
        (task_board / "ready").mkdir()
        (task_board / "in_progress").mkdir()
        before_ready = list((task_board / "ready").iterdir())
        before_ip = list((task_board / "in_progress").iterdir())

        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            f = io.StringIO()
            with redirect_stdout(f):
                activate_worker("worker-a", output_json=True)
            assert list((task_board / "ready").iterdir()) == before_ready
            assert list((task_board / "in_progress").iterdir()) == before_ip
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 5. No subprocess / HTTP / agent launch
# ---------------------------------------------------------------------------

class TestNoExternalCalls:
    """Activation never calls subprocess, HTTP, or launches agents."""

    def test_no_subprocess(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            with patch("subprocess.run") as mock_sub:
                f = io.StringIO()
                with redirect_stdout(f):
                    activate_worker("worker-a", output_json=True)
                mock_sub.assert_not_called()
        finally:
            for p in patches:
                p.stop()

    def test_no_urllib(self, tmp_path: Path):
        _register(tmp_path, "worker-a", "proj-a")
        _write_delivery_state(tmp_path, [_delivery_record()])
        patches = _patch_all(tmp_path)
        for p in patches:
            p.start()
        try:
            from worker_poller import activate_worker
            import urllib.request
            with patch.object(urllib.request, "urlopen") as mock_http:
                f = io.StringIO()
                with redirect_stdout(f):
                    activate_worker("worker-a", output_json=True)
                mock_http.assert_not_called()
        finally:
            for p in patches:
                p.stop()
