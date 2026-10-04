"""Create and submit a controller-observed report for a completed task run."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Callable

from coordination_common import delivery_file_for, utc_now_string
from submit_task import load_task_for_submission, submit_task


SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
SESSION_ID = re.compile(r"ses[A-Za-z0-9_.:-]{0,253}\Z")
CHANGE_KINDS = ("added", "modified", "deleted")
EvidenceProvider = Callable[[Mapping[str, object], str], object]


def make_delivery_callback(*, evidence_provider: EvidenceProvider) -> Callable[[Mapping[str, object], str], bool]:
    """Build a completion callback; success means the task entered review."""
    if not callable(evidence_provider):
        raise ValueError("controller evidence provider is required")

    def submit_completed(request: Mapping[str, object], session_id: str) -> bool:
        if not isinstance(request, Mapping):
            return False
        task_id, run_id, agent_id = (request.get(key) for key in ("task_id", "run_id", "agent_id"))
        if not all(isinstance(value, str) and SAFE_ID.fullmatch(value) for value in (task_id, run_id, agent_id)) or not isinstance(session_id, str) or SESSION_ID.fullmatch(session_id) is None:
            return False
        try:
            path, card, _ = load_task_for_submission(task_id, agent_id)
            if path.parent.name != "in_progress" or card.get("owner") != agent_id:
                return False
            if delivery_file_for(task_id, run_id).exists():
                return False
            changes = _validated_changes(evidence_provider(request, session_id))
            if changes is None:
                return False
            report = render_delivery_report(changes, task_id=task_id, run_id=run_id, agent_id=agent_id, session_id=session_id)
            submit_task(
                task_id,
                agent_id,
                expected_state="in_progress",
                require_exact_owner=True,
                delivery_report=report,
                delivery_run_id=run_id,
            )
            return True
        except Exception:
            # Do not surface provider errors, local paths, or file contents.
            return False

    return submit_completed


def render_delivery_report(changes: Mapping[str, list[str]], *, task_id: str, run_id: str, agent_id: str, session_id: str) -> str:
    lines = [
        f"# Automated Delivery Report - {task_id}",
        "",
        f"- Agent: `{agent_id}`",
        f"- Run: `{run_id}`",
        f"- OpenCode session: `{session_id}`",
        f"- Submitted: {utc_now_string()}",
        "- Report source: controller-observed worktree snapshots and exact supervised-session completion",
        "",
        "## Controller-observed changed paths",
        "",
        "Paths are classified by an in-memory comparison of files matching the assigned task's allowed scope. File contents and digests are not stored.",
        "",
    ]
    for kind in CHANGE_KINDS:
        lines.extend((f"### {kind.title()}", ""))
        paths = changes[kind]
        lines.extend([f"- `{path}`" for path in paths] or ["- None observed"])
        lines.append("")
    lines.extend(
        (
            "## Validation results",
            "",
            "The controller did not capture validation command output. The reviewer must independently verify the task's required checks.",
            "",
            "## Risk assessment",
            "",
            "The controller did not capture a risk assessment. The reviewer must inspect the actual task diff and task-specific risks.",
            "",
            "## Review requirement",
            "",
            "Inspect the actual task diff, acceptance criteria, and validation evidence before deciding whether to accept.",
            "",
        )
    )
    return "\n".join(lines)


def _validated_changes(value: object) -> dict[str, list[str]] | None:
    if not isinstance(value, Mapping) or set(value) != set(CHANGE_KINDS):
        return None
    result: dict[str, list[str]] = {}
    seen: set[str] = set()
    for kind in CHANGE_KINDS:
        paths = value[kind]
        if not isinstance(paths, list) or len(paths) > 5000:
            return None
        normalized: list[str] = []
        for path in paths:
            if not isinstance(path, str) or not _safe_repo_path(path) or path in seen:
                return None
            seen.add(path)
            normalized.append(path)
        result[kind] = sorted(normalized)
    return result


def _safe_repo_path(value: str) -> bool:
    if len(value) > 240 or "\\" in value or ":" in value or value.startswith("/") or re.fullmatch(r"[A-Za-z0-9_./@+-]+", value) is None:
        return False
    path = PurePosixPath(value)
    return bool(path.parts) and all(part not in {".", ".."} for part in path.parts) and str(path) == value
