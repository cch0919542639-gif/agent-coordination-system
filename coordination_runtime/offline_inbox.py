"""Offline admission only: no transport, process, controller or production verifier."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3

MAX_BYTES = 16 * 1024
DOMAIN = b"coordination-phase15-offline-v1\x00"
APPLICATION_ID = 0x434F4631
SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
IDS = {"controller_id", "machine_id", "project_id", "repository_id", "task_id",
       "owner", "run_id", "payload_id", "request_id", "message_id"}
INTS = {"controller_epoch", "machine_epoch", "attempt", "sequence", "fence",
        "expected_version", "execution_budget_ms", "protocol_version"}
DIGESTS = {"base_sha": 40, "contract_sha256": 64, "payload_sha256": 64}
BODY_KEYS = IDS | INTS | DIGESTS.keys() | {"operation"}
DYNAMIC = {"request_id", "message_id", "sequence"}
NAMESPACE = {"controller_id", "controller_epoch", "machine_id", "machine_epoch",
             "project_id", "repository_id"}
SCHEMA = """
CREATE TABLE metadata (
 id INTEGER PRIMARY KEY CHECK(id=1), namespace TEXT NOT NULL,
 sequence INTEGER NOT NULL CHECK(sequence>=0));
CREATE TABLE receipts (
 request_id TEXT PRIMARY KEY, message_id TEXT NOT NULL UNIQUE,
 run_id TEXT NOT NULL UNIQUE, task_id TEXT NOT NULL, fence INTEGER NOT NULL,
 digest TEXT NOT NULL, ack TEXT NOT NULL, UNIQUE(task_id,fence));
"""


class InboxRefused(RuntimeError):
    """Fixed categories only; never echo message or verifier/database errors."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _refuse(code):
    raise InboxRefused(code)


def _identifier(value):
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        _refuse("identifier_invalid")


