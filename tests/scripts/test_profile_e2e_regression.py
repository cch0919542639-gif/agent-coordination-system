"""End-to-end regression matrix for Phase 10 profile enforcement.

Quality gate task (phase10-profile-enforcement-04): verifies the combined
behavior of profile resolution, task-card validation, and dispatch recording
from an operator perspective.  Do NOT modify scripts/; this file only
exercises existing runtime through subprocess calls and the validator.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
TASK_BOARD_DIR = ROOT / "coordination" / "task-board"
PROFILES_DIR = ROOT / "profiles"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_validator() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "validate_coordination_files.py")],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )


def _run_dispatch(
    task_id: str,
    extra_args: list[str] | None = None,
    *,
    message_only: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "dispatch_task.py"),
        "--task-id", task_id,
        "--owner", "e2e-test-agent",
        "--allow-terminal",
    ]
    if message_only:
        cmd.append("--message-only")
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )


def _write_task_card(
    task_id: str,
    *,
    status: str = "READY",
    profile: str | None = None,
    execution_mode: str | None = None,
    extra_fm: str = "",
    state: str = "ready",
) -> Path:
    """Create a minimal valid task card for testing. Returns the path."""
    state_dir = TASK_BOARD_DIR / state
    state_dir.mkdir(parents=True, exist_ok=True)
    profile_line = f"\nprofile: {profile}" if profile else ""
    mode_line = f"\nexecution_mode: {execution_mode}" if execution_mode else ""
    fm = (
        f"---\n"
        f"task_id: {task_id}\n"
        f"phase: e2e-regression\n"
        f"status: {status}\n"
        f"owner: UNASSIGNED\n"
        f"reviewer: ORCHESTRATOR\n"
        f"priority: medium\n"
        f"dependencies: []\n"
        f"allowed_scope:\n"
        f"  - tests/**\n"
        f"forbidden_scope:\n"
        f"  - src/**\n"
        f"acceptance:\n"
        f"  - e2e regression test\n"
        f"expected_artifacts:\n"
        f"  - code_changes"
        f"{profile_line}{mode_line}{extra_fm}\n"
        f"---\n"
    )
    sections = (
        "# Task Packet\n\n"
        "## Objective\n\nE2E regression.\n\n"
        "## Context\n\nContext.\n\n"
        "## Constraints\n\nConstraints.\n\n"
        "## Implementation Notes\n\nNotes.\n\n"
        "## Validation Steps\n\nSteps.\n\n"
        "## Escalation Rules\n\nEscalation.\n"
    )
    card = state_dir / f"2026-07-16_{task_id}_e2e.md"
    card.write_text(fm + "\n" + sections, encoding="utf-8")
    return card


def _read_task_front_matter(card: Path) -> dict[str, object]:
    """Read the front matter dict from a task card using the shared parser."""
    from coordination_common import load_task
    fm, _ = load_task(card)
    return fm


IMMUTABLE_KEYS = (
    "owner", "reviewer", "execution_mode",
    "branch", "worktree_path", "machine_id", "profile",
)


def _assert_immutable(before: dict, after: dict) -> None:
    for key in IMMUTABLE_KEYS:
        assert after.get(key) == before.get(key), (
            f"field `{key}` changed from {before.get(key)!r} to {after.get(key)!r}"
        )


# ─── 1. Default-mode: no profile ──────────────────────────────────────


class TestDefaultModeNoProfile:
    """Default-mode tasks without a profile field must pass dispatch and validator."""

    def test_dispatch_works_without_profile(self) -> None:
        card = _write_task_card("e2e-default-01")
        try:
            result = _run_dispatch("e2e-default-01")
            assert result.returncode == 0
            assert "Dispatched task" in result.stdout
            assert "Profile context:" not in result.stdout
        finally:
            card.unlink(missing_ok=True)

    def test_validator_passes_without_profile(self) -> None:
        card = _write_task_card("e2e-default-02")
        try:
            result = _run_validator()
            assert result.returncode == 0
            assert "e2e-default-02" not in result.stdout
        finally:
            card.unlink(missing_ok=True)

    def test_dispatch_without_profile_does_not_add_profile(self) -> None:
        card = _write_task_card("e2e-default-03")
        try:
            _run_dispatch("e2e-default-03")
            fm = _read_task_front_matter(card)
            assert "profile" not in fm
        finally:
            card.unlink(missing_ok=True)


# ─── 2. Named profile: canonical name recording ────────────────────────


class TestNamedProfileRecording:
    """Mutating dispatch with --profile <name> stores canonical profile_name."""

    def test_named_profile_stored(self) -> None:
        card = _write_task_card("e2e-named-01")
        try:
            result = _run_dispatch("e2e-named-01", ["--profile", "rental-rebuild"])
            assert result.returncode == 0
            assert "profile: rental-rebuild" in result.stdout

            fm = _read_task_front_matter(card)
            assert fm["profile"] == "rental-rebuild"
        finally:
            card.unlink(missing_ok=True)

    def test_named_profile_validated_by_validator(self) -> None:
        card = _write_task_card("e2e-named-02", profile="rental-rebuild")
        try:
            result = _run_validator()
            # Should not produce a profile error for this card
            errors = [l for l in result.stdout.splitlines() if "e2e-named-02" in l]
            profile_errors = [e for e in errors if "profile" in e.lower()]
            assert len(profile_errors) == 0
        finally:
            card.unlink(missing_ok=True)


# ─── 3. Profile file path → canonical name ─────────────────────────────


class TestProfilePathRecording:
    """Dispatch with --profile <path> stores the canonical profile_name, not the path."""

    def test_profile_path_stores_canonical_name(self) -> None:
        card = _write_task_card("e2e-path-01")
        profile_file = str(PROFILES_DIR / "rental-rebuild-profile.md")
        try:
            result = _run_dispatch("e2e-path-01", ["--profile", profile_file])
            assert result.returncode == 0

            fm = _read_task_front_matter(card)
            assert fm["profile"] == "rental-rebuild"
            # Must not store the filesystem path
            assert "/" not in str(fm.get("profile", ""))
            assert "\\" not in str(fm.get("profile", ""))
        finally:
            card.unlink(missing_ok=True)


# ─── 4. Profile rule failure: validator enforces constraints ───────────


class TestProfileRuleEnforcement:
    """A persisted profile must constrain status, mode, and requirements."""

    def test_status_outside_profile_narrow_list_fails(self) -> None:
        """Task with BLOCKED status + profile that only allows READY/IN_PROGRESS."""
        narrow = PROFILES_DIR / "e2e-narrowstatus-profile.md"
        narrow.write_text(
            "---\n"
            "profile_name: e2e-narrowstatus\n"
            'schema_version: "1.0"\n'
            "description: E2E narrow-status test profile.\n"
            "task_format:\n"
            "  allowed_statuses:\n"
            "    - READY\n"
            "    - IN_PROGRESS\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            "e2e-rule-01", status="BLOCKED", profile="e2e-narrowstatus"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "BLOCKED" in result.stdout
            assert "not in profile" in result.stdout.lower() or "allowed_statuses" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            narrow.unlink(missing_ok=True)

    def test_mode_outside_profile_narrow_list_fails(self) -> None:
        """Task with WORKTREE + profile that only allows REPO_FIRST."""
        narrow = PROFILES_DIR / "e2e-narrowmode-profile.md"
        narrow.write_text(
            "---\n"
            "profile_name: e2e-narrowmode\n"
            'schema_version: "1.0"\n'
            "description: E2E narrow-mode test profile.\n"
            "task_format:\n"
            "  allowed_execution_modes:\n"
            "    - REPO_FIRST\n"
            "---\n",
            encoding="utf-8",
        )
        card = _write_task_card(
            "e2e-rule-02", execution_mode="WORKTREE", profile="e2e-narrowmode"
        )
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "WORKTREE" in result.stdout
            assert "not in profile" in result.stdout.lower() or "allowed_execution_modes" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            narrow.unlink(missing_ok=True)

    def test_missing_required_front_matter_fails(self) -> None:
        """Profile requiring 'sprint' field, task missing it."""
        extra = PROFILES_DIR / "e2e-extrafm-profile.md"
        extra.write_text(
            "---\n"
            "profile_name: e2e-extrafm\n"
            'schema_version: "1.0"\n'
            "description: E2E extra front matter profile.\n"
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
        card = _write_task_card("e2e-rule-03", profile="e2e-extrafm")
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "sprint" in result.stdout
            assert "requires additional front matter" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            extra.unlink(missing_ok=True)

    def test_missing_required_section_fails(self) -> None:
        """Profile requiring '## Risk Assessment' section, task missing it."""
        extra = PROFILES_DIR / "e2e-extrasec-profile.md"
        extra.write_text(
            "---\n"
            "profile_name: e2e-extrasec\n"
            'schema_version: "1.0"\n'
            "description: E2E extra section profile.\n"
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
        card = _write_task_card("e2e-rule-04", profile="e2e-extrasec")
        try:
            result = _run_validator()
            assert result.returncode != 0
            assert "Risk Assessment" in result.stdout
            assert "requires additional section" in result.stdout.lower()
        finally:
            card.unlink(missing_ok=True)
            extra.unlink(missing_ok=True)


class TestPreflightFailureNoMutation:
    """Unknown/malformed/schema-invalid profiles must leave all protected fields unchanged."""

    def test_unknown_profile_no_mutation(self) -> None:
        card = _write_task_card("e2e-pre-01")
        before = _read_task_front_matter(card)
        result = _run_dispatch("e2e-pre-01", ["--profile", "nonexistent-xyz-e2e"])
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()
        after = _read_task_front_matter(card)
        _assert_immutable(before, after)
        card.unlink(missing_ok=True)

    def test_malformed_profile_no_mutation(self) -> None:
        card = _write_task_card("e2e-pre-02")
        before = _read_task_front_matter(card)
        bad = PROFILES_DIR / "e2e-malformed-profile.md"
        bad.write_text("---\nnot: valid: yaml: [[[\n---\n", encoding="utf-8")
        try:
            result = _run_dispatch("e2e-pre-02", ["--profile", "e2e-malformed"])
            assert result.returncode != 0
            stderr = result.stderr.lower()
            assert "malformed" in stderr or "missing" in stderr or "error" in stderr
            after = _read_task_front_matter(card)
            _assert_immutable(before, after)
        finally:
            bad.unlink(missing_ok=True)
            card.unlink(missing_ok=True)

    def test_schema_invalid_profile_no_mutation(self) -> None:
        card = _write_task_card("e2e-pre-03")
        before = _read_task_front_matter(card)
        bad = PROFILES_DIR / "e2e-schema-invalid-profile.md"
        bad.write_text(
            "---\n"
            "profile_name: e2e-schema-invalid\n"
            "schema_version: \"9.9\"\n"
            "description: bad\n"
            "task_format:\n"
            "  allowed_statuses: READY\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            result = _run_dispatch("e2e-pre-03", ["--profile", "e2e-schema-invalid"])
            assert result.returncode != 0
            stderr = result.stderr.lower()
            assert "schema_version" in stderr or "allowed_statuses" in stderr or "validation" in stderr
            after = _read_task_front_matter(card)
            _assert_immutable(before, after)
        finally:
            bad.unlink(missing_ok=True)
            card.unlink(missing_ok=True)


# ─── 6. Message-only: no mutation ──────────────────────────────────────


class TestMessageOnlyNoMutation:
    """--message-only must never write task-card metadata."""

    def test_message_only_with_profile_no_mutation(self) -> None:
        card = _write_task_card("e2e-msg-01")
        before = _read_task_front_matter(card)
        result = _run_dispatch(
            "e2e-msg-01", ["--profile", "rental-rebuild"], message_only=True,
        )
        assert result.returncode == 0
        assert "Profile context: rental-rebuild" in result.stdout
        after = _read_task_front_matter(card)
        _assert_immutable(before, after)
        card.unlink(missing_ok=True)

    def test_message_only_without_profile_no_mutation(self) -> None:
        card = _write_task_card("e2e-msg-02")
        before = _read_task_front_matter(card)
        result = _run_dispatch("e2e-msg-02", message_only=True)
        assert result.returncode == 0
        after = _read_task_front_matter(card)
        _assert_immutable(before, after)
        card.unlink(missing_ok=True)

    def test_message_only_file_not_modified(self) -> None:
        card = _write_task_card("e2e-msg-03")
        mtime = card.stat().st_mtime
        _run_dispatch("e2e-msg-03", message_only=True)
        assert card.stat().st_mtime == mtime
        card.unlink(missing_ok=True)


# ─── 7. Full validator still passes ────────────────────────────────────


class TestValidatorStillPasses:
    """Full coordination validator must pass after all test cleanup."""

    def test_full_validator_passes(self) -> None:
        result = _run_validator()
        assert result.returncode == 0
        assert "Coordination validation passed" in result.stdout
