#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
COMPLETED_DIR = ROOT / "coordination" / "completed"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a draft phase-intake markdown file from CLI input.",
    )
    parser.add_argument("--phase-id", required=True, help="Short kebab-case phase identifier (e.g. phase7-example)")
    parser.add_argument("--objective", required=True, help="One or two sentences describing the phase objective")
    parser.add_argument("--in-scope", action="append", default=[], help="In-scope path or description (repeatable)")
    parser.add_argument("--out-of-scope", action="append", default=[], help="Out-of-scope path or description (repeatable)")
    parser.add_argument("--dependency", action="append", default=[], help="Dependency description (repeatable)")
    parser.add_argument("--entry-criteria", action="append", default=[], help="Entry criterion (repeatable)")
    parser.add_argument("--exit-criteria", action="append", default=[], help="Exit criterion (repeatable)")
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help=(
            "Task packet specification as JSON string. "
            'Example: --task \'{"id":"phase7-01","objective":"Do X","priority":"high",'
            '"deps":[],"allowed_scope":["src/**"],"forbidden_scope":["db/**"],'
            '"acceptance":["Works"]}\''
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: coordination/completed/{phase_id}-intake-draft.md)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the generated content instead of writing to file")
    return parser


def render_draft(args: argparse.Namespace) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = []
    lines.append(f"# Phase Intake: {args.phase_id}")
    lines.append("")
    lines.append("> Auto-generated draft. Review and edit before finalizing.")
    lines.append(f"> Generated at: {now}")
    lines.append("")

    # Phase ID
    lines.append("## Phase ID")
    lines.append("")
    lines.append(args.phase_id)
    lines.append("")

    # Objective
    lines.append("## Objective")
    lines.append("")
    lines.append(args.objective)
    lines.append("")

    # Entry Criteria
    lines.append("## Entry Criteria")
    lines.append("")
    if args.entry_criteria:
        for c in args.entry_criteria:
            lines.append(f"- {c}")
    else:
        lines.append("- *(list entry criteria)*")
    lines.append("")

    # Exit Criteria
    lines.append("## Exit Criteria")
    lines.append("")
    if args.exit_criteria:
        for c in args.exit_criteria:
            lines.append(f"- {c}")
    else:
        lines.append("- *(list exit criteria)*")
    lines.append("")

    # Scope
    lines.append("## Scope")
    lines.append("")
    lines.append("### In Scope")
    lines.append("")
    if args.in_scope:
        for s in args.in_scope:
            lines.append(f"- {s}")
    else:
        lines.append("- *(list in-scope items)*")
    lines.append("")
    lines.append("### Out Of Scope")
    lines.append("")
    if args.out_of_scope:
        for s in args.out_of_scope:
            lines.append(f"- {s}")
    else:
        lines.append("- *(list out-of-scope items)*")
    lines.append("")

    # Dependencies
    lines.append("## Dependencies")
    lines.append("")
    if args.dependency:
        for d in args.dependency:
            lines.append(f"- {d}")
    else:
        lines.append("- *(list dependencies)*")
    lines.append("")

    # Artifact Expectations
    lines.append("## Artifact Expectations")
    lines.append("")
    lines.append("- delivery_report (required)")
    lines.append("- code_changes (if applicable)")
    lines.append("- docs (if applicable)")
    lines.append("")

    # Task Packet Decomposition
    lines.append("## Task Packet Decomposition")
    lines.append("")
    if args.task:
        for i, raw in enumerate(args.task, start=1):
            task = json.loads(raw)
            task_id = task.get("id", f"TASK-ID-{i}")
            lines.append(f"### Task {i}: {task_id}")
            lines.append("")
            lines.append(f'- **Objective**: {task.get("objective", "Short description")}')
            lines.append(f'- **Priority**: {task.get("priority", "medium")}')
            deps = task.get("deps", [])
            deps_str = ", ".join(deps) if deps else "none"
            lines.append(f"- **Dependencies**: {deps_str}")
            allowed = task.get("allowed_scope", [])
            lines.append(f"- **Allowed Scope**: {', '.join(allowed) if allowed else 'not defined'}")
            forbidden = task.get("forbidden_scope", [])
            lines.append(f"- **Forbidden Scope**: {', '.join(forbidden) if forbidden else 'not defined'}")
            acceptance = task.get("acceptance", [])
            if acceptance:
                for a in acceptance:
                    lines.append(f"- **Acceptance Criteria**: {a}")
            else:
                lines.append("- **Acceptance Criteria**: *(define criteria)*")
            lines.append("")
    else:
        lines.append("*(add --task arguments to define the decomposition)*")
        lines.append("")

    # Review and Acceptance
    lines.append("## Review and Acceptance")
    lines.append("")
    lines.append("- Run `python scripts/orchestrate.py validate`")
    lines.append("- Review each task delivery report")
    lines.append("- Accept tasks individually before phase closure")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    content = render_draft(args)

    if args.dry_run:
        print(content)
        return 0

    output_path: Path
    if args.output:
        output_path = Path(args.output)
    else:
        COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = COMPLETED_DIR / f"{args.phase_id}-intake-draft.md"

    output_path.write_text(content, encoding="utf-8")
    print(f"Intake draft written to {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
