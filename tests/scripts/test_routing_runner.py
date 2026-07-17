#!/usr/bin/env python3
"""Focused regression tests for the event-routing runtime entry point.

Covers:
  - ready_assigned delivery to registered_worker
  - review_submitted delivery to orchestrator
  - incident_opened delivery to orchestrator
  - no-policy behavior (event not routed)
  - disabled-policy behavior (event not routed)
  - idempotency (repeated runs do not duplicate records)
  - no mutation of project task cards
  - project isolation
  - acknowledgement/retry state preservation
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure scripts/ is importable
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from event_ledger import Event, append_events, make_event_id, now_iso, EVENTS_FILE  # noqa: E402
from event_routing import (  # noqa: E402
    DeliveryRecord,
    RouteRule,
    RoutingPolicy,
    load_delivery_state_map,
    save_routing_policies,
    load_routing_policies,
    DELIVERY_FILE,
)
from routing_runner import route_pending_events  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_id(project_id: str, task_id: str, event_type: str, ref: str = "main", commit: str = "abc123") -> str:
    return make_event_id(project_id, f"/tmp/{project_id}", ref, commit, task_id, event_type)


def _make_event(
    project_id: str,
    task_id: str,
    event_type: str,
    ref: str = "main",
    commit: str = "abc123def456",
    delivery_state: str = "pending",
    owner: str = "",
    reviewer: str = "",
) -> Event:
    return Event(
        event_id=_event_id(project_id, task_id, event_type, ref, commit),
        project_id=project_id,
        repository=f"/tmp/{project_id}",
        ref=ref,
        commit=commit,
        task_id=task_id,
        event_type=event_type,
        detected_at=now_iso(),
        delivery_state=delivery_state,
        owner=owner,
        reviewer=reviewer,
    )


def _write_policy(project_id: str, routes: list[dict], enabled: bool = True) -> None:
    """Write a routing policy to the monitor dir."""
    policy = RoutingPolicy(
        project_id=project_id,
        routes=[RouteRule(r["event_type"], r["destination"]) for r in routes],
        enabled=enabled,
    )
    policies = load_routing_policies()
    policies = [p for p in policies if p.project_id != project_id]
    policies.append(policy)
    save_routing_policies(policies)


def _setup_env(tmp_path: Path):
    """Patch the monitor dir to use a temp directory."""
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    return patch.multiple(
        "event_routing",
        MONITOR_DIR=monitor_dir,
        POLICY_FILE=monitor_dir / "routing_policy.json",
        DELIVERY_DIR=monitor_dir / "delivery",
        DELIVERY_FILE=monitor_dir / "delivery" / "delivery_state.jsonl",
    ), patch.multiple(
        "event_ledger",
        MONITOR_DIR=monitor_dir,
        EVENTS_FILE=monitor_dir / "events.jsonl",
    )


# ---------------------------------------------------------------------------
# Test: ready_assigned -> registered_worker
# ---------------------------------------------------------------------------

class TestReadyAssignedDelivery:
    """ready_assigned events produce pending delivery records for registered_worker."""

    def test_ready_assigned_routes_to_worker(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-a", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            event = _make_event("proj-a", "task-01", "ready_assigned")
            append_events([event])

            rc = route_pending_events()
            assert rc == 0

            records = load_delivery_state_map()
            assert len(records) == 1

            rec = list(records.values())[0]
            assert rec.project_id == "proj-a"
            assert rec.task_id == "task-01"
            assert rec.event_type == "ready_assigned"
            assert rec.destination == "registered_worker"
            assert rec.status == "pending"

    def test_ready_assigned_idempotent(self, tmp_path: Path):
        """Repeated route_pending_events calls do not duplicate records."""
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-a", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            event = _make_event("proj-a", "task-01", "ready_assigned")
            append_events([event])

            route_pending_events()
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1


# ---------------------------------------------------------------------------
# Test: review_submitted -> orchestrator
# ---------------------------------------------------------------------------

class TestReviewSubmittedDelivery:
    """review_submitted events produce pending delivery records for orchestrator."""

    def test_review_routes_to_orchestrator(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-b", [
                {"event_type": "review_submitted", "destination": "orchestrator"},
            ])

            event = _make_event("proj-b", "task-02", "review_submitted")
            append_events([event])

            rc = route_pending_events()
            assert rc == 0

            records = load_delivery_state_map()
            assert len(records) == 1

            rec = list(records.values())[0]
            assert rec.destination == "orchestrator"
            assert rec.event_type == "review_submitted"

    def test_review_idempotent(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-b", [
                {"event_type": "review_submitted", "destination": "orchestrator"},
            ])
            event = _make_event("proj-b", "task-02", "review_submitted")
            append_events([event])

            route_pending_events()
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1


# ---------------------------------------------------------------------------
# Test: incident_opened -> orchestrator
# ---------------------------------------------------------------------------

class TestIncidentOpenedDelivery:
    """incident_opened events produce pending delivery records for orchestrator."""

    def test_incident_routes_to_orchestrator(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-c", [
                {"event_type": "incident_opened", "destination": "orchestrator"},
            ])

            event = _make_event("proj-c", "task-03", "incident_opened")
            append_events([event])

            rc = route_pending_events()
            assert rc == 0

            records = load_delivery_state_map()
            assert len(records) == 1

            rec = list(records.values())[0]
            assert rec.destination == "orchestrator"
            assert rec.event_type == "incident_opened"

    def test_incident_idempotent(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-c", [
                {"event_type": "incident_opened", "destination": "orchestrator"},
            ])
            event = _make_event("proj-c", "task-03", "incident_opened")
            append_events([event])

            route_pending_events()
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1


# ---------------------------------------------------------------------------
# Test: no policy
# ---------------------------------------------------------------------------

class TestNoPolicy:
    """Events for projects with no routing policy are not routed."""

    def test_event_with_no_policy_not_routed(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            # No policy written
            event = _make_event("unknown-proj", "task-99", "ready_assigned")
            append_events([event])

            rc = route_pending_events()
            assert rc == 0

            records = load_delivery_state_map()
            assert len(records) == 0


# ---------------------------------------------------------------------------
# Test: disabled policy
# ---------------------------------------------------------------------------

class TestDisabledPolicy:
    """Events for projects with disabled policy are not routed."""

    def test_disabled_policy_not_routed(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-disabled", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ], enabled=False)

            event = _make_event("proj-disabled", "task-10", "ready_assigned")
            append_events([event])

            rc = route_pending_events()
            assert rc == 0

            records = load_delivery_state_map()
            assert len(records) == 0


# ---------------------------------------------------------------------------
# Test: no mutation of project task cards
# ---------------------------------------------------------------------------

class TestNoTaskCardMutation:
    """Routing runner does not write to project task-board directories."""

    def test_no_files_written_to_task_board(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-x", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            # Create a fake task-board
            task_board = tmp_path / "coordination" / "task-board"
            task_board.mkdir(parents=True)
            ready_dir = task_board / "ready"
            ready_dir.mkdir()
            task_card = ready_dir / "task-11.md"
            task_card.write_text("---\ntask_id: task-11\n---\n")

            event = _make_event("proj-x", "task-11", "ready_assigned")
            append_events([event])

            # Snapshot task board
            before = list(task_board.rglob("*.md"))

            route_pending_events()

            after = list(task_board.rglob("*.md"))
            assert before == after

            # Task card content unchanged
            assert task_card.read_text() == "---\ntask_id: task-11\n---\n"


# ---------------------------------------------------------------------------
# Test: acknowledgement/retry state preserved
# ---------------------------------------------------------------------------

class TestAcknowledgementStatePreserved:
    """Existing acknowledged records are not overwritten by routing."""

    def test_acknowledged_record_preserved(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-y", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            # Create event and route it
            event = _make_event("proj-y", "task-12", "ready_assigned")
            append_events([event])
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1

            # Acknowledge the record
            from event_routing import acknowledge
            rec = list(records.values())[0]
            acknowledge(rec.payload_id)

            # Re-route — should not duplicate or reset
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1
            rec2 = list(records.values())[0]
            assert rec2.status == "acknowledged"
            assert rec2.acknowledged_at != ""

    def test_retry_pending_record_preserved(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-y", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            event = _make_event("proj-y", "task-13", "ready_assigned")
            append_events([event])
            route_pending_events()

            records = load_delivery_state_map()
            rec = list(records.values())[0]
            rec.status = "retry_pending"
            rec.attempts = 2
            rec.next_retry_at = "2099-01-01T00:00:00Z"
            from event_routing import update_delivery_record
            update_delivery_record(rec)

            # Re-route — should not reset to pending
            route_pending_events()

            records = load_delivery_state_map()
            rec2 = list(records.values())[0]
            assert rec2.status == "retry_pending"
            assert rec2.attempts == 2

    def test_failed_record_preserved(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-y", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            event = _make_event("proj-y", "task-14", "ready_assigned")
            append_events([event])
            route_pending_events()

            records = load_delivery_state_map()
            rec = list(records.values())[0]
            rec.status = "failed"
            rec.failure_reason = "exceeded max retries"
            from event_routing import update_delivery_record
            update_delivery_record(rec)

            route_pending_events()

            records = load_delivery_state_map()
            rec2 = list(records.values())[0]
            assert rec2.status == "failed"
            assert rec2.failure_reason == "exceeded max retries"


# ---------------------------------------------------------------------------
# Test: project isolation
# ---------------------------------------------------------------------------

class TestProjectIsolation:
    """Events from different projects are routed independently."""

    def test_two_projects_routed_independently(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-1", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])
            _write_policy("proj-2", [
                {"event_type": "review_submitted", "destination": "orchestrator"},
            ])

            e1 = _make_event("proj-1", "task-a", "ready_assigned")
            e2 = _make_event("proj-2", "task-b", "review_submitted")
            append_events([e1, e2])

            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 2

            recs = list(records.values())
            proj_ids = {r.project_id for r in recs}
            assert proj_ids == {"proj-1", "proj-2"}

            # proj-1 goes to registered_worker
            proj1_rec = [r for r in recs if r.project_id == "proj-1"][0]
            assert proj1_rec.destination == "registered_worker"

            # proj-2 goes to orchestrator
            proj2_rec = [r for r in recs if r.project_id == "proj-2"][0]
            assert proj2_rec.destination == "orchestrator"


# ---------------------------------------------------------------------------
# Test: no subprocess / HTTP / agent launch
# ---------------------------------------------------------------------------

class TestNoExternalCalls:
    """Routing runner does not call subprocess, HTTP, or launch agents."""

    def test_no_subprocess(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-z", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])
            event = _make_event("proj-z", "task-20", "ready_assigned")
            append_events([event])

            with patch("subprocess.run") as mock_run:
                route_pending_events()
                mock_run.assert_not_called()

    def test_no_urllib_import(self, tmp_path: Path):
        """Verify no urllib/requests calls are made."""
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-z", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])
            event = _make_event("proj-z", "task-21", "ready_assigned")
            append_events([event])

            import urllib.request
            with patch.object(urllib.request, "urlopen") as mock_open:
                route_pending_events()
                mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# Test: machine-readable JSON output
# ---------------------------------------------------------------------------

class TestJsonOutput:
    """route_pending_events produces valid JSON when requested."""

    def test_json_output(self, tmp_path: Path, capsys):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-j", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])
            event = _make_event("proj-j", "task-30", "ready_assigned")
            append_events([event])

            with patch("sys.argv", ["routing_runner.py", "--json"]):
                route_pending_events(output_json=True)

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert "routed" in data
            assert "skipped" in data
            assert "details" in data
            assert data["routed"] == 1

    def test_json_output_empty(self, tmp_path: Path, capsys):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            with patch("sys.argv", ["routing_runner.py", "--json"]):
                route_pending_events(output_json=True)

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["routed"] == 0
            assert data["skipped"] == 0


# ---------------------------------------------------------------------------
# Test: already-delivered event not re-routed
# ---------------------------------------------------------------------------

class TestAlreadyDeliveredEvent:
    """An event whose delivery record already exists is skipped."""

    def test_duplicate_event_skipped(self, tmp_path: Path):
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-d", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            # Route first time
            event = _make_event("proj-d", "task-40", "ready_assigned")
            append_events([event])
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1

            # Append same event again (ledger dedup prevents it)
            # But if it somehow appears, route again — delivery dedup handles it
            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 1


# ---------------------------------------------------------------------------
# Test: owner-aware worker delivery
# ---------------------------------------------------------------------------

class TestOwnerAwareDelivery:
    """Each worker only receives notifications for tasks assigned to them."""

    def test_two_workers_see_only_own_tasks(self, tmp_path: Path):
        """Two workers in one project each see only their own ready tasks."""
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            _write_policy("proj-own", [
                {"event_type": "ready_assigned", "destination": "registered_worker"},
            ])

            # Create events with different owners
            e1 = _make_event("proj-own", "task-alice", "ready_assigned", owner="alice")
            e2 = _make_event("proj-own", "task-bob", "ready_assigned", owner="bob")
            append_events([e1, e2])

            route_pending_events()

            records = load_delivery_state_map()
            assert len(records) == 2

            # Verify owner is stored in delivery records
            recs = list(records.values())
            owners = {r.owner for r in recs}
            assert owners == {"alice", "bob"}

    def test_worker_filters_by_owner(self, tmp_path: Path):
        """Worker poll filters by owner matching worker_id."""
        mock1, mock2 = _setup_env(tmp_path)
        with mock1, mock2:
            # Patch worker_poller paths too
            from worker_poller import poll_worker, register_worker, WORKERS_FILE
            with patch("worker_poller.WORKERS_FILE", tmp_path / "monitor" / "workers.json"):
                register_worker("alice", "proj-own")
                register_worker("bob", "proj-own")

                _write_policy("proj-own", [
                    {"event_type": "ready_assigned", "destination": "registered_worker"},
                ])

                e1 = _make_event("proj-own", "task-alice", "ready_assigned", owner="alice")
                e2 = _make_event("proj-own", "task-bob", "ready_assigned", owner="bob")
                append_events([e1, e2])

                route_pending_events()

                # Alice should see only task-alice
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    poll_worker("alice", output_json=True)
                data = json.loads(f.getvalue())
                task_ids = [n["task_id"] for n in data["notifications"]]
                assert task_ids == ["task-alice"]

                # Bob should see only task-bob
                f2 = io.StringIO()
                with redirect_stdout(f2):
                    poll_worker("bob", output_json=True)
                data2 = json.loads(f2.getvalue())
                task_ids2 = [n["task_id"] for n in data2["notifications"]]
                assert task_ids2 == ["task-bob"]

    def test_owner_field_populated_in_event(self, tmp_path: Path):
        """Events carry owner/reviewer metadata from task card front matter."""
        event = _make_event("proj-x", "task-50", "ready_assigned", owner="worker-1", reviewer="ORCH")
        assert event.owner == "worker-1"
        assert event.reviewer == "ORCH"

        # Serialization round-trip preserves owner/reviewer
        d = event.to_dict()
        restored = Event.from_dict(d)
        assert restored.owner == "worker-1"
        assert restored.reviewer == "ORCH"


# ---------------------------------------------------------------------------
# Test: --route --json combination rejected
# ---------------------------------------------------------------------------

class TestCombinedJsonRejected:
    """monitor --route --json is rejected with clear guidance."""

    def test_route_json_rejected(self, tmp_path: Path):
        """--route --json returns error with usage instructions."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"), "monitor", "--route", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 1
        assert "--route --json is not supported" in result.stderr
        assert "route-events --json" in result.stderr
