#!/usr/bin/env python3
"""Shared profile resolver for Phase 10 profile-aware task enforcement.

Provides a single contract for loading and resolving project profiles
by name or explicit file path.  Used by dispatch_task.py and available
to future validators.

Runtime contract (from profile-task-enforcement-runtime-plan.md):
  1. Profile is selected explicitly by name or path.  ``active`` is not a selector.
  2. Parsing a profile is NOT schema validation.
  3. No hidden global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
PROFILES_DIR = ROOT / "profiles"


@dataclass(frozen=True)
class ProfileResult:
    """Successful profile load."""

    data: dict
    path: Path


@dataclass(frozen=True)
class ProfileError:
    """Structured error when a profile cannot be loaded."""

    message: str
    path: Path | None = None


def resolve_profile_path(profile_ref: str) -> Path:
    """Return the filesystem path for *profile_ref*.

    *profile_ref* may be:
      - an explicit file path (absolute or relative)
      - a profile name looked up as ``profiles/<name>-profile.md``

    Raises ``FileNotFoundError`` when the resolved path does not exist.
    """
    candidate = Path(profile_ref)
    if candidate.is_file():
        return candidate.resolve()

    by_name = PROFILES_DIR / f"{profile_ref}-profile.md"
    if by_name.is_file():
        return by_name.resolve()

    raise FileNotFoundError(
        f"Profile `{profile_ref}` not found. "
        f"Searched: {by_name}"
    )


def _parse_front_matter(text: str) -> dict | None:
    """Parse YAML front matter from a markdown file's text.

    Returns the parsed dict or ``None`` when front matter is missing or invalid.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_profile(profile_ref: str) -> ProfileResult | ProfileError:
    """Load a profile by name or explicit path.

    Returns a ``ProfileResult`` on success or a ``ProfileError`` on failure.
    Never raises — callers get a structured error they can forward to
    incident reporting or CLI stderr.
    """
    try:
        resolved = resolve_profile_path(profile_ref)
    except FileNotFoundError as exc:
        return ProfileError(message=str(exc))

    text = resolved.read_text(encoding="utf-8")
    data = _parse_front_matter(text)
    if data is None:
        return ProfileError(
            message=f"Profile `{profile_ref}` at {resolved} has missing or malformed YAML front matter.",
            path=resolved,
        )

    return ProfileResult(data=data, path=resolved)
