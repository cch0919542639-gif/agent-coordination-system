"""Explicit durable task-board projection; no worker launch or task acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from coordination_common import parse_front_matter, require_serial
from .state_controller import StateController, StateError, FILENAME, _id, _projection, projection_states

MAX_CARD = 65536
STATES = ("ready", "in_progress", "review", "blocked", "done", "cancelled")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _intent_id(project, request):
    return _sha((project + ":" + request).encode())


def _desired(data, source, target, marker):
    header = re.match(rb"---\r?\n(.*?)\r?\n---\r?\n", data, re.S)
    if not header:
        raise StateError("Invalid board card header.")
    pattern = rb"(?m)^(status: *)" + source.upper().encode() + rb"(?= *\r?$)"
    changed, count = re.subn(pattern, lambda m: m[1] + target.upper().encode(), header[1])
    if count != 1:
        raise StateError("Board status line mismatched.")
    result = data[:header.start(1)] + changed + data[header.end(1):]
    result += ("\n<!-- coordination-intent: " + marker + " -->\n").encode()
    if len(result) > MAX_CARD:
        raise StateError("Projected card exceeds size bound.")
    return result


class BoardProjector:
    def __init__(self, controller, repo_root, project_id, *, _checkpoint=None, _parallel=False):
        _id(project_id)
        self._parallel = _parallel
        self.controller = controller
        self.root = Path(repo_root).resolve()
        self.project = project_id
        self.root_digest = _sha(os.path.normcase(str(self.root)).encode())
        self._checkpoint = _checkpoint or (lambda stage: None)

    def _path(self, relative):
        path = self.root / relative
        if path.resolve() != path or not path.is_relative_to(self.root):
            raise StateError("Board path is aliased or escapes its binding.")
        return path

    def _read(self, path):
        self._path(path.relative_to(self.root))
        if path.is_symlink():
            raise StateError("Board file alias refused.")
        if not path.exists(): return None
        with path.open("rb") as stream: data = stream.read(MAX_CARD + 1)
        if len(data) > MAX_CARD:
            raise StateError("Board card exceeds size bound.")
        return data

    @staticmethod
    def _header(data):
        try:
            fields, _ = parse_front_matter(data.decode("utf-8").replace("\r\n", "\n"))
        except UnicodeError:
            raise StateError("Board card encoding refused.") from None
        if not fields:
            raise StateError("Invalid board card metadata.")
        return fields

    def _cards(self, task):
        board = self._path("coordination/task-board")
        found = set()
        count = 0
        for state in STATES:
            directory = self._path(board.relative_to(self.root) / state)
            for path in directory.glob("*.md"):
                if path.name == "README.md": continue
                count += 1
                if count > 2048: raise StateError("Board scan exceeds size bound.")
                data = self._read(path)
                if data is None: raise StateError("Board changed during scan.")
                if self._header(data).get("task_id") == task: found.add(path)
        return found

    def prepare(self, command, filename, expected_sha256, *, reservation=None, _admission_check=None):
        self._routing()
        c = self.controller._validate(command)
        if c["project_id"] != self.project:
            raise StateError("Projection project mismatched.")
        source, target = projection_states(c)
        # Validate even a historical retry before any filesystem scan.
        spec = _projection(c, dict(root_digest=self.root_digest, filename=filename,
                                  before_sha=expected_sha256, after_sha="0" * 64))
        previous = self.controller.intent(self.project, c["request_id"])
        if previous:
            spec["after_sha"] = previous["after_sha"]
            return self.controller.apply(c, projection=spec, reservation=reservation, _parallel=self._parallel, _admission_check=_admission_check)
        path = self._path(Path("coordination/task-board") / source / filename)
        data = self._read(path)
        if data is None or _sha(data) != expected_sha256 or self._cards(c["task_id"]) != {path}:
            raise StateError("Board preimage or unique identity mismatched.")
        fields = self._header(data)
        if fields.get("status") != source.upper() or fields.get("owner") != c["owner"]:
            raise StateError("Board assignment or status mismatched.")
        self._report(fields, target, c["task_id"])
        after = _desired(data, source, target, _intent_id(self.project, c["request_id"]))
        spec["after_sha"] = _sha(after)
        result = self.controller.apply(c, projection=spec, reservation=reservation, _parallel=self._parallel, _admission_check=_admission_check)
        self._checkpoint("after_prepare")
        return result

    def _report(self, fields, target, task):
        if target == "review" and "delivery_report" in fields.get("expected_artifacts", []):
            report = self._path(Path("coordination/delivery") / (task + "-delivery-report.md"))
            if self._read(report) is None:
                raise StateError("Required delivery report missing.")

    def _paths(self, row):
        name = row["filename"]
        if not FILENAME.fullmatch(name) or row["source_state"] not in STATES or row["target_state"] not in STATES:
            raise StateError("Invalid stored projection path.")
        board = Path("coordination/task-board")
        return self._path(board / row["source_state"] / name), self._path(board / row["target_state"] / name)

    def _stage(self, row):
        source, target = self._paths(row)
        before, after = self._read(source), self._read(target)
        if self._cards(row["task_id"]) != ({source} if before is not None else set()) | ({target} if after is not None else set()):
            return "conflict"
        if before is not None and _sha(before) != row["before_sha"]: return "conflict"
        if after is not None and _sha(after) != row["after_sha"]: return "conflict"
        if before is None: return "complete" if after is not None else "conflict"
        return "published" if after is not None else "before"

    def _authority(self, db, row, now):
        current = self.controller._snapshot(db, self.project, row["task_id"])
        run = current["run"]
        return bool(run and current["active_run_id"] == row["run_id"]
                    and current["fence"] == row["fence"] == run["fence"]
                    and run["owner"] == row["owner"] and run["phase"] == row["phase"]
                    and now < run["lease_until_ms"])

    def _require_authority(self, db, row):
        now = self.controller._now()
        floor = db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()[0]
        if now < floor or not self._authority(db, row, now):
            raise StateError("Projection authority expired or revoked.")

    def _publish(self, db, row):
        source, target = self._paths(row)
        before = self._read(source)
        if before is None or _sha(before) != row["before_sha"]:
            raise StateError("Board preimage changed.")
        after = _desired(before, row["source_state"], row["target_state"], _intent_id(self.project, row["request_id"]))
        if _sha(after) != row["after_sha"]:
            raise StateError("Projection derivation mismatched.")
        # ponytail: native exclusive hard-link publication; unsupported FS refuses.
        fd, draft = tempfile.mkstemp(prefix=".coordination-intent-", suffix=".tmp", dir=target.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(after); stream.flush(); os.fsync(stream.fileno())
        if self._stage(row) != "before":
            raise StateError("Board changed before publication.")
        self._report(self._header(before), row["target_state"], row["task_id"])
        self._require_authority(db, row)
        os.link(draft, target)  # Complete file, no existing-destination overwrite.
        Path(draft).unlink()
        self._checkpoint("after_target")

    def reconcile(self, request_id, *, execute=False):
        return self._operate(request_id, execute=execute, cancel=False)

    def cancel(self, request_id, *, execute=False):
        return self._operate(request_id, execute=execute, cancel=True)

    def _routing(self):
        if not self._parallel:
            try: require_serial(self.root)
            except ValueError:
                raise StateError("Parallel board requires controller routing.") from None

    def _operate(self, request, *, execute, cancel):
        if execute:self._routing()
        _id(request)
        with self.controller._db(write=execute) as db:
            mode = db.execute("SELECT mode FROM parallel_projects WHERE project_id=?", (self.project,)).fetchone()
            if execute and mode and mode[0] == "parallel" and not self._parallel:
                raise StateError("Parallel board requires controller routing.")
            row = db.execute("SELECT * FROM board_intents WHERE project_id=? AND request_id=?", (self.project, request)).fetchone()
            if not row or row["root_digest"] != self.root_digest:
                raise StateError("Projection intent or bound root mismatched.")
            row = dict(row)
            if row["status"] in {"applied", "cancelled"}:
                return {"status": row["status"], "historical": True}
            now = self.controller._now()
            if now < db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()[0]:
                raise StateError("Clock moved backwards; recovery required.")
            try:
                stage = self._stage(row)
                if not cancel and stage in {"before", "published"}:
                    self._report(self._header(self._read(self._paths(row)[0])), row["target_state"], row["task_id"])
                if cancel:
                    status = "cancelled" if stage in {"before", "published"} else "recovery_required"
                else:
                    status = "applied" if stage == "complete" or (stage in {"before", "published"} and self._authority(db, row, now)) else "recovery_required"
                if not execute:
                    return {"status": row["status"], "observed": stage, "would_status": status, "dry_run": True}
                if status != "recovery_required" and stage != "complete":
                    source, target = self._paths(row)
                    if not cancel and stage == "before": self._publish(db, row)
                    expected = "published" if stage == "published" or not cancel else "before"
                    if self._stage(row) != expected:
                        raise StateError("Board changed before removal.")
                    if cancel:
                        if stage == "published": target.unlink()
                    else:
                        self._report(self._header(self._read(source)), row["target_state"], row["task_id"])
                        self._require_authority(db, row)
                        source.unlink()
                        self._checkpoint("after_source")
                reason = "board_conflict" if stage == "conflict" else "authority_or_stage_refused"
            except (OSError, StateError):
                if not execute:
                    return {"status": row["status"], "observed": "conflict", "would_status": "recovery_required", "dry_run": True}
                status, reason = "recovery_required", "board_io_or_identity_refused"
            self.controller._intent_status(db, self.project, request, status, now,
                                           reason if status == "recovery_required" else "")
            return {"status": status, "reason": reason if status == "recovery_required" else ""}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    subs = parser.add_subparsers(dest="action", required=True)
    prep = subs.add_parser("prepare"); prep.add_argument("--command-file", type=Path, required=True)
    prep.add_argument("--filename", required=True); prep.add_argument("--expected-sha256", required=True)
    for action in ("reconcile", "cancel"):
        sub = subs.add_parser(action); sub.add_argument("--request-id", required=True); sub.add_argument("--execute", action="store_true")
    listing = subs.add_parser("list"); listing.add_argument("--after", type=int, default=0); listing.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    try:
        controller = StateController(args.db)
        board = BoardProjector(controller, args.repo, args.project_id)
        if args.action == "prepare":
            with args.command_file.open("rb") as stream: raw = stream.read(16385)
            if len(raw) > 16384: raise StateError("Runtime command exceeds size bound.")
            result = board.prepare(json.loads(raw), args.filename, args.expected_sha256)
        elif args.action == "list": result = controller.intents(args.project_id, after_sequence=args.after, limit=args.limit)
        else: result = getattr(board, args.action)(args.request_id, execute=args.execute)
        print(json.dumps(result, sort_keys=True))
        return 1 if isinstance(result, dict) and result.get("status") == "recovery_required" else 0
    except (StateError, OSError, ValueError, RecursionError) as error:
        print(json.dumps({"error": "board_projection_refused", "reason": str(error) if isinstance(error, StateError) else "input_or_io_error"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
