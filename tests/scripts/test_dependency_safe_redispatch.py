from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import coordination_common
import dispatch_task
import orchestrate
import review_task
import wave_planner


def test_dependency_blockers_require_each_dependency_in_done() -> None:
    tasks = {
        "done-dep": {"_state_dir": "done"},
        "active-dep": {"_state_dir": "in_progress"},
        "child": {"_state_dir": "ready", "dependencies": ["done-dep", "active-dep", "missing-dep"]},
    }
    assert wave_planner.dependency_blockers("child", tasks) == [
        {"dependency": "active-dep", "state": "in_progress"},
        {"dependency": "missing-dep", "state": "missing"},
    ]
    tasks["child"]["dependencies"] = ["done-dep"]
    assert wave_planner.dependency_blockers("child", tasks) == []


def test_wave_planner_fails_closed_on_missing_and_malformed_dependencies() -> None:
    plan = wave_planner.plan_waves({
        "ready-child": {"_state_dir": "ready", "dependencies": ["missing"]},
        "malformed-child": {"_state_dir": "ready", "dependencies": "dep-01"},
        "invalid-item-child": {"_state_dir": "ready", "dependencies": [None]},
    })
    assert plan["ready"] == []
    assert set(plan["blocked"]) == {"ready-child", "malformed-child", "invalid-item-child"}
    assert {error["type"] for error in plan["errors"]} == {"missing_dependency", "invalid_dependencies"}


def test_duplicate_task_id_cannot_satisfy_dependency(monkeypatch, tmp_path) -> None:
    board = tmp_path / "task-board"
    for state in ("blocked", "done", "ready"):
        (board / state).mkdir(parents=True)
    (board / "blocked" / "dep-blocked.md").write_text(
        "---\ntask_id: shared-dependency\nstatus: BLOCKED\ndependencies: []\n---\nBlocked duplicate.\n",
        encoding="utf-8",
    )
    (board / "done" / "dep-done.md").write_text(
        "---\ntask_id: shared-dependency\nstatus: DONE\ndependencies: []\n---\nDone duplicate.\n",
        encoding="utf-8",
    )
    (board / "ready" / "child.md").write_text(
        "---\ntask_id: child-task\nstatus: READY\ndependencies:\n  - shared-dependency\n---\nChild.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(wave_planner, "TASK_BOARD_DIR", board)

    plan = wave_planner.plan_waves()
    assert plan["ready"] == []
    assert "child-task" in plan["blocked"]
    assert "shared-dependency" in plan["blocked"]
    assert wave_planner.dependency_blockers("child-task") == [
        {"dependency": "shared-dependency", "state": "duplicate_task_id"}
    ]
    assert wave_planner.dependency_blockers("shared-dependency") == [
        {"dependency": "shared-dependency", "state": "duplicate_task_id"}
    ]


def test_next_recommends_only_dependency_ready_task_and_never_blocked_dispatch(monkeypatch, capsys) -> None:
    ready = [
        (Path("coordination/task-board/ready/blocked.md"), {"task_id": "blocked", "owner": "UNASSIGNED"}),
        (Path("coordination/task-board/ready/eligible.md"), {"task_id": "eligible", "owner": "UNASSIGNED"}),
    ]

    def list_tasks(states):
        return {"review": [], "ready": ready, "blocked": [(Path("coordination/task-board/blocked/old.md"), {"task_id": "old-blocked", "owner": "agent-x"})]}[states[0]]

    monkeypatch.setattr(coordination_common, "list_tasks", list_tasks)
    monkeypatch.setattr(wave_planner, "plan_waves", lambda: {"ready": ["eligible"]})
    assert orchestrate.run_next(None) == 0
    output = capsys.readouterr().out
    assert "--task-id eligible" in output
    assert "--task-id blocked" not in output
    assert "old-blocked" not in output


def test_next_does_not_preselect_acceptance_for_a_review_task(monkeypatch, capsys) -> None:
    review = [(Path("coordination/task-board/review/task.md"), {"task_id": "task-01", "owner": "agent-01"})]
    monkeypatch.setattr(coordination_common, "list_tasks", lambda states: review if states == ("review",) else [])

    assert orchestrate.run_next(None) == 0
    output = capsys.readouterr().out
    assert "inspect the task card" in output.lower()
    assert "--decision accepted" not in output
    assert "If a human decision is needed" in output


@pytest.mark.parametrize(
    ("state", "blockers"),
    [
        ("blocked", []),
        ("review", []),
        ("ready", [{"dependency": "dep-01", "state": "review"}]),
        ("ready", [{"dependency": "<invalid>", "state": "invalid_dependencies"}]),
    ],
)
def test_direct_dispatch_refuses_blocked_or_unfinished_dependencies_without_mutation(monkeypatch, capsys, tmp_path, state, blockers) -> None:
    path = tmp_path / "coordination" / "task-board" / state / "task.md"
    card = {"task_id": "task-01", "owner": "UNASSIGNED", "reviewer": "ORCHESTRATOR", "dependencies": []}
    monkeypatch.setattr(dispatch_task, "find_task", lambda _: (path, card.copy(), "# packet\n"))
    monkeypatch.setattr(dispatch_task, "dependency_blockers", lambda _: blockers)
    monkeypatch.setattr(dispatch_task, "save_task", lambda *args: pytest.fail("dispatch must fail before mutation"))
    monkeypatch.setattr(sys, "argv", ["dispatch_task.py", "--task-id", "task-01", "--owner", "agent-01", "--message-only"])

    assert dispatch_task.main() == 1
    error = capsys.readouterr().err
    assert "cannot be dispatched" in error or "is blocked" in error or "awaiting review" in error


def test_assignment_helper_preserves_an_existing_owner(monkeypatch, tmp_path) -> None:
    path = tmp_path / "coordination" / "task-board" / "ready" / "task.md"
    card = {"task_id": "task-01", "owner": "other-agent", "reviewer": "ORCHESTRATOR", "dependencies": []}
    monkeypatch.setattr(dispatch_task, "find_task", lambda _: (path, card, "# packet\n"))
    monkeypatch.setattr(dispatch_task, "dependency_blockers", lambda _: [])
    monkeypatch.setattr(dispatch_task, "save_task", lambda *args: pytest.fail("must not overwrite an existing owner"))

    result = dispatch_task.assign_ready_task("task-01", "agent-01")
    assert isinstance(result, str) and "assigned to `other-agent`" in result
    assert card["owner"] == "other-agent"


def test_continuation_options_are_rejected_before_nonaccepted_review_mutation(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", [
        "review_task.py", "--task-id", "task-01", "--reviewer", "human", "--decision", "needs_fix",
        "--summary", "Needs changes",
    ])
    monkeypatch.setattr(review_task, "find_task", lambda _: pytest.fail("invalid continuation must fail before reading/mutating task"))
    assert review_task.main() == 1
    assert "require --controller-triage" in capsys.readouterr().err


