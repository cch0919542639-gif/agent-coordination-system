"""Tests for scripts/profile_resolver.py — shared profile resolution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
PROFILES_DIR = ROOT / "profiles"

sys.path.insert(0, str(SCRIPTS_DIR))

from profile_resolver import (
    ProfileError,
    ProfileResult,
    load_profile,
    resolve_profile_path,
)


class TestResolveProfilePath:
    """Unit tests for resolve_profile_path."""

    def test_resolve_by_name(self) -> None:
        result = resolve_profile_path("rental-rebuild")
        assert result.name == "rental-rebuild-profile.md"
        assert result.exists()

    def test_resolve_by_explicit_path(self) -> None:
        profile_file = PROFILES_DIR / "rental-rebuild-profile.md"
        result = resolve_profile_path(str(profile_file))
        assert result == profile_file.resolve()

    def test_resolve_nonexistent_name_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_profile_path("nonexistent-profile-xyz")

    def test_resolve_nonexistent_path_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_profile_path("/tmp/does-not-exist-profile.md")


class TestLoadProfile:
    """Unit tests for load_profile (structured result)."""

    def test_load_by_name_returns_result(self) -> None:
        result = load_profile("rental-rebuild")
        assert isinstance(result, ProfileResult)
        assert result.data["profile_name"] == "rental-rebuild"
        assert result.path.exists()

    def test_load_by_path_returns_result(self) -> None:
        profile_file = PROFILES_DIR / "rental-rebuild-profile.md"
        result = load_profile(str(profile_file))
        assert isinstance(result, ProfileResult)
        assert result.data["profile_name"] == "rental-rebuild"

    def test_load_nonexistent_returns_error(self) -> None:
        result = load_profile("nonexistent-profile-xyz")
        assert isinstance(result, ProfileError)
        assert "not found" in result.message

    def test_load_malformed_front_matter_returns_error(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad-profile.md"
        bad_file.write_text("not valid front matter\n", encoding="utf-8")
        result = load_profile(str(bad_file))
        assert isinstance(result, ProfileError)
        assert "malformed" in result.message.lower() or "missing" in result.message.lower()

    def test_load_missing_front_matter_returns_error(self, tmp_path: Path) -> None:
        no_fm = tmp_path / "no-fm-profile.md"
        no_fm.write_text("# Just a heading\n\nNo front matter here.\n", encoding="utf-8")
        result = load_profile(str(no_fm))
        assert isinstance(result, ProfileError)

    def test_load_empty_yaml_returns_error(self, tmp_path: Path) -> None:
        empty_yaml = tmp_path / "empty-yaml-profile.md"
        empty_yaml.write_text("---\n---\n# Body\n", encoding="utf-8")
        result = load_profile(str(empty_yaml))
        # Empty YAML block (yaml.safe_load("") → None) is not a valid dict
        assert isinstance(result, ProfileError)


class TestNoProfileDispatchCompatibility:
    """Ensure dispatch_task.py still works when no --profile is supplied."""

    def test_dispatch_without_profile(self) -> None:
        """Run dispatch_task.py --message-only without --profile and confirm clean output."""
        # Find a task that's in in_progress/ or ready/ with --allow-terminal
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "dispatch_task.py"),
                "--task-id", "phase10-profile-enforcement-01",
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert "phase10-profile-enforcement-01" in result.stdout
        # No profile context block should appear
        assert "Profile context:" not in result.stdout

    def test_dispatch_with_valid_profile(self) -> None:
        """Run dispatch_task.py --message-only --profile rental-rebuild."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "dispatch_task.py"),
                "--task-id", "phase10-profile-enforcement-01",
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
                "--profile", "rental-rebuild",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert "Profile context: rental-rebuild" in result.stdout

    def test_dispatch_with_invalid_profile_fails(self) -> None:
        """Run dispatch_task.py --message-only --profile nonexistent."""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "dispatch_task.py"),
                "--task-id", "phase10-profile-enforcement-01",
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
                "--profile", "nonexistent-profile-xyz",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_dispatch_profile_not_used_as_selector(self) -> None:
        """active: true in a profile must NOT auto-select it."""
        # rental-rebuild has active: false; confirm it still requires explicit --profile
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "dispatch_task.py"),
                "--task-id", "phase10-profile-enforcement-01",
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        # No profile context even though a profile exists with active: false
        assert "Profile context:" not in result.stdout
