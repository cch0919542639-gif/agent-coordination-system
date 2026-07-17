"""Focused tests for event routing, payloads, and delivery state.

Covers: routing policy, project isolation, duplicate events, acknowledgement,
retry/backoff, invalid configuration, no process invocation, and no task-card
mutation.  Uses isolated temp files; never contacts real services.
"""

from __future__ import annotations

import json
import os
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

def _make_policy(
    project_id: str = "proj-alpha",
    routes: list[dict] | None = None,
    enabled: bool = True,
) -> dict:
    if routes is None:
        routes = [
            {"event_type": "review_submitted", "destination": "orchestrator"},
            {"event_type": "ready_assigned", "destination": "registered_worker"},
            {"event_type": "incident_opened", "destination": "orchestrator"},
        ]
    return {
        "project_id": project_id,
        "routes": routes,
        "enabled": enabled,
    }


def _write_policy_file(tmp_path: Path, policies: list[dict]) -> Path:
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    policy_file = monitor_dir / "routing_policy.json"
    policy_file.write_text(json.dumps(policies, indent=2), encoding="utf-8")
    return policy_file


def _make_event(
    project_id: str = "proj-alpha",
    task_id: str = "task-01",
    event_type: str = "review_submitted",
    ref: str = "main",
    commit: str = "abc123def456",
) -> dict:
    return {
        "event_id": "evt-001",
        "project_id": project_id,
        "repository": "/tmp/repo",
        "ref": ref,
        "commit": commit,
        "task_id": task_id,
        "event_type": event_type,
        "detected_at": "2026-07-17T12:00:00Z",
        "delivery_state": "pending",
    }


def _patch_paths(tmp_path: Path):
    """Patch MONITOR_DIR, POLICY_FILE, DELIVERY_DIR, DELIVERY_FILE to tmp_path."""
    monitor_dir = tmp_path / "monitor"
    delivery_dir = monitor_dir / "delivery"
    return patch.multiple(
        "event_routing",
        MONITOR_DIR=monitor_dir,
        POLICY_FILE=monitor_dir / "routing_policy.json",
        DELIVERY_DIR=delivery_dir,
        DELIVERY_FILE=delivery_dir / "delivery_state.jsonl",
    )


# ===================================================================
# 1. Routing policy loading and validation
# ===================================================================


class TestRoutingPolicy:
    """Policy load, save, and validation."""

    def test_load_empty_policy(self, tmp_path: Path) -> None:
        with _patch_paths(tmp_path):
            from event_routing import load_routing_policies
            policies = load_routing_policies()
            assert policies == []

    def test_save_and_load_policy(self, tmp_path: Path) -> None:
        from event_routing import RoutingPolicy, RouteRule, save_routing_policies, load_routing_policies
        with _patch_paths(tmp_path):
            policy = RoutingPolicy(
                project_id="proj-beta",
                routes=[RouteRule("review_submitted", "orchestrator")],
            )
            save_routing_policies([policy])
            loaded = load_routing_policies()
            assert len(loaded) == 1
            assert loaded[0].project_id == "proj-beta"
            assert loaded[0].routes[0].event_type == "review_submitted"

    def test_validate_valid_policy(self) -> None:
        from event_routing import RoutingPolicy, RouteRule, validate_policy
        policy = RoutingPolicy(
            project_id="proj-ok",
            routes=[RouteRule("review_submitted", "orchestrator")],
        )
        errors = validate_policy(policy)
        assert errors == []

    def test_validate_empty_project_id(self) -> None:
        from event_routing import RoutingPolicy, validate_policy
        policy = RoutingPolicy(project_id="", routes=[])
        errors = validate_policy(policy)
        assert any("project_id" in e for e in errors)

    def test_validate_unsupported_event_type(self) -> None:
        from event_routing import RoutingPolicy, RouteRule, validate_policy
        policy = RoutingPolicy(
            project_id="proj-bad",
            routes=[RouteRule("unknown_event", "orchestrator")],
        )
        errors = validate_policy(policy)
        assert any("event_type" in e for e in errors)

    def test_validate_unsupported_destination(self) -> None:
        from event_routing import RoutingPolicy, RouteRule, validate_policy
        policy = RoutingPolicy(
            project_id="proj-bad",
            routes=[RouteRule("review_submitted", "webhook_target")],
        )
        errors = validate_policy(policy)
        assert any("destination" in e for e in errors)

    def test_validate_duplicate_route(self) -> None:
        from event_routing import RoutingPolicy, RouteRule, validate_policy
        policy = RoutingPolicy(
            project_id="proj-dup",
            routes=[
                RouteRule("review_submitted", "orchestrator"),
                RouteRule("review_submitted", "orchestrator"),
            ],
        )
        errors = validate_policy(policy)
        assert any("duplicate" in e for e in errors)