def _integer(value, minimum=1, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        _refuse("integer_invalid")


def _body(body):
    if type(body) is not dict or body.keys() != BODY_KEYS:
        _refuse("body_schema_invalid")
    for key in IDS:
        _identifier(body[key])
    for key in INTS:
        _integer(body[key], 0 if key == "expected_version" else 1)
    for key, size in DIGESTS.items():
        if type(body[key]) is not str or not re.fullmatch(r"[a-f0-9]{%d}" % size, body[key]):
            _refuse("digest_invalid")
    if (body["protocol_version"] != 1 or body["operation"] != "dispatch"
            or body["execution_budget_ms"] > 180000):
        _refuse("operation_or_budget_invalid")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _refuse("duplicate_key")
        result[key] = value
    return result


def _receipt(raw, body, digest):
    try:
        ack = json.loads(raw)
        core = dict(phase="received_durable", ack_for_message_id=body["message_id"],
                    command_digest=digest, offline_only=True)
        expected = core | {"receipt_digest": hashlib.sha256(canonical(core)).hexdigest()}
        if canonical(ack) != canonical(expected):
            _refuse("journal_receipt_invalid")
        return ack
    except (ValueError, TypeError, RecursionError):
        _refuse("journal_receipt_invalid")


class OfflineInbox:
    """Explicit trusted binding/verifier; construction never accesses a journal.

    verify_signature(signature_bytes, domain_separated_bytes) must return True.
    This package supplies no production verifier and cannot launch admitted work.
    """

    def __init__(self, path, *, binding, key_ref, key_epoch, verify_signature):
        if type(binding) is not dict or binding.keys() != BODY_KEYS - DYNAMIC:
            _refuse("binding_invalid")
        _body(binding | dict(request_id="validation", message_id="validation", sequence=1))
        _identifier(key_ref)
        _integer(key_epoch)
        if not callable(verify_signature):
            _refuse("verifier_required")
        self.path = Path(path).resolve()
        self._binding = dict(binding)
        self._key_ref, self._key_epoch = key_ref, key_epoch
        self._verify_signature = verify_signature
        self._namespace = canonical({k: binding[k] for k in NAMESPACE}).decode()

    def _validate(self, raw):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
            _refuse("frame_invalid")
        try:
            envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                                  parse_constant=lambda _: _refuse("json_invalid"))
        except (ValueError, UnicodeError, RecursionError):
            _refuse("json_invalid")
        if type(envelope) is not dict or envelope.keys() != {"body", "authentication"}:
            _refuse("envelope_schema_invalid")
        body, auth = envelope["body"], envelope["authentication"]
        _body(body)
        if any(body[k] != v for k, v in self._binding.items()):
            _refuse("binding_mismatch")
        if type(auth) is not dict or auth.keys() != {"key_ref", "key_epoch", "signature"}:
            _refuse("authentication_invalid")
        _identifier(auth["key_ref"])
        _integer(auth["key_epoch"])
        if auth["key_ref"] != self._key_ref or auth["key_epoch"] != self._key_epoch:
            _refuse("authentication_invalid")
        signature = auth["signature"]
        if type(signature) is not str or not re.fullmatch(r"[a-f0-9]{128}", signature):
            _refuse("authentication_invalid")
        signed = DOMAIN + canonical({"body": body, "authentication": {
            "key_ref": auth["key_ref"], "key_epoch": auth["key_epoch"]}})
        try:
            verified = self._verify_signature(bytes.fromhex(signature), signed)
        except Exception:
            _refuse("signature_invalid")
        if verified is not True:
            _refuse("signature_invalid")
        return body, hashlib.sha256(canonical(envelope)).hexdigest()

    def _check(self, db):
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if (db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
                or tables != {"metadata", "receipts"}):
            _refuse("journal_schema_invalid")
        meta = db.execute("SELECT namespace,sequence FROM metadata WHERE id=1").fetchone()
        if not meta or meta[0] != self._namespace:
            _refuse("journal_namespace_mismatch")
        _integer(meta[1], 0)
        return meta[1]

    @contextmanager
    def _db(self, *, initialize=False):
        db = None
        try:
            db = sqlite3.connect(self.path.as_uri() + ("?mode=rwc" if initialize else "?mode=rw"),
                                 uri=True, timeout=5, isolation_level=None)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except sqlite3.Error:
            _refuse("journal_unavailable")
        finally:
            if db is not None:
                db.close()  # An uncommitted error/exception rolls back.

    def initialize(self):
        """Explicitly create only this separate inbox; never migrate existing state."""
        with self._db(initialize=True) as db:
            app = db.execute("PRAGMA application_id").fetchone()[0]
            version = db.execute("PRAGMA user_version").fetchone()[0]
            entries = db.execute("SELECT name FROM sqlite_master").fetchall()
            if app == version == 0 and not entries:
                for statement in SCHEMA.split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute("INSERT INTO metadata VALUES(1,?,0)", (self._namespace,))
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            self._check(db)
        return {"schema_version": SCHEMA_VERSION, "offline_only": True}

    def receive(self, raw):
        """Authenticate before opening DB; commit receipt before returning an ACK."""
        body, digest = self._validate(raw)
        with self._db() as db:
            sequence = self._check(db)
            prior = db.execute("SELECT digest,ack FROM receipts WHERE request_id=?",
                               (body["request_id"],)).fetchone()
            if prior:
                if prior[0] != digest:
                    _refuse("request_conflict")
                return _receipt(prior[1], body, digest)
            if body["sequence"] <= sequence:
                _refuse("sequence_stale")
            if db.execute("SELECT 1 FROM receipts WHERE message_id=? OR run_id=? OR (task_id=? AND fence=?)",
                          (body["message_id"], body["run_id"], body["task_id"], body["fence"])).fetchone():
                _refuse("generation_conflict")
            ack = dict(phase="received_durable", ack_for_message_id=body["message_id"],
                       command_digest=digest, offline_only=True)
            ack["receipt_digest"] = hashlib.sha256(canonical(ack)).hexdigest()
            db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?,?)",
                       (body["request_id"], body["message_id"], body["run_id"], body["task_id"],
                        body["fence"], digest, canonical(ack).decode()))
            db.execute("UPDATE metadata SET sequence=? WHERE id=1", (body["sequence"],))
        return ack
