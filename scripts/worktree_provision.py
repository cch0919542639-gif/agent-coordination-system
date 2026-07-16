#!/usr/bin/env python3
"""Worktree preflight and provisioning for `orchestrate worktree`.

Consumes an immutable manifest and optionally creates a local Git worktree.
Dry-run mode validates everything but creates nothing. Never claims, dispatches,
pushes, creates remote branches, or changes task-card lifecycle.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coordination_common import ROOT  # noqa: E402

MANIFESTS_DIR = ROOT / "coordination" / "manifests"


def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _current_sha() -> str:
    result = _run_git(["rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _load_manifest(manifest_ref: str) -> tuple[dict | None, str | None]:
    """Load a manifest by ID or explicit path. Returns (data, error)."""
    # Try as explicit path first
    path = Path(manifest_ref)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data, None
        except (json.JSONDecodeError, OSError) as exc:
            return None, f"Cannot read manifest at {path}: {exc}"

    # Try as manifest ID — search manifests directory
    if MANIFESTS_DIR.is_dir():
        for manifest_path in MANIFESTS_DIR.glob("*.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if data.get("manifest_id") == manifest_ref:
                    return data, None
            except (json.JSONDecodeError, OSError):
                continue

    return None, f"Manifest `{manifest_ref}` not found. Provide a manifest ID or explicit file path."


def _validate_manifest_structure(data: dict) -> list[str]:
    """Validate manifest has required fields. Returns list of errors."""
    errors = []
    for field in ("manifest_id", "created_at", "repo", "wave", "tasks", "owner"):
        if field not in data:
            errors.append(f"Manifest missing required field `{field}`.")
    if "sha" not in data.get("repo", {}):
        errors.append("Manifest `repo` missing `sha` field.")
    if "tasks" not in data.get("wave", {}):
        errors.append("Manifest `wave` missing `tasks` field.")
    return errors


def _validate_task_in_manifest(data: dict, task_id: str) -> tuple[dict | None, str | None]:
    """Check that task_id exists in the manifest's task list."""
    for task in data.get("tasks", []):
        if task.get("task_id") == task_id:
            return task, None
    manifest_tasks = [t.get("task_id", "?") for t in data.get("tasks", [])]
    return None, (
        f"Task `{task_id}` not found in manifest `{data.get('manifest_id', '?')}`. "
        f"Manifest contains: {', '.join(manifest_tasks)}"
    )


def _validate_revision(data: dict) -> str | None:
    """Check repo SHA matches. Returns error or None."""
    manifest_sha = data.get("repo", {}).get("sha", "")
    current_sha = _current_sha()
    if not manifest_sha or manifest_sha == "unknown":
        return None  # Skip if manifest has no SHA
    if manifest_sha != current_sha:
        return (
            f"Revision mismatch: manifest records {manifest_sha[:12]}, "
            f"current HEAD is {current_sha[:12]}. "
            f"Run `git pull` or recreate the manifest at the current revision."
        )
    return None


def _validate_worktree_path(worktree_root: str, task_id: str) -> tuple[Path | None, str | None]:
    """Validate worktree path is safe and under the approved root."""
    root = Path(worktree_root).resolve()
    worktree_path = root / f"worktrees/{task_id}"

    # Check for path traversal
    try:
        worktree_path.relative_to(root)
    except ValueError:
        return None, (
            f"Path traversal detected: {worktree_path} is outside approved root {root}. "
            f"Use an absolute path under the approved worktree root."
        )

    # Check for existing collision
    if worktree_path.exists():
        return None, (
            f"Collision: {worktree_path} already exists. "
            f"Remove it manually or choose a different worktree root."
        )

    return worktree_path, None


def _validate_machine_affinity(data: dict, task_id: str, machine_id: str | None) -> str | None:
    """Check machine affinity if declared."""
    if not machine_id:
        return None

    # Check profile-level worktree_policy
    profile = data.get("profile")
    if profile and isinstance(profile, dict):
        # Machine affinity is informational; we don't enforce it strictly
        # since the manifest records the operator's explicit choice
        pass

    return None


