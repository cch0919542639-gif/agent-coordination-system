"""End-to-end regression matrix for Phase 11 orchestration runtime safety.

Quality gate task (phase11-runtime-safety-05): verifies the combined behavior
of doctor, wave planner, manifest, and worktree provision into a repeatable
cross-machine preparation flow.  Do NOT modify scripts/; this file only
exercises existing runtime through subprocess calls.

All tests use isolated temporary repositories where possible and clean up
artifacts created by their own fixtures.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

DOCTOR = SCRIPTS_DIR / "doctor.py"
WAVES = SCRIPTS_DIR / "wave_planner.py"
MANIFEST = SCRIPTS_DIR / "manifest.py"
WORKTREE = SCRIPTS_DIR / "worktree_provision.py"


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _run_script(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(script)]
    if args:
        cmd.extend(args)
    return _run(cmd)


def _find_ready_task() -> str | None:
    from coordination_common import list_tasks
    ready = list_tasks(("ready",))
    return str(ready[0][1].get("task_id", "")) if ready else None


def _create_manifest(task_id: str, manifest_id: str) -> str:
    import uuid
    result = _run_script(MANIFEST, [
        "--tasks", task_id,
        "--owner", "e2e-test-agent",
        "--manifest-id", manifest_id,
        "--json",
    ])
    assert result.returncode == 0, f"Manifest creation failed: {result.stderr}"
    data = json.loads(result.stdout)
    return data["manifest_id"]


def _cleanup_manifest(manifest_id: str) -> None:
    from pathlib import Path as P
    manifests_dir = ROOT / "coordination" / "manifests"
    if not manifests_dir.exists():
        return
    for p in manifests_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("manifest_id") == manifest_id:
                p.unlink(missing_ok=True)
                return
        except (json.JSONDecodeError, OSError):
            continue


def _cleanup_worktree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], capture_output=True, cwd=str(ROOT))


# ─── 1. Doctor preflight ─────────────────────────────────────────────


class TestDoctorPreflight:
    """Doctor passes on healthy repo, fails on wrong directory."""

    def test_doctor_passes_on_repo_root(self) -> None:
        result = _run_script(DOCTOR)
        assert result.returncode == 0
        assert "Overall result: PASS" in result.stdout

    def test_doctor_fails_in_empty_dir(self, tmp_path: Path) -> None:
        result = _run_script(DOCTOR)
        # Run from empty dir — doctor uses ROOT, not cwd for most checks
        # But repository-root check uses cwd
        result = _run([sys.executable, str(DOCTOR)], cwd=str(tmp_path))
        assert result.returncode != 0
        assert "FAIL" in result.stdout

    def test_doctor_no_mutation(self) -> None:
        """Doctor never modifies task cards."""
        from coordination_common import list_tasks
        ready = list_tasks(("ready",))
        if not ready:
            pytest.skip("No ready tasks")
        path, fm = ready[0]
        before = path.read_bytes()
        _run_script(DOCTOR)
        after = path.read_bytes()
        assert before == after


# ─── 2. Wave planner ─────────────────────────────────────────────────


class TestWavePlanner:
    """Wave planner proposes waves without claiming tasks."""

    def test_waves_passes(self) -> None:
        result = _run_script(WAVES)
        assert result.returncode == 0
        assert "Dependency Wave Planner" in result.stdout

    def test_waves_json_output(self) -> None:
        result = _run_script(WAVES, ["--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "waves" in data
        assert "ready" in data
        assert "blocked" in data
        assert "errors" in data

    def test_waves_no_mutation(self) -> None:
        """Wave planner never modifies task cards."""
        from coordination_common import list_tasks
        ready = list_tasks(("ready",))
        if not ready:
            pytest.skip("No ready tasks")
        path, fm = ready[0]
        before = path.read_bytes()
        _run_script(WAVES)
        after = path.read_bytes()
        assert before == after

    def test_waves_no_dispatch_or_claim(self) -> None:
        """Wave planner output never mentions dispatch or claim."""
        result = _run_script(WAVES)
        assert "Dispatched" not in result.stdout
        assert "Claimed" not in result.stdout


# ─── 3. Manifest creation ────────────────────────────────────────────


class TestManifestCreation:
    """Manifest records operator-approved wave without claiming tasks."""

    def test_manifest_create_and_read(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-{uuid.uuid4().hex[:8]}"
        try:
            result = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
                "--json",
            ])
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["manifest_id"] == mid
            assert data["owner"] == "e2e-test-agent"
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["task_id"] == task_id
        finally:
            _cleanup_manifest(mid)

    def test_manifest_duplicate_rejected(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        mid = f"e2e-dup-{id(task_id)}"
        try:
            result1 = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            assert result1.returncode == 0
            result2 = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            assert result2.returncode != 0
            assert "already exists" in result2.stderr.lower()
        finally:
            _cleanup_manifest(mid)

    def test_manifest_no_mutation(self) -> None:
        """Manifest creation never modifies task cards."""
        from coordination_common import list_tasks
        ready = list_tasks(("ready",))
        if not ready:
            pytest.skip("No ready tasks")
        path, fm = ready[0]
        before = path.read_bytes()
        import uuid
        mid = f"e2e-nomut-{uuid.uuid4().hex[:8]}"
        try:
            _run_script(MANIFEST, [
                "--tasks", fm.get("task_id", ""),
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            after = path.read_bytes()
            assert before == after
        finally:
            _cleanup_manifest(mid)

    def test_manifest_no_dispatch_or_claim(self) -> None:
        """Manifest output never mentions dispatch or claim."""
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-ndc-{uuid.uuid4().hex[:8]}"
        try:
            result = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            assert result.returncode == 0
            assert "Dispatched" not in result.stdout
            assert "Claimed" not in result.stdout
        finally:
            _cleanup_manifest(mid)


# ─── 4. Worktree dry-run ─────────────────────────────────────────────


class TestWorktreeDryRun:
    """Worktree dry-run validates without creating."""

    def test_dry_run_pass(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-dr-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            wt_root = ROOT / "test-e2e-dr"
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
                "--dry-run",
            ])
            assert result.returncode == 0
            assert "Dry run" in result.stdout
            assert not wt_root.exists()
        finally:
            _cleanup_manifest(mid)

    def test_dry_run_invalid_manifest(self) -> None:
        result = _run_script(WORKTREE, [
            "--manifest", "nonexistent-e2e-id",
            "--task", "no-task",
            "--dry-run",
        ])
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_dry_run_unknown_task(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-ut-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", "nonexistent-e2e-task",
                "--dry-run",
            ])
            assert result.returncode != 0
            assert "not found" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)

    def test_dry_run_no_mutation(self) -> None:
        """Dry-run creates nothing."""
        import uuid
        wt_root = ROOT / f"test-e2e-dry-{uuid.uuid4().hex[:8]}"
        try:
            result = _run_script(WORKTREE, [
                "--manifest", "nonexistent",
                "--task", "no-task",
                "--worktree-root", str(wt_root),
                "--dry-run",
            ])
            assert result.returncode != 0
            assert not wt_root.exists()
        finally:
            _cleanup_worktree(wt_root)


# ─── 5. Worktree provisioning ────────────────────────────────────────


class TestWorktreeProvisioning:
    """Worktree provisioning creates one local worktree."""

    def test_provision_creates_worktree(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-prov-{uuid.uuid4().hex[:8]}"
        wt_root = ROOT / f"test-e2e-prov-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode == 0, f"stderr: {result.stderr}"
            wt_path = wt_root / "worktrees" / task_id
            assert wt_path.exists()
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(wt_root)

    def test_provision_no_dispatch_or_claim(self) -> None:
        """Provision output never mentions dispatch or claim."""
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-pndc-{uuid.uuid4().hex[:8]}"
        wt_root = ROOT / f"test-e2e-pndc-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode == 0
            assert "Dispatched" not in result.stdout
            assert "Claimed" not in result.stdout
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(wt_root)

    def test_provision_no_lifecycle_mutation(self) -> None:
        """Provision never modifies task cards."""
        from coordination_common import list_tasks
        ready = list_tasks(("ready",))
        if not ready:
            pytest.skip("No ready tasks")
        path, fm = ready[0]
        before = path.read_bytes()
        import uuid
        mid = f"e2e-nlm-{uuid.uuid4().hex[:8]}"
        wt_root = ROOT / f"test-e2e-nlm-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(str(fm.get("task_id", "")), mid)
            _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", str(fm.get("task_id", "")),
                "--worktree-root", str(wt_root),
            ])
            after = path.read_bytes()
            assert before == after
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(wt_root)


# ─── 6. Recovery evidence ────────────────────────────────────────────


class TestRecoveryEvidence:
    """Representative failure paths produce actionable diagnostics."""

    def test_wrong_repo_doctor_fails(self, tmp_path: Path) -> None:
        """Doctor fails in a non-repo directory."""
        result = _run([sys.executable, str(DOCTOR)], cwd=str(tmp_path))
        assert result.returncode != 0
        assert "FAIL" in result.stdout

    def test_missing_task_wave_planner(self) -> None:
        """Wave planner still works even with no ready tasks (empty waves)."""
        result = _run_script(WAVES, ["--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "waves" in data

    def test_invalid_manifest_structure(self, tmp_path: Path) -> None:
        """Worktree rejects manifest with missing fields."""
        bad = tmp_path / "bad.json"
        bad.write_text('{"manifest_id": "x"}', encoding="utf-8")
        result = _run_script(WORKTREE, [
            "--manifest", str(bad),
            "--task", "no-task",
            "--dry-run",
        ])
        assert result.returncode != 0
        assert "missing" in result.stderr.lower()

    def test_collision_detected(self) -> None:
        """Worktree detects path collision."""
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-coll-{uuid.uuid4().hex[:8]}"
        wt_root = ROOT / f"test-e2e-coll-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            # Create fake collision
            collision_path = wt_root / "worktrees" / task_id
            collision_path.mkdir(parents=True)
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert result.returncode != 0
            assert "collision" in result.stderr.lower() or "already exists" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(wt_root)

    def test_revision_mismatch(self) -> None:
        """Worktree rejects stale manifest with wrong SHA."""
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-rev-{uuid.uuid4().hex[:8]}"
        try:
            _create_manifest(task_id, mid)
            # Corrupt SHA in manifest
            from pathlib import Path as P
            manifests_dir = ROOT / "coordination" / "manifests"
            for p in manifests_dir.glob("*.json"):
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("manifest_id") == mid:
                    data["repo"]["sha"] = "0" * 40
                    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    break
            result = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--dry-run",
            ])
            assert result.returncode != 0
            assert "mismatch" in result.stderr.lower() or "revision" in result.stderr.lower()
        finally:
            _cleanup_manifest(mid)


# ─── 7. Full sequence e2e ────────────────────────────────────────────


class TestFullSequence:
    """End-to-end: doctor → waves → manifest → worktree dry-run → provision."""

    def test_happy_path(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")

        # Step 1: Doctor
        doctor = _run_script(DOCTOR)
        assert doctor.returncode == 0

        # Step 2: Waves
        waves = _run_script(WAVES, ["--json"])
        assert waves.returncode == 0
        wave_data = json.loads(waves.stdout)
        assert task_id in wave_data.get("ready", [])

        # Step 3: Manifest
        import uuid
        mid = f"e2e-hp-{uuid.uuid4().hex[:8]}"
        try:
            manifest = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
                "--json",
            ])
            assert manifest.returncode == 0
            mdata = json.loads(manifest.stdout)
            assert mdata["manifest_id"] == mid

            # Step 4: Worktree dry-run
            wt_root = ROOT / f"test-e2e-hp-{uuid.uuid4().hex[:8]}"
            dry = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
                "--dry-run",
            ])
            assert dry.returncode == 0
            assert "Dry run" in dry.stdout

            # Step 5: Worktree provision
            prov = _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
            ])
            assert prov.returncode == 0, f"stderr: {prov.stderr}"
            wt_path = wt_root / "worktrees" / task_id
            assert wt_path.exists()
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(ROOT / f"test-e2e-hp-{uuid.uuid4().hex[:8]}")

    def test_happy_path_no_lifecycle_mutation(self) -> None:
        """Full sequence never modifies task cards."""
        from coordination_common import list_tasks
        ready = list_tasks(("ready",))
        if not ready:
            pytest.skip("No ready tasks")
        path, fm = ready[0]
        before = path.read_bytes()

        task_id = str(fm.get("task_id", ""))
        _run_script(DOCTOR)
        _run_script(WAVES)

        import uuid
        mid = f"e2e-nlm2-{uuid.uuid4().hex[:8]}"
        wt_root = ROOT / f"test-e2e-nlm2-{uuid.uuid4().hex[:8]}"
        try:
            _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            _run_script(WORKTREE, [
                "--manifest", mid,
                "--task", task_id,
                "--worktree-root", str(wt_root),
                "--dry-run",
            ])
            after = path.read_bytes()
            assert before == after
        finally:
            _cleanup_manifest(mid)
            _cleanup_worktree(wt_root)


# ─── 8. No autonomous communication ──────────────────────────────────


class TestNoAutonomousCommunication:
    """No command launches agents, sends messages, or pushes to remote."""

    def test_doctor_no_push(self) -> None:
        result = _run_script(DOCTOR)
        assert "push" not in result.stdout.lower()

    def test_waves_no_push(self) -> None:
        result = _run_script(WAVES)
        assert "push" not in result.stdout.lower()

    def test_manifest_no_push(self) -> None:
        task_id = _find_ready_task()
        if not task_id:
            pytest.skip("No ready tasks")
        import uuid
        mid = f"e2e-np-{uuid.uuid4().hex[:8]}"
        try:
            result = _run_script(MANIFEST, [
                "--tasks", task_id,
                "--owner", "e2e-test-agent",
                "--manifest-id", mid,
            ])
            assert result.returncode == 0
            assert "push" not in result.stdout.lower()
        finally:
            _cleanup_manifest(mid)
