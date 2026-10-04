#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import TASK_BOARD_DIR, delivery_file_for, load_task, move_task, progress_file_for, utc_now_string, write_text


def load_task_for_submission(
    task_id: str,
    agent: str,
    *,
    expected_state: str | None = None,
    require_exact_owner: bool = False,
):
    """Load one unambiguous active task card after checking its owner and state."""
    if not isinstance(task_id, str) or not task_id.strip() or not isinstance(agent, str) or not agent.strip():
        raise ValueError("Task ID and submitting agent are required.")

    matches = []
    for state_dir in sorted(TASK_BOARD_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        for candidate in sorted(state_dir.glob("*.md")):
            if candidate.name == "README.md":
                continue
            front_matter, body = load_task(candidate)
            if str(front_matter.get("task_id", "")).strip() == task_id:
                matches.append((candidate, front_matter, body))
    if not matches:
        raise FileNotFoundError(f"task_id `{task_id}` not found in task board")
    if len(matches) != 1:
        raise ValueError(f"Task `{task_id}` has ambiguous task-card entries.")
    path, front_matter, body = matches[0]

    if expected_state is not None and expected_state not in ("in_progress", "blocked"):
        raise ValueError(f"Unsupported expected task state `{expected_state}`.")
    if path.parent.name not in ("in_progress", "blocked"):
        raise ValueError(
            f"Task `{task_id}` is not in in_progress/ or blocked/; current state is `{path.parent.name}`."
        )
    if expected_state is not None and path.parent.name != expected_state:
        raise ValueError(f"Task `{task_id}` is not in `{expected_state}/`; current state is `{path.parent.name}/`.")
    if str(front_matter.get("status", "")).strip() != path.parent.name.upper():
        raise ValueError(f"Task `{task_id}` status does not match its task-board state.")

    current_owner = str(front_matter.get("owner", "")).strip()
    if require_exact_owner and current_owner != agent:
        raise ValueError(f"Task `{task_id}` is not owned by `{agent}`.")
    if current_owner and current_owner != agent:
        raise ValueError(f"Task `{task_id}` is owned by `{current_owner}`, not `{agent}`.")
    return path, front_matter, body


def submit_task(
    task_id: str,
    agent: str,
    *,
    skip_delivery_check: bool = False,
    expected_state: str | None = None,
    require_exact_owner: bool = False,
    delivery_report: str | None = None,
    delivery_run_id: str | None = None,
):
    """Move one uniquely identified, owner-matching task into review."""
    path, front_matter, body = load_task_for_submission(
        task_id,
        agent,
        expected_state=expected_state,
        require_exact_owner=require_exact_owner,
    )

    expected_artifacts = front_matter.get("expected_artifacts", [])
    delivery_path = delivery_file_for(task_id, delivery_run_id)
    if isinstance(expected_artifacts, list) and "delivery_report" in expected_artifacts and not skip_delivery_check:
        if delivery_report is None and not delivery_path.exists():
            raise ValueError(f"Missing required delivery report: {delivery_path}. Use --skip-delivery-check to bypass.")

    if delivery_report is not None:
        if not isinstance(delivery_report, str) or not delivery_report.strip():
            raise ValueError("Delivery report must be non-empty text.")
        delivery_path.parent.mkdir(parents=True, exist_ok=True)
        with delivery_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(delivery_report)

    destination = move_task(path, "review", front_matter, body)

    progress_path = progress_file_for(agent)
    if progress_path.exists():
        progress_content = (
            "# Progress Report\n\n"
            f"- Agent: {agent}\n"
            f"- Active Task: {task_id}\n"
            f"- Phase: {front_matter.get('phase')}\n"
            "- Status: WAITING_FOR_REVIEW\n"
            f"- Last Updated: {utc_now_string()}\n\n"
            "## Current Step\n\n"
            "Implementation complete. Ready for review.\n\n"
            "## Changes So Far\n\n"
            f"- {destination.relative_to(destination.parents[1])}\n\n"
            "## Blocker Status\n\n"
            "none\n\n"
            "## Next Step\n\n"
            "Await orchestrator review.\n"
        )
        write_text(progress_path, progress_content)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit an in-progress task for review.")
    parser.add_argument("--task-id", required=True, help="Task ID to submit.")
    parser.add_argument("--agent", required=True, help="Submitting agent/owner.")
    parser.add_argument(
        "--skip-delivery-check",
        action="store_true",
        help="Allow submit even if expected delivery_report is missing.",
    )
    args = parser.parse_args()

    try:
        destination = submit_task(args.task_id, args.agent, skip_delivery_check=args.skip_delivery_check)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Submitted task `{args.task_id}` for review.")
    print(f"Moved: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
