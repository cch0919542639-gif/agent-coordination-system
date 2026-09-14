#!/usr/bin/env python3
"""Phase C durable scheduler: sole task-card lifecycle writer.

The scheduler validates immutable outbox/inbox envelopes, verifies a
scheduler-owned authentication tag over canonical envelope data, applies
one revision-guarded lifecycle transition per accepted message through a
single storage adapter, persists the recipient delivery record with an
atomic file write, and appends only a sanitized event projection under
an exclusive lock. The event feed is a rebuildable projection, not a
second lifecycle state machine.

This module never launches a runtime, reads credentials, creates a
connector grant, touches version control metadata, or performs network
operations. All records are free of credentials, source bodies, prompts,
transcripts, absolute paths, and raw runtime output. Callers inject the
clock (``now``) so tests stay deterministic.
"""

from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0"
SENSITIVITY_LABEL = "internal"
MAX_SNAPSHOT_BYTES = 8192

ENVELOPE_FIELDS = (
    "message_id",
    "idempotency_key",
    "type",
    "project_id",
    "task_id",
    "run_id",
    "attempt",
    "lease_epoch",
    "sender_agent_id",
    "issued_at",
    "expires_at",
    "context_snapshot_ref",
    "context_snapshot_hash",
    "payload_ref",
    "capability_token_ref",
    "auth_tag",
)

MESSAGE_TYPES = ("dispatch", "acknowledge", "heartbeat", "submit", "cancel")

TASK_CARD_ALLOWLIST = (
    "task_id",
    "phase",
    "status",
    "owner",
    "reviewer",
    "priority",
    "dependencies",
    "allowed_scope",
    "forbidden_scope",
    "acceptance",
)

# Exact keys that must never appear in an envelope, event, snapshot, or
# delivery record. ``*_ref``, ``*_hash``, and ``*_digest`` suffix forms are
# safe references and are not matched; only the bare material key is denied.
FORBIDDEN_KEYS = frozenset({
    "credential",
    "credentials",
    "secret",
    "password",
    "token",
    "prompt",
    "transcript",
    "source_body",
    "source",
    "body",
    "output",
    "raw_output",
    "log",
    "logs",
    "argv",
    "command",
    "env",
    "environment",
})

ALLOWED_TRANSITIONS: dict[tuple[str, str], str] = {
    ("READY", "dispatch"): "IN_PROGRESS",
    ("IN_PROGRESS", "acknowledge"): "IN_PROGRESS",
    ("IN_PROGRESS", "heartbeat"): "IN_PROGRESS",
    ("IN_PROGRESS", "submit"): "REVIEW",
    ("READY", "cancel"): "BLOCKED",
    ("IN_PROGRESS", "cancel"): "BLOCKED",
    ("REVIEW", "cancel"): "BLOCKED",
}

TASK_STATUSES = ("READY", "IN_PROGRESS", "REVIEW", "BLOCKED", "DONE")


def _safe_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and len(value) <= 128
        and all(char.isalnum() or char in "-_." for char in value)
        and ".." not in value
    )


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if len(value) > 256:
        return False
    if value.startswith("/") or value.startswith("\\"):
        return False
    if ".." in value or "\\" in value or ":" in value:
        return False
    if value.startswith("./") or value.startswith("refs/") or "@{" in value:
        return False
    if "://" in value:
        return False
    parts = value.split("/")
    if any(not part or part == "." or part.endswith((".", " ")) for part in parts):
        return False
    if len(value) >= 2 and value[1] == ":":
        return False
    return True