def _review_paths(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "coordination" / "task-board"
    review = base / "review" / "reviewed.md"
    review.parent.mkdir(parents=True, exist_ok=True)
    ready = base / "ready" / "next.md"
    ready.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "coordination" / "reviews").mkdir(parents=True, exist_ok=True)
    return review, ready


def test_accepted_review_continues_at_most_one_matching_ready_task(monkeypatch, capsys, tmp_path) -> None:
    review_path, ready_path = _review_paths(tmp_path)
    accepted = {"task_id": "reviewed-task", "phase": "phase-test", "owner": "agent-01", "reviewer": "ORCHESTRATOR", "status": "REVIEW"}
    candidates = [
        (ready_path, {"task_id": "task-a", "owner": "UNASSIGNED", "dependencies": ["reviewed-task"]}),
        (ready_path, {"task_id": "task-b", "owner": "other-agent", "dependencies": ["other-parent"]}),
        (ready_path, {"task_id": "task-c", "owner": "", "dependencies": ["other-parent"]}),
    ]
    calls = []
    moved = []

    monkeypatch.setattr(review_task, "find_task", lambda _: (review_path, accepted.copy(), "# reviewed\n"))
    monkeypatch.setattr(review_task, "next_review_file_for", lambda _: tmp_path / "coordination" / "reviews" / "review.md")
    def move_task(path, state, fm, body):
        fm["status"] = state.upper()
        moved.append((state, fm["status"]))
        return tmp_path / "coordination" / "task-board" / state / path.name

    monkeypatch.setattr(review_task, "move_task", move_task)
    unrelated_review = [(Path("coordination/task-board/review/unrelated.md"), {"task_id": "unrelated", "owner": "agent-02"})]
    monkeypatch.setattr(review_task, "list_tasks", lambda states: unrelated_review if states == ("review",) else candidates)
    monkeypatch.setattr(review_task, "plan_waves", lambda: {"ready": ["task-c", "task-b", "task-a"]})

    def assign(task_id, owner):
        calls.append((task_id, owner))
        return ready_path, f"Assigned {task_id} to {owner}.\n"

    monkeypatch.setattr(review_task, "assign_ready_task", assign)
    monkeypatch.setattr(sys, "argv", [
        "review_task.py", "--task-id", "reviewed-task", "--reviewer", "ORCHESTRATOR", "--decision", "accepted",
        "--summary", "Accepted", "--controller-triage", "--human-decision", "not-needed", "--risk", "none",
    ])

    assert review_task.main() == 0
    output = capsys.readouterr().out
    assert moved == [("done", "DONE")]
    assert calls == [("task-a", "agent-01")]
    assert "Continued with dependency-ready task `task-a`" in output


