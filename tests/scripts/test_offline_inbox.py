"""Synthetic signature fixtures and local SQLite faults; zero transport/launch."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coordination_runtime.offline_inbox import (
    OfflineInbox, InboxRefused, DOMAIN, MAX_BYTES, canonical, BODY_KEYS, DYNAMIC,
)

BODY = dict(protocol_version=1, operation="dispatch", controller_id="authority-A",
            controller_epoch=1, machine_id="executor-B", machine_epoch=1,
            project_id="synthetic", repository_id="repo-1", task_id="task-1",
            owner="worker-1", run_id="run-1", payload_id="payload-1", attempt=1,
            request_id="request-1", message_id="message-1", sequence=1,
            base_sha="a" * 40, contract_sha256="b" * 64, payload_sha256="c" * 64,
            expected_version=0, fence=1, execution_budget_ms=180000)
# This HMAC is a synthetic fixture, NOT the remote protocol or a production key.
FIXTURE_KEY = b"synthetic-offline-test-only"


def verify(signature, signed):
    return hmac.compare_digest(signature, hmac.digest(FIXTURE_KEY, signed, "sha512"))


def frame(body=None, **changes):
    value = dict(BODY if body is None else body) | changes
    auth = dict(key_ref="synthetic-key", key_epoch=1)
    signed = DOMAIN + canonical(dict(body=value, authentication=auth))
    auth["signature"] = hmac.digest(FIXTURE_KEY, signed, "sha512").hex()
    return canonical(dict(body=value, authentication=auth))


def inbox(path, body=None, **options):
    binding = {k: v for k, v in (BODY if body is None else body).items() if k not in DYNAMIC}
    return OfflineInbox(path, **(dict(binding=binding, key_ref="synthetic-key", key_epoch=1,
                                     verify_signature=verify) | options))


def state(path):
    with sqlite3.connect(path) as db:
        return (db.execute("SELECT * FROM metadata").fetchall(),
                db.execute("SELECT * FROM receipts ORDER BY request_id").fetchall())


@pytest.fixture
def journal(tmp_path):
    path = tmp_path / "offline.db"
    receiver = inbox(path)
    receiver.initialize()
    return receiver, path


def test_constructor_and_invalid_receive_have_no_database_side_effects(tmp_path):
    path = tmp_path / "absent" / "inbox.db"
    receiver = inbox(path)
    assert not path.parent.exists()
    with pytest.raises(InboxRefused):
        receiver.receive(b"invalid")
    assert not path.parent.exists()
    with pytest.raises(InboxRefused, match="journal_unavailable"):
        receiver.receive(frame())
    assert not path.parent.exists()


def test_exact_durable_receipt_replay_and_canonical_whitespace(journal):
    receiver, path = journal
    ack = receiver.receive(frame())
    before = state(path)
    assert inbox(path).receive(frame()) == ack
    pretty = json.dumps(json.loads(frame()), indent=2).encode()
    assert receiver.receive(pretty) == ack
    assert state(path) == before
    assert ack["phase"] == "received_durable" and ack["offline_only"] is True
    core = {k: v for k, v in ack.items() if k != "receipt_digest"}
    assert ack["receipt_digest"] == hashlib.sha256(canonical(core)).hexdigest()
    assert ack["command_digest"] == hashlib.sha256(frame()).hexdigest()
    assert not ({"accepted", "launched", "reviewed_sha"} & ack.keys())
    assert len(before[1]) == 1 and before[0][0][2] == 1


@pytest.mark.parametrize("raw", [b"", b"x" * (MAX_BYTES + 1), b"\xff", b"\xef\xbb\xbf{}",
    b'{} {}', b'{"body":{},"body":{}}', b'{"body":{"x":1,"x":2}}',
    b'{"body":NaN}', b'{"body":Infinity}', b"[" * 2000 + b"]" * 2000,
    b"null", b"[]", b"{}", b'{"body":{},"authentication":{}}', "not-bytes"])
def test_bad_frames_reject_before_opening_database(journal, raw, monkeypatch):
    receiver, path = journal
    before = path.read_bytes()
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: pytest.fail("invalid frame opened DB"))
    with pytest.raises(InboxRefused):
        receiver.receive(raw)
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("protocol_version", 2), ("operation", "launch"), ("execution_budget_ms", 180001),
    ("attempt", True), ("expected_version", -1), ("sequence", True), ("sequence", 2**63),
    ("sequence", 0), ("fence", 1.0), ("base_sha", "A" * 40),
    ("contract_sha256", "x" * 64), ("payload_sha256", "a" * 63),
    ("owner", "../worker"), ("run_id", "D:/private"), ("request_id", "a" * 101),
    ("machine_id", "主機"), ("controller_epoch", 0), ("execution_budget_ms", 0),
])
def test_wrong_types_shapes_and_bounds_are_readonly(journal, field, value):
    receiver, path = journal
    before = state(path)
    with pytest.raises(InboxRefused):
        receiver.receive(frame(**{field: value}))
    assert state(path) == before


@pytest.mark.parametrize("field", sorted(BODY_KEYS - DYNAMIC - {"operation", "protocol_version"}))
def test_every_locally_bound_identity_source_and_authority_field_is_exact(journal, field):
    receiver, path = journal
    old = BODY[field]
    value = old + 1 if type(old) is int else ("d" * len(old) if field.endswith("sha") or field.endswith("sha256") else old + "-other")
    if field == "execution_budget_ms":
        value = old - 1
    before = state(path)
    with pytest.raises(InboxRefused, match="binding_mismatch"):
        receiver.receive(frame(**{field: value}))
    assert state(path) == before


@pytest.mark.parametrize("where", ["envelope", "body", "authentication", "missing-body-field"])
def test_unknown_and_missing_fields_refused(journal, where):
    receiver, path = journal
    value = json.loads(frame())
    if where == "missing-body-field":
        del value["body"]["base_sha"]
    else:
        (value if where == "envelope" else value[where])["private_prompt"] = "synthetic"
    before = state(path)
    with pytest.raises(InboxRefused):
        receiver.receive(canonical(value))
    assert state(path) == before


@pytest.mark.parametrize("change", [dict(key_ref="other"), dict(key_epoch=2),
    dict(key_epoch=True), dict(signature="0" * 128), dict(signature="bad")])
def test_authentication_changes_fail_before_database_access(journal, change, monkeypatch):
    receiver, _ = journal
    value = json.loads(frame())
    value["authentication"].update(change)
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: pytest.fail("authentication opened DB"))
    with pytest.raises(InboxRefused):
        receiver.receive(canonical(value))


@pytest.mark.parametrize("result", [False, None, 1, "True", "exception"])
def test_verifier_errors_and_nonboolean_results_fail_closed(journal, result, monkeypatch):
    _, path = journal
    def verifier(*args):
        if result == "exception":
            raise ValueError("synthetic-private-diagnostic")
        return result
    receiver = inbox(path, verify_signature=verifier)
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: pytest.fail("bad verifier opened DB"))
    with pytest.raises(InboxRefused, match="^signature_invalid$"):
        receiver.receive(frame())


def test_no_default_verifier_or_mutable_binding_alias(tmp_path):
    with pytest.raises(InboxRefused, match="verifier_required"):
        inbox(tmp_path / "absent.db", verify_signature=None)
    binding = {k: v for k, v in BODY.items() if k not in DYNAMIC}
    receiver = OfflineInbox(tmp_path / "a.db", binding=binding, key_ref="synthetic-key",
                            key_epoch=1, verify_signature=verify)
    binding["owner"] = "other"
    receiver.initialize()
    receiver.receive(frame())


def test_signature_covers_body_destination_and_key_metadata(journal):
    _, path = journal
    value = json.loads(frame())
    changed = BODY | dict(machine_id="executor-C")
    value["body"] = changed
    with pytest.raises(InboxRefused, match="signature_invalid"):
        inbox(path, changed).receive(canonical(value))
    value = json.loads(frame())
    value["authentication"]["key_ref"] = "other-key"
    with pytest.raises(InboxRefused, match="signature_invalid"):
        inbox(path, key_ref="other-key").receive(canonical(value))


@pytest.mark.parametrize("changes", [dict(sequence=2), dict(message_id="other-message", sequence=2)])
def test_same_request_changed_body_conflicts_and_preserves_ack(journal, changes):
    receiver, path = journal
    ack = receiver.receive(frame())
    before = state(path)
    with pytest.raises(InboxRefused, match="request_conflict"):
        receiver.receive(frame(**changes))
    assert state(path) == before and receiver.receive(frame()) == ack


@pytest.mark.parametrize("changes", [dict(), dict(run_id="other-run"), dict(fence=2),
    dict(payload_id="other-payload", payload_sha256="d" * 64, attempt=2),
    dict(run_id="other-run", message_id="message-1", fence=2)])
def test_new_request_cannot_bypass_generation_or_message_tombstones(journal, changes):
    receiver, path = journal
    receiver.receive(frame())
    body = BODY | dict(request_id="other-request", message_id="other-message", sequence=2) | changes
    before = state(path)
    with pytest.raises(InboxRefused, match="generation_conflict"):
        inbox(path, body).receive(frame(body))
    assert state(path) == before


def test_sequence_floor_durable_but_known_older_replay_allowed(journal):
    receiver, path = journal
    first = receiver.receive(frame())
    newer = BODY | dict(request_id="request-3", message_id="message-3", sequence=3,
                        task_id="task-3", run_id="run-3")
    inbox(path, newer).receive(frame(newer))
    assert inbox(path).receive(frame()) == first
    older = newer | dict(request_id="request-2", message_id="message-2", sequence=2,
                         task_id="task-2", run_id="run-2")
    before = state(path)
    with pytest.raises(InboxRefused, match="sequence_stale"):
        inbox(path, older).receive(frame(older))
    assert state(path) == before


def test_namespace_reenrollment_and_wrong_schema_do_not_overwrite(journal):
    receiver, path = journal
    receiver.receive(frame())
    before = path.read_bytes()
    other = BODY | dict(machine_epoch=2)
    with pytest.raises(InboxRefused, match="journal_namespace_mismatch"):
        inbox(path, other).initialize()
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=99")
    before = path.read_bytes()
    with pytest.raises(InboxRefused, match="journal_schema_invalid"):
        receiver.initialize()
    assert path.read_bytes() == before


def test_foreign_controller_database_is_never_migrated(tmp_path):
    from coordination_runtime.state_controller import StateController
    path = tmp_path / "state.db"
    StateController(path).initialize()
    before = path.read_bytes()
    with pytest.raises(InboxRefused, match="journal_schema_invalid"):
        inbox(path).initialize()
    assert path.read_bytes() == before


@pytest.mark.parametrize("ack", ['not-json', '{}', '{"offline_only":1}', '[' * 2000])
def test_corrupt_recorded_ack_fails_closed_without_overwrite(journal, ack):
    receiver, path = journal
    receiver.receive(frame())
    with sqlite3.connect(path) as db:
        db.execute("UPDATE receipts SET ack=?", (ack,))
    before = state(path)
    with pytest.raises(InboxRefused, match="journal_receipt_invalid"):
        receiver.receive(frame())
    assert state(path) == before


def test_mid_transaction_sqlite_failure_rolls_back_receipt_and_sequence(journal):
    receiver, path = journal
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER fail_sequence BEFORE UPDATE ON metadata "
                   "BEGIN SELECT RAISE(ABORT,'synthetic-private-error'); END")
    before = state(path)
    with pytest.raises(InboxRefused, match="^journal_unavailable$"):
        receiver.receive(frame())
    assert state(path) == before


def child(path, raw_path, mode="normal"):
    return subprocess.Popen([sys.executable, str(Path(__file__)), str(path), str(raw_path), mode],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def collect(process):
    out, err = process.communicate(timeout=30)
    assert not err, err.decode(errors="replace")
    return process.returncode, out


def test_concurrent_identical_receives_have_one_durable_ack(journal, tmp_path):
    _, path = journal
    raw = tmp_path / "frame.json"
    raw.write_bytes(frame())
    outputs = [collect(p) for p in [child(path, raw) for _ in range(6)]]
    assert all(code == 0 for code, _ in outputs)
    assert len({out for _, out in outputs}) == 1
    assert len(state(path)[1]) == 1


def test_concurrent_changed_request_ids_cannot_duplicate_run(journal, tmp_path):
    _, path = journal
    files = []
    for i in range(4):
        raw = tmp_path / f"frame-{i}.json"
        raw.write_bytes(frame(request_id=f"request-{i}", message_id=f"message-{i}", sequence=i + 1))
        files.append(raw)
    outputs = [collect(p) for p in [child(path, raw) for raw in files]]
    assert sum(code == 0 for code, _ in outputs) == 1
    assert all(code in (0, 2) for code, _ in outputs)
    assert len(state(path)[1]) == 1


@pytest.mark.parametrize("mode,committed", [("crash-before", False), ("crash-after", True)])
def test_actual_commit_crashes_preserve_atomic_ack_and_sequence(journal, tmp_path, mode, committed):
    receiver, path = journal
    raw = tmp_path / "frame.json"
    raw.write_bytes(frame())
    assert collect(child(path, raw, mode))[0] == 73
    before = state(path)
    assert len(before[1]) == int(committed)
    assert before[0][0][2] == int(committed)
    ack = receiver.receive(frame())
    assert len(state(path)[1]) == 1 and inbox(path).receive(frame()) == ack


def test_admission_never_calls_network_process_or_controller(tmp_path, monkeypatch):
    import socket
    from coordination_runtime.state_controller import StateController
    def forbidden(*args, **kwargs):
        pytest.fail("offline admission attempted external execution")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(StateController, "apply", forbidden)
    receiver = inbox(tmp_path / "offline.db")
    receiver.initialize()
    receiver.receive(frame())
    receiver.receive(frame())


if __name__ == "__main__":
    path, raw_path, mode = sys.argv[1:]
    raw = Path(raw_path).read_bytes()
    body = json.loads(raw)["body"]
    if mode.startswith("crash-"):
        connect = sqlite3.connect
        class CrashConnection(sqlite3.Connection):
            def commit(self):
                if mode == "crash-before":
                    os._exit(73)
                super().commit()
                os._exit(73)
        sqlite3.connect = lambda *a, **k: connect(*a, **(k | dict(factory=CrashConnection)))
    try:
        print(canonical(inbox(path, body).receive(raw)).decode())
    except InboxRefused as exc:
        print(str(exc))
        raise SystemExit(2)
