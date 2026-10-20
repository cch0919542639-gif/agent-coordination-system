"""SQLite runtime authority and durable board intents; no worker/network writes."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

DEFAULT_DB = Path(__file__).resolve().parents[1] / "coordination/monitor/runtime/coordination-v2/state.db"
APPLICATION_ID = 0x434F4F32
SCHEMA_VERSION = 4
BUSY_SECONDS = 5
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
TERMINAL = {"completed", "failed", "lost", "recovery_required"}
TRANSITIONS = {
    "claimed": {"launching", "failed", "recovery_required"},
    "launching": {"running", "failed", "recovery_required"},
    "running": {"submitted", "stopping", "failed", "lost", "recovery_required"},
    "submitted": {"verifying", "recovery_required"},
    "verifying": {"completed", "failed", "recovery_required"},
    "stopping": {"failed", "lost", "recovery_required"},
}
SCHEMA = """
CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), last_clock_ms INTEGER NOT NULL);
INSERT INTO metadata VALUES(1,0);
CREATE TABLE runtime_tasks (
 project_id TEXT NOT NULL, task_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>=0),
 fence INTEGER NOT NULL CHECK(fence>=0), active_run_id TEXT,
 PRIMARY KEY(project_id,task_id));
CREATE TABLE runs (
 project_id TEXT NOT NULL, run_id TEXT NOT NULL, task_id TEXT NOT NULL,
 owner TEXT NOT NULL, fence INTEGER NOT NULL CHECK(fence>0), phase TEXT NOT NULL,
 lease_until_ms INTEGER NOT NULL, heartbeat_ms INTEGER NOT NULL,
 base_sha TEXT NOT NULL, contract_sha256 TEXT NOT NULL,
 PRIMARY KEY(project_id,run_id), UNIQUE(project_id,task_id,fence),
 FOREIGN KEY(project_id,task_id) REFERENCES runtime_tasks(project_id,task_id));
CREATE TABLE requests (
 project_id TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL,
 result_json TEXT NOT NULL, PRIMARY KEY(project_id,request_id));
CREATE TABLE events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, schema_version INTEGER NOT NULL,
 event_id TEXT UNIQUE NOT NULL, project_id TEXT NOT NULL, task_id TEXT NOT NULL,
 run_id TEXT NOT NULL, agent_id TEXT NOT NULL, event_type TEXT NOT NULL,
 timestamp_ms INTEGER NOT NULL, causation_id TEXT NOT NULL, artifact_ref TEXT);
"""
TABLES = {"metadata", "runtime_tasks", "runs", "requests", "events"}
INTENT_SCHEMA = """
CREATE TABLE project_bindings (project_id TEXT PRIMARY KEY, root_digest TEXT NOT NULL UNIQUE);
CREATE TABLE board_intents (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 project_id TEXT NOT NULL, request_id TEXT NOT NULL, task_id TEXT NOT NULL,
 run_id TEXT NOT NULL, owner TEXT NOT NULL, fence INTEGER NOT NULL, phase TEXT NOT NULL,
 root_digest TEXT NOT NULL, filename TEXT NOT NULL,
 source_state TEXT NOT NULL, target_state TEXT NOT NULL,
 before_sha TEXT NOT NULL, after_sha TEXT NOT NULL, status TEXT NOT NULL,
 reason TEXT NOT NULL DEFAULT '', UNIQUE(project_id,request_id),
 FOREIGN KEY(project_id,request_id) REFERENCES requests(project_id,request_id));
"""
PARALLEL_SCHEMA = """
CREATE TABLE parallel_projects (
 project_id TEXT PRIMARY KEY, root_digest TEXT NOT NULL UNIQUE,
 workspace_root_digest TEXT NOT NULL, mode TEXT NOT NULL, capacity INTEGER NOT NULL);