def test_continuation_skips_task_owned_by_someone_else(monkeypatch, capsys) -> None:
    candidates = [
        (Path("coordination/task-board/ready/task-a.md"), {"task_id": "task-a", "owner": "other-agent", "dependencies": ["accepted-task"]}),
        (Path("coordination/task-board/ready/task-b.md"), {"task_id": "task-b", "owner": "UNASSIGNED", "dependencies": ["accepted-task"]}),
    ]
    assigned = []
    monkeypatch.setattr(review_task, "list_tasks", lambda states: [] if states == ("review",) else candidates)
    monkeypatch.setattr(review_task, "plan_waves", lambda: {"ready": ["task-a", "task-b"]})
    monkeypatch.setattr(review_task, "assign_ready_task", lambda task_id, owner: assigned.append((task_id, owner)) or (candidates[1][0], "message\n"))

    review_task._continue_one_ready_task("accepted-task", "agent-01")
    assert assigned == [("task-b", "agent-01")]
    assert candidates[0][1]["owner"] == "other-agent"
    assert "Continued with dependency-ready task `task-b`" in capsys.readouterr().out


def test_continuation_never_selects_an_unrelated_dependency_ready_task(monkeypatch, capsys) -> None:
    stale_pilot = (
        Path("coordination/task-board/ready/phase14.5-fresh-pilot-launch.md"),
        {"task_id": "phase14.5-fresh-pilot-launch", "owner": "UNASSIGNED", "dependencies": ["old-parent"]},
    )
    assigned = []
    monkeypatch.setattr(review_task, "list_tasks", lambda states: [stale_pilot] if states == ("ready",) else [])
    monkeypatch.setattr(review_task, "plan_waves", lambda: {"ready": ["phase14.5-fresh-pilot-launch"]})
    monkeypatch.setattr(review_task, "assign_ready_task", lambda *args: assigned.append(args))

    review_task._continue_one_ready_task("newly-accepted-task", "worker-01")

    assert assigned == []
    assert "no dependency-ready task" in capsys.readouterr().out


def test_accepted_review_stays_accepted_when_no_candidate_is_ready(monkeypatch, capsys, tmp_path) -> None:
    review_path, ready_path = _review_paths(tmp_path)
    accepted = {"task_id": "reviewed-task", "phase": "phase-test", "owner": "agent-01", "reviewer": "ORCHESTRATOR", "status": "REVIEW"}
    moved = []
    assigned = []
    monkeypatch.setattr(review_task, "find_task", lambda _: (review_path, accepted.copy(), "# reviewed\n"))
    monkeypatch.setattr(review_task, "next_review_file_for", lambda _: tmp_path / "coordination" / "reviews" / "review.md")
    monkeypatch.setattr(review_task, "move_task", lambda path, state, fm, body: moved.append(state) or (tmp_path / "coordination" / "task-board" / state / path.name))
    monkeypatch.setattr(review_task, "list_tasks", lambda states: [] if states == ("review",) else [(ready_path, {"task_id": "blocked-next", "owner": "UNASSIGNED"})])
    monkeypatch.setattr(review_task, "plan_waves", lambda: {"ready": []})
    monkeypatch.setattr(review_task, "assign_ready_task", lambda *args: assigned.append(args))
    monkeypatch.setattr(sys, "argv", [
        "review_task.py", "--task-id", "reviewed-task", "--reviewer", "ORCHESTRATOR", "--decision", "accepted",
        "--summary", "Accepted", "--controller-triage", "--human-decision", "not-needed", "--risk", "none",
    ])

    assert review_task.main() == 0
    assert moved == ["done"] and assigned == []
    assert "no dependency-ready task" in capsys.readouterr().out
