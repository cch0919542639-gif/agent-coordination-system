#!/usr/bin/env python3
"""Multi-project registry for Phase 12 event-driven orchestration.

Each entry names one project, its local clone path, Git remote, default
branch, optional profile, and enabled event destinations.  The registry
is local-only because it may contain machine paths.
"""

from __future__ import annotations

import json
from pathlib import Path

from coordination_common import ROOT

MONITOR_DIR = ROOT / "coordination" / "monitor"
REGISTRY_FILE = MONITOR_DIR / "projects.json"


@__import__("dataclasses").dataclass
class ProjectEntry:
    """One registered project."""

    project_id: str
    local_path: str
    remote_name: str = "origin"
    default_branch: str = "main"
    monitor_branches: list[str] | None = None
    profile: str | None = None
    event_destinations: list[str] | None = None

    def __post_init__(self) -> None:
        self.monitor_branches = _validated_monitor_branches(self.monitor_branches)

    def to_dict(self) -> dict:
        d = {
            "project_id": self.project_id,
            "local_path": self.local_path,
            "remote_name": self.remote_name,
            "default_branch": self.default_branch,
        }
        if self.profile:
            d["profile"] = self.profile
        if self.monitor_branches:
            d["monitor_branches"] = self.monitor_branches
        if self.event_destinations:
            d["event_destinations"] = self.event_destinations
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ProjectEntry:
        return cls(
            project_id=data["project_id"],
            local_path=data["local_path"],
            remote_name=data.get("remote_name", "origin"),
            default_branch=data.get("default_branch", "main"),
            monitor_branches=data.get("monitor_branches"),
            profile=data.get("profile"),
            event_destinations=data.get("event_destinations"),
        )


def _validated_monitor_branches(value: object) -> list[str] | None:
    """Return a de-duplicated, safe explicit worker-branch allowlist.

    The registry is local configuration, but invalid branch syntax must never
    broaden monitoring to arbitrary remote refs.  Empty/missing values retain
    the historical default-branch-only behaviour.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("monitor_branches must be a list of branch names")

    branches: list[str] = []
    for branch in value:
        if not isinstance(branch, str) or not _is_safe_branch_name(branch):
            raise ValueError("monitor_branches contains an invalid branch name")
        if branch not in branches:
            branches.append(branch)
    return branches


def _is_safe_branch_name(branch: str) -> bool:
    """Validate a branch name without invoking Git or a shell."""
    if not branch or branch != branch.strip() or branch.startswith("refs/"):
        return False
    if branch.startswith("/") or branch.endswith("/") or "//" in branch:
        return False
    if any(char.isspace() or ord(char) < 32 for char in branch):
        return False
    if any(token in branch for token in ("..", "@{", "\\", "~", "^", ":", "?", "*", "[")):
        return False
    return all(part and not part.startswith(".") and not part.endswith(".") and not part.endswith(".lock")
               for part in branch.split("/"))


def load_registry() -> list[ProjectEntry]:
    """Load the project registry from disk."""
    if not REGISTRY_FILE.exists():
        return []
    try:
        data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [ProjectEntry.from_dict(entry) for entry in data if isinstance(entry, dict)]


def save_registry(entries: list[ProjectEntry]) -> None:
    """Save the project registry to disk."""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    data = [entry.to_dict() for entry in entries]
    REGISTRY_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_project(entry: ProjectEntry) -> None:
    """Add or update a project in the registry."""
    entries = load_registry()
    # Replace if same project_id exists
    entries = [e for e in entries if e.project_id != entry.project_id]
    entries.append(entry)
    save_registry(entries)


def remove_project(project_id: str) -> bool:
    """Remove a project from the registry. Returns True if found."""
    entries = load_registry()
    original = len(entries)
    entries = [e for e in entries if e.project_id != project_id]
    if len(entries) == original:
        return False
    save_registry(entries)
    return True


def get_project(project_id: str) -> ProjectEntry | None:
    """Get a single project by ID."""
    for entry in load_registry():
        if entry.project_id == project_id:
            return entry
    return None