CREATE TABLE parallel_runs (
 project_id TEXT NOT NULL, run_id TEXT NOT NULL, task_id TEXT NOT NULL,
 owner TEXT NOT NULL, fence INTEGER NOT NULL, base_sha TEXT NOT NULL,
 path_digest TEXT NOT NULL UNIQUE, scope_json TEXT NOT NULL, resources_json TEXT NOT NULL,
 dependencies_json TEXT NOT NULL, filename TEXT NOT NULL, card_sha TEXT NOT NULL,
 output TEXT NOT NULL, claim_request TEXT NOT NULL, status TEXT NOT NULL,
 process_json TEXT NOT NULL DEFAULT '{}', delivery_sha TEXT NOT NULL DEFAULT '',
 submit_request TEXT NOT NULL DEFAULT '', PRIMARY KEY(project_id,run_id));
"""
EVIDENCE_SCHEMA = """
CREATE TABLE evidence_candidates (
 project_id TEXT NOT NULL,evidence_id TEXT NOT NULL,run_id TEXT NOT NULL,
 task_id TEXT NOT NULL,owner TEXT NOT NULL,fence INTEGER NOT NULL,
 base_sha TEXT NOT NULL,candidate_sha TEXT NOT NULL,snapshot_sha TEXT NOT NULL,
 checker_sha TEXT NOT NULL,policy_json TEXT NOT NULL,validation_digest TEXT NOT NULL,
 status TEXT NOT NULL,process_json TEXT NOT NULL DEFAULT '{}',
 tested_sha TEXT NOT NULL DEFAULT '',reviewed_sha TEXT NOT NULL DEFAULT '',
 review_json TEXT NOT NULL DEFAULT '',PRIMARY KEY(project_id,evidence_id));
CREATE TABLE publication_queue (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL,
 request_id TEXT NOT NULL,evidence_id TEXT NOT NULL,target_ref TEXT NOT NULL,
 expected_sha TEXT NOT NULL,candidate_sha TEXT NOT NULL,status TEXT NOT NULL,
 integrated_sha TEXT NOT NULL DEFAULT '',UNIQUE(project_id,request_id),
 FOREIGN KEY(project_id,evidence_id) REFERENCES evidence_candidates(project_id,evidence_id));
