#!/usr/bin/env python3
"""Finite, explicitly authorized local worker loop; preview unless --run."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time

from coordination_common import ROOT, load_task, move_task

PROJECT = "agent-coordination-system"
REVIEWER = "LOCAL_LOOP"
WORKERS = {
    "opencode-coordination-pilot": "opencode-coordination-worker",
    "hermes-coordination-pilot": "hermes-coordination-worker",
    "antigravity-coordination-pilot": "antigravity-coordination-worker",
    "reasonix-coordination-pilot": "reasonix-coordination-worker",
}


class LoopError(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}", value):
        raise LoopError("Invalid run or task identifier.")
    return value


def relative_path(value):
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise LoopError("Check paths must be repository-relative POSIX paths.")
    path = Path(value)
    if path.is_absolute() or not value or any(p in {".", ".."} for p in value.split("/")):
        raise LoopError("Check path escapes repository scope.")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or ".git" in path.parts:
        raise LoopError("Check path escapes repository scope.")
    return resolved


def task_card(task_id):
    matches = []
    for path in (ROOT / "coordination/task-board").glob("*/*.md"):
        if path.name == "README.md":
            continue
        header, body = load_task(path)
        if header.get("task_id") == task_id:
            matches.append((path, header, body))
    if len(matches) != 1:
        raise LoopError(f"Task {task_id} must have exactly one authoritative card.")
    path, header, body = matches[0]
    if header.get("status") != path.parent.name.upper():
        raise LoopError(f"Task {task_id} status differs from its folder.")
    return path, header, body


def task_contract(header, body):
    return digest({"header": {k: v for k, v in header.items() if k != "status"}, "body": body.strip()})


def allowed_file(name, header):
    import fnmatch
    return (any(fnmatch.fnmatchcase(name, pattern) for pattern in header["allowed_scope"])
            and not any(fnmatch.fnmatchcase(name, pattern) for pattern in header["forbidden_scope"]))


def accepted(task_id, reviewer=None):
    from validate_coordination_files import validate_review_file, validate_delivery_file
    path, header, _ = task_card(task_id)
    review = ROOT / "coordination/reviews" / f"review-{task_id}.md"
    report = ROOT / "coordination/delivery" / f"{task_id}-delivery-report.md"
    if path.parent.name != "done" or not review.is_file() or not report.is_file():
        return False
    text = review.read_text(encoding="utf-8")
    delivery_text = report.read_text(encoding="utf-8")
    reviewer = reviewer or header.get("reviewer")
    return (
        f"- Task ID: {task_id}\n" in text and "- Decision: accepted\n" in text
        and f"- Reviewer: {reviewer}\n" in text
        and f"- Phase: {header.get('phase')}\n" in text
        and f"- Task ID: {task_id}\n" in delivery_text
        and f"- Agent: {header.get('owner')}\n" in delivery_text
        and f"- Phase: {header.get('phase')}\n" in delivery_text
        and "- Status: DELIVERED\n" in delivery_text
        and not validate_review_file(review) and not validate_delivery_file(report)
    )


def load_plan(path):
    plan = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(plan, dict) or plan.get("version") != 1:
        raise LoopError("Expected version 1 task plan.")
    identifier(plan.get("run_id"))
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise LoopError("Plan must explicitly list 1 to 100 tasks.")
    for name, default, low, high in [
        ("max_attempts", 2, 1, 3), ("worker_timeout_seconds", 900, 10, 900),
        ("check_timeout_seconds", 60, 1, 300), ("run_timeout_seconds", 3600, 10, 7200),
    ]:
        value = plan.setdefault(name, default)
        if type(value) is not int or not low <= value <= high:
            raise LoopError(f"Invalid bounded {name}.")
    ids = set()
    headers = {}
    from validate_coordination_files import validate_task_file
    for task in tasks:
        task_id = identifier(task.get("task_id"))
        if task_id in ids or task.get("owner") not in WORKERS:
            raise LoopError("Duplicate task ID or unsupported worker.")
        ids.add(task_id)
        checks = task.get("checks")
        if not isinstance(checks, list) or not checks:
            raise LoopError(f"Task {task_id} requires independent acceptance checks.")
        for check in checks:
            if not isinstance(check, dict):
                raise LoopError("Malformed acceptance check.")
            if set(check) == {"path", "json_equals"}:
                relative_path(check["path"])
            elif set(check) == {"command"}:
                argv = check["command"]
                if not isinstance(argv, list) or len(argv) < 2 or argv[0] != "$PYTHON" or not all(isinstance(a, str) and a for a in argv):
                    raise LoopError("Command checks require explicit $PYTHON argv, without a shell.")
                relative_path(argv[1])
            else:
                raise LoopError("Unsupported acceptance check.")
        card, header, _ = task_card(task_id)
        if validate_task_file(card):
            raise LoopError(f"Invalid task contract for {task_id}.")
        if header.get("owner") != task["owner"] or header.get("reviewer") != REVIEWER:
            raise LoopError(f"Task {task_id} is not assigned to this loop's worker/reviewer.")
        if header.get("local_loop_checks_sha256") != digest(checks):
            raise LoopError(f"Task {task_id} does not authorize these exact review checks.")
        if header.get("execution_mode") != "REPO_FIRST":
            raise LoopError("This controller supports same-checkout REPO_FIRST tasks only.")
        if "delivery_report" not in header.get("expected_artifacts", []):
            raise LoopError("Automatic review requires a delivery report.")
        for pattern in header.get("allowed_scope", []):
            if not pattern or pattern.startswith(("/", "\\")) or ".." in pattern.split("/") or ":" in pattern:
                raise LoopError("Invalid worker scope.")
        for check in checks:
            if "path" in check and not allowed_file(check["path"], header):
                raise LoopError("Checked output must be within the task's declared worker scope.")
            if "command" in check:
                check_path = check["command"][1]
                if not relative_path(check_path).is_file() or allowed_file(check_path, header):
                    raise LoopError("Independent checker must exist outside worker-write scope.")
        headers[task_id] = header
    for task in tasks:
        for check in task["checks"]:
            if "command" in check and any(allowed_file(check["command"][1], h) for h in headers.values()):
                raise LoopError("Independent checker must exist outside worker-write scope for every listed task.")
    visiting, visited = set(), set()

    def visit(task_id):
        if task_id in visiting:
            raise LoopError("Task dependencies contain a cycle.")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in headers[task_id].get("dependencies", []):
            identifier(dep)
            if dep in headers:
                visit(dep)
            elif not accepted(dep):
                raise LoopError(f"External dependency {dep} has no accepted DONE evidence.")
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in headers:
        visit(task_id)
    return plan


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def process_lock():
    path = ROOT / "coordination/monitor/local-loop/controller.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise LoopError("Another local controller is running.") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def cli(script, *args):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", timeout=60)
    if result.returncode:
        raise LoopError(f"Coordination helper {script} failed with exit {result.returncode}.")
    return result.stdout


def fingerprints():
    names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    result = {}
    for raw in names.split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = ROOT / name
        if path.is_dir():
            continue  # Embedded Git checkouts are outside this coordination checkout.
        try:
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except FileNotFoundError:
            continue
        except PermissionError:
            result[name] = "unreadable"
    return result


def scope_changes(before, header):
    after = fingerprints()
    changed = [name for name in before.keys() | after.keys() if before.get(name) != after.get(name)]
    return [name for name in changed if not allowed_file(name, header)]


def emit_event(task_id, event_type, run_id, header):
    from event_ledger import Event, append_events, make_event_id
    from event_routing import route_event, append_delivery_records
    repository = "local-coordination-checkout"
    ref, commit = "local", run_id
    event_id = make_event_id(PROJECT, repository, ref, commit, task_id, event_type)
    append_events([Event(event_id, PROJECT, repository, ref, commit, task_id, event_type,
                         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         owner=header["owner"], reviewer=REVIEWER)])
    pairs = route_event(PROJECT, task_id, event_type, ref, commit, owner=header["owner"], reviewer=REVIEWER)
    destination = "registered_worker" if event_type == "ready_assigned" else "orchestrator"
    selected = [record for _, record in pairs if record.destination == destination]
    if len(selected) != 1:
        raise LoopError("Missing or ambiguous local routing policy.")
    append_delivery_records(selected)
    from event_routing import load_delivery_state_map
    stored = load_delivery_state_map().get(selected[0].payload_id)
    if stored is None or (stored.ref, stored.commit, stored.owner, stored.reviewer) != (ref, commit, header["owner"], REVIEWER):
        raise LoopError("Task already belongs to a different delivery generation; old receipts are not reset.")
    return selected[0].payload_id


def handoff(task_id, owner, payload_id):
    from event_routing import load_delivery_state_map
    delivery = load_delivery_state_map().get(payload_id)
    if delivery is None or (delivery.status, delivery.task_id, delivery.project_id, delivery.owner, delivery.destination) != (
        "acknowledged", task_id, PROJECT, owner, "registered_worker"
    ):
        raise LoopError("Missing matching acknowledged delivery.")
    path = ROOT / "coordination/monitor/inbox" / owner / f"{payload_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {"task_id": task_id, "project_id": PROJECT, "worker_id": owner, "payload_id": payload_id}
    if any(payload.get(k) != v for k, v in expected.items()):
        raise LoopError("Inbox identity does not match the selected task.")
    if not re.fullmatch(r"coordination/task-board/ready/[^/\\]+\.md", payload.get("task_card_path", "")):
        raise LoopError("Unexpected original task-card path.")
    card, header, _ = task_card(task_id)
    if card.name != Path(payload["task_card_path"]).name or header.get("owner") != owner:
        raise LoopError("Task card no longer matches its durable handoff.")
    return payload


def process_alive(pid):
    if os.name == "nt":
        import ctypes
        api = ctypes.windll.kernel32
        api.OpenProcess.restype = ctypes.c_void_p
        handle = api.OpenProcess(0x1000, False, pid)
        if not handle:
            return api.GetLastError() != 87  # Access denied is also fail-closed.
        try:
            code = ctypes.c_ulong()
            api.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
            return not api.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            api.CloseHandle.argtypes = [ctypes.c_void_p]
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def worker_metadata(line):
    """Keep numeric lifecycle evidence; never forward model or terminal text."""
    try:
        value = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    safe = {}
    for key in ("api_step", "api_calls", "input_tokens", "output_tokens", "last_prompt_tokens"):
        limit = 1000000 if key.endswith("tokens") else 10000
        if type(value.get(key)) is int and 0 <= value[key] <= limit:
            safe[key] = value[key]
    for key in ("completed", "failed"):
        if type(value.get(key)) is bool:
            safe[key] = value[key]
    if isinstance(value.get("turn_exit_category"), str) and value["turn_exit_category"] in {
        "text_response", "empty_response_exhausted", "all_retries_exhausted_no_response",
        "max_iterations_reached", "interrupted", "local_processing_error", "other",
    }:
        safe["turn_exit_category"] = value["turn_exit_category"]
    if isinstance(value.get("tool_results"), list):
        safe["tool_results"] = [{k: item[k] for k in ("exit_code", "error")
                                  if (type(item.get(k)) is int if k == "exit_code" else type(item.get(k)) is bool)}
                                 for item in value["tool_results"][:24] if isinstance(item, dict)]
    # Both the SDK and this boundary redact diagnostics, independently.
    pattern = (r"Rate limited|Provider overloaded|Waiting [0-9.]+s|attempt \d+/\d+|"
               r"(?:HTTP|Error code:)\s*\d{3}|Limit \d+(?:, Used \d+)?, Requested \d+|"
               r"rate_limit_exceeded|tool_use_failed|payload too large|maximum context length|"
               r"tool call validation failed|failed to call a function|failed to generate|"
               r"invalid_request_error|failed_generation|context_length_exceeded|missing_review_receipt|"
               r"tokens per (?:minute|day)|requests per (?:minute|day)|\b(?:TPM|TPD|RPM|RPD)\b|"
               r"\b(?:ITPM|OTPM)\b|try again in [0-9.hms ]{1,30}")
    for key in ("status", "diagnostics", "failure_reason"):
        flags = re.findall(pattern, str(value.get(key, "")), re.IGNORECASE)
        if flags:
            safe[key] = flags[:12]
    return safe or None


def bounded_process(command, timeout, on_start=None, on_metadata=None):
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE if on_metadata else subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=os.name != "nt")
    reader = None
    messages = []
    def drain():
        oversized = False
        while chunk := process.stdout.readline(4096):
            complete = chunk.endswith(b"\n")
            if not oversized and complete:
                metadata = worker_metadata(chunk.decode("utf-8", errors="replace"))
                if metadata and len(messages) < 100:
                    messages.append(metadata)
            oversized = not complete
    try:
        if on_start is not None:
            on_start(process.pid)
        if on_metadata:
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
        deadline = time.monotonic() + timeout
        while True:
            while messages:
                on_metadata(messages.pop(0))
            budget = deadline - time.monotonic()
            if budget <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                code = process.wait(timeout=min(0.2, budget))
                if reader:
                    reader.join(timeout=1)
                while messages:
                    on_metadata(messages.pop(0))
                return code
            except subprocess.TimeoutExpired:
                continue
    except BaseException as exc:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        if isinstance(exc, subprocess.TimeoutExpired):
            raise LoopError("Owned process tree was stopped before verified completion.") from exc
        raise


def launch_worker(task_id, owner, payload_id, timeout, on_start=None, on_metadata=None):
    command = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "integrations" / WORKERS[owner] / "run-controlled-worker.ps1"),
               "-Run", "-ResumePayload", payload_id]
    return bounded_process(command, timeout, on_start, on_metadata if owner == "hermes-coordination-pilot" else None)


def acceptance_checks(task, timeout):
    failures = []
    deadline = time.monotonic() + timeout
    for index, check in enumerate(task["checks"], 1):
        budget = deadline - time.monotonic()
        if budget <= 0:
            raise LoopError("Independent review check budget exhausted.")
        if "path" in check:
            try:
                actual = json.loads(relative_path(check["path"]).read_text(encoding="utf-8-sig"))
                if actual != check["json_equals"]:
                    failures.append(f"Check {index}: {check['path']} JSON differs from the declared contract.")
            except (OSError, ValueError):
                failures.append(f"Check {index}: {check['path']} is missing or invalid JSON.")
        else:
            argv = [sys.executable, *check["command"][1:]]
            try:
                code = bounded_process(argv, budget)
                if code:
                    failures.append(f"Check {index}: independent command exited {code}.")
            except LoopError:
                failures.append(f"Check {index}: independent command timed out.")
    return failures


def run_loop(plan_path, *, execute=False, resume=False, launch=None):
    plan = load_plan(plan_path)
    if not execute:
        print(json.dumps({"mode": "preview", "run_id": plan["run_id"], "tasks": plan["tasks"],
                          "max_attempts": plan["max_attempts"], "run_timeout_seconds": plan["run_timeout_seconds"]}))
        return 0
    with process_lock():
        from project_registry import get_project
        from worker_poller import get_worker
        project = get_project(PROJECT)
        if project is None or Path(project.local_path).resolve() != ROOT.resolve():
            raise LoopError("Central project registration does not match this checkout.")
        for task in plan["tasks"]:
            worker = get_worker(task["owner"])
            if worker is None or not worker.enabled or worker.project_id != PROJECT:
                raise LoopError("Worker is not enabled for this central project.")
        directory = ROOT / "coordination/monitor/local-loop" / plan["run_id"]
        state_path = directory / "state.json"
        plan_hash = digest(plan)
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("plan_sha256") != plan_hash:
                raise LoopError("Run ID already belongs to another immutable plan.")
            if state.get("status") != "completed" and not resume:
                raise LoopError("Interrupted run requires explicit --resume; no acknowledgement is reset.")
        else:
            state = {"run_id": plan["run_id"], "plan_sha256": plan_hash, "status": "running", "tasks": {},
                     "contracts": {t["task_id"]: task_contract(*task_card(t["task_id"])[1:]) for t in plan["tasks"]},
                     "checkers": {c["command"][1]: hashlib.sha256(relative_path(c["command"][1]).read_bytes()).hexdigest()
                                  for t in plan["tasks"] for c in t["checks"] if "command" in c}}
        for entry in state["tasks"].values():
            if entry.get("terminal_failure"):
                raise LoopError("This run recorded a scope breach; operator investigation is required.")
            if entry.get("pid") and process_alive(entry["pid"]):
                raise LoopError("Previous worker process is still running; duplicate launch prevented.")
            if entry.get("phase") in {"running", "launch_intent"}:
                raise LoopError("Interrupted process tree has no durable exit; verify it stopped before operator recovery.")
        directory.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + plan["run_timeout_seconds"]

        def record(event, task_id=None, **values):
            item = {"event": event, "task_id": task_id, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **values}
            with (directory / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(item) + "\n")
            print(json.dumps(item), flush=True)
            atomic_json(state_path, state)

        def remaining(limit):
            budget = min(limit, deadline - time.monotonic())
            if budget <= 0:
                raise LoopError("Finite run time limit exhausted.")
            return budget

        try:
            record("run_started")
            while True:
                pending = []
                for task in plan["tasks"]:
                    task_id = task["task_id"]
                    card, header, body = task_card(task_id)
                    if header.get("owner") != task["owner"] or header.get("reviewer") != REVIEWER or header.get("local_loop_checks_sha256") != digest(task["checks"]):
                        raise LoopError("Task ownership or review contract changed during execution.")
                    if state["contracts"].get(task_id) != task_contract(header, body):
                        raise LoopError("Frozen task scope, dependencies or instructions changed.")
                    for name, expected in state["checkers"].items():
                        if hashlib.sha256(relative_path(name).read_bytes()).hexdigest() != expected:
                            raise LoopError("Independent checker source changed; acceptance stopped.")
                    if card.parent.name == "done":
                        entry = state["tasks"].get(task_id, {})
                        if entry.get("exit_code") != 0 or not accepted(task_id, REVIEWER) or acceptance_checks(task, remaining(plan["check_timeout_seconds"])):
                            raise LoopError(f"Task {task_id} has no valid accepted completion evidence.")
                        handoff(task_id, task["owner"], entry["payload_id"])
                        continue
                    if card.parent.name not in {"ready", "in_progress", "review"}:
                        raise LoopError(f"Task {task_id} requires operator attention in {card.parent.name}.")
                    pending.append(task)
                if not pending:
                    state["status"] = "completed"
                    record("run_completed", accepted_tasks=[t["task_id"] for t in plan["tasks"]])
                    (directory / "summary.md").write_text(
                        "# Local Agent Run\n\nStatus: COMPLETED\n\n" + "\n".join(
                            f"- {t['task_id']}: accepted DONE; worker {t['owner']}; attempts {state['tasks'].get(t['task_id'], {}).get('attempts', 0)}"
                            for t in plan["tasks"]
                        ) + "\n", encoding="utf-8")
                    return 0
                selected = None
                for task in pending:
                    _, header, _ = task_card(task["task_id"])
                    if all(accepted(dep) for dep in header.get("dependencies", [])):
                        selected = task
                        break
                if selected is None:
                    raise LoopError("No dependency-ready task remains; run cannot make progress.")
                task = selected
                task_id, owner = task["task_id"], task["owner"]
                card, header, body = task_card(task_id)
                entry = state["tasks"].setdefault(task_id, {"attempts": 0})
                if "payload_id" not in entry:
                    if card.parent.name != "ready":
                        raise LoopError("A partial task without this run's durable handoff cannot be adopted.")
                    payload_id = emit_event(task_id, "ready_assigned", plan["run_id"], header)
                    entry.update(payload_id=payload_id, activation="pending")
                    record("dispatch_prepared", task_id, owner=owner, payload_id=payload_id)
                if entry.get("activation") != "acknowledged":
                    from event_routing import load_delivery_state_map
                    stored = load_delivery_state_map().get(entry["payload_id"])
                    if stored is None:
                        raise LoopError("Prepared dispatch disappeared from the delivery ledger.")
                    if stored.status == "pending":
                        output = json.loads(cli("worker_poller.py", "activate", owner, "--task-id", task_id, "--json"))
                        if not output.get("activated") or output.get("payload_id") != entry["payload_id"]:
                            raise LoopError("Exact task activation failed; unrelated work was not consumed.")
                    handoff(task_id, owner, entry["payload_id"])
                    entry["activation"] = "acknowledged"
                    record("task_dispatched", task_id, owner=owner, payload_id=entry["payload_id"])
                handoff(task_id, owner, entry["payload_id"])
                if card.parent.name != "review":
                    if entry["attempts"] >= plan["max_attempts"]:
                        raise LoopError(f"Task {task_id} exhausted its bounded attempts.")
                    entry["attempts"] += 1
                    entry.pop("exit_code", None)
                    entry.pop("scope_violations", None)
                    entry["scope_baseline"] = fingerprints()
                    entry["phase"] = "launch_intent" if launch is None else "injected_worker"
                    record("worker_started", task_id, owner=owner, attempt=entry["attempts"])
                    def started(pid):
                        entry.update(pid=pid, phase="running")
                        record("worker_process_started", task_id, pid=pid)
                    if launch is None:
                        code = launch_worker(task_id, owner, entry["payload_id"], remaining(plan["worker_timeout_seconds"]), started,
                                             lambda metadata: record("worker_metadata", task_id, metadata=metadata))
                    else:
                        code = launch(task_id, owner, entry["payload_id"], remaining(plan["worker_timeout_seconds"]))
                    violations = scope_changes(entry["scope_baseline"], header)
                    entry.update(exit_code=code, scope_violations=violations, phase="exited")
                    entry.pop("pid", None)
                    if violations:
                        entry["terminal_failure"] = "scope_breach"
                    record("worker_exited", task_id, exit_code=code, scope_violations=violations)
                    if violations:
                        raise LoopError("Worker changed files outside its declared scope; further dispatch stopped.")
                    if code:
                        raise LoopError(f"Worker {owner} failed with exit {code}; no delivery accepted.")
                card, header, body = task_card(task_id)
                if card.parent.name != "review":
                    raise LoopError("Worker exit alone is insufficient: matching REVIEW card is missing.")
                if entry.get("phase") != "exited" or entry.get("exit_code") != 0 or not entry.get("attempts") or "scope_baseline" not in entry:
                    raise LoopError("Submission has no clean recorded worker exit; review cannot be adopted.")
                if state["contracts"][task_id] != task_contract(header, body):
                    raise LoopError("Worker changed the frozen task contract.")
                if scope_changes(entry["scope_baseline"], header):
                    entry["terminal_failure"] = "scope_breach"
                    raise LoopError("Resumed submission has an unresolved scope breach.")
                for name, expected in state["checkers"].items():
                    if hashlib.sha256(relative_path(name).read_bytes()).hexdigest() != expected:
                        raise LoopError("Independent checker source changed; acceptance stopped.")
                handoff(task_id, owner, entry["payload_id"])
                from validate_coordination_files import validate_task_file, validate_delivery_file
                report = ROOT / "coordination/delivery" / f"{task_id}-delivery-report.md"
                failures = []
                if not report.is_file():
                    raise LoopError("Required delivery report is missing.")
                text = report.read_text(encoding="utf-8")
                if f"- Task ID: {task_id}\n" not in text or f"- Agent: {owner}\n" not in text:
                    failures.append("Delivery report does not identify this exact task and worker.")
                if f"- Phase: {header.get('phase')}\n" not in text or "- Status: DELIVERED\n" not in text:
                    failures.append("Delivery report phase or DELIVERED status differs from this task.")
                failures.extend(str(e) for e in validate_task_file(card) + validate_delivery_file(report))
                failures.extend(acceptance_checks(task, remaining(plan["check_timeout_seconds"])))
                decision = "needs_fix" if failures else "accepted"
                review_args = ["--task-id", task_id, "--reviewer", REVIEWER, "--decision", decision,
                               "--summary", "Independent declared checks failed." if failures else "All declared independent checks and submission receipts passed.",
                               "--validation", "Task/report format, exact handoff, scope fingerprints and pinned acceptance checks inspected.",
                               "--artifact", report.relative_to(ROOT).as_posix()]
                for failure in failures:
                    review_args.extend(["--required-change", failure])
                notification = emit_event(task_id, "review_submitted", plan["run_id"], header)
                cli("review_task.py", *review_args)
                from event_routing import acknowledge
                if not acknowledge(notification):
                    raise LoopError("Verified review notification could not be acknowledged.")
                entry["last_decision"] = decision
                record("task_reviewed", task_id, decision=decision, failed_checks=failures)
                if failures:
                    review = ROOT / "coordination/reviews" / f"review-{task_id}.md"
                    (directory / f"{task_id}-attempt-{entry['attempts']}-review.md").write_bytes(review.read_bytes())
                    # The shared review helper records NEEDS_FIX in review/. The
                    # authorized lead explicitly makes this same-task repair runnable.
                    header, body = load_task(card)
                    move_task(card, "in_progress", header, body)
                    record("repair_dispatched", task_id, same_acknowledged_payload=entry["payload_id"])
                    if entry["attempts"] >= plan["max_attempts"]:
                        raise LoopError(f"Task {task_id} exhausted its bounded repair attempts.")
        except (LoopError, OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
            state["status"] = "failed"
            record("run_stopped", reason=str(exc) if isinstance(exc, LoopError) else type(exc).__name__)
            return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run", action="store_true", help="Authorize the finite plan's worker launches and deterministic reviews.")
    parser.add_argument("--resume", action="store_true", help="Resume this exact plan using durable handoffs, never reset acknowledgements.")
    args = parser.parse_args()
    try:
        return run_loop(args.plan, execute=args.run, resume=args.resume)
    except (LoopError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "stopped", "reason": str(exc) if isinstance(exc, LoopError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
