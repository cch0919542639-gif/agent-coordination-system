#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import find_task, move_task, progress_file_for, review_file_for, save_task, utc_now_string, write_text


VALID_DECISIONS = {"accepted", "needs_fix", "reassign", "rejected"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a review report and apply a review decision to a task.")
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
        "--move-to",
        choices=["done", "review"],
        help="Optional explicit destination. Defaults: accepted->done, others->review.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name != "review":
        print(f"Task `{args.task_id}` is not in review/; current state is `{path.parent.name}`.", file=sys.stderr)
        return 1

    timestamp = utc_now_string()
    review_path = review_file_for(args.task_id)
    findings = args.finding or ["No additional findings."]
    required_changes = args.required_change or (["None."] if args.decision == "accepted" else ["Specify required follow-up work."])
    accepted_artifacts = args.artifact or [str(path.relative_to(path.parents[1]))]

    review_content = (
        "# Review Report\n\n"
        f"- Review ID: review-{args.task_id}\n"
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
        + "## Required Changes\n\n"
        + "\n".join(f"- {item}" for item in required_changes)
        + "\n\n## Accepted Artifacts\n\n"
        + "\n".join(f"- {item}" for item in accepted_artifacts)
        + "\n"
    )
    write_text(review_path, review_content)

    destination_state = args.move_to or ("done" if args.decision == "accepted" else "review")
    if args.decision == "accepted":
        destination = move_task(path, destination_state, front_matter, body)
    else:
        front_matter["status"] = args.decision.upper()
        save_task(path, front_matter, body)
        destination = path

    owner = str(front_matter.get("owner", "")).strip()
    if owner:
        progress_path = progress_file_for(owner)
        if progress_path.exists():
            next_status = "DONE" if args.decision == "accepted" else args.decision.upper()
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
                    else f"Review returned `{args.decision}`. Await next action."
                )
                + "\n\n## Changes So Far\n\n"
                + f"- {destination.relative_to(destination.parents[1])}\n"
                + f"\n- {review_path.relative_to(review_path.parents[1])}\n\n"
                + "## Blocker Status\n\n"
                + ("none" if args.decision == "accepted" else args.summary)
                + "\n\n## Next Step\n\n"
                + ("No further action required." if args.decision == "accepted" else "Follow reviewer feedback or await reassignment.")
                + "\n"
            )
            write_text(progress_path, progress_content)

    print(f"Recorded review for `{args.task_id}` with decision `{args.decision}`.")
    print(f"Review report: {review_path}")
    print(f"Task file: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