"""
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,149}\.md")


def projection_states(command):
    if command["op"] == "claim":
        return "ready", "in_progress"
    if command["op"] == "transition":
        if command["phase"] == "submitted":
            return "in_progress", "review"
        if command["phase"] in {"failed", "lost", "recovery_required"}:
            return "in_progress", "blocked"
    raise StateError("Runtime command has no permitted board projection.")


def _projection(command, value):
    if not isinstance(value, dict) or set(value) != {"root_digest", "filename", "before_sha", "after_sha"}:
        raise StateError("Invalid board projection shape.")
    value = dict(value)
    for key in ("root_digest", "before_sha", "after_sha"):
        if not isinstance(value[key], str) or not re.fullmatch("[a-f0-9]{64}", value[key]):
            raise StateError("Invalid projection digest.")
    if not isinstance(value["filename"], str) or not FILENAME.fullmatch(value["filename"]) or value["filename"] == "README.md":
        raise StateError("Invalid projection filename.")
    projection_states(command)
    return value



class StateError(Exception):
    """A fixed local failure category; never includes SQL, paths or input text."""


def _id(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise StateError("Invalid runtime identifier.")


def _integer(value, minimum=0, maximum=2**63-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise StateError("Invalid runtime integer.")


def _verify(db, versions=(SCHEMA_VERSION,)):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT GLOB 'sqlite_*'")}
    version = db.execute("PRAGMA user_version").fetchone()[0]
    expected = set(TABLES)
    if version >= 2: expected |= {"project_bindings", "board_intents"}
    if version >= 3: expected |= {"parallel_projects", "parallel_runs"}
    if version >= 4: expected |= {"evidence_candidates", "publication_queue"}
    if (db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or version not in versions or tables != expected):
        raise StateError("Unsupported runtime schema; migration required.")
    clock = db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()
    if not clock or type(clock[0]) is not int or clock[0] < 0:
        raise StateError("Runtime clock metadata invalid; recovery required.")


class StateController:
    def __init__(self, path=DEFAULT_DB, *, _clock=None):
        self.path = Path(path).resolve()
        self._clock = _clock or (lambda: time.time_ns() // 1_000_000)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=BUSY_SECONDS, isolation_level=None)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            app = db.execute("PRAGMA application_id").fetchone()[0]
            tables = db.execute("SELECT name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'").fetchall()
            if version == app == 0 and not tables:
                for statement in (SCHEMA + INTENT_SCHEMA + PARALLEL_SCHEMA + EVIDENCE_SCHEMA).split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            _verify(db)
            db.commit()
            return {"schema_version": SCHEMA_VERSION}
        except sqlite3.Error:
            raise StateError("Runtime database initialization failed.") from None
        finally:
            if db is not None:
                db.close()

    @contextmanager
    def _db(self, write=False, *, versions=(SCHEMA_VERSION,)):
        db = None
        try:
            db = sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                                 uri=True, timeout=BUSY_SECONDS, isolation_level=None)
            db.row_factory = sqlite3.Row
            if write:
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("PRAGMA synchronous=FULL")
                # ponytail: one SQLite writer; no extra lease service or thread.
                db.execute("BEGIN IMMEDIATE")
            else:
                db.execute("BEGIN")  # One coherent read snapshot across tables.
            _verify(db, versions)
            yield db
            if write:
                db.commit()
        except sqlite3.Error:
            raise StateError("Runtime database unavailable or operation refused.") from None
        finally:
            if db is not None:
                db.close()

    def _now(self):
        now = self._clock()
        _integer(now, maximum=2**63-1-3_600_000)
        return now

    @staticmethod
    def _snapshot(db, project, task):
        row = db.execute("SELECT * FROM runtime_tasks WHERE project_id=? AND task_id=?", (project, task)).fetchone()
        result = dict(row) if row else {"project_id": project, "task_id": task, "version": 0,
                                       "fence": 0, "active_run_id": None}
        run = db.execute("SELECT * FROM runs WHERE project_id=? AND run_id=?",
                         (project, result["active_run_id"])).fetchone()
        result["run"] = dict(run) if run else None
        return result

    def get(self, project_id, task_id):
        _id(project_id); _id(task_id)
        with self._db() as db:
            result = self._snapshot(db, project_id, task_id)
            floor = db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()[0]
            now, run = self._now(), result["run"]
            result["lease_valid"] = bool(now >= floor and run and run["phase"] not in TERMINAL
                                         and now < run["lease_until_ms"] and run["fence"] == result["fence"])
            return result

    def history(self, project_id, task_id, *, after_fence=0, limit=100):
        _id(project_id); _id(task_id); _integer(after_fence); _integer(limit, 1, 100)
        with self._db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM runs WHERE project_id=? AND task_id=? AND fence>? ORDER BY fence LIMIT ?",
                                               (project_id, task_id, after_fence, limit))]

    def events(self, project_id, *, after_sequence=0, limit=100):
        _id(project_id); _integer(after_sequence); _integer(limit, 1, 100)
        with self._db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM events WHERE project_id=? AND sequence>? ORDER BY sequence LIMIT ?",
                                               (project_id, after_sequence, limit))]

    @staticmethod
    def _validate(command):
        if not isinstance(command, dict):
            raise StateError("Invalid runtime command.")
        command = dict(command)
        fields = {"claim": {"owner", "lease_seconds", "base_sha", "contract_sha256"},
                  "renew": {"owner", "fence", "lease_seconds"},
                  "transition": {"owner", "fence", "phase"},
                  "revoke": {"actor", "fence", "reason"}}
        common = {"op", "project_id", "task_id", "request_id", "expected_version", "run_id"}
        op = command.get("op")
        if not isinstance(op, str) or op not in fields or set(command) != common | fields[op]:
            raise StateError("Invalid runtime command shape.")
        for key in ("project_id", "task_id", "request_id", "run_id", "actor" if op == "revoke" else "owner"):
            _id(command[key])
        _integer(command["expected_version"])
        if op != "claim":
            _integer(command["fence"], 1)
        if op in {"claim", "renew"}:
            _integer(command["lease_seconds"], 1, 3600)
        if op == "claim":
            for key, size in (("base_sha", 40), ("contract_sha256", 64)):
                if not isinstance(command[key], str) or re.fullmatch("[a-f0-9]{" + str(size) + "}", command[key]) is None:
                    raise StateError("Invalid runtime source digest.")
        if op == "transition" and (not isinstance(command["phase"], str) or command["phase"] not in set(TRANSITIONS) | TERMINAL):
            raise StateError("Invalid runtime phase.")
        if op == "revoke" and command["reason"] not in ("expired", "operator", "interrupted", "completed"):
            raise StateError("Invalid revocation reason.")
        return command

    def apply(self, command, *, projection=None, reservation=None, _parallel=False, _connection=None, _admission_check=None):
        c = self._validate(command)
        projection = _projection(c, projection) if projection is not None else None
        if reservation is not None:
            from .parallel_policy import validate_reservation
            reservation = validate_reservation(reservation)
        op, project, task = c["op"], c["project_id"], c["task_id"]
        envelope = c if projection is None else {"command": c, "projection": projection}
        if reservation is not None:
            envelope = {"command": c, "projection": projection, "reservation": reservation}
        digest = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with (self._db(write=True) if _connection is None else nullcontext(_connection)) as db:
            prior = db.execute("SELECT digest,result_json FROM requests WHERE project_id=? AND request_id=?",
                               (project, c["request_id"])).fetchone()
            if prior:
                if prior["digest"] != digest:
                    raise StateError("Idempotency key conflicts with recorded command.")
                return {"replayed": True, "recorded": json.loads(prior["result_json"])}
            mode = db.execute("SELECT mode FROM parallel_projects WHERE project_id=?", (project,)).fetchone()
            enabled = bool(mode and mode[0] == "parallel")
            if enabled and not _parallel:
                raise StateError("Parallel project requires controller routing.")
            if enabled and op == "claim" and (reservation is None or projection is None):
                raise StateError("Parallel claim requires atomic admission and board intent.")
            if reservation is not None:
                if not enabled or not _parallel or op != "claim" or projection is None:
                    raise StateError("Parallel admission is not enabled.")
                from .parallel_policy import check_admission
                if _admission_check is None:
                    raise StateError("Parallel admission requires live controller preconditions.")
                _admission_check()
                check_admission(db, c, projection, reservation)
            if (op not in {"renew", "revoke"} and db.execute(
                    "SELECT 1 FROM board_intents WHERE project_id=? AND task_id=? AND status IN ('pending','recovery_required')",
                    (project, task)).fetchone()):
                raise StateError("Unresolved board intent requires reconciliation.")
            if projection is not None:
                db.execute("INSERT OR IGNORE INTO project_bindings VALUES(?,?)", (project, projection["root_digest"]))
                bound = db.execute("SELECT root_digest FROM project_bindings WHERE project_id=?", (project,)).fetchone()
                if not bound or bound[0] != projection["root_digest"]:
                    raise StateError("Project board binding mismatched.")
            now = self._now()
            if now < db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()[0]:
                raise StateError("Clock moved backwards; recovery required.")
            state = self._snapshot(db, project, task)
            if c["expected_version"] != state["version"]:
                raise StateError("Runtime version conflict.")
            _integer(state["version"], maximum=2**63-2)
            _integer(state["fence"], maximum=2**63-2)
            if op == "claim":
                if state["active_run_id"] is not None:
                    raise StateError("Active authority requires explicit revocation.")
                if db.execute("SELECT 1 FROM runs WHERE project_id=? AND run_id=?", (project, c["run_id"])).fetchone():
                    raise StateError("Runtime run ID cannot be reused.")
                db.execute("INSERT OR IGNORE INTO runtime_tasks VALUES(?,?,0,0,NULL)", (project, task))
                db.execute("UPDATE runtime_tasks SET fence=fence+1,version=version+1,active_run_id=? WHERE project_id=? AND task_id=?",
                           (c["run_id"], project, task))
                fence = state["fence"] + 1
                db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (project, c["run_id"], task, c["owner"], fence, "claimed", now + c["lease_seconds"] * 1000,
                            now, c["base_sha"], c["contract_sha256"]))
            else:
                run = state["run"]
                if not run or c["run_id"] != run["run_id"] or c["fence"] != state["fence"] or c["fence"] != run["fence"]:
                    raise StateError("Runtime authority is stale or revoked.")
                if op == "revoke":
                    if ((c["reason"] == "expired" and now < run["lease_until_ms"])
                            or (c["reason"] == "completed" and run["phase"] != "completed")):
                        raise StateError("Revocation reason conflicts with runtime state.")
                    phase = run["phase"] if run["phase"] in TERMINAL else "recovery_required"
                    db.execute("UPDATE runs SET phase=?,lease_until_ms=0 WHERE project_id=? AND run_id=?", (phase, project, c["run_id"]))
                    db.execute("UPDATE runtime_tasks SET fence=fence+1,version=version+1,active_run_id=NULL WHERE project_id=? AND task_id=?", (project, task))
                else:
                    if c["owner"] != run["owner"] or now >= run["lease_until_ms"]:
                        raise StateError("Runtime lease expired or owner mismatched.")
                    if run["phase"] in TERMINAL:
                        raise StateError("Terminal runtime cannot write or renew.")
                    if op == "transition":
                        if c["phase"] not in TRANSITIONS[run["phase"]]:
                            raise StateError("Runtime phase transition refused.")
                        db.execute("UPDATE runs SET phase=? WHERE project_id=? AND run_id=?", (c["phase"], project, c["run_id"]))
                    else:
                        db.execute("UPDATE runs SET lease_until_ms=?,heartbeat_ms=? WHERE project_id=? AND run_id=?",
                                   (max(run["lease_until_ms"], now + c["lease_seconds"] * 1000), now, project, c["run_id"]))
                    db.execute("UPDATE runtime_tasks SET version=version+1 WHERE project_id=? AND task_id=?", (project, task))
            result = self._snapshot(db, project, task)
            db.execute("UPDATE metadata SET last_clock_ms=? WHERE id=1", (now,))
            db.execute("INSERT INTO requests VALUES(?,?,?,?)", (project, c["request_id"], digest, json.dumps(result, sort_keys=True)))
            event_id = hashlib.sha256((project + ":" + c["request_id"]).encode()).hexdigest()
            db.execute("INSERT INTO events(schema_version,event_id,project_id,task_id,run_id,agent_id,event_type,timestamp_ms,causation_id) VALUES(?,?,?,?,?,?,?,?,?)",
                       (1, event_id, project, task, c["run_id"], c.get("actor", c.get("owner")),
                        "revoke." + c["reason"] if op == "revoke" else op, now, c["request_id"]))
            if reservation is not None:
                r = reservation
                db.execute("INSERT INTO parallel_runs(project_id,run_id,task_id,owner,fence,base_sha,path_digest,scope_json,resources_json,dependencies_json,filename,card_sha,output,claim_request,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (project, c["run_id"], task, c["owner"], result["fence"], c["base_sha"], r["path_digest"],
                            json.dumps(r["scope"]), json.dumps(r["resources"]), json.dumps(r["dependencies"]),
                            r["filename"], r["card_sha"], r["output"], c["request_id"], "reserved"))
            if projection is not None:
                source, target = projection_states(c)
                db.execute("INSERT INTO board_intents(project_id,request_id,task_id,run_id,owner,fence,phase,root_digest,filename,source_state,target_state,before_sha,after_sha,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (project, c["request_id"], task, c["run_id"], c["owner"], result["fence"], result["run"]["phase"],
                            projection["root_digest"], projection["filename"], source, target,
                            projection["before_sha"], projection["after_sha"], "pending"))
                self._intent_status(db, project, c["request_id"], "pending", now)
            return {"replayed": False, "recorded": result}

    @staticmethod
    def _intent_status(db, project, request, status, now, reason=""):
        db.execute("UPDATE board_intents SET status=?,reason=? WHERE project_id=? AND request_id=?", (status, reason, project, request))
        row = db.execute("SELECT * FROM board_intents WHERE project_id=? AND request_id=?", (project, request)).fetchone()
        event = hashlib.sha256((project + ":" + request + ":intent." + status).encode()).hexdigest()
        db.execute("INSERT OR IGNORE INTO events(schema_version,event_id,project_id,task_id,run_id,agent_id,event_type,timestamp_ms,causation_id) VALUES(?,?,?,?,?,?,?,?,?)",
                   (1, event, project, row["task_id"], row["run_id"], row["owner"], "intent." + status, now, request))
        db.execute("UPDATE metadata SET last_clock_ms=? WHERE id=1", (now,))

    def intent(self, project_id, request_id):
        _id(project_id); _id(request_id)
        with self._db() as db:
            row = db.execute("SELECT * FROM board_intents WHERE project_id=? AND request_id=?", (project_id, request_id)).fetchone()
            return dict(row) if row else None

    def intents(self, project_id, *, after_sequence=0, limit=100):
        _id(project_id); _integer(after_sequence); _integer(limit, 1, 100)
        with self._db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM board_intents WHERE project_id=? AND sequence>? ORDER BY sequence LIMIT ?", (project_id, after_sequence, limit))]

    def migrate(self, backup=None, *, execute=False):
        with self._db(write=execute, versions=(1, 2, 3, 4)) as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                return {"schema_version": version, "migrated": False}
            if not execute:
                return {"schema_version": version, "target_version": 4, "would_migrate": True}
            if backup is None:
                raise StateError("Migration requires an explicit new backup.")
            self.backup(backup, _versions=(version,))
            additions = (INTENT_SCHEMA if version == 1 else "") + (PARALLEL_SCHEMA if version < 3 else "") + EVIDENCE_SCHEMA
            for statement in additions.split(";"):
                if statement.strip(): db.execute(statement)
            db.execute("PRAGMA user_version=4")
            _verify(db)
            return {"schema_version": 4, "migrated": True}

    def backup(self, target, *, _versions=(SCHEMA_VERSION,)):
        target = Path(target).resolve()
        if target == self.path:
            raise StateError("Backup cannot overwrite its source.")
        # Exclusive creation refuses existing files; partial failures stay for inspection.
        with target.open("xb"):
            pass
        deadline = time.monotonic() + BUSY_SECONDS
        def progress(*_):
            if time.monotonic() >= deadline:
                raise StateError("Runtime backup deadline exhausted.")
        try:
            with self._db(versions=_versions) as source:
                destination = sqlite3.connect(target, timeout=BUSY_SECONDS, isolation_level=None)
                try:
                    source.backup(destination, pages=128, progress=progress, sleep=.01)
                    _verify(destination, _versions)
                    version = destination.execute("PRAGMA user_version").fetchone()[0]
                    if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise StateError("Runtime backup integrity failed.")
                finally:
                    destination.close()
            with target.open("r+b") as stream:
                import os
                os.fsync(stream.fileno())
            return {"schema_version": version, "backup_verified": True}
        except sqlite3.Error:
            raise StateError("Runtime backup failed.") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("init")
    migrate = subs.add_parser("migrate"); migrate.add_argument("--backup", type=Path); migrate.add_argument("--execute", action="store_true")
    apply = subs.add_parser("apply"); apply.add_argument("--command-file", type=Path, required=True)
    backup = subs.add_parser("backup"); backup.add_argument("--to", type=Path, required=True)
    for action in ("get", "history", "events"):
        sub = subs.add_parser(action); sub.add_argument("--project-id", required=True)
        if action != "events":
            sub.add_argument("--task-id", required=True)
        if action != "get":
            sub.add_argument("--after", type=int, default=0); sub.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    controller = StateController(args.db)
    try:
        if args.action == "init": result = controller.initialize()
        elif args.action == "migrate": result = controller.migrate(args.backup, execute=args.execute)
        elif args.action == "backup": result = controller.backup(args.to)
        elif args.action == "apply":
            with args.command_file.open("rb") as stream: raw = stream.read(16385)
            if len(raw) > 16384: raise StateError("Runtime command exceeds size bound.")
            result = controller.apply(json.loads(raw))
        elif args.action == "get": result = controller.get(args.project_id, args.task_id)
        elif args.action == "history": result = controller.history(args.project_id, args.task_id, after_fence=args.after, limit=args.limit)
        else: result = controller.events(args.project_id, after_sequence=args.after, limit=args.limit)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (StateError, OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"error": "runtime_state_refused",
                          "reason": str(exc) if isinstance(exc, StateError) else "input_or_io_error"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
