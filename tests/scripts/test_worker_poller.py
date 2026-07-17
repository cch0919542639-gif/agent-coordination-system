"""Focused tests for the worker poller (Phase 12 Events 03).

Covers: worker registration, worker/project isolation, polling,
acknowledgement, payload rendering, malformed state, no subprocess/network
invocation, and no lifecycle mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_delivery_record(
    payload_id: str = "pay-001",
    project_id: str = "proj-alpha",
    task_id: str = "task-01",
    event_type: str = "ready_assigned",
    destination: str = "registered_worker",
    status: str = "pending",
    ref: str = "main",
    commit: str = "abc123def456",
    owner: str = "",
    reviewer: str = "orchestrator",
) -> dict:
    return {
        "payload_id": payload_id,
        "project_id": project_id,
        "task_id": task_id,
        "event_type": event_type,
        "destination": destination,
        "status": status,
        "ref": ref,
        "commit": commit,
        "owner": owner,
        "reviewer": reviewer,
        "artifact_paths": [],
    }


def _write_delivery_state(tmp_path: Path, records: list[dict]) -> Path:
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    dfile = delivery_dir / "delivery_state.jsonl"
    lines = "\n".join(json.dumps(r) for r in records) + "\n"
    dfile.write_text(lines, encoding="utf-8")
    return dfile


def _patch_paths(tmp_path: Path):
    """Patch MONITOR_DIR, WORKERS_FILE, and event_routing paths to tmp_path."""
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    workers_file = monitor_dir / "workers.json"
    return patch.multiple(
        "worker_poller",
        MONITOR_DIR=monitor_dir,
        WORKERS_FILE=workers_file,
    )


def _patch_event_routing_paths(tmp_path: Path):
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    return patch.multiple(
        "event_routing",
        MONITOR_DIR=monitor_dir,
        DELIVERY_DIR=delivery_dir,
        DELIVERY_FILE=delivery_dir / "delivery_state.jsonl",
    )


# ===================================================================
# 1. Worker Registration
# ===================================================================


class TestWorkerRegistration:
    """Register, unregister, list workers."""

    def test_register_worker(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, get_worker
            result = register_worker("worker-1", "proj-alpha")
            assert result is True
            worker = get_worker("worker-1")
            assert worker is not None
            assert worker.worker_id == "worker-1"
            assert worker.project_id == "proj-alpha"
            assert worker.enabled is True

    def test_register_duplicate_updates_project(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, get_worker
            register_worker("worker-1", "proj-alpha")
            register_worker("worker-1", "proj-beta")
            worker = get_worker("worker-1")
            assert worker.project_id == "proj-beta"

    def test_unregister_worker(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, unregister_worker, get_worker
            register_worker("worker-1", "proj-alpha")
            assert unregister_worker("worker-1") is True
            assert get_worker("worker-1") is None

    def test_unregister_nonexistent_returns_false(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import unregister_worker
            assert unregister_worker("nobody") is False

    def test_list_workers(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, list_workers
            register_worker("w1", "proj-a")
            register_worker("w2", "proj-b")
            workers = list_workers()
            assert len(workers) == 2
            ids = {w.worker_id for w in workers}
            assert ids == {"w1", "w2"}

    def test_list_empty_when_no_workers(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import list_workers
            workers = list_workers()
            assert workers == []

    def test_register_updates_existing(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, list_workers
            register_worker("w1", "proj-a")
            register_worker("w1", "proj-b")
            workers = list_workers()
            assert len(workers) == 1
            assert workers[0].project_id == "proj-b"

    def test_malformed_workers_file(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import WORKERS_FILE, list_workers
            WORKERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            WORKERS_FILE.write_text("NOT JSON {{{", encoding="utf-8")
            workers = list_workers()
            assert workers == []


# ===================================================================
# 2. Worker/Project Isolation
# ===================================================================


class TestWorkerProjectIsolation:
    """Worker only sees notifications for its own project."""

    def test_worker_sees_only_own_project(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("worker-proj-a", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1", owner="worker-proj-a"),
                _make_delivery_record(payload_id="p2", project_id="proj-b", task_id="t2", owner="worker-proj-a"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("worker-proj-a")
            assert rc == 0
            output = f.getvalue()
            assert "t1" in output
            assert "t2" not in output

    def test_worker_other_project_no_results(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("worker-c", "proj-c")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("worker-c")
            assert rc == 0
            assert "No pending work" in f.getvalue()

    def test_poll_unregistered_worker_errors(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import poll_worker
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("nonexistent-worker")
            assert rc == 1

    def test_poll_disabled_worker_errors(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("disabled-w", "proj-a")
            from worker_poller import get_worker
            w = get_worker("disabled-w")
            w.enabled = False
            from worker_poller import _save_workers
            _save_workers([w])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("disabled-w")
            assert rc == 1


# ===================================================================
# 3. Polling
# ===================================================================


class TestPolling:
    """Poll behavior with delivery records."""

    def test_empty_poll_no_delivery_state(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w", "proj-a")
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w")
            assert rc == 0
            assert "No pending work" in f.getvalue()

    def test_poll_finds_pending_ready(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="task-ready", owner="w1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            output = f.getvalue()
            assert "task-ready" in output
            assert "proj-a" in output
            assert "main" in output
            assert "abc123def456" in output

    def test_poll_ignores_non_ready_events(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1",
                                      event_type="review_submitted", owner="w1"),
                _make_delivery_record(payload_id="p2", project_id="proj-a", task_id="t2",
                                      event_type="ready_assigned", owner="w1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            output = f.getvalue()
            assert "t1" not in output
            assert "t2" in output

    def test_poll_ignores_non_pending_records(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1",
                                      status="acknowledged", owner="w1"),
                _make_delivery_record(payload_id="p2", project_id="proj-a", task_id="t2",
                                      status="pending", owner="w1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            output = f.getvalue()
            assert "t1" not in output
            assert "t2" in output

    def test_poll_ignores_other_destinations(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1",
                                      destination="orchestrator", owner="w1"),
                _make_delivery_record(payload_id="p2", project_id="proj-a", task_id="t2",
                                      destination="registered_worker", owner="w1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            output = f.getvalue()
            assert "t1" not in output
            assert "t2" in output

    def test_poll_json_output(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p-json", project_id="proj-a", task_id="t-json", owner="w1"),
            ])
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["worker_id"] == "w1"
            assert len(data["notifications"]) == 1
            assert data["notifications"][0]["task_id"] == "t-json"

    def test_poll_json_empty(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1", output_json=True)
            assert rc == 0
            data = json.loads(f.getvalue())
            assert data["notifications"] == []

    def test_duplicate_poll_idempotent(self, tmp_path: Path) -> None:
        """Polling the same state twice produces same output, no side effects."""
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "proj-a")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="proj-a", task_id="t1"),
            ])
            import io
            from contextlib import redirect_stdout
            f1 = io.StringIO()
            with redirect_stdout(f1):
                poll_worker("w1")
            f2 = io.StringIO()
            with redirect_stdout(f2):
                poll_worker("w1")
            # Outputs should be the same (same pending tasks)
            assert f1.getvalue() == f2.getvalue()


# ===================================================================
# 4. Acknowledgement
# ===================================================================


class TestAcknowledgement:
    """Acknowledge confirms delivery, not claim or execution."""

    def test_acknowledge_pending_notification(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="pay-ack"),
            ])
            from event_routing import load_delivery_state_map
            rc = acknowledge_delivery("pay-ack")
            assert rc == 0
            rmap = load_delivery_state_map()
            assert rmap["pay-ack"].status == "acknowledged"
            assert rmap["pay-ack"].acknowledged_at != ""

    def test_acknowledge_nonexistent_returns_error(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            import io
            from contextlib import redirect_stderr
            f = io.StringIO()
            with redirect_stderr(f):
                rc = acknowledge_delivery("nonexistent-id")
            assert rc == 1
            assert "not found" in f.getvalue()

    def test_acknowledge_idempotent(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="pay-idem"),
            ])
            rc1 = acknowledge_delivery("pay-idem")
            assert rc1 == 0
            rc2 = acknowledge_delivery("pay-idem")
            assert rc2 == 0

    def test_acknowledge_does_not_change_task_state(self, tmp_path: Path) -> None:
        """Acknowledge only changes delivery status, not task lifecycle."""
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            from event_routing import load_delivery_state_map
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="pay-safe", task_id="t-safe"),
            ])
            acknowledge_delivery("pay-safe")
            rmap = load_delivery_state_map()
            rec = rmap["pay-safe"]
            assert rec.status == "acknowledged"
            # Verify no lifecycle fields were changed
            assert rec.event_type == "ready_assigned"
            assert rec.destination == "registered_worker"
            # No fields that suggest claim/execution
            assert rec.terminal_failure_at == ""


# ===================================================================
# 5. Payload Safety
# ===================================================================


class TestPayloadSafety:
    """Rendered payload contains no raw content or sensitive data."""

    def test_payload_has_no_raw_content(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import _build_safe_payload
            rec = _make_delivery_record()
            payload = _build_safe_payload(rec)
            assert "prompt" not in payload
            assert "credentials" not in payload
            assert "body" not in payload
            assert "content" not in payload
            assert "password" not in payload
            assert "secret" not in payload
            assert "token" not in payload

    def test_payload_has_required_fields(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import _build_safe_payload
            rec = _make_delivery_record(
                payload_id="pay-req",
                project_id="proj-req",
                task_id="task-req",
                ref="feat/x",
                commit="deadbeef12345678",
                owner="agent-x",
                reviewer="reviewer-y",
            )
            payload = _build_safe_payload(rec)
            assert payload["payload_id"] == "pay-req"
            assert payload["project_id"] == "proj-req"
            assert payload["task_id"] == "task-req"
            assert payload["ref"] == "feat/x"
            assert payload["commit"] == "deadbeef12345678"
            assert payload["owner"] == "agent-x"
            assert payload["reviewer"] == "reviewer-y"
            assert payload["task_card_path"] == "coordination/task-board/ready/task-req.md"

    def test_payload_with_artifact_paths(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import _build_safe_payload
            rec = _make_delivery_record(project_id="p1", task_id="t1")
            rec["artifact_paths"] = ["docs/report.md", "src/main.py"]
            payload = _build_safe_payload(rec)
            assert payload["artifact_paths"] == ["docs/report.md", "src/main.py"]


# ===================================================================
# 6. Malformed delivery state
# ===================================================================


class TestMalformedState:
    """Malformed or corrupt delivery state handled gracefully."""

    def test_corrupt_delivery_line_skipped(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "p1")
            monitor_dir = tmp_path / "monitor"
            delivery_file = monitor_dir / "delivery" / "delivery_state.jsonl"
            delivery_file.parent.mkdir(parents=True, exist_ok=True)
            delivery_file.write_text(
                '{"payload_id": "good", "project_id": "p1", "task_id": "t1", '
                '"event_type": "ready_assigned", "destination": "registered_worker", '
                '"status": "pending", "owner": "w1"}\n'
                'NOT JSON\n'
                '{"payload_id": "good2", "project_id": "p1", "task_id": "t2", '
                '"event_type": "ready_assigned", "destination": "registered_worker", '
                '"status": "pending", "owner": "w1"}\n',
                encoding="utf-8",
            )
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            # At least one good record was found
            output = f.getvalue()
            assert "t1" in output or "t2" in output

    def test_empty_delivery_file(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "p1")
            monitor_dir = tmp_path / "monitor"
            delivery_file = monitor_dir / "delivery" / "delivery_state.jsonl"
            delivery_file.parent.mkdir(parents=True, exist_ok=True)
            delivery_file.write_text("", encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = poll_worker("w1")
            assert rc == 0
            assert "No pending work" in f.getvalue()


# ===================================================================
# 7. No subprocess / network invocation
# ===================================================================


class TestNoSubprocess:
    """Worker poller never calls subprocess, HTTP, or external APIs."""

    def test_poll_no_subprocess(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "p1")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="p1", task_id="t1"),
            ])
            with patch("subprocess.run") as mock_sub:
                poll_worker("w1")
                mock_sub.assert_not_called()

    def test_register_no_subprocess(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker
            with patch("subprocess.run") as mock_sub:
                register_worker("w1", "p1")
                mock_sub.assert_not_called()

    def test_unregister_no_subprocess(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import register_worker, unregister_worker
            register_worker("w1", "p1")
            with patch("subprocess.run") as mock_sub:
                unregister_worker("w1")
                mock_sub.assert_not_called()

    def test_list_no_subprocess(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from worker_poller import list_workers
            with patch("subprocess.run") as mock_sub:
                list_workers()
                mock_sub.assert_not_called()

    def test_acknowledge_no_subprocess(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="pay-nosub"),
            ])
            with patch("subprocess.run") as mock_sub:
                acknowledge_delivery("pay-nosub")
                mock_sub.assert_not_called()

    def test_acknowledge_no_http(self, tmp_path: Path) -> None:
        """Acknowledge should not import or use urllib/requests."""
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="pay-nohttp"),
            ])
            with patch("urllib.request.urlopen") as mock_http:
                acknowledge_delivery("pay-nohttp")
                mock_http.assert_not_called()


# ===================================================================
# 8. No lifecycle mutation
# ===================================================================


class TestNoLifecycleMutation:
    """Worker poller never modifies task cards or lifecycle state."""

    def test_poll_no_card_files_written(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import register_worker, poll_worker
            register_worker("w1", "p1")
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="p1", task_id="t1"),
            ])
            # Create a fake task board to detect writes
            task_board = tmp_path / "coordination" / "task-board"
            task_board.mkdir(parents=True)
            (task_board / "ready").mkdir()
            (task_board / "review").mkdir()

            with patch("worker_poller.ROOT", tmp_path):
                poll_worker("w1")

                # Verify no new files in task board
                ready_files = list((task_board / "ready").iterdir())
                review_files = list((task_board / "review").iterdir())
                assert ready_files == []
                assert review_files == []

    def test_acknowledge_no_card_files_written(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path), _patch_event_routing_paths(tmp_path):
            from worker_poller import acknowledge_delivery
            _write_delivery_state(tmp_path, [
                _make_delivery_record(payload_id="p1", project_id="p1", task_id="t1"),
            ])
            task_board = tmp_path / "coordination" / "task-board"
            task_board.mkdir(parents=True)
            (task_board / "ready").mkdir()

            with patch("worker_poller.ROOT", tmp_path):
                acknowledge_delivery("p1")

                ready_files = list((task_board / "ready").iterdir())
                assert ready_files == []


# ===================================================================
# 9. CLI integration
# ===================================================================


class TestCLI:
    """CLI produces valid output."""

    def test_parser_register(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["register", "w1", "proj-a"])
        assert args.command == "register"
        assert args.worker_id == "w1"
        assert args.project_id == "proj-a"

    def test_parser_unregister(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["unregister", "w1"])
        assert args.command == "unregister"
        assert args.worker_id == "w1"

    def test_parser_list(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_poll(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["poll", "w1"])
        assert args.command == "poll"
        assert args.worker_id == "w1"

    def test_parser_poll_json(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["poll", "w1", "--json"])
        assert args.json is True

    def test_parser_acknowledge(self) -> None:
        from worker_poller import build_parser
        parser = build_parser()
        args = parser.parse_args(["acknowledge", "pay-001"])
        assert args.command == "acknowledge"
        assert args.payload_id == "pay-001"
