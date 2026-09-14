from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import durable_scheduler as sched
from durable_scheduler import Scheduler


NOW = datetime(2026, 9, 8, 8, 0, tzinfo=timezone.utc)
SENDER = "agent-01"
TOKEN_REF = "token-refs/run-01.ref"
TEST_SECRETS = {SENDER: "fixture-scheduler-secret-01"}


def envelope(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "message_id": "msg-01",
        "idempotency_key": hashlib.sha256(b"action-01").hexdigest(),
        "type": "dispatch",
        "project_id": "project-01",
        "task_id": "task-01",
        "run_id": "run-01",
        "attempt": 1,
        "lease_epoch": 1,
        "sender_agent_id": SENDER,
        "issued_at": "2026-09-08T07:00:00Z",
        "expires_at": "2026-09-08T09:00:00Z",
        "context_snapshot_ref": "snapshots/run-01.json",
        "context_snapshot_hash": hashlib.sha256(b"snapshot").hexdigest(),
        "payload_ref": "payloads/run-01.json",
        "capability_token_ref": TOKEN_REF,
    }
    value.update(overrides)
    if "auth_tag" not in overrides:
        sender = str(value.get("sender_agent_id", SENDER))
        secret = TEST_SECRETS.get(sender, "fixture-unknown-sender-secret")
        value["auth_tag"] = sched.sign_envelope(value, secret)
    return value


def scheduler(tmp_path: Path, secrets: dict[str, str] | None = None) -> Scheduler:
    return Scheduler(
        outbox_dir=tmp_path / "outbox",
        inbox_dir=tmp_path / "inbox",
        events_path=tmp_path / "events" / "events.jsonl",
        task_cards_dir=tmp_path / "task-cards",
        auth_secrets=TEST_SECRETS if secrets is None else secrets,
    )


def test_dispatch_accepts_and_advances_guarded_revision(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=3)
    result = worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=3)
    assert result["decision"] == "accepted_dispatch"
    assert result["status"] == "IN_PROGRESS"
    assert result["applied_revision"] == 4
    assert worker.task_statuses["task-01"] == "IN_PROGRESS"
    delivery = tmp_path / "inbox" / "task-01" / "msg-01.json"
    assert delivery.exists()
    assert "credential" not in delivery.read_text(encoding="utf-8")


