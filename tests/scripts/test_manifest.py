"""Tests for scripts/manifest.py — immutable run manifest.

Covers manifest creation, reproducibility, duplicate rejection,
unknown task rejection, invalid profile rejection, and no-mutation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
MANIFEST_SCRIPT = SCRIPTS_DIR / "manifest.py"
MANIFESTS_DIR = ROOT / "coordination" / "manifests"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_manifest(extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(MANIFEST_SCRIPT)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )


def _find_ready_tasks() -> list[str]:
    """Find task IDs in ready/ state."""
    from coordination_common import list_tasks
    ready = list_tasks(("ready",))
    return [str(fm.get("task_id", "")) for _, fm in ready if fm.get("task_id")]


def _assert_no_mutation(paths: list[Path], before: list[bytes]) -> None:
    for path, content in zip(paths, before):
        assert path.read_bytes() == content, f"File {path} was mutated"


# ─── 1. Manifest creation ────────────────────────────────────────────


class TestManifestCreation:
    """Basic manifest creation with valid inputs."""

    def test_help_flag(self) -> None:
        result = _run_manifest(["--help"])
        assert result.returncode == 0
        assert "manifest" in result.stdout.lower()

    def test_create_with_ready_task(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        task_id = ready[0]
        result = _run_manifest([
            "--tasks", task_id,
            "--owner", "test-agent",
        ])
        assert result.returncode == 0
        assert "Manifest ID:" in result.stdout
        # Clean up created manifest
        _cleanup_last_manifest()

    def test_json_output(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "manifest_id" in data
        assert "created_at" in data
        assert "repo" in data
        assert "wave" in data
        assert "tasks" in data
        assert "owner" in data
        assert "reviewer" in data
        assert "profile" in data
        assert "command_context" in data
        _cleanup_last_manifest()

    def test_manifest_file_written(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        before_count = len(list(MANIFESTS_DIR.glob("*.json"))) if MANIFESTS_DIR.exists() else 0
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
        ])
        assert result.returncode == 0
        after_count = len(list(MANIFESTS_DIR.glob("*.json")))
        assert after_count == before_count + 1
        _cleanup_last_manifest()


# ─── 2. Reproducibility fields ───────────────────────────────────────


class TestReproducibilityFields:
    """Manifest records repo identity, tasks, owner, reviewer, profile."""

    def test_repo_identity_recorded(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        repo = data["repo"]
        assert "sha" in repo
        assert "branch" in repo
        assert "remote" in repo
        _cleanup_last_manifest()

    def test_owner_and_reviewer_recorded(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "my-agent",
            "--reviewer", "my-reviewer",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["owner"] == "my-agent"
        assert data["reviewer"] == "my-reviewer"
        _cleanup_last_manifest()

    def test_profile_recorded(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--profile", "rental-rebuild",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["profile"] is not None
        assert data["profile"]["profile_name"] == "rental-rebuild"
        _cleanup_last_manifest()

    def test_task_details_recorded(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == ready[0]
        _cleanup_last_manifest()

    def test_wave_plan_recorded(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "waves" in data["wave"]
        assert "blocked" in data["wave"]
        assert "errors" in data["wave"]
        _cleanup_last_manifest()


# ─── 3. Duplicate rejection ──────────────────────────────────────────


class TestDuplicateRejection:
    """Duplicate manifest IDs must fail without overwriting."""

    def test_duplicate_id_rejected(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        mid = "test-duplicate-id-001"
        result1 = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--manifest-id", mid,
        ])
        assert result1.returncode == 0
        try:
            result2 = _run_manifest([
                "--tasks", ready[0],
                "--owner", "test-agent",
                "--manifest-id", mid,
            ])
            assert result2.returncode != 0
            assert "already exists" in result2.stderr.lower()
        finally:
            _cleanup_manifest_by_id(mid)


# ─── 4. Unknown/non-runnable task rejection ──────────────────────────


class TestTaskValidation:
    """Unknown or non-runnable tasks are rejected."""

    def test_unknown_task_rejected(self) -> None:
        result = _run_manifest([
            "--tasks", "nonexistent-task-999",
            "--owner", "test-agent",
        ])
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_multiple_tasks_one_unknown(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0], "nonexistent-task-999",
            "--owner", "test-agent",
        ])
        assert result.returncode != 0
        assert "nonexistent-task-999" in result.stderr


# ─── 5. Invalid profile rejection ────────────────────────────────────


class TestProfileValidation:
    """Invalid profile references are rejected."""

    def test_nonexistent_profile_rejected(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--profile", "nonexistent-profile-xyz",
        ])
        assert result.returncode != 0
        assert "profile" in result.stderr.lower()


# ─── 6. No-mutation behavior ─────────────────────────────────────────


class TestNoMutation:
    """Manifest creation never modifies task cards or profiles."""

    def test_task_cards_unchanged(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")

        from coordination_common import find_task
        path, _, _ = find_task(ready[0])
        before = path.read_bytes()

        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
        ])
        assert result.returncode == 0
        after = path.read_bytes()
        assert before == after
        _cleanup_last_manifest()

    def test_profiles_unchanged(self) -> None:
        profile_path = ROOT / "profiles" / "rental-rebuild-profile.md"
        if not profile_path.exists():
            pytest.skip("rental-rebuild profile not found")
        before = profile_path.read_bytes()

        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--profile", "rental-rebuild",
        ])
        assert result.returncode == 0
        after = profile_path.read_bytes()
        assert before == after
        _cleanup_last_manifest()

    def test_manifest_dir_only_written(self) -> None:
        """Only the manifest file is created; no other files are touched."""
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")

        # Snapshot all coordination files
        before_files = {}
        for f in ROOT.glob("coordination/**/*.md"):
            if f.is_file():
                before_files[f] = f.read_bytes()

        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
        ])
        assert result.returncode == 0

        # Verify no .md files were modified
        for f, content in before_files.items():
            if f.exists():
                assert f.read_bytes() == content, f"File {f} was mutated"
            else:
                assert False, f"File {f} was deleted"

        _cleanup_last_manifest()


# ─── 7. Custom manifest ID ───────────────────────────────────────────


class TestCustomManifestId:
    """Explicit --manifest-id is used instead of auto-generated."""

    def test_custom_id_used(self) -> None:
        ready = _find_ready_tasks()
        if not ready:
            pytest.skip("No ready tasks available")
        mid = "my-custom-manifest-id"
        result = _run_manifest([
            "--tasks", ready[0],
            "--owner", "test-agent",
            "--manifest-id", mid,
            "--json",
        ])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["manifest_id"] == mid
        _cleanup_manifest_by_id(mid)


# ─── Helpers ──────────────────────────────────────────────────────────


def _cleanup_last_manifest() -> None:
    """Remove the most recently created manifest file."""
    if not MANIFESTS_DIR.exists():
        return
    files = sorted(MANIFESTS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if files:
        files[-1].unlink(missing_ok=True)


def _cleanup_manifest_by_id(manifest_id: str) -> None:
    """Remove a manifest file by its manifest_id."""
    if not MANIFESTS_DIR.exists():
        return
    for path in MANIFESTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("manifest_id") == manifest_id:
                path.unlink(missing_ok=True)
                return
        except (json.JSONDecodeError, OSError):
            continue
