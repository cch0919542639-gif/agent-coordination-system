"""Read-only, fail-closed Phase H worktree checks."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Callable, Mapping, Sequence


GitRun = Callable[[list[str]], subprocess.CompletedProcess[str]]


def verify_worktrees(bindings: object, worktree_root: Path, reviewed_commit: str, *, run: GitRun | None = None) -> dict[str, object]:
    """Verify six exact detached, clean, pinned worktrees with scoped Git trust."""
    if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)) or len(bindings) != 6 or not isinstance(reviewed_commit, str):
        return _deny(0)
    runner = run or _run
    root = worktree_root.resolve()
    passed = 0
    for binding in bindings:
        ref = binding.get("worktree_ref") if isinstance(binding, Mapping) else None
        target = _target(root, ref)
        if target is None or not _current(target, reviewed_commit, runner):
            return _deny(passed)
        passed += 1
    return {"decision": "worktrees_current", "binding_count": 6, "current_bindings": passed, "control_level": "best_effort"}


def _target(root: Path, ref: object) -> Path | None:
    if not isinstance(ref, str) or not ref or ref.startswith(("/", "\\")) or any(part in {"", ".", ".."} for part in ref.split("/")):
        return None
    target = (root / ref).resolve()
    return target if target.is_relative_to(root) else None


def _current(target: Path, reviewed_commit: str, run: GitRun) -> bool:
    if not target.is_dir():
        return False
    base = ["git", "-c", f"safe.directory={target}", "-C", str(target)]
    status = run([*base, "status", "--porcelain"])
    detached = run([*base, "symbolic-ref", "-q", "HEAD"])
    pinned = run([*base, "rev-parse", "HEAD"])
    return status.returncode == 0 and status.stdout == "" and detached.returncode != 0 and pinned.returncode == 0 and pinned.stdout.strip() == reviewed_commit


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _deny(passed: int) -> dict[str, object]:
    return {"decision": "deny_worktree_state", "binding_count": 6, "current_bindings": passed, "control_level": "best_effort"}
