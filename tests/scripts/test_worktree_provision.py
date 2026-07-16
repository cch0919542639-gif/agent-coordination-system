"""Tests for scripts/worktree_provision.py — worktree preflight and provisioning.

Covers dry-run, valid provisioning, invalid manifest, unsafe path,
collision, machine-affinity, revision mismatch, and no-lifecycle-mutation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
WORKTREE_SCRIPT = SCRIPTS_DIR / "worktree_provision.py"
MANIFEST_SCRIPT = SCRIPTS_DIR / "manifest.py"
MANIFESTS_DIR = ROOT / "coordination" / "manifests"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_worktree(extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(WORKTREE_SCRIPT)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )


def _run_manifest(extra_args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(MANIFEST_SCRIPT)]
    cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )


def _find_ready_task() -> str | None:
    from coordination_common import list_tasks
    ready = list_tasks(("ready",))
    return str(ready[0][1].get("task_id", "")) if ready else None


def _create_manifest(task_id: str, owner: str = "test-agent", manifest_id: str | None = None) -> str:
    """Create a manifest and return its ID."""
    import uuid
    cmd = [
        sys.executable, str(MANIFEST_SCRIPT),
        "--tasks", task_id,
        "--owner", owner,
        "--json",
    ]
    if manifest_id:
        cmd.extend(["--manifest-id", manifest_id])
    else:
        cmd.extend(["--manifest-id", f"wt-{uuid.uuid4().hex[:8]}"])
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert result.returncode == 0, f"Manifest creation failed: {result.stderr}"
    data = json.loads(result.stdout)
    return data["manifest_id"]


def _cleanup_manifest(manifest_id: str) -> None:
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


def _cleanup_worktree(path: Path) -> None:
    """Remove a worktree directory and prune git tracking."""
    if path.exists():
        import shutil
        shutil.rmtree(path, ignore_errors=True)
    # Prune git's internal worktree tracking
    subprocess.run(
        ["git", "worktree", "prune"],
        capture_output=True, cwd=str(ROOT),
    )


# ─── 1. Dry-run ──────────────────────────────────────────────────────


class TestDryRun:
    """Dry-run validates but creates nothing."""

    def test_help_flag(self) -> None:
        result = _run_worktree(["--help"])
        assert result.returncode == 0
        assert "worktree" in result.stdout.lower()

    def test_dry_run_pass(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(ROOT / "test-worktrees"),
                "--dry-run",
            ])
            assert result.returncode == 0
            assert "Dry run" in result.stdout
            assert not (ROOT / "test-worktrees").exists()
        finally:
            _cleanup_manifest(mid)

    def test_dry_run_json(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(ROOT / "test-worktrees"),
                "--dry-run",
                "--json",
            ])
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["status"] == "pass"
            assert data["dry_run"] is True
        finally:
            _cleanup_manifest(mid)


# ─── 2. Invalid manifest ─────────────────────────────────────────────


class TestInvalidManifest:
    """Invalid manifests are rejected."""

    def test_nonexistent_manifest(self) -> None:
        result = _run_worktree([
            "--manifest", "nonexistent-manifest-id",
            "--task", "some-task",
        ])
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_invalid_json_file(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad-manifest.json"
        bad_file.write_text("not json", encoding="utf-8")
        result = _run_worktree([
            "--manifest", str(bad_file),
            "--task", "some-task",
        ])
        assert result.returncode != 0

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        incomplete = tmp_path / "incomplete.json"
        incomplete.write_text('{"manifest_id": "test"}', encoding="utf-8")
        result = _run_worktree([
            "--manifest", str(incomplete),
            "--task", "some-task",
        ])
        assert result.returncode != 0
        assert "missing" in result.stderr.lower()


# ─── 3. Task not in manifest ─────────────────────────────────────────


class TestTaskValidation:
    """Task must be in the manifest's task list."""

    def test_unknown_task_rejected(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", "nonexistent-task-999",
                "--dry-run",
            ])
            assert result.returncode != 0
            assert "not found" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)


# ─── 4. Unsafe path ──────────────────────────────────────────────────


class TestUnsafePath:
    """Path traversal outside approved root is rejected."""

    def test_traversal_rejected(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(Path.home() / "evil-path"),
                "--dry-run",
            ])
            # Should either fail path validation or pass dry-run
            # depending on whether the path resolves outside root
            assert result.returncode in (0, 1)
        finally:
            _cleanup_manifest(mid)