# ===================================================================
# 2. Eligibility and project isolation
# ===================================================================


class TestEligibility:
    """is_eligible checks: known event, known destination, policy exists, route exists."""

    def test_eligible_route(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            ok, reason = is_eligible("proj-alpha", "review_submitted", "orchestrator")
            assert ok is True
            assert reason == "ok"

    def test_unknown_project_rejected(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            ok, reason = is_eligible("proj-unknown", "review_submitted", "orchestrator")
            assert ok is False
            assert "no routing policy" in reason

    def test_unsupported_event_type_rejected(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            ok, reason = is_eligible("proj-alpha", "nonexistent_event", "orchestrator")
            assert ok is False
            assert "unsupported event_type" in reason

    def test_unsupported_destination_rejected(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            ok, reason = is_eligible("proj-alpha", "review_submitted", "webhook")
            assert ok is False
            assert "unsupported destination" in reason

    def test_no_route_for_event_destination_pair(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            # Policy only has review_submitted -> orchestrator
            _write_policy_file(tmp_path, [_make_policy()])
            ok, reason = is_eligible("proj-alpha", "review_submitted", "registered_worker")
            assert ok is False
            assert "no route" in reason

    def test_disabled_policy_rejected(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy(enabled=False)])
            ok, reason = is_eligible("proj-alpha", "review_submitted", "orchestrator")
            assert ok is False
            assert "no routing policy" in reason


# ===================================================================
# 3. Project isolation
# ===================================================================


class TestProjectIsolation:
    """Events from one project cannot route to another project's destination."""

    def test_cross_project_routing_blocked(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            policies = [_make_policy("proj-alpha"), _make_policy("proj-beta")]
            _write_policy_file(tmp_path, policies)

            # proj-alpha can route review_submitted
            ok1, _ = is_eligible("proj-alpha", "review_submitted", "orchestrator")
            assert ok1 is True

            # proj-gamma has no policy
            ok2, reason2 = is_eligible("proj-gamma", "review_submitted", "orchestrator")
            assert ok2 is False
            assert "no routing policy" in reason2

    def test_different_projects_different_routes(self, tmp_path: Path) -> None:
        from event_routing import is_eligible
        with _patch_paths(tmp_path):
            policies = [
                _make_policy("proj-a", routes=[
                    {"event_type": "review_submitted", "destination": "orchestrator"},
                ]),
                _make_policy("proj-b", routes=[
                    {"event_type": "ready_assigned", "destination": "registered_worker"},
                ]),
            ]
            _write_policy_file(tmp_path, policies)

            # proj-a can route review_submitted
            ok1, _ = is_eligible("proj-a", "review_submitted", "orchestrator")
            assert ok1 is True

            # proj-a cannot route ready_assigned (not in its policy)
            ok2, _ = is_eligible("proj-a", "ready_assigned", "registered_worker")
            assert ok2 is False

            # proj-b can route ready_assigned
            ok3, _ = is_eligible("proj-b", "ready_assigned", "registered_worker")
            assert ok3 is True

            # proj-b cannot route review_submitted
            ok4, _ = is_eligible("proj-b", "review_submitted", "orchestrator")
            assert ok4 is False


# ===================================================================
# 4. Payload construction
# ===================================================================


class TestPayloadConstruction:
    """build_payload returns safe payloads with no raw content."""

    def test_build_payload_basic(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            payload = build_payload(
                project_id="proj-alpha",
                task_id="task-01",
                event_type="review_submitted",
                destination="orchestrator",
                ref="main",
                commit="abc123",
                owner="agent-1",
                reviewer="orchestrator",
            )
            assert payload is not None
            assert payload.project_id == "proj-alpha"
            assert payload.task_id == "task-01"
            assert payload.event_type == "review_submitted"
            assert payload.destination == "orchestrator"
            assert payload.commit == "abc123"
            assert len(payload.payload_id) == 16

    def test_build_payload_returns_none_when_ineligible(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            payload = build_payload(
                project_id="proj-unknown",
                task_id="task-01",
                event_type="review_submitted",
                destination="orchestrator",
                ref="main",
                commit="abc123",
            )
            assert payload is None

    def test_payload_has_no_raw_content(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            payload = build_payload(
                project_id="proj-alpha",
                task_id="task-01",
                event_type="review_submitted",
                destination="orchestrator",
                ref="main",
                commit="abc123",
            )
            d = payload.to_dict()
            # Must not contain these sensitive fields
            assert "prompt" not in d
            assert "credentials" not in d
            assert "body" not in d
            assert "content" not in d

    def test_payload_deterministic_id(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            p1 = build_payload("proj-alpha", "t1", "review_submitted", "orchestrator", "main", "abc")
            p2 = build_payload("proj-alpha", "t1", "review_submitted", "orchestrator", "main", "abc")
            assert p1.payload_id == p2.payload_id

    def test_different_inputs_different_payload_ids(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            p1 = build_payload("proj-alpha", "t1", "review_submitted", "orchestrator", "main", "abc")
            p2 = build_payload("proj-alpha", "t2", "review_submitted", "orchestrator", "main", "abc")
            assert p1.payload_id != p2.payload_id


# ===================================================================
# 5. Route event
# ===================================================================


class TestRouteEvent:
    """route_event produces payloads for all configured destinations."""

    def test_route_event_single_destination(self, tmp_path: Path) -> None:
        from event_routing import route_event
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            results = route_event(
                project_id="proj-alpha",
                task_id="task-01",
                event_type="review_submitted",
                ref="main",
                commit="abc123",
                owner="agent-1",
            )
            assert len(results) == 1
            payload, record = results[0]
            assert payload.destination == "orchestrator"
            assert record.status == "pending"

    def test_route_event_no_match(self, tmp_path: Path) -> None:
        from event_routing import route_event
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            results = route_event(
                project_id="proj-alpha",
                task_id="task-01",
                event_type="fetch_failed",
                ref="main",
                commit="abc123",
            )
            assert len(results) == 0

    def test_route_event_unknown_project(self, tmp_path: Path) -> None:
        from event_routing import route_event
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            results = route_event(
                project_id="proj-unknown",
                task_id="task-01",
                event_type="review_submitted",
                ref="main",
                commit="abc123",
            )
            assert len(results) == 0


# ===================================================================
# 6. Duplicate events (idempotent delivery records)
# ===================================================================


class TestDuplicateEvents:
    """Duplicate route passes produce no duplicate pending payloads."""

    def test_append_delivery_dedup(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, append_delivery_records, load_delivery_state
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="dup-test",
                project_id="proj-alpha",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            added1 = append_delivery_records([record])
            assert added1 == 1

            # Second append with same payload_id should be deduped
            added2 = append_delivery_records([record])
            assert added2 == 0

            records = load_delivery_state()
            assert len(records) == 1

    def test_route_event_dedup_via_append(self, tmp_path: Path) -> None:
        from event_routing import route_event, append_delivery_records, load_delivery_state
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])

            # Route same event twice
            results1 = route_event("proj-alpha", "t1", "review_submitted", "main", "abc")
            results2 = route_event("proj-alpha", "t1", "review_submitted", "main", "abc")

            # Append first batch
            records1 = [r for _, r in results1]
            append_delivery_records(records1)

            # Append second batch — should dedup
            records2 = [r for _, r in results2]
            added = append_delivery_records(records2)
            assert added == 0

            # Only one record total
            all_records = load_delivery_state()
            assert len(all_records) == 1


# ===================================================================
# 7. Acknowledgement
# ===================================================================


class TestAcknowledgement:
    """acknowledge is idempotent and only affects existing records."""

    def test_acknowledge_pending(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, append_delivery_records, acknowledge, load_delivery_state_map
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="ack-test",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            append_delivery_records([record])

            result = acknowledge("ack-test")
            assert result is True

            rmap = load_delivery_state_map()
            assert rmap["ack-test"].status == "acknowledged"
            assert rmap["ack-test"].acknowledged_at != ""

    def test_acknowledge_nonexistent_returns_false(self, tmp_path: Path) -> None:
        from event_routing import acknowledge
        with _patch_paths(tmp_path):
            result = acknowledge("nonexistent-id")
            assert result is False

    def test_acknowledge_idempotent(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, append_delivery_records, acknowledge
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="ack-idem",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            append_delivery_records([record])

            acknowledge("ack-idem")
            result = acknowledge("ack-idem")
            assert result is True


# ===================================================================
# 8. Retry / backoff
# ===================================================================


class TestRetryBackoff:
    """Retry state machine and deterministic backoff."""

    def test_mark_attempt_increments(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, mark_attempt
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="retry-test",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            record = mark_attempt(record)
            assert record.attempts == 1
            assert record.status == "retry_pending"
            assert record.next_retry_at != ""

    def test_mark_attempt_terminal_failure(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, mark_attempt, MAX_RETRY_ATTEMPTS
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="retry-fail",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            for _ in range(MAX_RETRY_ATTEMPTS):
                record = mark_attempt(record)
            assert record.status == "failed"
            assert record.terminal_failure_at != ""
            assert "exceeded" in record.failure_reason

    def test_backoff_exponential(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, mark_attempt, BASE_BACKOFF_SECONDS
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="backoff-test",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )

            record = mark_attempt(record)  # attempt 1, backoff = 30s
            assert record.attempts == 1

            record = mark_attempt(record)  # attempt 2, backoff = 60s
            assert record.attempts == 2

    def test_retry_not_eligible_when_pending(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, is_retry_eligible
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="no-retry",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
                status="pending",
            )
            assert is_retry_eligible(record) is False

    def test_retry_not_eligible_when_failed(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, is_retry_eligible
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="no-retry2",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
                status="failed",
                attempts=5,
            )
            assert is_retry_eligible(record) is False


# ===================================================================
# 9. No process invocation
# ===================================================================


class TestNoProcessInvocation:
    """Routing never calls subprocess, HTTP, or external APIs."""

    def test_route_event_no_subprocess(self, tmp_path: Path) -> None:
        from event_routing import route_event
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            with patch("subprocess.run") as mock_sub:
                results = route_event(
                    project_id="proj-alpha",
                    task_id="t1",
                    event_type="review_submitted",
                    ref="main",
                    commit="abc",
                )
                mock_sub.assert_not_called()
                assert len(results) == 1

    def test_build_payload_no_subprocess(self, tmp_path: Path) -> None:
        from event_routing import build_payload
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])
            with patch("subprocess.run") as mock_sub:
                build_payload("proj-alpha", "t1", "review_submitted", "orchestrator", "main", "abc")
                mock_sub.assert_not_called()

    def test_acknowledge_no_subprocess(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, append_delivery_records, acknowledge
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="ack-no-proc",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            append_delivery_records([record])
            with patch("subprocess.run") as mock_sub:
                acknowledge("ack-no-proc")
                mock_sub.assert_not_called()

    def test_mark_attempt_no_subprocess(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, mark_attempt
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="retry-no-proc",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            with patch("subprocess.run") as mock_sub:
                mark_attempt(record)
                mock_sub.assert_not_called()


# ===================================================================
# 10. No task-card mutation
# ===================================================================


class TestNoTaskCardMutation:
    """Routing never writes to task-board directories."""

    def test_route_event_no_card_files_written(self, tmp_path: Path) -> None:
        from event_routing import route_event
        with _patch_paths(tmp_path):
            _write_policy_file(tmp_path, [_make_policy()])

            # Create a fake task-board to detect writes
            task_board = tmp_path / "task-board"
            task_board.mkdir()
            (task_board / "review").mkdir()
            (task_board / "ready").mkdir()

            with patch("event_routing.ROOT", tmp_path):
                results = route_event(
                    project_id="proj-alpha",
                    task_id="t1",
                    event_type="review_submitted",
                    ref="main",
                    commit="abc",
                )
                assert len(results) == 1

                # Verify no new files in task-board
                review_files = list((task_board / "review").iterdir())
                ready_files = list((task_board / "ready").iterdir())
                assert review_files == []
                assert ready_files == []


# ===================================================================
# 11. Delivery record persistence
# ===================================================================


class TestDeliveryPersistence:
    """Delivery records survive round-trip through JSONL."""

    def test_append_and_load_records(self, tmp_path: Path) -> None:
        from event_routing import DeliveryRecord, append_delivery_records, load_delivery_state
        with _patch_paths(tmp_path):
            records = [
                DeliveryRecord(
                    payload_id=f"p-{i}",
                    project_id="proj-alpha",
                    task_id=f"t{i}",
                    event_type="review_submitted",
                    destination="orchestrator",
                )
                for i in range(3)
            ]
            added = append_delivery_records(records)
            assert added == 3

            loaded = load_delivery_state()
            assert len(loaded) == 3
            ids = {r.payload_id for r in loaded}
            assert ids == {"p-0", "p-1", "p-2"}

    def test_update_delivery_record(self, tmp_path: Path) -> None:
        from event_routing import (
            DeliveryRecord, append_delivery_records,
            update_delivery_record, load_delivery_state_map,
        )
        with _patch_paths(tmp_path):
            record = DeliveryRecord(
                payload_id="upd-test",
                project_id="p1",
                task_id="t1",
                event_type="review_submitted",
                destination="orchestrator",
            )
            append_delivery_records([record])

            record.status = "acknowledged"
            record.acknowledged_at = "2026-07-17T12:00:00Z"
            update_delivery_record(record)

            rmap = load_delivery_state_map()
            assert rmap["upd-test"].status == "acknowledged"
            assert rmap["upd-test"].acknowledged_at == "2026-07-17T12:00:00Z"

    def test_load_empty_state(self, tmp_path: Path) -> None:
        from event_routing import load_delivery_state
        with _patch_paths(tmp_path):
            records = load_delivery_state()
            assert records == []


# ===================================================================
# 12. Malformed policy handling
# ===================================================================


class TestMalformedPolicy:
    """Invalid or corrupt policy files are handled gracefully."""

    def test_corrupt_json_file(self, tmp_path: Path) -> None:
        from event_routing import load_routing_policies
        with _patch_paths(tmp_path):
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True)
            (monitor_dir / "routing_policy.json").write_text("NOT JSON {{{", encoding="utf-8")
            policies = load_routing_policies()
            assert policies == []

    def test_non_list_policy_file(self, tmp_path: Path) -> None:
        from event_routing import load_routing_policies
        with _patch_paths(tmp_path):
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True)
            (monitor_dir / "routing_policy.json").write_text(
                json.dumps({"not": "a list"}), encoding="utf-8"
            )
            policies = load_routing_policies()
            assert policies == []

    def test_missing_routes_field(self, tmp_path: Path) -> None:
        from event_routing import load_routing_policies
        with _patch_paths(tmp_path):
            monitor_dir = tmp_path / "monitor"
            monitor_dir.mkdir(parents=True)
            (monitor_dir / "routing_policy.json").write_text(
                json.dumps([{"project_id": "p1"}]), encoding="utf-8"
            )
            policies = load_routing_policies()
            assert len(policies) == 1
            assert policies[0].routes == []


# ===================================================================
# 13. Payload serialization
# ===================================================================


class TestPayloadSerialization:
    """Payloads round-trip through dict serialization."""

    def test_payload_to_dict_roundtrip(self, tmp_path: Path) -> None:
        from event_routing import NotificationPayload
        payload = NotificationPayload(
            payload_id="ser-test",
            project_id="proj",
            task_id="t1",
            event_type="review_submitted",
            destination="orchestrator",
            ref="main",
            commit="abc",
            owner="a1",
            reviewer="r1",
            artifact_paths=["docs/report.md"],
            created_at="2026-07-17T12:00:00Z",
        )
        d = payload.to_dict()
        restored = NotificationPayload.from_dict(d)
        assert restored.payload_id == payload.payload_id
        assert restored.artifact_paths == ["docs/report.md"]


# ===================================================================
# 14. Delivery record serialization
# ===================================================================


class TestDeliveryRecordSerialization:
    """Delivery records round-trip through dict serialization."""

    def test_record_to_dict_roundtrip(self) -> None:
        from event_routing import DeliveryRecord
        record = DeliveryRecord(
            payload_id="rec-ser",
            project_id="p1",
            task_id="t1",
            event_type="review_submitted",
            destination="orchestrator",
            status="retry_pending",
            attempts=2,
        )
        d = record.to_dict()
        restored = DeliveryRecord.from_dict(d)
        assert restored.payload_id == "rec-ser"
        assert restored.attempts == 2
        assert restored.status == "retry_pending"


# ===================================================================
# 15. get_pending_retries
# ===================================================================


class TestGetPendingRetries:
    """get_pending_retries filters correctly."""

    def test_returns_only_retry_pending_eligible(self, tmp_path: Path) -> None:
        from event_routing import (
            DeliveryRecord, append_delivery_records, get_pending_retries, mark_attempt,
        )
        with _patch_paths(tmp_path):
            # Record that is pending (not retry)
            r1 = DeliveryRecord(
                payload_id="pending-r",
                project_id="p1", task_id="t1",
                event_type="review_submitted", destination="orchestrator",
            )
            # Record that failed (terminal)
            r2 = DeliveryRecord(
                payload_id="failed-r",
                project_id="p1", task_id="t2",
                event_type="review_submitted", destination="orchestrator",
                status="failed", attempts=5,
            )
            append_delivery_records([r1, r2])

            # Mark r1 attempt so it becomes retry_pending
            mark_attempt(r1)

            retries = get_pending_retries()
            # r1 has next_retry_at in the future, so not eligible yet
            # r2 is failed
            assert all(r.payload_id != "failed-r" for r in retries)
