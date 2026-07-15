#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coordination_common import find_task, save_task
from profile_resolver import load_profile, ProfileError
from validate_coordination_files import validate_profile_file, ValidationError

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
PROTOCOL_DOC = "docs/operations/agent-task-execution-protocol.md"
EXECUTION_DOC = "docs/operations/lead-agent-orchestration-protocol.md"
ASSIGNMENT_DOC = "docs/operations/worker-assignment-policy.md"


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def build_profile_context_block(profile_data: dict) -> list[str]:
    """Build the profile context section for the dispatch message.

    Shows what the profile declares and explicitly separates
    script-supported behavior from manual/operator follow-up.
    """
    profile_name = profile_data.get("profile_name", "unknown")
    description = profile_data.get("description", "")
    lines = [
        "",
        f"Profile context: {profile_name}",
    ]
    if description:
        lines.append(f"- description: {description}")

    task_format = profile_data.get("task_format", {})
    if isinstance(task_format, dict):
        default_status = task_format.get("default_status")
        default_mode = task_format.get("default_execution_mode")
        if default_status:
            lines.append(f"- default task status: {default_status}")
        if default_mode:
            lines.append(f"- default execution mode: {default_mode}")

    role_mapping = profile_data.get("role_mapping", {})
    if isinstance(role_mapping, dict):
        owner_naming = role_mapping.get("owner_naming")
        reviewer_naming = role_mapping.get("reviewer_naming")
        if owner_naming:
            lines.append(f"- owner naming convention: {owner_naming}")
        if reviewer_naming:
            lines.append(f"- reviewer naming convention: {reviewer_naming}")

    artifact_mapping = profile_data.get("artifact_mapping", {})
    if isinstance(artifact_mapping, dict):
        coord = artifact_mapping.get("coordination_structure", {})
        if isinstance(coord, dict):
            task_board = coord.get("task_board")
            if task_board:
                lines.append(f"- task board path: {task_board}")
                lines.append("  NOTE: path remapping is NOT script-supported yet. Task cards still live under coordination/task-board/ by default.")

    worktree = profile_data.get("worktree_policy", {})
    if isinstance(worktree, dict) and worktree.get("enabled"):
        lines.append("- worktree policy: enabled")
        prefix = worktree.get("default_path_prefix")
        if prefix:
            lines.append(f"  - default path prefix: {prefix}")
        if worktree.get("machine_affinity_required"):
            lines.append("  - machine affinity: required")

    lines.extend([
        "",
        "Supported by scripts:",
        "- profile name and description are shown in this dispatch message",
        "- default execution mode from the profile is informational only; pass --execution-mode explicitly if needed",
        "- owner/reviewer naming conventions are informational; assign actual agent names via --owner/--reviewer",
        "",
        "Manual follow-up required by operator:",
        "- task card placement (coordination/task-board/ paths are NOT remapped automatically)",
        "- artifact path overrides (progress, incidents, delivery, reviews, templates)",
        "- branch/PR naming conventions",
        "- any profile-specific front matter fields (sprint, epic, etc.)",
    ])
    return lines


