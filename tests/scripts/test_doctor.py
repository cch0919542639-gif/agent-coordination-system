"""Tests for scripts/doctor.py — read-only preflight diagnostics.

Covers healthy repository, missing repository/runtime/task/profile inputs,
and explicit no-mutation assertions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
DOCTOR_SCRIPT = SCRIPTS_DIR / "doctor.py"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_doctor(extra_args: list[str] | None = None, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(DOCTOR_SCRIPT)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _assert_no_mutation(paths: list[Path], before_contents: list[bytes]) -> None:
    """Assert files at *paths* are byte-for-byte identical to *before_contents*."""
    for path, content in zip(paths, before_contents):
        assert path.read_bytes() == content, (
            f"File {path} was mutated by doctor"
        )


# ─── 1. Healthy repository ─────────────────────────────────────────────


class TestHealthyRepository:
    """All checks pass when run from the correct root."""

    def test_all_checks_pass(self) -> None:
        result = _run_doctor()
        assert result.returncode == 0
        assert "PASS" in result.stdout
        assert "FAIL" not in result.stdout
        assert "Overall result: PASS" in result.stdout

    def test_repository_root_check_passes(self) -> None:
        result = _run_doctor()
        assert "repository-root" in result.stdout
        assert "[PASS]" in result.stdout

    def test_git_checks_pass(self) -> None:
        result = _run_doctor()
        assert "git-available" in result.stdout
        assert "git-repository" in result.stdout
        assert "git-remote" in result.stdout
        assert "[FAIL]" not in result.stdout.split("git-")[1] if "git-" in result.stdout else True

    def test_python_runtime_reported(self) -> None:
        result = _run_doctor()
        assert "python-runtime" in result.stdout
        assert "Python" in result.stdout

    def test_coordination_dirs_pass(self) -> None:
        result = _run_doctor()
        assert "coordination-dirs" in result.stdout
        lines = [l for l in result.stdout.splitlines() if "coordination-dirs" in l]
        pass_lines = [l for l in lines if "[FAIL]" not in l]
        assert len(pass_lines) > 0


# ─── 2. Missing repository root ────────────────────────────────────────


class TestMissingRepositoryRoot:
    """Repository-root check fails when run from a non-repo directory."""

    def test_fails_in_empty_directory(self, tmp_path: Path) -> None:
        result = _run_doctor(cwd=str(tmp_path))
        assert result.returncode != 0
        assert "repository-root" in result.stdout
        assert "FAIL" in result.stdout

    def test_fails_with_partial_directories(self, tmp_path: Path) -> None:
        (tmp_path / "coordination").mkdir()
        (tmp_path / "scripts").mkdir()
        result = _run_doctor(cwd=str(tmp_path))
        assert result.returncode != 0
        assert "repository-root" in result.stdout
        assert "FAIL" in result.stdout


# ─── 3. Not a git repository ───────────────────────────────────────────


class TestNotAGitRepository:
    """Git-related checks outside a git repo."""

    def test_git_fails_in_empty_new_dir(self, tmp_path: Path) -> None:
        """An empty temp dir has no coordination dirs and is not a git repo."""
        for d in ("coordination", "scripts", "docs", "profiles"):
            (tmp_path / d).mkdir()
        result = _run_doctor(cwd=str(tmp_path))
        # On Windows, 'git rev-parse --show-toplevel' from a path
        # outside any repo fails.  Verify at least one check reports FAIL.
        assert result.returncode != 0


# ─── 4. Task reference checks ──────────────────────────────────────────


class TestTaskReference:
    """--task-id argument validates task existence."""

    def test_existing_task_passes(self) -> None:
        result = _run_doctor(["--task-id", "phase11-runtime-safety-01"])
        assert result.returncode == 0
        assert "task-reference" in result.stdout
        assert "[PASS]" in result.stdout
        assert "phase11-runtime-safety-01" in result.stdout

    def test_nonexistent_task_fails(self) -> None:
        result = _run_doctor(["--task-id", "nonexistent-task-999"])
        assert result.returncode != 0
        assert "task-reference" in result.stdout
        assert "[FAIL]" in result.stdout
        assert "nonexistent-task-999" in result.stdout

    def test_task_no_mutation(self) -> None:
        """Verify doctor does not modify task card files."""
        task_id = "phase11-runtime-safety-01"
        from coordination_common import find_task
        path, _, _ = find_task(task_id)
        before = path.read_bytes()
        result = _run_doctor(["--task-id", task_id])
        assert result.returncode == 0
        _assert_no_mutation([path], [before])


# ─── 5. Profile reference checks ───────────────────────────────────────


class TestProfileReference:
    """--profile argument validates profile existence."""

    def test_existing_profile_passes(self) -> None:
        result = _run_doctor(["--profile", "rental-rebuild"])
        assert result.returncode == 0
        assert "profile-reference" in result.stdout
        assert "[PASS]" in result.stdout
        assert "rental-rebuild" in result.stdout

    def test_nonexistent_profile_fails(self) -> None:
        result = _run_doctor(["--profile", "nonexistent-profile-xyz"])
        assert result.returncode != 0
        assert "profile-reference" in result.stdout
        assert "[FAIL]" in result.stdout
        assert "nonexistent-profile-xyz" in result.stdout

    def test_profile_path_resolves(self) -> None:
        profile_path = str(ROOT / "profiles" / "rental-rebuild-profile.md")
        result = _run_doctor(["--profile", profile_path])
        assert result.returncode == 0
        assert "[PASS]" in result.stdout
        assert "rental-rebuild" in result.stdout

    def test_profile_no_mutation(self) -> None:
        """Verify doctor does not modify profile files."""
        profile_path = ROOT / "profiles" / "rental-rebuild-profile.md"
        before = profile_path.read_bytes()
        result = _run_doctor(["--profile", "rental-rebuild"])
        assert result.returncode == 0
        _assert_no_mutation([profile_path], [before])


# ─── 6. Combined task + profile reference ──────────────────────────────


class TestCombinedReferences:
    """Both --task-id and --profile can be specified together."""

    def test_both_valid_passes(self) -> None:
        result = _run_doctor(["--task-id", "phase11-runtime-safety-01", "--profile", "rental-rebuild"])
        assert result.returncode == 0
        assert "task-reference" in result.stdout
        assert "profile-reference" in result.stdout
        assert result.stdout.count("[PASS]") >= 6

    def test_valid_invalid_combination(self) -> None:
        result = _run_doctor(["--task-id", "phase11-runtime-safety-01", "--profile", "nonexistent-profile"])
        assert result.returncode != 0
        assert "profile-reference" in result.stdout
        assert "[FAIL]" in result.stdout


# ─── 7. No-mutation across fixtures ────────────────────────────────────


class TestNoMutationAcrossFixtures:
    """All test fixture files remain byte-for-byte unchanged after doctor runs."""

    def test_no_mutation_with_temp_task_card(self, tmp_path: Path) -> None:
        """Create a temp task card and profile, then verify doctor does not touch them."""
        for d in ("coordination", "scripts", "docs", "profiles"):
            (tmp_path / d).mkdir(parents=True)

        from coordination_common import dump_front_matter
        fm = {
            "task_id": "doctor-no-mutation-test",
            "phase": "test",
            "status": "READY",
            "owner": "test",
            "reviewer": "test",
            "priority": "low",
            "dependencies": [],
            "allowed_scope": ["tests/**"],
            "forbidden_scope": ["src/**"],
            "acceptance": ["test"],
            "expected_artifacts": ["code_changes"],
        }
        body = "# Task Packet\n\n## Objective\n\nTest.\n"
        card_content = dump_front_matter(fm, body)
        task_file = tmp_path / "coordination" / "task-board" / "ready" / "doctor-no-mutation.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_bytes(card_content.encode("utf-8"))
        task_files = [task_file]
        before_contents = [card_content.encode("utf-8")]

        profile_content = "---\nprofile_name: doctor-test\nschema_version: \"1.0\"\n---\n# body\n"
        profile_file = tmp_path / "profiles" / "doctor-test-profile.md"
        profile_file.write_bytes(profile_content.encode("utf-8"))
        task_files.append(profile_file)
        before_contents.append(profile_content.encode("utf-8"))

        result = _run_doctor(
            ["--task-id", "doctor-no-mutation-test", "--profile", "doctor-test"],
            cwd=str(tmp_path),
        )
        # The repo-root and git checks will fail in tmp_path — that's expected
        # The task/profile reference checks should also fail because their
        # parsers use the real ROOT, not tmp_path.
        # For this test we just verify no-mutation on the fixture files.
        _assert_no_mutation(task_files, before_contents)
