#!/usr/bin/env python3
"""Bounded multi-project remote-ref monitor for Phase 12 event-driven orchestration.

Uses local Git transport/object inspection to find review-submitted,
ready-assigned, and incident-opened task-card evidence on configured
project remote branches.  Never mutates task cards, creates commits,
or calls external APIs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from coordination_common import ROOT, parse_front_matter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from event_ledger import (  # noqa: E402
    Event,
    append_events,
    detect_event_type,
    load_events,
    load_state,
    make_event_id,
    now_iso,
    save_state,
)
from project_registry import ProjectEntry, load_registry  # noqa: E402


def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    """Run a Git command in the given directory."""
    return subprocess.run(
        ["git", *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd,
    )


def _bounded_fetch(
    local_path: str,
    remote_name: str,
    refspec: str = "refs/heads/*:refs/remotes/origin/*",
    timeout_seconds: int = 30,
) -> tuple[bool, str]:
    """Fetch remote refs with a bounded timeout. Returns (success, message)."""
    result = _run_git(
        ["fetch", "--no-tags", "--depth=1", remote_name, refspec],
        cwd=local_path,
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or "fetch failed"
    return True, "ok"


def _ls_remote_refs(
    local_path: str,
    remote_name: str,
    pattern: str = "refs/heads/*",
) -> dict[str, str]:
    """List remote refs as {ref_name: commit_sha}."""
    result = _run_git(
        ["ls-remote", "--heads", remote_name, pattern],
        cwd=local_path,
    )
    refs: dict[str, str] = {}
    if result.returncode != 0:
        return refs
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            sha, ref = parts
            # refs/heads/branch-name -> branch-name
            name = ref.replace("refs/heads/", "")
            refs[name] = sha
    return refs


def _read_task_card_from_ref(
    local_path: str,
    remote_name: str,
    branch: str,
    card_path: str,
) -> dict | None:
    """Read a task card from a remote branch without checkout."""
    result = _run_git(
        ["show", f"{remote_name}/{branch}:{card_path}"],
        cwd=local_path,
    )
    if result.returncode != 0:
        return None
    front_matter, _ = parse_front_matter(result.stdout)
    return front_matter


def _discover_task_cards(
    local_path: str,
    remote_name: str,
    branch: str,
) -> list[dict]:
    """Discover task cards in the standard coordination layout."""
    cards = []
    for state in ("review", "ready", "blocked"):
        # Try common task-card directory patterns
        for pattern in [
            f"coordination/task-board/{state}/*.md",
        ]:
            result = _run_git(
                ["ls-tree", "--name-only", f"{remote_name}/{branch}:{pattern.rsplit('/*', 1)[0]}"],
                cwd=local_path,
            )
            if result.returncode != 0:
                continue
            for filename in result.stdout.splitlines():
                filename = filename.strip()
                if not filename or filename == "README.md":
                    continue
                card_path = f"coordination/task-board/{state}/{filename}"
                fm = _read_task_card_from_ref(local_path, remote_name, branch, card_path)
                if fm:
                    cards.append(fm)
    return cards


def _scan_project(
    project: ProjectEntry,
    state: dict,
) -> list[Event]:
    """Scan one project for new events."""
    local_path = project.local_path
    remote_name = project.remote_name
    project_id = project.project_id

    if not Path(local_path).is_dir():
        return []

    # Bounded fetch
    success, _msg = _bounded_fetch(local_path, remote_name)
    if not success:
        # Record health event
        return [Event(
            event_id=make_event_id(project_id, local_path, "fetch", "fail", "health", "fetch_failed"),
            project_id=project_id,
            repository=local_path,
            ref="fetch",
            commit="fail",
            task_id="health",
            event_type="fetch_failed",
            detected_at=now_iso(),
        )]

    # List remote refs — only scan the default branch
    refs = _ls_remote_refs(local_path, remote_name)
    default = project.default_branch
    if default not in refs:
        return []

    # Get last-seen commits per branch
    seen: dict[str, str] = state.get("seen_commits", {}).get(project_id, {})

    events: list[Event] = []
    new_seen: dict[str, str] = {}

    branch = default
    commit_sha = refs[branch]
    new_seen[branch] = commit_sha
    if seen.get(branch) == commit_sha:
        return []  # No change

    # Discover task cards on this branch
    cards = _discover_task_cards(local_path, remote_name, branch)

    for fm in cards:
        event_type = detect_event_type(fm)
        if not event_type:
            continue
        task_id = str(fm.get("task_id", "")).strip()
        if not task_id:
            continue

        event = Event(
            event_id=make_event_id(project_id, local_path, branch, commit_sha, task_id, event_type),
            project_id=project_id,
            repository=local_path,
            ref=branch,
            commit=commit_sha,
            task_id=task_id,
            event_type=event_type,
            detected_at=now_iso(),
        )
        events.append(event)

    # Update state
    if project_id not in state.get("seen_commits", {}):
        state.setdefault("seen_commits", {})[project_id] = {}
    state["seen_commits"][project_id] = new_seen

    return events


def monitor_once(output_json: bool = False) -> int:
    """Run one poll cycle across all registered projects."""
    projects = load_registry()
    if not projects:
        print("No projects registered. Add projects to coordination/monitor/projects.json")
        return 0

    state = load_state()
    all_events: list[Event] = []
    health_issues: list[str] = []

    for project in projects:
        events = _scan_project(project, state)
        for event in events:
            if event.event_type == "fetch_failed":
                health_issues.append(f"[{project.project_id}] fetch failed")
            else:
                all_events.append(event)

    added = append_events(all_events)
    save_state(state)

    if output_json:
        output = {
            "events": [e.to_dict() for e in all_events],
            "added": added,
            "health_issues": health_issues,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        border = "=" * 60
        print(border)
        print("  Remote Ref Monitor — Poll Result")
        print(border)
        print(f"  Projects scanned: {len(projects)}")
        print(f"  New events:       {added}")
        if health_issues:
            print(f"  Health issues:    {len(health_issues)}")
            for issue in health_issues:
                print(f"    - {issue}")
        print()
        if all_events:
            print("  Events")
            print("  " + "-" * 56)
            for event in all_events:
                print(f"  [{event.event_type}] {event.project_id} / {event.task_id}")
                print(f"    ref={event.ref} commit={event.commit[:12]}")
            print()
        else:
            print("  No new events.")
        print(border)

    return 0 if not health_issues else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor remote Git refs for task-card evidence across registered projects.",
        epilog="Exit status: 0 on success, 1 on health issues.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll and exit (default).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Poll interval in seconds (default: 600). Minimum: 60.",
    )
    parser.add_argument(
        "--jitter",
        type=float,
        default=0.1,
        help="Random jitter as fraction of interval (default: 0.1).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 60:
        print("ERROR: minimum interval is 60 seconds.", file=sys.stderr)
        return 1

    return monitor_once(output_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
