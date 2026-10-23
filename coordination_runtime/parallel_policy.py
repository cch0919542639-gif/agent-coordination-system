"""Bounded conservative worker scopes and transactional parallel admission."""
import json
from pathlib import PurePosixPath
import re
from .state_controller import StateError, _id, FILENAME

PROTECTED = (".git", ".coordination-runtime", "coordination/task-board", "coordination/delivery", "coordination/reviews", "coordination/progress")


def path_key(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 240 or "\\" in value
            or ":" in value or any(ord(c) < 32 for c in value)):
        raise StateError("Invalid worker path.")
    p = PurePosixPath(value)
    if (p.is_absolute() or str(p) != value or any(c in {".", ".."} or c.endswith((".", " "))
            or c.split(".")[0].casefold() in {"con", "prn", "aux", "nul", *("com"+str(n) for n in range(1,10)), *("lpt"+str(n) for n in range(1,10))} for c in p.parts)):
        raise StateError("Invalid worker path.")
    return value.casefold()


def overlap(a, b):
    a = a.removesuffix("/**"); b = b.removesuffix("/**")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def scopes(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 64:
        raise StateError("Invalid worker scope list.")
    result = []
    for value in values:
        key = path_key(value)
        base = key.removesuffix("/**")
        if any(c in base for c in "*?[]{}") or any(overlap(base, p) for p in PROTECTED):
            raise StateError("Unsupported or protected worker scope.")
        if key in result: raise StateError("Duplicate worker scope.")
        result.append(key)
    return sorted(result)


def allows(path, allowed):
    key = path_key(path)
    if any(overlap(key, p) for p in PROTECTED): return False
    return any(key == p or (p.endswith("/**") and key.startswith(p[:-3] + "/")) for p in allowed)


def identifiers(values, limit):
    if not isinstance(values, list) or len(values) > limit:
        raise StateError("Invalid scheduling identifiers.")
    for value in values: _id(value)
    if len(set(values)) != len(values): raise StateError("Duplicate scheduling identifiers.")
    return sorted(values)


def validate_reservation(value):
    fields = {"root_digest", "workspace_root_digest", "path_digest", "scope", "resources", "dependencies", "filename", "card_sha", "output"}
    if not isinstance(value, dict) or set(value) != fields:
        raise StateError("Invalid parallel reservation.")
    r = dict(value)
    for k in ("root_digest", "workspace_root_digest", "path_digest", "card_sha"):
        if not isinstance(r[k], str) or not re.fullmatch("[a-f0-9]{64}", r[k]): raise StateError("Invalid reservation digest.")
    if not isinstance(r["filename"], str) or not FILENAME.fullmatch(r["filename"]): raise StateError("Invalid reservation filename.")
    r["scope"] = scopes(r["scope"]); r["resources"] = identifiers(r["resources"],16)
    r["dependencies"] = identifiers(r["dependencies"],32)
    path_key(r["output"])
    if not allows(r["output"], r["scope"]) or any(c in r["output"] for c in "*?[]{}"):
        raise StateError("Mock output is outside worker scope.")
    return r


def check_admission(db, command, projection, r):
    from .resource_guard import admission_gate
    admission_gate(db, command['project_id'])
    settings = db.execute("SELECT * FROM parallel_projects WHERE project_id=?", (command["project_id"],)).fetchone()
    if (not settings or settings["mode"] != "parallel" or settings["root_digest"] != r["root_digest"]
            or settings["workspace_root_digest"] != r["workspace_root_digest"]
            or projection["root_digest"] != r["root_digest"] or projection["filename"] != r["filename"]
            or projection["before_sha"] != r["card_sha"]):
        raise StateError("Parallel reservation binding mismatched.")
    held = db.execute("SELECT * FROM parallel_runs WHERE project_id=? AND status!='released'", (command["project_id"],)).fetchall()
    if len(held) >= settings["capacity"]: raise StateError("Parallel capacity is reserved.")
    for row in held:
        if set(r["resources"]) & set(json.loads(row["resources_json"])):
            raise StateError("Exclusive resource is reserved.")
        if any(overlap(a,b) for a in r["scope"] for b in json.loads(row["scope_json"])):
            raise StateError("Worker scopes conflict.")