def build_dispatch_message(
    task_id: str,
    task_file: Path,
    owner: str,
    reviewer: str | None,
    execution_mode: str | None,
    branch: str | None,
    worktree_path: str | None,
    machine_id: str | None,
    profile_data: dict | None = None,
) -> str:
    rel_task = task_file.relative_to(ROOT).as_posix()
    agent_name = owner
    lines = [
        f"You are assigned task {task_id}.",
        "",
        "Please pull the latest repo, then read:",
        f"- {rel_task}",
        f"- {PROTOCOL_DOC}",
        "",
        "When you start:",
        f"- move the task card to coordination/task-board/in_progress/",
        f"- update coordination/progress/{agent_name}.md",
        "",
        "If blocked:",
        "- create an incident in coordination/incidents/",
        "- do not continue by guessing outside the task scope",
        "",
        "When finished:",
        "- move the task card to coordination/task-board/review/",
        "- submit repo-based delivery evidence and validation notes",
    ]
    if execution_mode == "WORKTREE":
        lines.extend(
            [
                "",
                "Execution mode:",
                "- WORKTREE",
            ]
        )
        if branch:
            lines.append(f"- branch: {branch}")
        if worktree_path:
            lines.append(f"- worktree_path: {worktree_path}")
        if machine_id:
            lines.append(f"- machine_id: {machine_id}")
        lines.extend(
            [
                "- if the assigned worktree does not exist locally, stop and report it before implementation",
                "- do not switch to another branch or worktree unless reassigned",
            ]
        )
    elif execution_mode == "REPO_FIRST":
        lines.extend(
            [
                "",
                "Execution mode:",
                "- REPO_FIRST",
            ]
        )

    if profile_data:
        lines.extend(build_profile_context_block(profile_data))

    lines.extend(
        [
            "",
            "Protocol references:",
            f"- {PROTOCOL_DOC}",
            f"- {EXECUTION_DOC}",
            f"- {ASSIGNMENT_DOC}",
        ]
    )
    if reviewer:
        lines.append("")
        lines.append(f"Reviewer: {reviewer}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign or reassign a task owner, optionally update reviewer, and generate a dispatch message.",
    )
    parser.add_argument("--task-id", required=True, help="Task ID to dispatch.")
    parser.add_argument("--owner", required=True, help="Owner/agent to assign.")
    parser.add_argument("--reviewer", help="Optional reviewer override.")
    parser.add_argument(
        "--execution-mode",
        choices=["REPO_FIRST", "WORKTREE"],
        help="Optional execution mode override stored on the task card.",
    )
    parser.add_argument(
        "--branch",
        help="Optional branch provenance for worktree-aware dispatch.",
    )
    parser.add_argument(
        "--worktree-path",
        help="Optional worktree path provenance for worktree-aware dispatch.",
    )
    parser.add_argument(
        "--machine-id",
        help="Optional machine identifier for distributed runs.",
    )
    parser.add_argument(
        "--allow-terminal",
        action="store_true",
        help="Allow dispatching tasks already in terminal states such as done/.",
    )
    parser.add_argument(
        "--no-message",
        action="store_true",
        help="Suppress dispatch message output.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the dispatch message to FILE (use `-` for stdout-only, suppresses the decorated print block).",
    )
    parser.add_argument(
        "--message-only",
        action="store_true",
        help="Print the dispatch message without updating owner/reviewer.",
    )
    parser.add_argument(
        "--profile",
        metavar="NAME_OR_PATH",
        help="Profile name (e.g. rental-rebuild) or path to a profile file. Adds profile context to the dispatch message.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name in ("done", "cancelled") and not args.allow_terminal:
        print(
            f"Task `{args.task_id}` is in terminal state `{path.parent.name}`. Use --allow-terminal to override.",
            file=sys.stderr,
        )
        return 1

    branch = normalize_optional(args.branch)
    worktree_path = normalize_optional(args.worktree_path)
    machine_id = normalize_optional(args.machine_id)

    execution_mode = args.execution_mode
    if execution_mode is None:
        if branch or worktree_path:
            execution_mode = "WORKTREE"
        else:
            current_mode = str(front_matter.get("execution_mode", "")).strip()
            execution_mode = current_mode or None

    if execution_mode == "WORKTREE" and (not branch or not worktree_path):
        existing_branch = normalize_optional(str(front_matter.get("branch", "")))
        existing_worktree_path = normalize_optional(str(front_matter.get("worktree_path", "")))
        branch = branch or existing_branch
        worktree_path = worktree_path or existing_worktree_path

    if execution_mode == "WORKTREE" and (not branch or not worktree_path):
        print(
            "WORKTREE dispatch requires both --branch and --worktree-path, or equivalent values already present in task front matter.",
            file=sys.stderr,
        )
        return 1

    if execution_mode == "REPO_FIRST":
        branch = None
        worktree_path = None
        machine_id = machine_id or None

    # Load profile if specified
    profile_data = None
    if args.profile:
        result = load_profile(args.profile)
        if isinstance(result, ProfileError):
            print(result.message, file=sys.stderr)
            return 1
        # Schema preflight: reject structurally invalid profiles
        profile_errors = validate_profile_file(result.path)
        if profile_errors:
            for err in profile_errors:
                print(str(err), file=sys.stderr)
            return 1
        profile_data = result.data

    # Update owner/reviewer unless --message-only
    if not args.message_only:
        front_matter["owner"] = args.owner
        if args.reviewer:
            front_matter["reviewer"] = args.reviewer
        if execution_mode:
            front_matter["execution_mode"] = execution_mode
        if branch:
            front_matter["branch"] = branch
        else:
            front_matter.pop("branch", None)
        if worktree_path:
            front_matter["worktree_path"] = worktree_path
        else:
            front_matter.pop("worktree_path", None)
        if machine_id:
            front_matter["machine_id"] = machine_id
        else:
            front_matter.pop("machine_id", None)
        if profile_data:
            pname = str(profile_data.get("profile_name", "")).strip()
            if pname:
                front_matter["profile"] = pname
        save_task(path, front_matter, body)
        print(f"Dispatched task `{args.task_id}`.")
        print(f"  file: {path}")
        print(f"  owner: {args.owner}")
        if args.reviewer:
            print(f"  reviewer: {args.reviewer}")
        if execution_mode:
            print(f"  execution_mode: {execution_mode}")
        if branch:
            print(f"  branch: {branch}")
        if worktree_path:
            print(f"  worktree_path: {worktree_path}")
        if machine_id:
            print(f"  machine_id: {machine_id}")
        if profile_data:
            pname = str(profile_data.get("profile_name", "")).strip()
            print(f"  profile: {pname}")

    # Generate dispatch message
    reviewer = args.reviewer or str(front_matter.get("reviewer", "")).strip() or None
    message = build_dispatch_message(
        args.task_id,
        path,
        args.owner,
        reviewer,
        execution_mode,
        branch,
        worktree_path,
        machine_id,
        profile_data,
    )

    if args.output == "-":
        print(message, end="")
    elif not args.no_message:
        print()
        print("--- Dispatch Message ---")
        print(message)

    if args.output and args.output != "-":
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(message, encoding="utf-8", newline="\n")
        print(f"Dispatch message written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
