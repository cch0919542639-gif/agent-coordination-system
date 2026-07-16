#!/usr/bin/env python3
"""Immutable run manifest for `orchestrate manifest`.

Writes an auditable record of an operator-approved execution wave.
Never mutates task cards, profiles, assignments, branches, or worktrees.
Duplicate manifest IDs are rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coordination_common import (  # noqa: E402
    ROOT,
    COORDINATION_DIR,
    TASK_BOARD_DIR,
    find_task,
    load_task,
)
from profile_resolver import ProfileError, load_profile  # noqa: E402
from wave_planner import plan_waves  # noqa: E402

MANIFESTS_DIR = COORDINATION_DIR / "manifests"


def _run_git(args: list[str]) -> str:
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=str(ROOT),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def _repo_identity() -> dict:
    """Gather immutable repo identity fields."""
    remote = _run_git(["remote", "get-url", "origin"])
    sha = _run_git(["rev-parse", "HEAD"])
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return {
        "remote": remote or "unknown",
        "sha": sha or "unknown",
        "branch": branch or "unknown",
    }


def _validate_tasks(task_ids: list[str], plan: dict) -> tuple[list[dict], list[str]]:
    """Validate that each task ID is in a runnable state (wave-0 ready).

    Returns (task_details, errors).
    """
    all_tasks = {}
    for state_dir in sorted(TASK_BOARD_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                fm, _ = load_task(path)
            except (ValueError, KeyError):
                continue
            tid = str(fm.get("task_id", "")).strip()
            if tid:
                fm["_file"] = str(path.relative_to(ROOT))
                fm["_state_dir"] = state_dir.name
                all_tasks[tid] = fm

    # Build set of runnable tasks from the plan
    runnable = set()
    for wave in plan.get("waves", []):
        runnable.update(wave)

    details = []
    errors = []
    for tid in task_ids:
        if tid not in all_tasks:
            errors.append(f"Task `{tid}` not found in the task board.")
            continue
        fm = all_tasks[tid]
        state = fm.get("_state_dir", "")
        if tid not in runnable:
            errors.append(
                f"Task `{tid}` is not runnable (state={state}). "
                f"Only tasks in the wave proposal are eligible."
            )
            continue
        detail = {
            "task_id": tid,
            "status": fm.get("status", ""),
            "owner": fm.get("owner", ""),
            "reviewer": fm.get("reviewer", ""),
            "phase": fm.get("phase", ""),
            "file": fm.get("_file", ""),
            "state_dir": state,
        }
        deps = fm.get("dependencies", [])
        if isinstance(deps, list):
            detail["dependencies"] = deps
        details.append(detail)

    return details, errors


def _validate_profile(profile_ref: str | None) -> tuple[dict | None, str | None]:
    """Validate an explicit profile reference. Returns (profile_info, error)."""
    if not profile_ref:
        return None, None
    result = load_profile(profile_ref)
    if isinstance(result, ProfileError):
        return None, f"Profile `{profile_ref}`: {result.message}"
    return {
        "profile_name": result.data.get("profile_name", profile_ref),
        "path": str(result.path.relative_to(ROOT)),
    }, None


def _generate_manifest_id(task_ids: list[str], owner: str, sha: str) -> str:
    """Generate a deterministic manifest ID from key inputs."""
    content = f"{sorted(task_ids)}:{owner}:{sha}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _find_existing_manifests() -> set[str]:
    """Return set of manifest IDs already written."""
    ids: set[str] = set()
    if not MANIFESTS_DIR.is_dir():
        return ids
    for path in MANIFESTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mid = data.get("manifest_id", "")
            if mid:
                ids.add(mid)
        except (json.JSONDecodeError, OSError):
            continue
    return ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write an immutable run manifest for an operator-approved execution wave.",
        epilog="Exit status: 0 on success, 1 on validation failure.",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        required=True,
        help="Task IDs to include in this manifest wave.",
    )
    parser.add_argument(
        "--owner",
        required=True,
        help="Explicit owner assignment for dispatched tasks.",
    )
    parser.add_argument(
        "--reviewer",
        default="ORCHESTRATOR",
        help="Explicit reviewer assignment (default: ORCHESTRATOR).",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Explicit profile name or path (optional).",
    )
    parser.add_argument(
        "--manifest-id",
        default=None,
        help="Explicit manifest ID (optional; auto-generated if omitted).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output manifest as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 1. Gather repo identity
    repo = _repo_identity()

    # 2. Run wave planner to get current plan
    plan = plan_waves()

    # 3. Validate task selection
    task_details, task_errors = _validate_tasks(args.tasks, plan)
    if task_errors:
        for err in task_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # 4. Validate profile
    profile_info, profile_err = _validate_profile(args.profile)
    if profile_err:
        print(f"ERROR: {profile_err}", file=sys.stderr)
        return 1

    # 5. Generate or validate manifest ID
    manifest_id = args.manifest_id or _generate_manifest_id(args.tasks, args.owner, repo["sha"])

    # 6. Check for duplicates
    existing = _find_existing_manifests()
    if manifest_id in existing:
        print(
            f"ERROR: Manifest ID `{manifest_id}` already exists. "
            f"Duplicate manifests are rejected. Choose a different --manifest-id.",
            file=sys.stderr,
        )
        return 1

    # 7. Build manifest
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "manifest_id": manifest_id,
        "created_at": now,
        "repo": repo,
        "wave": {
            "tasks": args.tasks,
            "waves": plan["waves"],
            "blocked": plan["blocked"],
            "errors": plan["errors"],
        },
        "tasks": task_details,
        "owner": args.owner,
        "reviewer": args.reviewer,
        "profile": profile_info,
        "command_context": {
            "command": "orchestrate manifest",
            "args": {
                "tasks": args.tasks,
                "owner": args.owner,
                "reviewer": args.reviewer,
                "profile": args.profile,
            },
        },
    }

    # 8. Write manifest
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{ts}_{manifest_id}.json"
    manifest_path = MANIFESTS_DIR / filename
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 9. Output
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        border = "=" * 60
        print(border)
        print("  Immutable Run Manifest Created")
        print(border)
        print(f"  Manifest ID:  {manifest_id}")
        print(f"  Created at:   {now}")
        print(f"  File:         coordination/manifests/{filename}")
        print(f"  Repo SHA:     {repo['sha'][:12]}")
        print(f"  Branch:       {repo['branch']}")
        print(f"  Owner:        {args.owner}")
        print(f"  Reviewer:     {args.reviewer}")
        if profile_info:
            print(f"  Profile:      {profile_info['profile_name']}")
        print(f"  Tasks:        {', '.join(args.tasks)}")
        print(f"  Waves:        {len(plan['waves'])} wave(s)")
        print(border)
        print("  Manifest is immutable. This file records the operator-approved")
        print("  execution wave. It does not dispatch or claim any task.")
        print(border)

    return 0


if __name__ == "__main__":
    sys.exit(main())
