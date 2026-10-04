from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import coordination_common
import submit_task as submit_module
import task_delivery_callback as callback_module
from task_delivery_callback import make_delivery_callback


def install_board(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, state: str = "in_progress", owner: str = "agent-01") -> tuple[Path, Path]:
    board = tmp_path / "task-board"
    task_dir = board / state
    task_dir.mkdir(parents=True)
    report_dir = tmp_path / "delivery"
    report_dir.mkdir()
    progress_dir = tmp_path / "progress"
    progress_dir.mkdir()
    card = task_dir / "2026-09-30_task-01.md"
    card.write_text(
        "---\n"
        "task_id: task-01\n"
        "phase: test\n"
        f"status: {state.upper()}\n"
        f"owner: {owner}\n"
        "expected_artifacts:\n"
        "  - delivery_report\n"
        "---\n\nTask.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(coordination_common, "TASK_BOARD_DIR", board)
    monkeypatch.setattr(coordination_common, "DELIVERY_DIR", report_dir)
    monkeypatch.setattr(coordination_common, "PROGRESS_DIR", progress_dir)
    monkeypatch.setattr(submit_module, "TASK_BOARD_DIR", board)
    return board, report_dir


def changes(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {"added": ["docs/new.md"], "modified": ["scripts/example.py"], "deleted": []}
    value.update(overrides)
    return value


def test_controller_observed_report_is_generated_and_submitted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)
    observed: list[tuple[str, str]] = []
    callback = make_delivery_callback(
        evidence_provider=lambda request, session: observed.append((str(request["run_id"]), session)) or changes()
    )

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is True
    assert observed == [("run-01", "ses_exact")]
    report = coordination_common.delivery_file_for("task-01", "run-01").read_text(encoding="utf-8")
    assert "Controller-observed changed paths" in report
    assert "### Added\n\n- `docs/new.md`" in report
    assert "### Modified\n\n- `scripts/example.py`" in report
    assert "did not capture validation command output" in report
    assert "risk assessment" in report
    assert "worker-reported" not in report.casefold()
    assert "sha256" not in report.casefold()
    assert (board / "review" / "2026-09-30_task-01.md").exists()


@pytest.mark.parametrize(
    ("state", "owner", "bound_request", "session", "expected_provider"),
    [
        ("ready", "agent-01", {"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact", 0),
        ("in_progress", "agent-other", {"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact", 0),
        ("in_progress", "agent-01", {"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_bad/path", 0),
    ],
)
def test_stale_or_invalid_delivery_does_not_collect_or_submit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    state: str,
    owner: str,
    bound_request: dict,
    session: str,
    expected_provider: int,
) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path, state=state, owner=owner)
    observed: list[str] = []
    callback = make_delivery_callback(evidence_provider=lambda _request, _session: observed.append("called") or changes())

    assert callback(bound_request, session) is False
    assert len(observed) == expected_provider
    assert not coordination_common.delivery_files_for("task-01", report_dir)
    assert not (board / "review" / "2026-09-30_task-01.md").exists()


@pytest.mark.parametrize(
    "bad_changes",
    [
        {"added": ["../outside.py"], "modified": [], "deleted": []},
        {"added": ["scripts/a.py"], "modified": ["scripts/a.py"], "deleted": []},
        {"added": ["scripts/a.py"], "modified": [], "deleted": [], "extra": []},
        {"added": ["x" * 241], "modified": [], "deleted": []},
    ],
)
def test_invalid_controller_evidence_does_not_submit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_changes: dict) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)
    callback = make_delivery_callback(evidence_provider=lambda _request, _session: bad_changes)

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is False
    assert (board / "in_progress" / "2026-09-30_task-01.md").exists()
    assert not coordination_common.delivery_files_for("task-01", report_dir)


