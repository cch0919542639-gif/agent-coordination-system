"""Tests for profile-aware task validation in validate_coordination_files.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
TASK_BOARD_DIR = ROOT / "coordination" / "task-board"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_validator() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "validate_coordination_files.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )


def _write_task_card(
    tmp_path: Path,
    task_id: str,
    status: str = "READY",
    profile: str | None = None,
    execution_mode: str | None = None,
    extra_fm: str = "",
    extra_sections: str = "",
    in_state: str = "ready",
) -> Path:
    """Write a minimal valid task card for testing."""
    state_dir = TASK_BOARD_DIR / in_state
    state_dir.mkdir(parents=True, exist_ok=True)
    profile_line = f"\nprofile: {profile}" if profile else ""
    mode_line = f"\nexecution_mode: {execution_mode}" if execution_mode else ""
    fm = f"""---
task_id: {task_id}
phase: test-phase
status: {status}
owner: test-agent
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - scripts/**
forbidden_scope:
  - src/**
acceptance:
  - test acceptance
expected_artifacts:
  - code_changes{profile_line}{mode_line}{extra_fm}
---"""
    sections = f"""# Task Packet

## Objective

Test objective.

## Context

Test context.

## Constraints

Test constraints.

## Implementation Notes

Test notes.

## Validation Steps

Test validation.

## Escalation Rules

Test escalation.
{extra_sections}"""
    card = state_dir / f"2026-07-14_{task_id}_test.md"
    card.write_text(fm + "\n" + sections, encoding="utf-8")
    return card


class TestUnprofiledTaskCompatibility:
    """Unprofiled task cards must retain current validation behavior."""

    def test_unprofiled_task_passes(self, tmp_path: Path) -> None:
        card = _write_task_card(tmp_path, "test-unprofiled-01", in_state="ready")
        try:
            result = _run_validator()
            assert result.returncode == 0
            assert "test-unprofiled-01" not in result.stdout
        finally:
            card.unlink(missing_ok=True)

    def test_unprofiled_task_with_active_profile_not_auto_selected(self, tmp_path: Path) -> None:
        """A profile with active: true must NOT be auto-applied."""
        card = _write_task_card(tmp_path, "test-unprofiled-02", in_state="ready")
        try:
            result = _run_validator()
            assert result.returncode == 0
            assert "test-unprofiled-02" not in result.stdout
        finally:
            card.unlink(missing_ok=True)


class TestProfileResolutionErrors:
    """Profiled tasks with unresolvable profiles must fail."""

    def test_nonexistent_profile_fails(self, tmp_path: Path) -> None:
        card = _write_task_card(
            tmp_path, "test-bad-profile-01", profile="nonexistent-xyz", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "nonexistent-xyz" in result.stdout
            assert "not found" in result.stdout.lower() or "profile" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)

    def test_malformed_profile_fails(self, tmp_path: Path) -> None:
        from profile_resolver import PROFILES_DIR

        bad_profile = tmp_path / "badprofile-profile.md"
        bad_profile.write_text("not valid front matter\n", encoding="utf-8")
        # Temporarily symlink or copy into profiles dir
        target = PROFILES_DIR / "badprofile-profile.md"
        try:
            target.write_text("not valid front matter\n", encoding="utf-8")
            card = _write_task_card(
                tmp_path, "test-bad-profile-02", profile="badprofile", in_state="ready"
            )
            try:
                result = _run_validator()
                assert result.returncode != 0
                assert "badprofile" in result.stdout
            finally:
                card.unlink(missing_ok=True)
        finally:
            target.unlink(missing_ok=True)


class TestProfileStatusEnforcement:
    """Profile allowed_statuses must be enforced when present on the task."""

    def test_valid_status_passes(self, tmp_path: Path) -> None:
        card = _write_task_card(
            tmp_path, "test-profile-status-01", status="READY", profile="rental-rebuild", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode == 0
            assert "test-profile-status-01" not in result.stdout or "not in profile" not in result.stdout
        finally:
            card.unlink(missing_ok=True)

    def test_invalid_status_fails(self, tmp_path: Path) -> None:
        """Task status not in profile's allowed_statuses should fail."""
        # rental-rebuild allows all core statuses, so we need a profile that narrows.
        # Use a task with a fake status that no profile allows.
        # Actually, let's create a temporary profile with narrowed statuses.
        from profile_resolver import PROFILES_DIR

        narrow_profile = PROFILES_DIR / "narrowstatus-profile.md"
        narrow_profile.write_text(
            "---\n"
            "profile_name: narrowstatus\n"
            'schema_version: "1.0"\n'
            "description: Test profile with narrow statuses.\n"
            "task_format:\n"
            "  allowed_statuses:\n"
            "    - READY\n"
            "    - IN_PROGRESS\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            tmp_path, "test-profile-status-02", status="BLOCKED", profile="narrowstatus", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "BLOCKED" in result.stdout
            assert "not in profile" in result.stdout.lower() or "allowed_statuses" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            narrow_profile.unlink(missing_ok=True)


class TestProfileExecutionModeEnforcement:
    """Profile allowed_execution_modes must be enforced when present on the task."""

    def test_valid_mode_passes(self, tmp_path: Path) -> None:
        card = _write_task_card(
            tmp_path, "test-profile-mode-01", execution_mode="REPO_FIRST", profile="rental-rebuild", in_state="ready"
        )
        try:
            result = _run_validator()
            # rental-rebuild allows both REPO_FIRST and WORKTREE, so this should pass
            # (ignoring other unrelated errors)
            errors = [l for l in result.stdout.splitlines() if "test-profile-mode-01" in l]
            mode_errors = [e for e in errors if "not in profile" in e.lower() or "allowed_execution_modes" in e.lower()]
            assert len(mode_errors) == 0
        finally:
            card.unlink(missing_ok=True)

    def test_invalid_mode_fails(self, tmp_path: Path) -> None:
        from profile_resolver import PROFILES_DIR

        narrow_profile = PROFILES_DIR / "narrowmode-profile.md"
        narrow_profile.write_text(
            "---\n"
            "profile_name: narrowmode\n"
            'schema_version: "1.0"\n'
            "description: Test profile with narrow modes.\n"
            "task_format:\n"
            "  allowed_execution_modes:\n"
            "    - REPO_FIRST\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            tmp_path, "test-profile-mode-02", execution_mode="WORKTREE", profile="narrowmode", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "WORKTREE" in result.stdout
            assert "not in profile" in result.stdout.lower() or "allowed_execution_modes" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            narrow_profile.unlink(missing_ok=True)


class TestProfileAdditionalRequirements:
    """Profile-declared extra required fields and sections must be enforced."""

    def test_extra_required_front_matter_missing_fails(self, tmp_path: Path) -> None:
        from profile_resolver import PROFILES_DIR

        extra_fm_profile = PROFILES_DIR / "extrafm-profile.md"
        extra_fm_profile.write_text(
            "---\n"
            "profile_name: extrafm\n"
            'schema_version: "1.0"\n'
            "description: Test profile with extra required front matter.\n"
            "task_format:\n"
            "  required_front_matter:\n"
            "    - task_id\n"
            "    - phase\n"
            "    - status\n"
            "    - owner\n"
            "    - reviewer\n"
            "    - priority\n"
            "    - dependencies\n"
            "    - allowed_scope\n"
            "    - forbidden_scope\n"
            "    - acceptance\n"
            "    - expected_artifacts\n"
            "    - sprint\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            tmp_path, "test-extra-fm-01", profile="extrafm", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "sprint" in result.stdout
            assert "requires additional front matter" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            extra_fm_profile.unlink(missing_ok=True)

    def test_extra_required_front_matter_present_passes(self, tmp_path: Path) -> None:
        from profile_resolver import PROFILES_DIR

        extra_fm_profile = PROFILES_DIR / "extrafm2-profile.md"
        extra_fm_profile.write_text(
            "---\n"
            "profile_name: extrafm2\n"
            'schema_version: "1.0"\n'
            "description: Test profile with extra required front matter.\n"
            "task_format:\n"
            "  required_front_matter:\n"
            "    - task_id\n"
            "    - phase\n"
            "    - status\n"
            "    - owner\n"
            "    - reviewer\n"
            "    - priority\n"
            "    - dependencies\n"
            "    - allowed_scope\n"
            "    - forbidden_scope\n"
            "    - acceptance\n"
            "    - expected_artifacts\n"
            "    - sprint\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            tmp_path,
            "extrafm2",
            profile="extrafm2",
            extra_fm="\nsprint: 1",
            in_state="ready",
        )
        try:
            result = _run_validator()
            # Should not fail for the sprint field
            errors = [l for l in result.stdout.splitlines() if "extrafm2" in l]
            sprint_errors = [e for e in errors if "sprint" in e.lower()]
            assert len(sprint_errors) == 0
        finally:
            card.unlink(missing_ok=True)
            extra_fm_profile.unlink(missing_ok=True)

    def test_extra_required_section_missing_fails(self, tmp_path: Path) -> None:
        from profile_resolver import PROFILES_DIR

        extra_sec_profile = PROFILES_DIR / "extrasec-profile.md"
        extra_sec_profile.write_text(
            "---\n"
            "profile_name: extrasec\n"
            'schema_version: "1.0"\n'
            "description: Test profile with extra required sections.\n"
            "task_format:\n"
            "  required_sections:\n"
            '    - "## Objective"\n'
            '    - "## Context"\n'
            '    - "## Constraints"\n'
            '    - "## Implementation Notes"\n'
            '    - "## Validation Steps"\n'
            '    - "## Escalation Rules"\n'
            '    - "## Risk Assessment"\n'
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            tmp_path, "test-extra-sec-01", profile="extrasec", in_state="ready"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "Risk Assessment" in result.stdout
            assert "requires additional section" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            extra_sec_profile.unlink(missing_ok=True)


class TestProfileDoesNotAutoSelect:
    """active: true in a profile must NOT cause auto-selection."""

    def test_global_defaults_active_true_not_auto_applied(self, tmp_path: Path) -> None:
        """global-defaults has active: true but must not be auto-applied to unprofiled tasks."""
        card = _write_task_card(tmp_path, "test-no-auto-01", in_state="ready")
        try:
            result = _run_validator()
            assert result.returncode == 0
            # No profile-related errors for this unprofiled task
            profile_errors = [l for l in result.stdout.splitlines() if "test-no-auto-01" in l and "profile" in l.lower()]
            assert len(profile_errors) == 0
        finally:
            card.unlink(missing_ok=True)


class TestProfileScalarTypeValidation:
    """profile field must be a scalar, not a YAML list."""

    def test_profile_as_list_fails(self, tmp_path: Path) -> None:
        """A task card with profile as a YAML list should fail with a type error only."""
        state_dir = TASK_BOARD_DIR / "ready"
        state_dir.mkdir(parents=True, exist_ok=True)
        fm = """---
task_id: test-profile-list-01
phase: test-phase
status: READY
owner: test-agent
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - scripts/**
forbidden_scope:
  - src/**
acceptance:
  - test acceptance
expected_artifacts:
  - code_changes
profile:
  - rental-rebuild
---"""
        sections = """# Task Packet

## Objective

Test objective.

## Context

Test context.

## Constraints

Test constraints.

## Implementation Notes

Test notes.

## Validation Steps

Test validation.

## Escalation Rules

Test escalation."""
        card = state_dir / "2026-07-15_test-profile-list-01_test.md"
        card.write_text(fm + "\n" + sections, encoding="utf-8")
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "`profile` must be a scalar value, not a list" in result.stdout
            # Must NOT produce a misleading "not found" or list-to-string reference
            assert "not found" not in result.stdout.lower()
            assert "['rental-rebuild']" not in result.stdout
        finally:
            card.unlink(missing_ok=True)


class TestExistingValidatorStillPasses:
    """Full coordination validator must still pass after changes."""

    def test_validator_passes(self) -> None:
        result = _run_validator()
        assert result.returncode == 0
        assert "Coordination validation passed" in result.stdout