def _safe_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _has_absolute_path(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith("/") or stripped.startswith("\\"):
        return True
    if len(stripped) >= 2 and stripped[1] == ":":
        return True
    if "://" in stripped:
        return True
    return False


def _forbidden_key_present(mapping: Mapping[str, Any]) -> bool:
    for key in mapping:
        if not isinstance(key, str):
            return True
        if key in FORBIDDEN_KEYS:
            return True
        lowered = key.lower()
        if lowered in FORBIDDEN_KEYS:
            return True
    return False


def _forbidden_value_present(envelope: Mapping[str, Any]) -> bool:
    for value in envelope.values():
        if isinstance(value, str) and _has_absolute_path(value):
            return True
    return False


def validate_envelope(envelope: object, *, now: datetime) -> str | None:
    """Return a denial category, or ``None`` when the envelope is well-formed.

    Well-formed means: exact required fields including ``auth_tag``, safe
    identifiers and relative references, a known message type, integer
    attempt/epoch counters, a hash-bound snapshot reference, an in-window
    validity period, and no forbidden material or absolute paths.
    Authentication, duplication, lease fencing, and revision checks are
    applied separately by the scheduler so each denial category stays
    precise. Signature verification needs the scheduler-owned secret and
    happens in ``Scheduler.ingest``.
    """
    if not isinstance(envelope, Mapping):
        return "deny_invalid_envelope"
    if _forbidden_key_present(envelope):
        return "deny_unsafe_content"
    if set(envelope.keys()) != set(ENVELOPE_FIELDS):
        return "deny_invalid_envelope"
    if _forbidden_value_present(envelope):
        return "deny_unsafe_content"
    if not _safe_identifier(envelope.get("message_id")):
        return "deny_invalid_envelope"
    if not _safe_hex64(envelope.get("idempotency_key")):
        return "deny_invalid_envelope"
    if envelope.get("type") not in MESSAGE_TYPES:
        return "deny_invalid_envelope"
    for field in ("project_id", "task_id", "run_id", "sender_agent_id"):
        if not _safe_identifier(envelope.get(field)):
            return "deny_invalid_envelope"
    for field in ("attempt", "lease_epoch"):
        value = envelope.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return "deny_invalid_envelope"
    for field in ("context_snapshot_ref", "payload_ref", "capability_token_ref"):
        if not _safe_relative(envelope.get(field)):
            return "deny_unsafe_content"
    if not _safe_hex64(envelope.get("context_snapshot_hash")):
        return "deny_invalid_envelope"
    if not _safe_hex64(envelope.get("auth_tag")):
        return "deny_invalid_envelope"
    issued = _parse_time(envelope.get("issued_at"))
    expires = _parse_time(envelope.get("expires_at"))
    if issued is None or expires is None or issued >= expires:
        return "deny_invalid_envelope"
    if now.tzinfo is None or not (issued <= now < expires):
        return "deny_expired"
    return None


def canonical_envelope_bytes(envelope: Mapping[str, Any]) -> bytes:
    """Return canonical bytes covered by the scheduler-owned auth tag."""
    body = {key: envelope[key] for key in ENVELOPE_FIELDS if key != "auth_tag" and key in envelope}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sign_envelope(envelope: Mapping[str, Any], secret: str) -> str:
    """Compute the HMAC tag for canonical envelope data with one secret."""
    if not isinstance(secret, str) or not secret:
        raise ValueError("signing secret required")
    return hmac.new(secret.encode("utf-8"), canonical_envelope_bytes(envelope), hashlib.sha256).hexdigest()


def verify_envelope_auth(envelope: Mapping[str, Any], secret: str) -> bool:
    """Verify the envelope tag using constant-time comparison."""
    if not isinstance(secret, str) or not secret:
        return False
    presented = envelope.get("auth_tag")
    if not _safe_hex64(presented):
        return False
    expected = sign_envelope(envelope, secret)
    return hmac.compare_digest(str(presented), expected)


def envelope_digest(envelope: Mapping[str, Any]) -> str:
    """Return the canonical digest of an envelope mapping.

    The digest covers canonical envelope data excluding ``auth_tag`` so it
    stays stable across signing and can be used as a content binding.
    """
    return hashlib.sha256(canonical_envelope_bytes(envelope)).hexdigest()


def build_context_snapshot(
    task_projection: Mapping[str, Any],
    dependency_evidence_refs: list[str],
    *,
    snapshot_ref: str,
    expires_at: str,
    max_bytes: int = MAX_SNAPSHOT_BYTES,
) -> dict[str, Any]:
    """Build one immutable, bounded context snapshot from allowlisted inputs.

    Only allowlisted task-card fields and project-relative evidence
    references enter the snapshot. Untrusted task text stays data: it is
    never expanded into commands or connector configuration here.
    """
    projection = {key: task_projection[key] for key in TASK_CARD_ALLOWLIST if key in task_projection}
    if not isinstance(snapshot_ref, str) or not _safe_relative(snapshot_ref):
        return {"decision": "deny_unsafe_content"}
    if any(not _safe_relative(ref) for ref in dependency_evidence_refs):
        return {"decision": "deny_unsafe_content"}
    if _parse_time(expires_at) is None:
        return {"decision": "deny_invalid_envelope"}
    body = {
        "schema_version": SCHEMA_VERSION,
        "sensitivity_label": SENSITIVITY_LABEL,
        "max_bytes": max_bytes,
        "task_projection": projection,
        "dependency_evidence_refs": list(dependency_evidence_refs),
        "expires_at": expires_at,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > max_bytes:
        return {"decision": "deny_payload_too_large"}
    return {
        "snapshot_ref": snapshot_ref,
        "snapshot_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "byte_size": len(encoded.encode("utf-8")),
        "schema_version": SCHEMA_VERSION,
        "sensitivity_label": SENSITIVITY_LABEL,
        "expires_at": expires_at,
        "decision": "snapshot_ready",
    }


def _event_id(message_id: str, decision: str) -> str:
    return hashlib.sha256(f"{message_id}|{decision}".encode("utf-8")).hexdigest()[:32]


def build_event_projection(
    envelope: Mapping[str, Any], *, decision: str, at: datetime, applied_revision: int | None
) -> dict[str, Any]:
    """Build the sanitized, append-only event projection for one decision."""
    event: dict[str, Any] = {
        "event_id": _event_id(str(envelope["message_id"]), decision),
        "schema_version": SCHEMA_VERSION,
        "message_id": envelope["message_id"],
        "idempotency_key": envelope["idempotency_key"],
        "type": envelope["type"],
        "project_id": envelope["project_id"],
        "task_id": envelope["task_id"],
        "run_id": envelope["run_id"],
        "attempt": envelope["attempt"],
        "lease_epoch": envelope["lease_epoch"],
        "sender_agent_id": envelope["sender_agent_id"],
        "context_snapshot_ref": envelope["context_snapshot_ref"],
        "context_snapshot_hash": envelope["context_snapshot_hash"],
        "payload_ref": envelope["payload_ref"],
        "decision": decision,
        "at": at.isoformat(),
    }
    if applied_revision is not None:
        event["applied_revision"] = applied_revision
    return event


def rebuild_run_view(events: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Rebuild the derived per-run view from the append-only event feed.

    The view is keyed by ``task_id/run_id`` and carries only safe
    projection fields. It can always be reconstructed from events, which
    proves the feed is evidence rather than a second lifecycle authority.
    """
    view: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=lambda item: str(item.get("at", ""))):
        if not isinstance(event, Mapping):
            continue
        task_id = event.get("task_id")
        run_id = event.get("run_id")
        if not _safe_identifier(task_id) or not _safe_identifier(run_id):
            continue
        key = f"{task_id}/{run_id}"
        current = view.get(key, {})
        merged = dict(current)
        for field in ("type", "attempt", "lease_epoch", "decision", "at", "applied_revision"):
            if field in event:
                merged[field] = event[field]
        merged["task_id"] = task_id
        merged["run_id"] = run_id
        view[key] = merged
    return view


def write_envelope_atomic(directory: Path, envelope: Mapping[str, Any]) -> Path:
    """Persist one immutable envelope file with tmp-file plus rename.

    Rewriting the same ``message_id`` with identical bytes is idempotent
    and returns the existing path. Rewriting it with different bytes
    raises ``ValueError`` because ``message_id`` is immutable.
    """
    message_id = str(envelope.get("message_id", ""))
    if not _safe_identifier(message_id):
        raise ValueError("unsafe message_id")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{message_id}.json"
    payload = json.dumps(dict(envelope), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") == payload:
            return target
        raise ValueError("immutable message_id rewrite denied")
    fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".envelope-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        Path(tmp_name).replace(target)
        _fsync_dir(directory)
    finally:
        Path(tmp_name).unlink(missing_ok=True)
    return target


def _fsync_dir(directory: Path) -> None:
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


# --- Exclusive, crash-safe event append ------------------------------------

_PATH_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}


def _path_lock(key: str) -> threading.Lock:
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


def _acquire_dir_lock(lockdir: Path, *, timeout_s: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            os.mkdir(str(lockdir))
            return
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        if time.monotonic() >= deadline:
            raise TimeoutError(f"event lock busy: {lockdir}")
        time.sleep(0.005)


def _release_dir_lock(lockdir: Path) -> None:
    try:
        os.rmdir(str(lockdir))
    except OSError:
        pass


def _repair_partial_tail(raw: bytes) -> bytes:
    """Drop a torn trailing line left by an interrupted append.

    A crash during the single append write can leave trailing bytes
    without a terminating newline. Complete lines are preserved; only
    the incomplete tail is discarded so the next exclusive append heals
    the feed without duplicating or interleaving records.
    """
    if not raw or raw.endswith(b"\n"):
        return raw
    head, _, tail = raw.rpartition(b"\n")
    try:
        data = json.loads(tail.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return head + b"\n" if head else b""
    if isinstance(data, dict) and data.get("event_id"):
        return raw
    return head + b"\n" if head else b""


def append_event_atomic(events_path: Path, event: Mapping[str, Any]) -> bool:
    """Append one sanitized event unless its ``event_id`` is present.

    Returns ``True`` when a new line was appended and ``False`` when the
    event was already recorded. The append holds a per-path in-process
    lock plus a cross-process directory lock, repairs a torn trailing
    line from an interrupted write, checks duplicates, then performs one
    ``O_APPEND`` write followed by flush and fsync, so concurrent
    writers cannot interleave and a crash cannot duplicate a record.
    """
    if _forbidden_key_present(event) or _forbidden_value_present(event):
        raise ValueError("unsafe event content")
    if not _safe_identifier(event.get("event_id")):
        raise ValueError("unsafe event_id")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    lockdir = events_path.parent / (events_path.name + ".lockdir")
    guard = _path_lock(str(events_path.resolve()) if events_path.exists() else str(events_path))
    payload = (json.dumps(dict(event), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    with guard:
        _acquire_dir_lock(lockdir)
        try:
            raw = b""
            if events_path.exists():
                raw = events_path.read_bytes()
                repaired = _repair_partial_tail(raw)
                if repaired != raw:
                    tmp_fd, tmp_name = tempfile.mkstemp(
                        dir=str(events_path.parent), prefix=".events-repair-", suffix=".tmp"
                    )
                    try:
                        with os.fdopen(tmp_fd, "wb") as handle:
                            handle.write(repaired)
                            handle.flush()
                            os.fsync(handle.fileno())
                        Path(tmp_name).replace(events_path)
                        _fsync_dir(events_path.parent)
                    finally:
                        Path(tmp_name).unlink(missing_ok=True)
                    raw = repaired
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(data, dict) and str(data.get("event_id")) == str(event.get("event_id")):
                    return False
            fd = os.open(str(events_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            try:
                view = memoryview(payload)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_dir(events_path.parent)
            return True
        finally:
            _release_dir_lock(lockdir)


def load_envelopes(directory: Path) -> list[dict[str, Any]]:
    """Load every envelope file in a directory in filename order."""
    if not directory.exists():
        return []
    envelopes: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            envelopes.append(data)
    return envelopes


def load_events(events_path: Path) -> list[dict[str, Any]]:
    """Load every event projection in append order.

    A torn trailing line without a terminating newline is ignored here
    and repaired on the next exclusive append.
    """
    if not events_path.exists():
        return []
    try:
        raw = events_path.read_bytes()
    except OSError:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    if raw and not raw.endswith(b"\n"):
        head, _, tail = text.rpartition("\n")
        try:
            data = json.loads(tail)
            tail_ok = isinstance(data, dict) and bool(data.get("event_id"))
        except ValueError:
            tail_ok = False
        if not tail_ok:
            text = head + "\n" if head else ""
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events


class TaskCardRevisionConflict(Exception):
    """Raised when a task-card compare-and-swap sees a stale revision."""


class TaskCardStore:
    """Single scheduler-owned adapter for revision-guarded task state.

    Each task owns one JSON file ``{task_id}.json`` holding ``task_id``,
    ``status``, and ``revision``. All transitions go through
    :meth:`compare_and_swap`, which holds an exclusive directory lock,
    re-reads the current file, enforces the expected revision, and
    commits with tmp-file plus atomic rename. Readers outside the
    scheduler must treat these files as read-only evidence.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._guard = _path_lock(f"task-cards:{self.root}")

    def _path(self, task_id: str) -> Path:
        if not _safe_identifier(task_id):
            raise ValueError("unsafe task_id")
        return self.root / f"{task_id}.json"

    def read(self, task_id: str) -> tuple[str, int] | None:
        path = self._path(task_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        status = data.get("status")
        revision = data.get("revision")
        if status not in TASK_STATUSES:
            return None
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            return None
        return (str(status), int(revision))

    def seed(self, task_id: str, *, status: str, revision: int) -> None:
        if not _safe_identifier(task_id) or status not in TASK_STATUSES:
            raise ValueError("invalid task seed")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("invalid revision seed")
        path = self._path(task_id)
        lockdir = self.root / ".store.lockdir"
        with self._guard:
            _acquire_dir_lock(lockdir)
            try:
                if path.exists():
                    current = self.read(task_id)
                    if current is not None:
                        return
                self._write_locked(path, {"task_id": task_id, "status": status, "revision": revision})
            finally:
                _release_dir_lock(lockdir)

    def overwrite(self, task_id: str, *, status: str, revision: int) -> None:
        """Heal the stored record during restart recovery only."""
        if not _safe_identifier(task_id) or status not in TASK_STATUSES:
            raise ValueError("invalid task record")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("invalid revision")
        path = self._path(task_id)
        lockdir = self.root / ".store.lockdir"
        with self._guard:
            _acquire_dir_lock(lockdir)
            try:
                self._write_locked(path, {"task_id": task_id, "status": status, "revision": revision})
            finally:
                _release_dir_lock(lockdir)

    def compare_and_swap(self, task_id: str, *, expected_revision: int, next_status: str) -> int:
        """Apply one guarded transition; return the new revision.

        Raises :class:`TaskCardRevisionConflict` when the stored revision
        differs from ``expected_revision``, and ``ValueError`` for unsafe
        inputs. Only the scheduler calls this method.
        """
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("invalid expected revision")
        if next_status not in TASK_STATUSES:
            raise ValueError("invalid next status")
        path = self._path(task_id)
        lockdir = self.root / ".store.lockdir"
        with self._guard:
            _acquire_dir_lock(lockdir)
            try:
                current = self.read(task_id)
                if current is None:
                    raise TaskCardRevisionConflict(f"missing task record: {task_id}")
                _, stored_revision = current
                if stored_revision != expected_revision:
                    raise TaskCardRevisionConflict(
                        f"revision conflict for {task_id}: expected {expected_revision}, stored {stored_revision}"
                    )
                applied = stored_revision + 1
                self._write_locked(path, {"task_id": task_id, "status": next_status, "revision": applied})
                return applied
            finally:
                _release_dir_lock(lockdir)

    def _write_locked(self, path: Path, body: dict[str, Any]) -> None:
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
        fd, tmp_name = tempfile.mkstemp(dir=str(self.root), prefix=".taskcard-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            Path(tmp_name).replace(path)
            _fsync_dir(self.root)
        finally:
            Path(tmp_name).unlink(missing_ok=True)


class Scheduler:
    """Revision-guarded, idempotent scheduler over atomic-file records."""

    def __init__(
        self,
        *,
        outbox_dir: Path,
        inbox_dir: Path,
        events_path: Path,
        task_cards_dir: Path | None = None,
        auth_secrets: Mapping[str, str] | None = None,
    ) -> None:
        self.outbox_dir = outbox_dir
        self.inbox_dir = inbox_dir
        self.events_path = events_path
        cards_root = task_cards_dir if task_cards_dir is not None else inbox_dir.parent / "task-cards"
        self.task_cards_dir = cards_root
        self.store = TaskCardStore(cards_root)
        self.auth_secrets: dict[str, str] = dict(auth_secrets) if auth_secrets else {}
        self.seen_message_ids: set[str] = set()
        self.idempotency_index: dict[str, str] = {}
        self.lease_epochs: dict[str, int] = {}
        self.task_revisions: dict[str, int] = {}
        self.task_statuses: dict[str, str] = {}

    def register_task(self, task_id: str, *, status: str, revision: int) -> None:
        """Seed one task record through the scheduler-owned store."""
        self.store.seed(task_id, status=status, revision=revision)
        stored = self.store.read(task_id)
        if stored is not None:
            current_status, current_revision = stored
            self.task_revisions[task_id] = current_revision
            self.task_statuses[task_id] = current_status

    def ingest(
        self,
        envelope: object,
        *,
        now: datetime,
        expected_sender: str,
        expected_token_ref: str,
        expected_revision: int,
    ) -> dict[str, Any]:
        """Validate one envelope and apply at most one guarded transition.

        Authentication uses the scheduler-owned secret for
        ``sender_agent_id`` to verify ``auth_tag`` over canonical envelope
        data; public reference equality alone never authenticates. Every
        denial is fail-closed and persists a sanitized event only for
        well-formed envelopes, so replays and probes stay observable
        without ever mutating task state or duplicating a delivery.
        """
        if not isinstance(envelope, Mapping):
            return {"decision": "deny_invalid_envelope"}
        denial = validate_envelope(envelope, now=now)
        if denial is not None:
            return {"decision": denial, "message_id": str(envelope.get("message_id", ""))}
        assert isinstance(envelope, Mapping)
        message_id = str(envelope["message_id"])
        idempotency_key = str(envelope["idempotency_key"])
        task_id = str(envelope["task_id"])
        run_id = str(envelope["run_id"])
        sender = str(envelope["sender_agent_id"])
        token_ref = str(envelope["capability_token_ref"])

        secret = self.auth_secrets.get(sender)
        if secret is None or not verify_envelope_auth(envelope, secret):
            self._record(envelope, decision="deny_unauthenticated", now=now, applied_revision=None)
            return {"decision": "deny_unauthenticated", "message_id": message_id}

        if not hmac.compare_digest(sender, expected_sender) or not hmac.compare_digest(
            token_ref, expected_token_ref
        ):
            self._record(envelope, decision="deny_unauthenticated", now=now, applied_revision=None)
            return {"decision": "deny_unauthenticated", "message_id": message_id}

        if message_id in self.seen_message_ids:
            return {"decision": "deny_duplicate", "message_id": message_id}
        if idempotency_key in self.idempotency_index and self.idempotency_index[idempotency_key] != message_id:
            self._record(envelope, decision="deny_duplicate", now=now, applied_revision=None)
            return {"decision": "deny_duplicate", "message_id": message_id}

        lease_key = f"{task_id}/{run_id}"
        current_epoch = self.lease_epochs.get(lease_key, 0)
        epoch = int(envelope["lease_epoch"])
        if epoch < current_epoch:
            self._record(envelope, decision="deny_stale_epoch", now=now, applied_revision=None)
            return {"decision": "deny_stale_epoch", "message_id": message_id}

        stored = self.store.read(task_id)
        if stored is not None:
            self.task_statuses[task_id] = stored[0]
            self.task_revisions[task_id] = stored[1]
        current_revision = self.task_revisions.get(task_id)
        if current_revision is None or current_revision != expected_revision:
            self._record(envelope, decision="deny_revision_conflict", now=now, applied_revision=None)
            return {
                "decision": "deny_revision_conflict",
                "message_id": message_id,
                "incident": "reconciliation_required",
                "expected_revision": expected_revision,
                "current_revision": current_revision,
            }

        current_status = self.task_statuses.get(task_id, "READY")
        message_type = str(envelope["type"])
        next_status = ALLOWED_TRANSITIONS.get((current_status, message_type))
        if next_status is None:
            self._record(envelope, decision="deny_invalid_transition", now=now, applied_revision=None)
            return {"decision": "deny_invalid_transition", "message_id": message_id}

        # Commit order: persist the inbox delivery file first (idempotent
        # on identical bytes), then apply the single revision-guarded
        # task-card transition through the owned store, then append the
        # accepted event. Recovery replays from outbox files plus inbox
        # keys, store revisions, and event ids, which keeps a restart
        # from duplicating a dispatch or losing an accepted one.
        self.seen_message_ids.add(message_id)
        self.idempotency_index[idempotency_key] = message_id
        self.lease_epochs[lease_key] = max(current_epoch, epoch)
        delivery_path = self.inbox_dir / task_id / f"{message_id}.json"
        try:
            write_envelope_atomic(delivery_path.parent, envelope)
        except ValueError:
            self._record(envelope, decision="deny_duplicate", now=now, applied_revision=None)
            return {"decision": "deny_duplicate", "message_id": message_id}

        try:
            applied_revision = self.store.compare_and_swap(
                task_id, expected_revision=current_revision, next_status=next_status
            )
        except TaskCardRevisionConflict:
            stored_now = self.store.read(task_id)
            if stored_now is not None:
                self.task_statuses[task_id] = stored_now[0]
                self.task_revisions[task_id] = stored_now[1]
            self._record(envelope, decision="deny_revision_conflict", now=now, applied_revision=None)
            return {
                "decision": "deny_revision_conflict",
                "message_id": message_id,
                "incident": "reconciliation_required",
                "expected_revision": expected_revision,
                "current_revision": self.task_revisions.get(task_id),
            }

        self.task_revisions[task_id] = applied_revision
        self.task_statuses[task_id] = next_status
        self._record(envelope, decision="accepted_" + message_type, now=now, applied_revision=applied_revision)
        return {
            "decision": "accepted_" + message_type,
            "message_id": message_id,
            "task_id": task_id,
            "run_id": run_id,
            "status": next_status,
            "applied_revision": applied_revision,
            "delivery_ref": f"{task_id}/{message_id}.json",
        }

    def hydrate(self) -> None:
        """Rebuild idempotency, epoch, and revision state from disk.

        Restart recovery calls this before replaying the outbox so an
        accepted dispatch is never applied twice: inbox files restore the
        seen message and idempotency keys, the owned task-card store
        restores durable revisions, and events restore lease epochs plus
        the last applied revision and heal the store forward when the
        event feed is ahead.
        """
        if self.inbox_dir.exists():
            for path in sorted(self.inbox_dir.rglob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if not isinstance(data, dict):
                    continue
                message_id = data.get("message_id")
                idempotency_key = data.get("idempotency_key")
                if _safe_identifier(message_id):
                    self.seen_message_ids.add(str(message_id))
                if _safe_hex64(idempotency_key) and _safe_identifier(message_id):
                    self.idempotency_index.setdefault(str(idempotency_key), str(message_id))
                task_id = data.get("task_id")
                run_id = data.get("run_id")
                epoch = data.get("lease_epoch")
                if (
                    _safe_identifier(task_id)
                    and _safe_identifier(run_id)
                    and isinstance(epoch, int)
                    and not isinstance(epoch, bool)
                    and epoch >= 1
                ):
                    lease_key = f"{task_id}/{run_id}"
                    self.lease_epochs[lease_key] = max(self.lease_epochs.get(lease_key, 0), epoch)
        if self.store.root.exists():
            for path in sorted(self.store.root.glob("*.json")):
                task_id = path.stem
                stored = self.store.read(task_id)
                if stored is not None:
                    status, revision = stored
                    self.task_statuses[task_id] = status
                    self.task_revisions[task_id] = max(self.task_revisions.get(task_id, 0), revision)
        for event in load_events(self.events_path):
            task_id = event.get("task_id")
            applied = event.get("applied_revision")
            if _safe_identifier(task_id) and isinstance(applied, int) and not isinstance(applied, bool):
                self.task_revisions[str(task_id)] = max(self.task_revisions.get(str(task_id), 0), applied)
                if event.get("decision", "").startswith("accepted_") and event.get("type") in MESSAGE_TYPES:
                    message_type = str(event["type"])
                    current = self.task_statuses.get(str(task_id), "READY")
                    next_status = ALLOWED_TRANSITIONS.get((current, message_type))
                    if next_status is not None:
                        self.task_statuses[str(task_id)] = next_status
            lease_key = (
                f"{event.get('task_id')}/{event.get('run_id')}"
                if _safe_identifier(event.get("task_id")) and _safe_identifier(event.get("run_id"))
                else None
            )
            epoch = event.get("lease_epoch")
            if lease_key and isinstance(epoch, int) and not isinstance(epoch, bool) and epoch >= 1:
                self.lease_epochs[lease_key] = max(self.lease_epochs.get(lease_key, 0), epoch)
        # Heal the durable store forward when accepted events are ahead
        # (crash between event append and store commit is recovered here).
        for task_id, revision in list(self.task_revisions.items()):
            stored = self.store.read(task_id)
            status = self.task_statuses.get(task_id)
            if stored is None and status in TASK_STATUSES:
                try:
                    self.store.overwrite(task_id, status=status, revision=revision)
                except ValueError:
                    pass
            elif stored is not None and stored[1] < revision and status in TASK_STATUSES:
                try:
                    self.store.overwrite(task_id, status=status, revision=revision)
                except ValueError:
                    pass

    def recover(self, *, now: datetime, resolve: Any) -> list[dict[str, Any]]:
        """Replay pending outbox files after a restart without duplication.

        Already-accepted message IDs stay denied, while inbox files with
        no matching accepted event are treated as interrupted commits and
        allowed to complete exactly once. ``resolve`` maps one envelope
        to its ``(expected_sender, expected_token_ref, expected_revision)``
        triple.
        """
        results: list[dict[str, Any]] = []
        self.hydrate()
        accepted_ids = {
            str(event.get("message_id"))
            for event in load_events(self.events_path)
            if isinstance(event, dict)
            and str(event.get("decision", "")).startswith("accepted_")
            and _safe_identifier(event.get("message_id"))
        }
        for envelope in load_envelopes(self.outbox_dir):
            message_id = envelope.get("message_id")
            if (
                _safe_identifier(message_id)
                and str(message_id) in self.seen_message_ids
                and str(message_id) not in accepted_ids
            ):
                self.seen_message_ids.discard(str(message_id))
                key = envelope.get("idempotency_key")
                if _safe_hex64(key) and self.idempotency_index.get(str(key)) == str(message_id):
                    del self.idempotency_index[str(key)]
            try:
                expected_sender, expected_token_ref, expected_revision = resolve(envelope)
            except Exception:
                results.append({"decision": "deny_invalid_envelope", "message_id": str(envelope.get("message_id", ""))})
                continue
            results.append(
                self.ingest(
                    envelope,
                    now=now,
                    expected_sender=expected_sender,
                    expected_token_ref=expected_token_ref,
                    expected_revision=expected_revision,
                )
            )
        return results

    def _record(self, envelope: Mapping[str, Any], *, decision: str, now: datetime, applied_revision: int | None) -> None:
        try:
            append_event_atomic(
                self.events_path,
                build_event_projection(envelope, decision=decision, at=now, applied_revision=applied_revision),
            )
        except ValueError:
            return