def test_existing_report_is_never_overwritten(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _, report_dir = install_board(monkeypatch, tmp_path)
    report = coordination_common.delivery_file_for("task-01", "run-01")
    report.write_text("existing evidence", encoding="utf-8")
    callback = make_delivery_callback(evidence_provider=lambda _request, _session: changes())

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is False
    assert report.read_text(encoding="utf-8") == "existing evidence"


def test_submission_failure_is_not_reported_as_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)

    def fail_submission(*_args: object, **_kwargs: object) -> None:
        raise ValueError("card changed during submission")

    monkeypatch.setattr(callback_module, "submit_task", fail_submission)
    callback = make_delivery_callback(evidence_provider=lambda _request, _session: changes())

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is False
    assert (board / "in_progress" / "2026-09-30_task-01.md").exists()
    assert not coordination_common.delivery_files_for("task-01", report_dir)


@pytest.mark.parametrize("change", ["blocked", "clear_owner"])
def test_task_must_still_be_in_progress_and_owned_after_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    change: str,
) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)
    card_path = board / "in_progress" / "2026-09-30_task-01.md"

    def mutate_during_snapshot(_request: object, _session: str) -> dict[str, object]:
        front_matter, body = coordination_common.load_task(card_path)
        if change == "blocked":
            blocked = board / "blocked"
            blocked.mkdir()
            front_matter["status"] = "BLOCKED"
            coordination_common.save_task(card_path, front_matter, body)
            card_path.replace(blocked / card_path.name)
        else:
            front_matter.pop("owner")
            coordination_common.save_task(card_path, front_matter, body)
        return changes()

    callback = make_delivery_callback(evidence_provider=mutate_during_snapshot)

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is False
    assert not coordination_common.delivery_files_for("task-01", report_dir)
    assert not (board / "review" / "2026-09-30_task-01.md").exists()
    if change == "blocked":
        assert (board / "blocked" / "2026-09-30_task-01.md").exists()
    else:
        front_matter, _ = coordination_common.load_task(card_path)
        assert "owner" not in front_matter


def test_duplicate_task_id_cannot_be_auto_submitted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)
    duplicate_dir = board / "ready"
    duplicate_dir.mkdir()
    (duplicate_dir / "duplicate.md").write_text(
        "---\n"
        "task_id: task-01\n"
        "phase: test\n"
        "status: READY\n"
        "owner: agent-01\n"
        "---\n\nDuplicate.\n",
        encoding="utf-8",
    )
    observed: list[str] = []
    callback = make_delivery_callback(evidence_provider=lambda _request, _session: observed.append("called") or changes())

    assert callback({"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}, "ses_exact") is False
    assert observed == []
    assert not coordination_common.delivery_files_for("task-01", report_dir)


def test_correction_run_submits_a_new_report_without_replacing_first_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    board, report_dir = install_board(monkeypatch, tmp_path)
    legacy_report = coordination_common.delivery_file_for("task-01")
    legacy_report.write_text("historical first-run evidence\n", encoding="utf-8")
    callback = make_delivery_callback(
        evidence_provider=lambda request, _session: changes(modified=[f"scripts/{request['run_id']}.py"])
    )
    first_request = {"task_id": "task-01", "run_id": "run-01", "agent_id": "agent-01"}
    second_request = {"task_id": "task-01", "run_id": "run-02", "agent_id": "agent-01"}

    assert callback(first_request, "ses_first") is True
    first_report = coordination_common.delivery_file_for("task-01", "run-01")
    first_content = first_report.read_text(encoding="utf-8")
    review_path = board / "review" / "2026-09-30_task-01.md"
    front_matter, body = coordination_common.load_task(review_path)
    in_progress = coordination_common.move_task(review_path, "in_progress", front_matter, body)

    assert callback(second_request, "ses_second") is True
    second_report = coordination_common.delivery_file_for("task-01", "run-02")
    assert first_report.read_text(encoding="utf-8") == first_content
    assert first_report != second_report and second_report.exists()
    assert legacy_report.read_text(encoding="utf-8") == "historical first-run evidence\n"
    assert len(coordination_common.delivery_files_for("task-01", report_dir)) == 3
    assert (board / "review" / in_progress.name).exists()
