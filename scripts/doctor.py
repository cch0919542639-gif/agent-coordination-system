#!/usr/bin/env python3
"""Read-only preflight diagnostic for `orchestrate doctor`.

Performs deterministic checks on the working directory, Git runtime, Python
runtime, required coordination directories, and optional task/profile
references.  Never mutates task cards, profiles, branches, or worktrees.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coordination_common import find_task  # noqa: E402
from profile_resolver import ProfileError, load_profile  # noqa: E402


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

REQUIRED_ROOT_DIRS = ("coordination", "scripts", "docs", "profiles")
REQUIRED_TASK_BOARD_DIRS = ("ready", "in_progress", "review", "blocked", "done")
COORDINATION_DIR = ROOT / "coordination"


def _check(description: str, status: str, detail: str = "") -> dict:
    return {"description": description, "status": status, "detail": detail}


def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _check_root(cwd: Path) -> list[dict]:
    missing = [d for d in REQUIRED_ROOT_DIRS if not (cwd / d).is_dir()]
    if missing:
        return [_check(
            "repository-root",
            "FAIL",
            f"Not a repository root. Missing directories in {cwd}: {', '.join(missing)}. "
            f"Change to the repository root and try again.",
        )]
    return [_check("repository-root", "PASS", f"All required directories found in {cwd}")]


def _check_git(cwd: str | None = None) -> list[dict]:
    results = []
    git_avail = _run_git(["--version"], cwd=cwd)
    if git_avail.returncode != 0:
        return [_check(
            "git-available",
            "FAIL",
            "Git is not installed or not on PATH. Install Git and try again.",
        )]
    results.append(_check("git-available", "PASS", git_avail.stdout.strip()))

    rev_parse = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if rev_parse.returncode != 0:
        results.append(_check(
            "git-repository",
            "FAIL",
            "Current directory is not a Git repository. Run `git init` or clone a repository.",
        ))
        return results
    results.append(_check("git-repository", "PASS", f"Repository root: {rev_parse.stdout.strip()}"))

    remote = _run_git(["remote", "get-url", "origin"], cwd=cwd)
    if remote.returncode != 0:
        results.append(_check(
            "git-remote",
            "FAIL",
            "Remote 'origin' is not configured. Run `git remote add origin <url>`.",
        ))
    else:
        results.append(_check("git-remote", "PASS", f"Remote origin: {remote.stdout.strip()}"))

    return results


def _check_python() -> list[dict]:
    return [_check(
        "python-runtime",
        "PASS",
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
        f"({sys.executable})",
    )]


def _check_coordination_dirs() -> list[dict]:
    if not COORDINATION_DIR.is_dir():
        return [_check("coordination-dirs", "FAIL", "coordination/ directory is missing.")]
    results: list[dict] = []
    all_ok = True
    for sub in REQUIRED_TASK_BOARD_DIRS:
        target = COORDINATION_DIR / "task-board" / sub
        if not target.is_dir():
            all_ok = False
            results.append(_check(
                "coordination-dirs",
                "FAIL",
                f"coordination/task-board/{sub}/ is missing. Create: mkdir -p coordination/task-board/{sub}",
            ))
    for sub in ("progress", "incidents", "reviews", "delivery", "templates"):
        target = COORDINATION_DIR / sub
        if not target.is_dir() and sub != "incidents":
            results.append(_check(
                "coordination-dirs",
                "WARN",
                f"coordination/{sub}/ is missing (optional but recommended). "
                f"Create: mkdir -p coordination/{sub}",
            ))
    if all_ok:
        results.insert(0, _check("coordination-dirs", "PASS", "All required coordination directories exist."))
    return results


def _discover_task_dir() -> Path | None:
    for sub in ("ready", "in_progress", "review", "blocked", "done"):
        candidate = COORDINATION_DIR / "task-board" / sub
        if candidate.is_dir():
            return candidate
    return None


def _check_task(task_id: str) -> list[dict]:
    try:
        path, front_matter, _ = find_task(task_id)
        return [_check(
            "task-reference",
            "PASS",
            f"Task `{task_id}` found at {path} (status={front_matter.get('status', '?')})",
        )]
    except FileNotFoundError:
        task_dir = _discover_task_dir() or COORDINATION_DIR / "task-board"
        return [_check(
            "task-reference",
            "FAIL",
            f"Task `{task_id}` not found in any task-board subdirectory. "
            f"Searched: {task_dir.parent}. Verify the task ID and ensure the card exists.",
        )]


def _check_profile(profile_ref: str) -> list[dict]:
    result = load_profile(profile_ref)
    if isinstance(result, ProfileError):
        return [_check(
            "profile-reference",
            "FAIL",
            f"{result.message}. Verify the profile name or path and ensure the file exists.",
        )]
    return [_check(
        "profile-reference",
        "PASS",
        f"Profile `{profile_ref}` loaded from {result.path}",
    )]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run read-only preflight diagnostics for the orchestration environment.",
        epilog="Exit status: 0 if all checks pass, 1 if any check fails.",
    )
    parser.add_argument(
        "--task-id",
        help="Optional: verify that a specific task ID exists in the task board.",
    )
    parser.add_argument(
        "--profile",
        help="Optional: verify that a named profile or profile path is resolvable.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    cwd = Path.cwd().resolve()
    checks: list[dict] = []

    checks.extend(_check_root(cwd))
    checks.extend(_check_git(cwd=str(cwd)))
    checks.extend(_check_python())
    checks.extend(_check_coordination_dirs())

    if args.task_id:
        checks.extend(_check_task(args.task_id))

    if args.profile:
        checks.extend(_check_profile(args.profile))

    overall = "PASS"
    for check in checks:
        if check["status"] == "FAIL":
            overall = "FAIL"

    border = "=" * 60
    print(border)
    print("  Orchestrate Doctor - Preflight Diagnostic Report")
    print(border)
    for check in checks:
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}.get(check["status"], "[INFO]")
        print(f"\n  {icon}  {check['description']}")
        if check["detail"]:
            print(f"       {check['detail']}")
    print()
    print(border)
    print(f"  Overall result: {overall}")
    print(border)

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
