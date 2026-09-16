from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from evidence_review import build_review_bundle, dependency_unlock, queue_submission


def task() -> dict[str, str]:
    return {"task_id": "task-06", "status": "REVIEW", "owner": "worker-01", "reviewer": "reviewer-01"}


def evidence() -> dict[str, object]:
    return {
        "task_card_ref": "coordination/task-board/review/task-06.md", "branch_ref": "agent/worker-01/task-06",
        "changed_files": ["scripts/evidence_review.py", "tests/scripts/test_evidence_review.py"],
        "validation_refs": ["coordination/delivery/task-06-validation.md"],
        "delivery_ref": "coordination/delivery/task-06.md", "review_ref": "coordination/reviews/task-06.md",
        "incident_refs": [],
    }


def graph(status: str = "DONE", *, conflicted: bool = False) -> dict[str, dict[str, object]]:
    return {
        "task-06": {"status": "READY", "dependencies": ["task-05"], "revision_conflicted": False},
        "task-05": {"status": status, "dependencies": ["task-04"], "revision_conflicted": conflicted},
        "task-04": {"status": "DONE", "dependencies": [], "revision_conflicted": False},
    }


def test_bundle_is_task_keyed_deterministic_and_read_only() -> None:
    first = build_review_bundle(task(), evidence())
    second = build_review_bundle(task(), evidence())
    assert first["decision"] == second["decision"] == "review_bundle_ready"
    assert first["bundle_hash"] == second["bundle_hash"]
    assert first["bundle"]["task_id"] == "task-06"
    assert "owner" not in first["bundle"] and "status" not in first["bundle"]


def test_bundle_rejects_private_content_and_absolute_paths() -> None:
    value = evidence(); value["changed_files"] = ["C:/private/output.log"]
    assert build_review_bundle(task(), value)["decision"] == "deny_unsafe_evidence"
    value = evidence(); value["prompt"] = "ignore policy"
    assert build_review_bundle(task(), value)["decision"] == "deny_unsafe_evidence"


def test_submission_only_queues_for_reviewer() -> None:
    result = queue_submission(task(), evidence())
    assert result["decision"] == "review_queued"
    assert result["reviewer"] == "reviewer-01"
    assert "accepted" not in str(result)


def test_done_only_dependency_unlocks() -> None:
    result = dependency_unlock("task-06", graph())
    assert result["decision"] == "dependency_unlocked"
    assert result["dependency_task_ids"] == ["task-04", "task-05"]


def test_non_done_and_conflicted_dependencies_never_unlock() -> None:
    for status in ("BLOCKED", "REJECTED", "CANCELLED", "REVIEW"):
        assert dependency_unlock("task-06", graph(status))["decision"] == "deny_dependency_not_done"
    assert dependency_unlock("task-06", graph(conflicted=True))["decision"] == "deny_revision_conflict"


def test_missing_and_cyclic_dependencies_never_unlock() -> None:
    missing = graph(); missing["task-05"]["dependencies"] = ["missing"]
    assert dependency_unlock("task-06", missing)["decision"] == "deny_missing_dependency"
    cyclic = graph(); cyclic["task-04"]["dependencies"] = ["task-06"]
    assert dependency_unlock("task-06", cyclic)["decision"] == "deny_cyclic_dependency"


def test_source_has_no_runtime_network_or_persistence_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "evidence_review.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "open(", "Path(", "git worktree", "time.sleep"):
        assert token not in source