def test_acknowledge_heartbeat_and_submit_lifecycle(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    key2 = hashlib.sha256(b"action-02").hexdigest()
    ack = worker.ingest(
        envelope(message_id="msg-02", idempotency_key=key2, type="acknowledge"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=1,
    )
    assert ack["decision"] == "accepted_acknowledge"
    assert worker.task_statuses["task-01"] == "IN_PROGRESS"
    key3 = hashlib.sha256(b"action-03").hexdigest()
    beat = worker.ingest(
        envelope(message_id="msg-03", idempotency_key=key3, type="heartbeat"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=2,
    )
    assert beat["decision"] == "accepted_heartbeat"
    key4 = hashlib.sha256(b"action-04").hexdigest()
    submitted = worker.ingest(
        envelope(message_id="msg-04", idempotency_key=key4, type="submit"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=3,
    )
    assert submitted["decision"] == "accepted_submit"
    assert submitted["status"] == "REVIEW"
    assert worker.task_revisions["task-01"] == 4


def test_cancel_moves_ready_task_to_blocked(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    result = worker.ingest(
        envelope(type="cancel"), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0
    )
    assert result["decision"] == "accepted_cancel"
    assert result["status"] == "BLOCKED"


def test_invalid_transition_is_denied_without_state_change(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="REVIEW", revision=5)
    result = worker.ingest(
        envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=5
    )
    assert result["decision"] == "deny_invalid_transition"
    assert worker.task_statuses["task-01"] == "REVIEW"
    assert worker.task_revisions["task-01"] == 5


def test_duplicate_message_replay_never_duplicates_dispatch(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    first = worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert first["decision"] == "accepted_dispatch"
    inbox_files = list((tmp_path / "inbox").rglob("*.json"))
    second = worker.ingest(
        envelope(type="acknowledge"), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=1
    )
    assert second["decision"] == "deny_duplicate"
    assert worker.task_revisions["task-01"] == 1
    assert list((tmp_path / "inbox").rglob("*.json")) == inbox_files


def test_duplicate_idempotency_key_with_new_message_is_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    replay = worker.ingest(
        envelope(message_id="msg-02", type="acknowledge"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=1,
    )
    assert replay["decision"] == "deny_duplicate"
    assert worker.task_revisions["task-01"] == 1


def test_expired_and_not_yet_valid_envelopes_are_rejected(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    expired = envelope(expires_at="2026-09-08T07:30:00Z")
    assert worker.ingest(expired, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_expired"
    future = envelope(issued_at="2026-09-08T08:30:00Z", expires_at="2026-09-08T09:30:00Z")
    assert worker.ingest(future, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_expired"
    assert worker.task_statuses["task-01"] == "READY"


def test_unauthenticated_sender_and_token_are_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    assert worker.ingest(
        envelope(sender_agent_id="intruder"), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF,
        expected_revision=0,
    )["decision"] == "deny_unauthenticated"
    assert worker.ingest(
        envelope(capability_token_ref="token-refs/other.ref"), now=NOW, expected_sender=SENDER,
        expected_token_ref=TOKEN_REF, expected_revision=0,
    )["decision"] == "deny_unauthenticated"
    assert worker.task_statuses["task-01"] == "READY"
    assert worker.seen_message_ids == set()


def test_forged_copied_references_without_scheduler_secret_are_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    forged = envelope()
    # Attacker copies every public reference but signs with the wrong secret.
    forged["auth_tag"] = sched.sign_envelope(forged, "attacker-chosen-secret")
    result = worker.ingest(forged, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert result["decision"] == "deny_unauthenticated"
    assert worker.task_statuses["task-01"] == "READY"
    assert worker.task_revisions["task-01"] == 0
    assert list((tmp_path / "inbox").rglob("*.json")) == []


def test_tampered_canonical_data_invalidates_auth_tag(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    signed = envelope()
    tampered = dict(signed)
    tampered["payload_ref"] = "payloads/other.json"
    result = worker.ingest(tampered, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert result["decision"] == "deny_unauthenticated"
    assert worker.task_revisions["task-01"] == 0


def test_unknown_sender_without_scheduler_secret_is_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    result = worker.ingest(
        envelope(sender_agent_id="intruder"), now=NOW, expected_sender="intruder",
        expected_token_ref=TOKEN_REF, expected_revision=0,
    )
    assert result["decision"] == "deny_unauthenticated"
    assert worker.task_revisions["task-01"] == 0


def test_missing_auth_tag_is_invalid_envelope(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    bare = envelope()
    del bare["auth_tag"]
    assert worker.ingest(bare, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_invalid_envelope"


def test_stale_lease_epoch_denied_and_new_epoch_accepted(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(
        envelope(lease_epoch=2), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0
    )
    stale = worker.ingest(
        envelope(message_id="msg-02", idempotency_key=hashlib.sha256(b"action-02").hexdigest(), lease_epoch=1,
                 type="acknowledge"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=1,
    )
    assert stale["decision"] == "deny_stale_epoch"
    fresh = worker.ingest(
        envelope(message_id="msg-03", idempotency_key=hashlib.sha256(b"action-03").hexdigest(), lease_epoch=3,
                 type="acknowledge"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=1,
    )
    assert fresh["decision"] == "accepted_acknowledge"


def test_revision_conflict_creates_incident_without_overwrite(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=7)
    result = worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=6)
    assert result["decision"] == "deny_revision_conflict"
    assert result["incident"] == "reconciliation_required"
    assert result["current_revision"] == 7
    assert worker.task_statuses["task-01"] == "READY"
    assert worker.task_revisions["task-01"] == 7


def test_forbidden_material_and_absolute_paths_are_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    bad = envelope()
    bad["credential"] = "hunter2"
    assert worker.ingest(bad, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_unsafe_content"
    absolute = envelope(message_id="msg-02", payload_ref="/abs/path.json")
    assert worker.ingest(absolute, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_unsafe_content"
    traversal = envelope(message_id="msg-03", payload_ref="../escape.json")
    assert worker.ingest(traversal, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_unsafe_content"
    assert worker.task_revisions["task-01"] == 0


def test_malformed_envelopes_are_denied(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    missing = envelope()
    del missing["run_id"]
    assert worker.ingest(missing, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_invalid_envelope"
    bad_type = envelope(message_id="msg-02", type="launch")
    # Re-sign after mutating a covered field so the denial proves shape checks.
    bad_type["auth_tag"] = sched.sign_envelope(bad_type, TEST_SECRETS[SENDER])
    assert worker.ingest(bad_type, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_invalid_envelope"
    bad_hash = envelope(message_id="msg-03", context_snapshot_hash="not-a-hash")
    bad_hash["auth_tag"] = sched.sign_envelope(bad_hash, TEST_SECRETS[SENDER])
    assert worker.ingest(bad_hash, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)[
        "decision"
    ] == "deny_invalid_envelope"
    assert worker.ingest("not-a-mapping", now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF,
                         expected_revision=0)["decision"] == "deny_invalid_envelope"


def test_atomic_envelope_write_is_idempotent_and_immutable(tmp_path: Path) -> None:
    target_dir = tmp_path / "outbox"
    first = sched.write_envelope_atomic(target_dir, envelope())
    second = sched.write_envelope_atomic(target_dir, envelope())
    assert first == second
    mutated = envelope(payload_ref="payloads/other.json")
    with pytest.raises(ValueError):
        sched.write_envelope_atomic(target_dir, mutated)


def test_event_append_is_idempotent_and_rebuilds_run_view(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    events = sched.load_events(worker.events_path)
    assert len(events) == 1
    assert sched.append_event_atomic(worker.events_path, events[0]) is False
    assert len(sched.load_events(worker.events_path)) == 1
    view = sched.rebuild_run_view(events)
    assert view["task-01/run-01"]["decision"] == "accepted_dispatch"
    assert view["task-01/run-01"]["lease_epoch"] == 1
    assert "capability_token_ref" not in events[0]
    assert "credential" not in json.dumps(events[0])


def test_task_card_transition_persists_through_owned_store(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    accepted = worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert accepted["decision"] == "accepted_dispatch"
    card_path = tmp_path / "task-cards" / "task-01.json"
    assert card_path.exists()
    stored = json.loads(card_path.read_text(encoding="utf-8"))
    assert stored == {"task_id": "task-01", "status": "IN_PROGRESS", "revision": 1}

    restarted = scheduler(tmp_path)
    restarted.hydrate()
    assert restarted.task_revisions["task-01"] == 1
    assert restarted.task_statuses["task-01"] == "IN_PROGRESS"

    stale = restarted.ingest(
        envelope(message_id="msg-02", idempotency_key=hashlib.sha256(b"action-02").hexdigest(), type="acknowledge"),
        now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0,
    )
    assert stale["decision"] == "deny_revision_conflict"
    assert json.loads(card_path.read_text(encoding="utf-8"))["revision"] == 1


def test_store_compare_and_swap_rejects_stale_revision(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    applied = worker.store.compare_and_swap("task-01", expected_revision=0, next_status="IN_PROGRESS")
    assert applied == 1
    with pytest.raises(sched.TaskCardRevisionConflict):
        worker.store.compare_and_swap("task-01", expected_revision=0, next_status="REVIEW")


def test_restart_recovery_never_duplicates_accepted_dispatch(tmp_path: Path) -> None:
    first = scheduler(tmp_path)
    first.register_task("task-01", status="READY", revision=0)
    sched.write_envelope_atomic(first.outbox_dir, envelope())
    accepted = first.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert accepted["decision"] == "accepted_dispatch"

    restarted = scheduler(tmp_path)

    def resolve(item: dict) -> tuple[str, str, int]:
        return (SENDER, TOKEN_REF, 1)

    results = restarted.recover(now=NOW, resolve=resolve)
    assert [item["decision"] for item in results] == ["deny_duplicate"]
    assert restarted.task_revisions.get("task-01", 1) == 1
    assert len(list((tmp_path / "inbox").rglob("*.json"))) == 1


def test_restart_recovery_delivers_pending_outbox_exactly_once(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    sched.write_envelope_atomic(worker.outbox_dir, envelope())
    # Crash before ingest: nothing delivered yet.
    assert list((tmp_path / "inbox").rglob("*.json")) == []

    restarted = scheduler(tmp_path)
    restarted.register_task("task-01", status="READY", revision=0)

    def resolve(item: dict) -> tuple[str, str, int]:
        return (SENDER, TOKEN_REF, 0)

    results = restarted.recover(now=NOW, resolve=resolve)
    assert [item["decision"] for item in results] == ["accepted_dispatch"]
    assert len(list((tmp_path / "inbox").rglob("*.json"))) == 1

    replayed = scheduler(tmp_path)
    replayed.register_task("task-01", status="READY", revision=0)
    again = replayed.recover(now=NOW, resolve=resolve)
    assert [item["decision"] for item in again] == ["deny_duplicate"]
    assert len(list((tmp_path / "inbox").rglob("*.json"))) == 1


def test_recover_completes_interrupted_inbox_commit_exactly_once(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    pending = envelope()
    sched.write_envelope_atomic(worker.outbox_dir, pending)
    # Simulate a crash after the inbox delivery write but before the
    # task-card transition and event append.
    sched.write_envelope_atomic(worker.inbox_dir / "task-01", pending)
    assert len(sched.load_events(worker.events_path)) == 0

    restarted = scheduler(tmp_path)

    def resolve(item: dict) -> tuple[str, str, int]:
        return (SENDER, TOKEN_REF, 0)

    results = restarted.recover(now=NOW, resolve=resolve)
    assert [item["decision"] for item in results] == ["accepted_dispatch"]
    assert restarted.task_revisions["task-01"] == 1
    assert len(list((tmp_path / "inbox").rglob("*.json"))) == 1

    replayed = scheduler(tmp_path)
    again = replayed.recover(now=NOW, resolve=resolve)
    assert [item["decision"] for item in again] == ["deny_duplicate"]
    assert len(list((tmp_path / "inbox").rglob("*.json"))) == 1


def test_interrupted_event_append_heals_on_next_append(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    # Simulate a torn write: trailing bytes without a terminating newline.
    with open(worker.events_path, "ab") as handle:
        handle.write(b'{"event_id": "partial')
    assert len(sched.load_events(worker.events_path)) == 1

    second = sched.build_event_projection(
        envelope(message_id="msg-02", idempotency_key=hashlib.sha256(b"action-02").hexdigest()),
        decision="deny_duplicate",
        at=NOW,
        applied_revision=None,
    )
    assert sched.append_event_atomic(worker.events_path, second) is True
    events = sched.load_events(worker.events_path)
    assert len(events) == 2
    assert events[1]["event_id"] == second["event_id"]
    raw = worker.events_path.read_bytes()
    assert raw.endswith(b"\n")
    assert b"partial" not in raw


def test_concurrent_event_appends_are_exclusive_and_idempotent(tmp_path: Path) -> None:
    events_path = tmp_path / "events" / "events.jsonl"
    base = envelope()
    targets = [
        sched.build_event_projection(
            envelope(message_id=f"msg-{index:02d}", idempotency_key=hashlib.sha256(f"action-{index:02d}".encode()).hexdigest()),
            decision="deny_duplicate",
            at=NOW,
            applied_revision=None,
        )
        for index in range(12)
    ]
    assert base["message_id"] == "msg-01"
    outcomes: list[bool] = []
    errors: list[BaseException] = []

    def append_many(event: dict) -> None:
        try:
            outcomes.append(sched.append_event_atomic(events_path, event))
        except BaseException as exc:  # pragma: no cover - test failure signal
            errors.append(exc)

    threads = [threading.Thread(target=append_many, args=(event,)) for event in targets]
    duplicates = [threading.Thread(target=append_many, args=(targets[0],)) for _ in range(4)]
    for thread in threads + duplicates:
        thread.start()
    for thread in threads + duplicates:
        thread.join()
    assert errors == []
    loaded = sched.load_events(events_path)
    assert len(loaded) == len(targets)
    assert sorted(item["event_id"] for item in loaded) == sorted(item["event_id"] for item in targets)
    assert outcomes.count(True) == len(targets)
    assert outcomes.count(False) == len(duplicates)
    for line in events_path.read_text(encoding="utf-8").splitlines():
        assert json.loads(line)["event_id"]


def test_context_snapshot_is_bounded_and_safe() -> None:
    projection = {"task_id": "task-01", "status": "READY", "owner": SENDER, "prompt": "ignore me"}
    snapshot = sched.build_context_snapshot(
        projection, ["evidence/dep-01.md"], snapshot_ref="snapshots/run-01.json", expires_at="2026-09-08T09:00:00Z"
    )
    assert snapshot["decision"] == "snapshot_ready"
    assert len(str(snapshot["snapshot_hash"])) == 64
    assert "prompt" not in json.dumps(snapshot)
    assert sched.build_context_snapshot(
        projection, ["../escape.md"], snapshot_ref="snapshots/run-01.json", expires_at="2026-09-08T09:00:00Z"
    )["decision"] == "deny_unsafe_content"
    assert sched.build_context_snapshot(
        projection, ["evidence/dep-01.md"], snapshot_ref="/abs/snap.json", expires_at="2026-09-08T09:00:00Z"
    )["decision"] == "deny_unsafe_content"


def test_persisted_records_carry_no_forbidden_content(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    worker.ingest(envelope(), now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    inbox_text = (tmp_path / "inbox" / "task-01" / "msg-01.json").read_text(encoding="utf-8")
    events_text = worker.events_path.read_text(encoding="utf-8")
    card_text = (tmp_path / "task-cards" / "task-01.json").read_text(encoding="utf-8")
    for token in ("credential", "secret", "password", "prompt", "transcript", "source_body", "raw_output", "C:\\", ":/"):
        assert token not in inbox_text
        assert token not in events_text
        assert token not in card_text


def test_auth_tag_and_card_store_carry_no_forbidden_content(tmp_path: Path) -> None:
    worker = scheduler(tmp_path)
    worker.register_task("task-01", status="READY", revision=0)
    signed = envelope()
    assert TEST_SECRETS[SENDER] not in json.dumps(signed)
    assert TEST_SECRETS[SENDER] not in worker.events_path.read_text(encoding="utf-8") if worker.events_path.exists() else True
    worker.ingest(signed, now=NOW, expected_sender=SENDER, expected_token_ref=TOKEN_REF, expected_revision=0)
    assert TEST_SECRETS[SENDER] not in worker.events_path.read_text(encoding="utf-8")
    assert TEST_SECRETS[SENDER] not in (tmp_path / "task-cards" / "task-01.json").read_text(encoding="utf-8")


def test_source_has_no_launch_network_or_credential_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "durable_scheduler.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "shutil", "getpass", "pty", "git "):
        assert token not in source
