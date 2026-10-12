"""Finite local orchestration using real lifecycle helpers and fake workers."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[2]
OPEN = "opencode-coordination-pilot"
HERMES = "hermes-coordination-pilot"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # Copy scripts so subprocess helpers resolve the same isolated ROOT. No
    # production registry, inbox, task card or installed model is accessed.
    root = tmp_path / "repo"
    shutil.copytree(SOURCE / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    names = {path.stem for path in (root / "scripts").glob("*.py")}
    saved = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    monkeypatch.syspath_prepend(str(root / "scripts"))
    loop = importlib.import_module("local_agent_loop")
    common = importlib.import_module("coordination_common")
    routing = importlib.import_module("event_routing")
    monitor = root / "coordination/monitor"
    for name in ("task-board/ready", "task-board/in_progress", "task-board/review", "task-board/done",
                 "delivery", "reviews", "progress", "monitor"):
        (root / "coordination" / name).mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text("coordination/monitor/\n__pycache__/\n", encoding="utf-8")
    (root / "protected.txt").write_text("original", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (monitor / "projects.json").write_text(json.dumps([
        {"project_id": loop.PROJECT, "local_path": str(root)}]), encoding="utf-8")
    (monitor / "workers.json").write_text(json.dumps([
        {"worker_id": owner, "project_id": loop.PROJECT, "enabled": True}
        for owner in (OPEN, HERMES)]), encoding="utf-8")
    (monitor / "routing_policy.json").write_text(json.dumps([{
        "project_id": loop.PROJECT, "routes": [
            {"event_type": "ready_assigned", "destination": "registered_worker"},
            {"event_type": "review_submitted", "destination": "orchestrator"}],
    }]), encoding="utf-8")

    def task(task_id="first", owner=OPEN, dependencies=(), checks=None):
        checks = checks or [{"path": f"artifacts/{task_id}.json", "json_equals": {"complete": True}}]
        header = {
            "task_id": task_id, "phase": "local-test", "status": "READY",
            "owner": owner, "reviewer": "LOCAL_LOOP", "priority": "high",
            "dependencies": list(dependencies),
            "allowed_scope": [f"coordination/task-board/{state}/{task_id}.md"
                              for state in ("ready", "in_progress", "review")]
                             + [f"coordination/delivery/{task_id}-delivery-report.md",
                                f"coordination/progress/{owner}.md", f"artifacts/{task_id}.json"],
            "forbidden_scope": ["scripts/**", "protected.txt"],
            "acceptance": ["Declared artifact checks pass."],
            "expected_artifacts": ["delivery_report"], "execution_mode": "REPO_FIRST",
            "local_loop_checks_sha256": loop.digest(checks),
        }
        sections = ("Objective", "Context", "Constraints", "Implementation Notes", "Validation Steps", "Escalation Rules")
        common.save_task(root / f"coordination/task-board/ready/{task_id}.md", header,
                         "# Task Packet\n\n" + "\n\n".join(f"## {s}\n\nLocal test contract." for s in sections) + "\n")
        return {"task_id": task_id, "owner": owner, "checks": checks}

    def plan(tasks, **options):
        value = {"version": 1, "run_id": "test-run", "tasks": tasks, **options}
        path = root / "plan.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def submit(task_id, owner, payload_id, timeout, *, valid=True):
        assert loop.handoff(task_id, owner, payload_id)["task_id"] == task_id
        card, _, _ = loop.task_card(task_id)
        if card.parent.name == "ready":
            loop.cli("claim_task.py", "--task-id", task_id, "--agent", owner)
        artifact = root / f"artifacts/{task_id}.json"
        artifact.parent.mkdir(exist_ok=True)
        artifact.write_text(json.dumps({"complete": valid}), encoding="utf-8")
        report = root / f"coordination/delivery/{task_id}-delivery-report.md"
        report.write_text(
            f"# Delivery Report\n\n- Task ID: {task_id}\n- Agent: {owner}\n"
            "- Phase: local-test\n- Status: DELIVERED\n\n"
            + "\n\n".join(f"## {label}\n\nTest worker evidence." for label in (
                "Changed Files", "Validation Steps Performed", "Known Residual Risks", "Acceptance Criteria Coverage"))
            + "\n", encoding="utf-8")
        loop.cli("submit_task.py", "--task-id", task_id, "--agent", owner)
        return 0

    def state():
        return json.loads((monitor / "local-loop/test-run/state.json").read_text(encoding="utf-8"))

    def edit_card(task_id, **changes):
        path, header, body = loop.task_card(task_id)
        header.update(changes)
        common.save_task(path, header, body)

    try:
        yield SimpleNamespace(root=root, loop=loop, common=common, routing=routing,
                              task=task, plan=plan, submit=submit, state=state, edit_card=edit_card)
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved)


def test_repair_then_dependent_worker_completes_without_consuming_other_work(repo):
    first = repo.task()
    second = repo.task("second", HERMES, dependencies=["first"])
    foreign = repo.task("other", OPEN)
    _, header, _ = repo.loop.task_card("other")
    foreign_payload = repo.loop.emit_event("other", "ready_assigned", "foreign-run", header)
    calls = []

    def worker(task_id, owner, payload_id, timeout):
        calls.append((task_id, owner, payload_id))
        if task_id == "first" and len(calls) == 2:
            notifications = [record for record in repo.routing.load_delivery_state_map().values()
                             if record.task_id == "first" and record.destination == "orchestrator"]
            assert notifications and all(record.status == "acknowledged" for record in notifications)
        if task_id == "second":
            assert repo.loop.accepted("first")
        return repo.submit(task_id, owner, payload_id, timeout, valid=len(calls) != 1)

    path = repo.plan([second, first])  # Dependency order, not list order, drives execution.
    assert repo.loop.run_loop(path, execute=True, launch=worker) == 0
    assert [call[:2] for call in calls] == [("first", OPEN), ("first", OPEN), ("second", HERMES)]
    assert calls[0][2] == calls[1][2]
    assert all(repo.loop.accepted(task) for task in ("first", "second"))
    assert repo.routing.load_delivery_state_map()[foreign_payload].status == "pending"
    assert repo.loop.task_card(foreign["task_id"])[0].parent.name == "ready"
    directory = repo.root / "coordination/monitor/local-loop/test-run"
    assert "- Decision: needs_fix" in (directory / "first-attempt-1-review.md").read_text(encoding="utf-8")
    assert "Status: COMPLETED" in (directory / "summary.md").read_text(encoding="utf-8")
    assert repo.state()["status"] == "completed"
    assert repo.loop.run_loop(path, execute=True, launch=worker) == 0
    assert len(calls) == 3


def test_interrupted_run_requires_resume_and_reuses_its_handoff(repo):
    path = repo.plan([repo.task()])
    calls = []

    def interrupted(task_id, owner, payload_id, timeout):
        calls.append(payload_id)
        repo.loop.cli("claim_task.py", "--task-id", task_id, "--agent", owner)
        return 9

    assert repo.loop.run_loop(path, execute=True, launch=interrupted) == 1
    assert repo.state()["status"] == "failed"
    with pytest.raises(repo.loop.LoopError, match="requires explicit --resume"):
        repo.loop.run_loop(path, execute=True, launch=repo.submit)

    def resumed(task_id, owner, payload_id, timeout):
        calls.append(payload_id)
        return repo.submit(task_id, owner, payload_id, timeout)

    assert repo.loop.run_loop(path, execute=True, resume=True, launch=resumed) == 0
    assert len(calls) == 2 and calls[0] == calls[1]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["max_attempts"] = 3
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(repo.loop.LoopError, match="immutable plan"):
        repo.loop.run_loop(path, execute=True, resume=True, launch=resumed)


@pytest.mark.parametrize("failure", ["missing_receipt", "nonzero_exit", "missing_report", "scope", "exhaustion"])
def test_failures_stop_before_dependent_dispatch_and_never_accept(repo, failure):
    path = repo.plan([repo.task(), repo.task("second", HERMES, dependencies=["first"])])
    calls = []

    def worker(task_id, owner, payload_id, timeout):
        calls.append(task_id)
        if failure == "missing_receipt":
            return 0
        code = repo.submit(task_id, owner, payload_id, timeout, valid=failure != "exhaustion")
        if failure == "nonzero_exit":
            return 7
        if failure == "missing_report":
            (repo.root / f"coordination/delivery/{task_id}-delivery-report.md").unlink()
        if failure == "scope":
            (repo.root / "protected.txt").write_text("worker changed forbidden file", encoding="utf-8")
        return code

    assert repo.loop.run_loop(path, execute=True, launch=worker) == 1
    assert calls == ["first"] * (2 if failure == "exhaustion" else 1)
    assert repo.state()["status"] == "failed"
    assert not repo.loop.accepted("first")
    assert repo.loop.task_card("second")[0].parent.name == "ready"
    if failure == "scope":
        # A REVIEW card produced alongside forbidden changes must not become
        # acceptable merely because the operator retries the same failed run.
        with pytest.raises(repo.loop.LoopError, match="scope breach"):
            repo.loop.run_loop(path, execute=True, resume=True, launch=worker)
        assert not repo.loop.accepted("first")
        assert calls == ["first"]


@pytest.mark.parametrize("change", ["reviewer", "checks", "cycle", "escape"])
def test_unapproved_contracts_rejected_before_any_dispatch(repo, change):
    first = repo.task()
    second = repo.task("second", HERMES, dependencies=["first"])
    if change == "reviewer":
        repo.edit_card("first", reviewer="ORCHESTRATOR")
    elif change == "checks":
        first["checks"][0]["json_equals"] = {"complete": "unapproved"}
    elif change == "cycle":
        repo.edit_card("first", dependencies=["second"])
    else:
        first["checks"][0]["path"] = "../outside.json"
    with pytest.raises(repo.loop.LoopError):
        repo.loop.run_loop(repo.plan([first, second]), execute=True, launch=repo.submit)
    assert not (repo.root / "coordination/monitor/local-loop/test-run/state.json").exists()


def test_independent_command_check_can_fail_a_delivery(repo):
    (repo.root / "check.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    task = repo.task(checks=[{"command": ["$PYTHON", "check.py"]}])
    assert repo.loop.run_loop(repo.plan([task], max_attempts=1), execute=True, launch=repo.submit) == 1
    assert "independent command exited 1" in (repo.root / "coordination/reviews/review-first.md").read_text(encoding="utf-8")
    assert not repo.loop.accepted("first")


def test_preview_has_no_runtime_effect_and_live_lock_rejects_a_second_controller(repo):
    path = repo.plan([repo.task()])
    assert repo.loop.run_loop(path) == 0
    assert not (repo.root / "coordination/monitor/local-loop").exists()
    with repo.loop.process_lock():
        with pytest.raises(repo.loop.LoopError, match="Another local controller"):
            repo.loop.run_loop(path, execute=True, launch=repo.submit)


@pytest.mark.parametrize("tamper", ["reviewer", "report_task", "report_owner"])
def test_completed_run_rechecks_exact_completion_identity(repo, tamper):
    path = repo.plan([repo.task()])
    assert repo.loop.run_loop(path, execute=True, launch=repo.submit) == 0
    if tamper == "reviewer":
        evidence = repo.root / "coordination/reviews/review-first.md"
        original, replacement = "- Reviewer: LOCAL_LOOP", "- Reviewer: UNAUTHORIZED"
    else:
        evidence = repo.root / "coordination/delivery/first-delivery-report.md"
        original, replacement = (("- Task ID: first", "- Task ID: another-task") if tamper == "report_task"
                                 else (f"- Agent: {OPEN}", f"- Agent: {HERMES}"))
    evidence.write_text(evidence.read_text(encoding="utf-8").replace(original, replacement), encoding="utf-8")
    assert repo.loop.run_loop(path, execute=True, launch=repo.submit) == 1
    assert repo.state()["status"] == "failed"


def test_wrong_durable_inbox_identity_cannot_become_an_accepted_receipt(repo):
    path = repo.plan([repo.task()])

    def worker(task_id, owner, payload_id, timeout):
        repo.submit(task_id, owner, payload_id, timeout)
        inbox = repo.root / f"coordination/monitor/inbox/{owner}/{payload_id}.json"
        payload = json.loads(inbox.read_text(encoding="utf-8"))
        payload["task_id"] = "some-other-task"
        inbox.write_text(json.dumps(payload), encoding="utf-8")
        return 0

    assert repo.loop.run_loop(path, execute=True, launch=worker) == 1
    assert not repo.loop.accepted("first")


def test_checker_must_be_outside_every_worker_write_scope(repo):
    (repo.root / "check.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    task = repo.task(checks=[{"command": ["$PYTHON", "check.py"]}])
    _, header, _ = repo.loop.task_card("first")
    repo.edit_card("first", allowed_scope=[*header["allowed_scope"], "check.py"])
    with pytest.raises(repo.loop.LoopError, match="outside worker-write scope"):
        repo.loop.run_loop(repo.plan([task]), execute=True, launch=repo.submit)


def test_worker_cannot_rewrite_its_authorized_packet_to_get_accepted(repo):
    path = repo.plan([repo.task()])

    def worker(task_id, owner, payload_id, timeout):
        repo.submit(task_id, owner, payload_id, timeout)
        repo.edit_card(task_id, acceptance=["Worker replaced the original acceptance contract."])
        return 0

    assert repo.loop.run_loop(path, execute=True, launch=worker) == 1
    assert not repo.loop.accepted("first")
    assert "frozen task contract" in (repo.root / "coordination/monitor/local-loop/test-run/events.jsonl").read_text(encoding="utf-8")


def test_worker_metadata_discards_private_text_and_invalid_field_types(repo):
    value = {
        "api_step": 2, "api_calls": True, "completed": False, "failed": "private-marker",
        "tool_results": [{"exit_code": 7, "error": True, "output": "private-marker"},
                         {"exit_code": "private-marker", "error": "private-marker"}],
        "diagnostics": ["private-marker HTTP 429 rate_limit_exceeded private-marker"],
        "status": "private-marker Waiting 12.5s (attempt 1/2)",
        "failure_reason": "private-marker missing_review_receipt",
        "final_response": "private-marker", "messages": ["private-marker"],
    }
    result = repo.loop.worker_metadata(json.dumps(value))
    assert result == {
        "api_step": 2, "completed": False,
        "tool_results": [{"exit_code": 7, "error": True}, {}],
        "diagnostics": ["HTTP 429", "rate_limit_exceeded"],
        "status": ["Waiting 12.5s", "attempt 1/2"],
        "failure_reason": ["missing_review_receipt"],
    }
    assert "private-marker" not in json.dumps(result)
    assert repo.loop.worker_metadata('{"turn_exit_category":"text_response"}') == {"turn_exit_category": "text_response"}
    for category in ([], {}, "private-marker", True, None):
        assert repo.loop.worker_metadata(json.dumps({"turn_exit_category": category})) is None
    for line in ("private-marker", "[]", '{"output":"private-marker"}', '{"api_step":-1}', '{"api_calls":10001}'):
        assert repo.loop.worker_metadata(line) is None


def test_bounded_child_forwards_only_sanitized_metadata_and_skips_oversized_lines(repo):
    metadata = []
    code = (
        "import json\n"
        "print('private-marker', flush=True)\n"
        "print(json.dumps({'api_calls':3, 'output':'private-marker'*1000}), flush=True)\n"
        "print(json.dumps({'api_step':1, 'output':'private-marker'}), flush=True)\n"
        "print(json.dumps({'failed':True, 'diagnostics':['private-marker HTTP 413 payload too large']}), flush=True)\n"
        "raise SystemExit(7)\n"
    )
    assert repo.loop.bounded_process([sys.executable, "-c", code], 10, on_metadata=metadata.append) == 7
    assert metadata == [{"api_step": 1}, {"failed": True, "diagnostics": ["HTTP 413", "payload too large"]}]
    assert "private-marker" not in json.dumps(metadata)


def test_bounded_child_timeout_stops_the_owned_process(repo):
    pids = []
    with pytest.raises(repo.loop.LoopError, match="Owned process tree was stopped"):
        repo.loop.bounded_process([sys.executable, "-c", "import time; time.sleep(30)"],
                                  0.2, on_start=pids.append)
    assert len(pids) == 1 and not repo.loop.process_alive(pids[0])


def test_structured_submit_generates_real_evidence_and_refuses_unverified_reporting(repo):
    shutil.copytree(SOURCE / "coordination/templates", repo.root / "coordination/templates")
    repo.task("reported", HERMES)
    _, header, _ = repo.loop.task_card("reported")
    payload = repo.loop.emit_event("reported", "ready_assigned", "report-test", header)
    repo.loop.cli("worker_poller.py", "activate", HERMES, "--task-id", "reported", "--json")
    repo.loop.cli("claim_task.py", "--task-id", "reported", "--agent", HERMES)
    artifact = repo.root / "artifacts/reported.json"
    artifact.parent.mkdir()
    artifact.write_text('{"complete":true}')
    report = repo.root / "coordination/delivery/reported-delivery-report.md"
    base = [sys.executable, str(repo.root / "scripts/submit_task.py"), "--task-id", "reported", "--agent", HERMES, "--summary", "Produced the declared artifact."]
    for args in (["--artifact", "artifacts/reported.json"],
                 ["--payload-id", "0000000000000000", "--artifact", "artifacts/reported.json"],
                 ["--payload-id", payload, "--artifact", "protected.txt"]):
        result = subprocess.run(base + args, cwd=repo.root, capture_output=True, text=True, timeout=30)
        assert result.returncode == 1
        assert not report.exists()
        assert repo.loop.task_card("reported")[0].parent.name == "in_progress"
    result = subprocess.run(base + ["--payload-id", payload, "--artifact", "artifacts/reported.json"], cwd=repo.root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    text = report.read_text()
    assert "- Task ID: reported" in text and "- Agent: " + HERMES in text
    assert "- Status: DELIVERED" in text and "- Payload ID: " + payload in text
    assert "SHA256 " + __import__("hashlib").sha256(artifact.read_bytes()).hexdigest() in text
    assert "coordination validation passed before submission" in text
    assert "## Artifact Paths" in text and "## Recommended Handoff" in text
    assert repo.loop.task_card("reported")[0].parent.name == "review"
    # A real validation failure produces no REVIEW receipt and no PASS claim.
    repo.task("failed", HERMES)
    _, header, _ = repo.loop.task_card("failed")
    payload = repo.loop.emit_event("failed", "ready_assigned", "report-failed", header)
    repo.loop.cli("worker_poller.py", "activate", HERMES, "--task-id", "failed", "--json")
    repo.loop.cli("claim_task.py", "--task-id", "failed", "--agent", HERMES)
    (repo.root / "artifacts/failed.json").write_text('{"complete":true}')
    (repo.root / "coordination/delivery/bad-delivery-report.md").write_text("invalid unrelated report")
    command = [sys.executable, str(repo.root / "scripts/submit_task.py"), "--task-id", "failed", "--agent", HERMES, "--summary", "Artifact exists.", "--payload-id", payload, "--artifact", "artifacts/failed.json"]
    result = subprocess.run(command, cwd=repo.root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1
    assert repo.loop.task_card("failed")[0].parent.name == "in_progress"
    failed = (repo.root / "coordination/delivery/failed-delivery-report.md").read_text()
    assert "Repository validation failed" in failed
    assert "coordination validation passed" not in failed