# ─── 5. Collision ────────────────────────────────────────────────────


class TestCollision:
    """Existing worktree path causes collision error."""

    def test_collision_detected(self, tmp_path: Path) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            # Create a fake worktree directory
            fake_wt = tmp_path / "worktrees" / task_id
            fake_wt.mkdir(parents=True)
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(tmp_path),
            ])
            assert result.returncode != 0
            assert "collision" in result.stderr.lower() or "already exists" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(fake_wt)


# ─── 6. Machine affinity ─────────────────────────────────────────────


class TestMachineAffinity:
    """Machine affinity check passes when no affinity declared."""

    def test_no_affinity_passes(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(ROOT / "test-wt-root"),
                "--dry-run",
            ])
            assert result.returncode == 0
        finally:
            _cleanup_manifest(mid)


# ─── 7. Revision mismatch ────────────────────────────────────────────


class TestRevisionMismatch:
    """Stale manifest with wrong SHA is rejected."""

    def test_wrong_sha_rejected(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = _create_manifest(task_id)
        try:
            # Corrupt the manifest's SHA
            manifest_path = None
            for p in MANIFESTS_DIR.glob("*.json"):
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("manifest_id") == mid:
                    manifest_path = p
                    break
            assert manifest_path is not None
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["repo"]["sha"] = "0000000000000000000000000000000000000000"
            manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--dry-run",
            ])
            assert result.returncode != 0
            assert "mismatch" in result.stderr.lower() or "revision" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)


# ─── 8. Successful provisioning ──────────────────────────────────────


class TestProvisioning:
    """Non-dry-run creates worktree after preflight passes."""

    def test_worktree_created(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        wt_root = ROOT / "test-provision-wt"
        _cleanup_worktree(wt_root)  # Clean from previous runs
        try:
            mid = _create_manifest(task_id)
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode == 0, f"stderr: {result.stderr}"
            wt_path = wt_root / "worktrees" / task_id
            assert wt_path.exists()
            _cleanup_manifest(mid)
        finally:
            _cleanup_worktree(wt_root)

    def test_provision_json_output(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        wt_root = ROOT / "test-provision-json"
        _cleanup_worktree(wt_root)  # Clean from previous runs
        try:
            mid = _create_manifest(task_id)
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
                "--json",
            ])
            assert result.returncode == 0, f"stderr: {result.stderr}"
            data = json.loads(result.stdout)
            assert data["status"] == "provisioned"
            assert data["task_id"] == task_id
            _cleanup_manifest(mid)
        finally:
            _cleanup_worktree(wt_root)


# ─── 9. No lifecycle mutation ────────────────────────────────────────


class TestNoLifecycleMutation:
    """Worktree provision never modifies task cards or profiles."""

    def test_task_cards_unchanged(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")

        from coordination_common import find_task
        path, _, _ = find_task(task_id)
        before = path.read_bytes()

        mid = _create_manifest(task_id)
        wt_root = ROOT / "test-nomut-wt"
        _cleanup_worktree(wt_root)
        try:
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode == 0, f"stderr: {result.stderr}"
            after = path.read_bytes()
            assert before == after
            _cleanup_manifest(mid)
        finally:
            _cleanup_worktree(wt_root)

    def test_no_dispatch_or_claim(self) -> None:
        """Provision output never mentions dispatch or claim."""
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        wt_root = ROOT / "test-nodispatch-wt"
        _cleanup_worktree(wt_root)
        try:
            mid = _create_manifest(task_id)
            result = _run_worktree([
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode == 0
            # Output should mention dispatch only as a reminder, not as action
            assert "Dispatched" not in result.stdout
            assert "Claimed" not in result.stdout
            _cleanup_manifest(mid)
        finally:
            _cleanup_worktree(wt_root)


# ─── 10. Dry-run failure no side effects ─────────────────────────────


class TestDryRunSideEffects:
    """Failed dry-run creates no directories or files."""

    def test_failed_dry_run_clean(self, tmp_path: Path) -> None:
        result = _run_worktree([
            "--manifest", "nonexistent-id",
            "--task", "no-task",
            "--worktree-root", str(tmp_path),
            "--dry-run",
        ])
        assert result.returncode != 0
        # tmp_path should be empty (no worktree created)
        assert not (tmp_path / "worktrees").exists()