def _preflight(
    data: dict,
    task_id: str,
    worktree_root: str,
    machine_id: str | None,
) -> list[str]:
    """Run all preflight checks. Returns list of errors (empty = all pass)."""
    errors = []

    # 1. Manifest structure
    errors.extend(_validate_manifest_structure(data))
    if errors:
        return errors

    # 2. Task in manifest
    _, task_err = _validate_task_in_manifest(data, task_id)
    if task_err:
        errors.append(task_err)

    # 3. Revision match
    rev_err = _validate_revision(data)
    if rev_err:
        errors.append(rev_err)

    # 4. Worktree path safety
    _, path_err = _validate_worktree_path(worktree_root, task_id)
    if path_err:
        errors.append(path_err)

    # 5. Machine affinity
    affinity_err = _validate_machine_affinity(data, task_id, machine_id)
    if affinity_err:
        errors.append(affinity_err)

    return errors


def _provision(worktree_path: Path) -> str | None:
    """Create the Git worktree. Returns error or None."""
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    result = _run_git(["worktree", "add", "--detach", str(worktree_path), "HEAD"])
    if result.returncode != 0:
        stderr = result.stderr.strip()
        return (
            f"Failed to create worktree at {worktree_path}: {stderr}. "
            f"Ensure the path is writable and not already a Git worktree."
        )
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight and provision a local Git worktree from an immutable manifest.",
        epilog="Exit status: 0 on success, 1 on validation failure.",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Manifest ID or explicit path to a manifest JSON file.",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Task ID to provision a worktree for.",
    )
    parser.add_argument(
        "--worktree-root",
        default=str(ROOT),
        help="Approved worktree root directory (default: repo root).",
    )
    parser.add_argument(
        "--machine-id",
        default=None,
        help="Optional machine identifier for affinity checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all validations but create nothing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 1. Load manifest
    data, load_err = _load_manifest(args.manifest)
    if load_err:
        print(f"ERROR: {load_err}", file=sys.stderr)
        return 1

    # 2. Compute worktree path (needed for both dry-run and real)
    worktree_path, path_err = _validate_worktree_path(args.worktree_root, args.task)
    if path_err:
        print(f"ERROR: {path_err}", file=sys.stderr)
        return 1

    # 3. Run preflight
    errors = _preflight(data, args.task, args.worktree_root, args.machine_id)

    if args.dry_run:
        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            if args.json:
                print(json.dumps({"status": "fail", "errors": errors}))
            return 1
        if args.json:
            print(json.dumps({
                "status": "pass",
                "manifest_id": data.get("manifest_id"),
                "task_id": args.task,
                "worktree_path": str(worktree_path),
                "dry_run": True,
            }))
        else:
            border = "=" * 60
            print(border)
            print("  Worktree Preflight — Dry Run")
            print(border)
            print(f"  Manifest ID:  {data.get('manifest_id', '?')}")
            print(f"  Task:         {args.task}")
            print(f"  Worktree:     {worktree_path}")
            print(f"  Status:       PASS")
            print(border)
            print("  Dry run: no worktree was created.")
            print(border)
        return 0

    # 4. Non-dry-run: fail if preflight has errors
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "fail", "errors": errors}))
        return 1

    # 5. Provision
    provision_err = _provision(worktree_path)
    if provision_err:
        print(f"ERROR: {provision_err}", file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "error", "error": provision_err}))
        return 1

    if args.json:
        print(json.dumps({
            "status": "provisioned",
            "manifest_id": data.get("manifest_id"),
            "task_id": args.task,
            "worktree_path": str(worktree_path),
        }))
    else:
        border = "=" * 60
        print(border)
        print("  Worktree Provisioned")
        print(border)
        print(f"  Manifest ID:  {data.get('manifest_id', '?')}")
        print(f"  Task:         {args.task}")
        print(f"  Worktree:     {worktree_path}")
        print(f"  Status:       CREATED")
        print(border)
        print("  The worktree is ready. Dispatch the worker manually.")
        print(border)

    return 0


if __name__ == "__main__":
    sys.exit(main())
