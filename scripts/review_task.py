#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from coordination_common import find_task, list_tasks, move_task, next_review_file_for, progress_file_for, save_task, utc_now_string, write_text
from dispatch_task import assign_ready_task
from wave_planner import plan_waves


VALID_DECISIONS = {"accepted", "needs_fix", "reassign", "paused"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a lead-agent review decision and apply the controller triage gate.")
    parser.add_argument("--task-id", required=True, help="Task ID under review.")
    parser.add_argument("--reviewer", required=True, help="Reviewer/orchestrator name.")
    parser.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS), help="Review decision.")
    parser.add_argument("--summary", required=True, help="One-sentence review summary.")
    parser.add_argument("--finding", action="append", default=[], help="Finding line; may be repeated.")
    parser.add_argument("--scope", default="PASS", help="Scope compliance summary.")
    parser.add_argument("--validation", default="Validator reviewed and submission inspected.", help="Validation summary.")
    parser.add_argument("--required-change", action="append", default=[], help="Required change line; may be repeated.")
    parser.add_argument("--artifact", action="append", default=[], help="Accepted artifact path; may be repeated.")
    parser.add_argument(
        "--controller-triage",
        action="store_true",
        help="Apply the lead-agent risk gate and automatically continue after a clear acceptance.",
    )
    parser.add_argument(
        "--human-decision",
        choices=["not-needed", "required"],
        help="Lead-agent triage result; required with --controller-triage.",
    )
    parser.add_argument(
        "--risk",
        choices=["none", "identified"],
        help="Lead-agent triage result; required with --controller-triage.",
    )
    parser.add_argument(
        "--reassign-owner",
        help="New owner selected by the lead agent for a safe controller-triage reassignment.",
    )
    args = parser.parse_args()

    if not args.controller_triage:
        print("Lifecycle-changing review decisions require --controller-triage.", file=sys.stderr)
        return 1
    if args.reviewer != "ORCHESTRATOR":
        print("--controller-triage requires --reviewer ORCHESTRATOR.", file=sys.stderr)
        return 1
    if args.human_decision is None or args.risk is None:
        print("--controller-triage requires --human-decision and --risk.", file=sys.stderr)
        return 1
    needs_pause = args.human_decision == "required" or args.risk == "identified"
    if needs_pause and args.decision != "paused":
        print("Controller triage cannot continue while a human decision is required or risk is identified; use --decision paused.", file=sys.stderr)
        return 1
    if args.decision == "paused" and not needs_pause:
        print("--decision paused requires a human decision or identified risk.", file=sys.stderr)
        return 1
    if args.decision not in {"accepted", "needs_fix", "reassign", "paused"}:
        print("--controller-triage supports accepted, needs_fix, reassign, or paused decisions.", file=sys.stderr)
        return 1
    if args.decision == "reassign":
        if not args.reassign_owner or args.reassign_owner == "UNASSIGNED" or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", args.reassign_owner) is None:
            print("Controller-triage reassign requires a valid --reassign-owner.", file=sys.stderr)
            return 1
    elif args.reassign_owner:
        print("--reassign-owner requires --decision reassign.", file=sys.stderr)
        return 1

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name != "review":
        print(f"Task `{args.task_id}` is not in review/; current state is `{path.parent.name}`.", file=sys.stderr)
        return 1

    owner = str(front_matter.get("owner", "")).strip()
    previous_owner = owner
    if args.controller_triage and args.decision == "accepted" and (
        owner in {"", "UNASSIGNED"}
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", owner) is None
    ):
        print("Controller acceptance requires a concrete task owner; pause for an owner decision before continuing.", file=sys.stderr)
        return 1
    if args.controller_triage and args.decision == "needs_fix" and (
        owner in {"", "UNASSIGNED"}
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", owner) is None
    ):
        print("Automatic correction dispatch requires a valid existing task owner; pause for an owner decision.", file=sys.stderr)
        return 1

    timestamp = utc_now_string()
    review_path = next_review_file_for(args.task_id)
    findings = args.finding or ["No additional findings."]
    required_changes = args.required_change or (
        ["None."] if args.decision == "accepted"
        else ["Await human decision or risk resolution."] if args.decision == "paused"
        else ["Continue from the review findings under the selected owner."] if args.decision == "reassign"
        else ["Specify required follow-up work."]
    )
    accepted_artifacts = args.artifact or [str(path.relative_to(path.parents[1]))]
    artifact_heading = "Accepted Artifacts" if args.decision == "accepted" else "Reviewed Artifacts"

    review_content = (
        "# Review Report\n\n"
        f"- Review ID: {review_path.stem}\n"
        f"- Reviewer: {args.reviewer}\n"
        f"- Task ID: {args.task_id}\n"
        f"- Phase: {front_matter.get('phase')}\n"
        f"- Decision: {args.decision}\n"
        f"- Reviewed At: {timestamp}\n\n"
        "## Summary\n\n"
        f"{args.summary}\n\n"
        "## Findings\n\n"
        + "\n".join(f"- {item}" for item in findings)
        + "\n\n## Scope Compliance\n\n"
        + f"{args.scope}\n\n"
        + "## Validation Check\n\n"
        + f"{args.validation}\n\n"
        + "## Controller Triage\n\n"
        + (
            f"- Human decision: {args.human_decision}\n- Risk: {args.risk}\n"
            + (f"- Reassigned owner: {args.reassign_owner}\n" if args.decision == "reassign" else "")
            + "\n"
            if args.controller_triage
            else "- Not recorded by this review command.\n\n"
        )
        + "## Required Changes\n\n"
        + "\n".join(f"- {item}" for item in required_changes)
        + f"\n\n## {artifact_heading}\n\n"
        + "\n".join(f"- {item}" for item in accepted_artifacts)
        + "\n"
    )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    with review_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(review_content)

    destination_state = "done" if args.decision == "accepted" else "review"
    if args.decision == "accepted":
        destination = move_task(path, destination_state, front_matter, body)
    elif args.decision == "paused":
        front_matter["status"] = "REVIEW"
        save_task(path, front_matter, body)
        destination = path
    elif args.controller_triage and args.decision in {"needs_fix", "reassign"}:
        if args.decision == "reassign":
            owner = args.reassign_owner
            front_matter["owner"] = owner
        body = _append_correction_feedback(body, args.summary, findings, required_changes, review_path)
        destination = move_task(path, "ready", front_matter, body)
    else:
        front_matter["status"] = args.decision.upper()
        save_task(path, front_matter, body)
        destination = path

    if owner:
        progress_path = progress_file_for(owner)
        if progress_path.exists():
            next_status = (
                "DONE" if args.decision == "accepted"
                else "READY" if args.controller_triage and args.decision in {"needs_fix", "reassign"} and destination.parent.name == "ready"
                else "WAITING_FOR_HUMAN" if args.decision == "paused"
                else args.decision.upper()
            )
            progress_content = (
                "# Progress Report\n\n"
                f"- Agent: {owner}\n"
                f"- Active Task: {args.task_id}\n"
                f"- Phase: {front_matter.get('phase')}\n"
                f"- Status: {next_status}\n"
                f"- Last Updated: {timestamp}\n\n"
                "## Current Step\n\n"
                + (
                    "Review accepted. Task completed." if args.decision == "accepted"
                    else "Controller added correction feedback and returned the task to ready/." if args.controller_triage and args.decision == "needs_fix" and destination.parent.name == "ready"
                    else "Controller reassigned the task and returned it to ready/." if args.controller_triage and args.decision == "reassign" and destination.parent.name == "ready"
                    else "Controller paused delivery for a human decision." if args.decision == "paused"
                    else f"Review returned `{args.decision}`. Await next action."
                )
                + "\n\n## Changes So Far\n\n"
                + f"- {destination.relative_to(destination.parents[1])}\n"
                + f"\n- {review_path.relative_to(review_path.parents[1])}\n\n"
                + "## Blocker Status\n\n"
                + ("none" if args.decision == "accepted" else args.summary)
                + "\n\n## Next Step\n\n"
                + ("No further action required." if args.decision == "accepted" else "Continue the assigned task from the controller feedback." if args.controller_triage and args.decision == "needs_fix" and destination.parent.name == "ready" else "Continue the reassigned task from the controller feedback." if args.controller_triage and args.decision == "reassign" and destination.parent.name == "ready" else "Human decision required." if args.decision == "paused" else "Follow reviewer feedback or await reassignment.")
                + "\n"
            )
            write_text(progress_path, progress_content)

    if args.controller_triage and args.decision == "reassign" and previous_owner and previous_owner != owner:
        previous_progress = progress_file_for(previous_owner)
        if previous_progress.exists():
            write_text(
                previous_progress,
                "# Progress Report\n\n"
                f"- Agent: {previous_owner}\n"
                f"- Active Task: {args.task_id}\n"
                f"- Phase: {front_matter.get('phase')}\n"
                "- Status: REASSIGNED\n"
                f"- Last Updated: {timestamp}\n\n"
                "## Current Step\n\n"
                f"Controller reassigned the task to `{owner}`.\n\n"
                "## Changes So Far\n\n"
                f"- {destination.relative_to(destination.parents[1])}\n"
                f"\n- {review_path.relative_to(review_path.parents[1])}\n\n"
                "## Blocker Status\n\n"
                "none\n\n"
                "## Next Step\n\n"
                "The new owner continues from the controller review.\n"
            )

    print(f"Recorded review for `{args.task_id}` with decision `{args.decision}`.")
    print(f"Review report: {review_path}")
    print(f"Task file: {destination}")
    if args.controller_triage and args.decision == "paused":
        reasons = []
        if args.human_decision == "required":
            reasons.append("human decision needed")
        if args.risk == "identified":
            reasons.append("risk identified")
        print(f"ESCALATION REQUIRED ({'; '.join(reasons)}): delivery remains in review/; no continuation was dispatched.")
    elif args.controller_triage and args.decision == "accepted":
        if owner:
            _continue_one_ready_task(args.task_id, owner)
        else:
            print("Continuation paused: accepted task has no owner to carry the dispatch forward.")
    elif args.controller_triage and args.decision in {"needs_fix", "reassign"}:
        result = assign_ready_task(args.task_id, owner)
        if isinstance(result, str):
            print(f"Controller redispatch deferred: {result}.")
        else:
            fix_path, message = result
            action = "Returned for in-scope corrections" if args.decision == "needs_fix" else "Reassigned"
            print(f"{action}: task `{args.task_id}` is assigned to `{owner}`.")
            print(f"Task file: {fix_path}")
            print("--- Correction Dispatch Message ---")
            print(message, end="")
    return 0


