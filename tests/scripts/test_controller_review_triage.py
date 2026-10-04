from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import coordination_common
import review_task
from validate_coordination_files import validate_review_file


def _review_card(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    path = tmp_path / "coordination" / "task-board" / "review" / "task.md"
    path.parent.mkdir(parents=True)
    (tmp_path / "coordination" / "reviews").mkdir(parents=True)
    return path, {
        "task_id": "task-01",
        "phase": "phase-test",
        "owner": "worker-01",
        "reviewer": "ORCHESTRATOR",
        "status": "REVIEW",
    }


def _argv(*extra: str) -> list[str]:
    return [
        "review_task.py",
        "--task-id", "task-01",
        "--reviewer", "ORCHESTRATOR",
        "--summary", "Evidence reviewed.",
        "--controller-triage",
        "--human-decision", "not-needed",
        "--risk", "none",
        *extra,
    ]


def test_escalation_stays_in_review_and_never_dispatches(monkeypatch, capsys, tmp_path) -> None:
    path, card = _review_card(tmp_path)
    saved = []
    monkeypatch.setattr(review_task, "find_task", lambda _: (path, card.copy(), "# task\n"))
    monkeypatch.setattr(review_task, "next_review_file_for", lambda _: tmp_path / "coordination" / "reviews" / "review-task.md")
    monkeypatch.setattr(review_task, "save_task", lambda current, front, body: saved.append((current, front.copy(), body)))
    monkeypatch.setattr(review_task, "progress_file_for", lambda _: tmp_path / "missing-progress.md")
    monkeypatch.setattr(review_task, "move_task", lambda *args: pytest.fail("paused delivery must remain in review/"))
    monkeypatch.setattr(review_task, "assign_ready_task", lambda *args: pytest.fail("paused delivery must not dispatch"))
    monkeypatch.setattr(sys, "argv", _argv("--decision", "paused", "--human-decision", "required"))

    assert review_task.main() == 0
    assert saved and saved[0][0] == path and saved[0][1]["status"] == "REVIEW"
    assert "ESCALATION REQUIRED (human decision needed)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("reviewer", "decision", "triage"),
    [
        ("worker-01", "accepted", ()),
        ("ORCHESTRATOR", "accepted", ("--risk", "identified")),
    ],
)
def test_acceptance_requires_controller_clear_triage_before_task_lookup(
    monkeypatch, capsys, reviewer: str, decision: str, triage: tuple[str, ...]
) -> None:
    monkeypatch.setattr(sys, "argv", [
        "review_task.py", "--task-id", "task-01", "--reviewer", reviewer,
        "--decision", decision, "--summary", "Evidence reviewed.",
        "--controller-triage", "--human-decision", "not-needed", "--risk", "none",
        *triage,
    ])
    monkeypatch.setattr(review_task, "find_task", lambda _: pytest.fail("invalid triage must fail before task lookup"))

    assert review_task.main() == 1
    error = capsys.readouterr().err
    assert "--reviewer ORCHESTRATOR" in error or "use --decision paused" in error


def test_safe_correction_dispatch_is_not_blocked_by_unrelated_reviews(monkeypatch, capsys, tmp_path) -> None:
    path, card = _review_card(tmp_path)
    ready_path = tmp_path / "coordination" / "task-board" / "ready" / "task.md"
    moved = []
    dispatched = []

    monkeypatch.setattr(review_task, "find_task", lambda _: (path, card.copy(), "# task\n"))
    monkeypatch.setattr(review_task, "next_review_file_for", lambda _: tmp_path / "coordination" / "reviews" / "review-task.md")

    def move(current, state, front, body):
        moved.append((state, front.copy(), body))
        return ready_path

    monkeypatch.setattr(review_task, "move_task", move)
    monkeypatch.setattr(review_task, "list_tasks", lambda states: [(path, {"task_id": "unrelated", "owner": "worker-02"})] if states == ("review",) else [])
    monkeypatch.setattr(review_task, "progress_file_for", lambda _: tmp_path / "missing-progress.md")
    monkeypatch.setattr(review_task, "assign_ready_task", lambda task_id, owner: dispatched.append((task_id, owner)) or (ready_path, "dispatch message\n"))
    monkeypatch.setattr(sys, "argv", _argv("--decision", "needs_fix", "--required-change", "Fix the scoped regression."))

    assert review_task.main() == 0
    assert moved[0][0] == "ready"
    assert "Latest Controller Review Feedback" in moved[0][2]
    assert dispatched == [("task-01", "worker-01")]
    assert "Returned for in-scope corrections" in capsys.readouterr().out


def test_correction_review_preserves_prior_review_and_points_to_latest(monkeypatch, capsys, tmp_path) -> None:
    path, card = _review_card(tmp_path)
    reviews = tmp_path / "coordination" / "reviews"
    prior = reviews / "review-task-01.md"
    prior.write_text("prior review evidence\n", encoding="utf-8")
    moved = []
    monkeypatch.setattr(coordination_common, "REVIEWS_DIR", reviews)
    monkeypatch.setattr(review_task, "find_task", lambda _: (path, card.copy(), "# task\n"))
    monkeypatch.setattr(review_task, "move_task", lambda current, state, front, body: moved.append((state, body)) or (tmp_path / "coordination" / "task-board" / state / current.name))
    monkeypatch.setattr(review_task, "progress_file_for", lambda _: tmp_path / "missing-progress.md")
    monkeypatch.setattr(review_task, "assign_ready_task", lambda *_: "not dispatched")
    monkeypatch.setattr(sys, "argv", _argv("--decision", "needs_fix", "--required-change", "Fix one issue."))

    assert review_task.main() == 0
    latest = reviews / "review-task-01-2.md"
    assert prior.read_text(encoding="utf-8") == "prior review evidence\n"
    assert "Review report: `coordination/reviews/review-task-01-2.md`" in moved[0][1]
    assert latest.exists() and "- Decision: needs_fix" in latest.read_text(encoding="utf-8")


@pytest.mark.parametrize("artifact_section", ["## Accepted Artifacts", "## Reviewed Artifacts"])
def test_review_validator_accepts_either_artifact_section(tmp_path: Path, artifact_section: str) -> None:
    path = tmp_path / "review.md"
    path.write_text(
        "# Review Report\n\n"
        "- Review ID: review-task-01\n- Reviewer: ORCHESTRATOR\n- Task ID: task-01\n"
        "- Phase: phase-test\n- Decision: paused\n- Reviewed At: now\n\n"
        "## Summary\n\nSummary.\n\n## Findings\n\n- none\n\n"
        "## Scope Compliance\n\nPASS\n\n## Validation Check\n\nChecked.\n\n"
        "## Required Changes\n\n- Wait\n\n" + artifact_section + "\n\n- task.md\n",
        encoding="utf-8",
    )

    assert validate_review_file(path) == []
