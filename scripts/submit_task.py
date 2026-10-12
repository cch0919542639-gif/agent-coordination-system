#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys

from coordination_common import ROOT, delivery_file_for, find_task, move_task, progress_file_for, utc_now_string, write_text


def prepare_worker_report(args, card, header):
    """Generate factual, canonical evidence for an acknowledged local worker."""
    from local_agent_loop import allowed_file, handoff, relative_path

    if not args.payload_id or not args.artifact or args.skip_delivery_check:
        raise ValueError("Report generation requires an acknowledged payload and artifact; delivery checks cannot be skipped.")
    handoff(args.task_id, args.agent, args.payload_id)
    report = delivery_file_for(args.task_id)
    review_card = card.parent.parent / "review" / card.name
    progress = progress_file_for(args.agent)
    for target in (report, review_card, progress):
        name = target.relative_to(ROOT).as_posix()
        resolved = relative_path(name)
        if not allowed_file(name, header) or not allowed_file(resolved.relative_to(ROOT.resolve()).as_posix(), header):
            raise ValueError("Reporting or submission path is outside the assigned scope.")
    evidence = []
    for name in args.artifact:
        artifact = relative_path(name)
        if not allowed_file(name, header) or not allowed_file(artifact.relative_to(ROOT.resolve()).as_posix(), header) or not artifact.is_file():
            raise ValueError("Artifact is missing or outside the assigned scope.")
        with artifact.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        evidence.append(f"- {name}; SHA256 {checksum}")
    template = (ROOT / "coordination/templates/delivery-report.md").read_text(encoding="utf-8")
    parts = template.split("\n## ")
    names = [part.partition("\n")[0] for part in parts[1:]]
    sections = {
        "Changed Files": "\n".join(f"- {p}" for p in [*args.artifact, report.relative_to(ROOT).as_posix(), review_card.relative_to(ROOT).as_posix(), progress.relative_to(ROOT).as_posix()]),
        "Artifact Paths": "\n".join(evidence),
        "Validation Steps Performed": "Artifact existence, allowed scope and SHA256 checked. Repository validation pending.",
        "Known Residual Risks": "Independent artifact acceptance is pending; provider failures remain recorded in the controller journal.",
        "Recommended Handoff": f"Reviewer {header.get('reviewer')} independently checks the declared artifact contract before accepting.",
        "Acceptance Criteria Coverage": args.summary + "\n\n" + "\n".join(f"- {criterion}: reviewer verifies against the summary and artifact evidence." for criterion in header.get("acceptance", [])),
    }
    if set(names) != set(sections):
        raise ValueError("Delivery template sections changed; report generation stopped.")
    prefix = parts[0].replace("TASK-ID-HERE", args.task_id).replace("AGENT-NAME", args.agent).replace("PHASE-ID-HERE", str(header.get("phase")))
    prefix += f"\n- Payload ID: {args.payload_id}\n"
    def render():
        return prefix.rstrip() + "\n\n" + "\n\n".join(f"## {name}\n\n{sections[name]}" for name in names) + "\n"
    write_text(report, render())
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_coordination_files.py")], cwd=ROOT, timeout=30)
    if result.returncode:
        sections["Validation Steps Performed"] = f"Artifact existence, allowed scope and SHA256 checked. Repository validation failed (exit{result.returncode}); no submission performed."
        write_text(report, render())
        raise ValueError("Repository validation failed; no submission performed.")
    sections["Validation Steps Performed"] = "Artifact existence, allowed scope and SHA256 checked. Repository coordination validation passed before submission."
    write_text(report, render())


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit an in-progress task for review.")
    parser.add_argument("--task-id", required=True, help="Task ID to submit.")
    parser.add_argument("--agent", required=True, help="Submitting agent/owner.")
    parser.add_argument("--summary", help="Generate a canonical worker report from this factual execution summary.")
    parser.add_argument("--artifact", action="append", default=[], help="Existing scoped artifact for generated report; repeatable.")
    parser.add_argument("--payload-id", help="Acknowledged local worker payload required for generated reports.")
    parser.add_argument(
        "--skip-delivery-check",
        action="store_true",
        help="Allow submit even if expected delivery_report is missing.",
    )
    args = parser.parse_args()
    if (args.artifact or args.payload_id) and args.summary is None:
        parser.error("Generated report arguments require --summary.")

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name not in ("in_progress", "blocked"):
        print(
            f"Task `{args.task_id}` is not in in_progress/ or blocked/; current state is `{path.parent.name}`.",
            file=sys.stderr,
        )
        return 1

    current_owner = str(front_matter.get("owner", "")).strip()
    if current_owner and current_owner != args.agent:
        print(f"Task `{args.task_id}` is owned by `{current_owner}`, not `{args.agent}`.", file=sys.stderr)
        return 1

    if args.summary is not None:
        if path.parent.name != "in_progress":
            print("Generated reports require an IN_PROGRESS task.", file=sys.stderr)
            return 1
        try:
            prepare_worker_report(args, path, front_matter)
        except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    expected_artifacts = front_matter.get("expected_artifacts", [])
    if isinstance(expected_artifacts, list) and "delivery_report" in expected_artifacts and not args.skip_delivery_check:
        delivery_path = delivery_file_for(args.task_id)
        if not delivery_path.exists():
            print(
                f"Missing required delivery report: {delivery_path}. Use --skip-delivery-check to bypass.",
                file=sys.stderr,
            )
            return 1

    destination = move_task(path, "review", front_matter, body)

    progress_path = progress_file_for(args.agent)
    if progress_path.exists():
        progress_content = (
            "# Progress Report\n\n"
            f"- Agent: {args.agent}\n"
            f"- Active Task: {args.task_id}\n"
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

    print(f"Submitted task `{args.task_id}` for review.")
    print(f"Moved: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