def _continue_one_ready_task(accepted_task_id: str, owner: str) -> None:
    ready_tasks = {str(front_matter.get("task_id", "")): (path, front_matter) for path, front_matter in list_tasks(("ready",))}
    eligible_ids = set(plan_waves()["ready"])
    for task_id in sorted(eligible_ids):
        selected = ready_tasks.get(task_id)
        if selected is None:
            continue
        _, front_matter = selected
        dependencies = front_matter.get("dependencies")
        if not isinstance(dependencies, list) or accepted_task_id not in dependencies:
            continue
        current_owner = str(front_matter.get("owner", "")).strip()
        if current_owner not in ("", "UNASSIGNED", owner):
            continue
        result = assign_ready_task(task_id, owner)
        if isinstance(result, str):
            print(f"Continuation paused: {result}.")
            return
        path, message = result
        print(f"Continued with dependency-ready task `{task_id}` for `{owner}`.")
        print(f"Task file: {path}")
        print("--- Next Dispatch Message ---")
        print(message, end="")
        return

    print(f"Continuation paused: no dependency-ready task is available for `{owner}`.")


def _append_correction_feedback(
    body: str, summary: str, findings: list[str], required_changes: list[str], review_path: Path
) -> str:
    clean = lambda value: " ".join(value.split())
    previous_feedback = "\n## Latest Controller Review Feedback\n"
    if previous_feedback in body:
        body = body.split(previous_feedback, 1)[0]
    lines = [
        "## Latest Controller Review Feedback",
        "",
        f"Review report: `{review_path.relative_to(review_path.parents[2]).as_posix()}`",
        f"Summary: {clean(summary)}",
        "",
        "Findings:",
        *[f"- {clean(item)}" for item in findings],
        "",
        "Required changes:",
        *[f"- {clean(item)}" for item in required_changes],
    ]
    return body.rstrip() + "\n\n" + "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
