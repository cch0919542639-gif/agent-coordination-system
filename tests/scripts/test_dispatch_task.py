"""Tests for scripts/dispatch_task.py — dispatch message generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
SCRIPT = SCRIPTS_DIR / "dispatch_task.py"
READY_DIR = ROOT / "coordination" / "task-board" / "ready"
PROFILES_DIR = ROOT / "profiles"

# Add scripts/ to path for coordination_common imports
sys.path.insert(0, str(SCRIPTS_DIR))

# phase6-lead-agent-02 is in in_progress/ (we moved it there); use --message-only for it
MSG_TASK_ID = "phase6-lead-agent-02"
# phase6-lead-agent-03 is in ready/; use for full-flow integration test
FLOW_TASK_ID = "phase6-lead-agent-03"
FLOW_TASK_FILE = READY_DIR / "2026-07-02_phase6-lead-agent-03_docs-and-validation-integration.md"


@pytest.fixture
def dispatch_script() -> str:
    return str(SCRIPT)


def _run_dispatch(task_id: str, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable, str(SCRIPT),
        "--task-id", task_id,
        "--owner", "test-agent",
        "--message-only",
        "--allow-terminal",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


class TestDispatchMessageGeneration:
    """Unit tests for build_dispatch_message via subprocess invocation."""

    def test_help_flag(self, dispatch_script: str) -> None:
        result = subprocess.run(
            [sys.executable, dispatch_script, "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "owner" in result.stdout.lower()

    def test_message_only_no_file_change(self, dispatch_script: str) -> None:
        """--message-only should not modify the task card."""
        from coordination_common import find_task
        path, _, _ = find_task(MSG_TASK_ID)

        original_mtime = path.stat().st_mtime
        result = _run_dispatch(MSG_TASK_ID)
        assert result.returncode == 0
        assert path.stat().st_mtime == original_mtime

    def test_dispatch_message_contains_task_id(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID)
        assert result.returncode == 0
        assert MSG_TASK_ID in result.stdout

    def test_dispatch_message_contains_protocol_docs(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID)
        assert result.returncode == 0
        assert "agent-task-execution-protocol.md" in result.stdout
        assert "lead-agent-orchestration-protocol.md" in result.stdout
        assert "worker-assignment-policy.md" in result.stdout

    def test_dispatch_message_contains_blocked_instructions(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID)
        assert result.returncode == 0
        assert "blocked" in result.stdout.lower()
        assert "incident" in result.stdout.lower()

    def test_dispatch_message_contains_start_instructions(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID)
        assert result.returncode == 0
        assert "in_progress" in result.stdout
        assert "progress" in result.stdout

    def test_dispatch_message_contains_reviewer(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID, ["--reviewer", "ORCHESTRATOR"])
        assert result.returncode == 0
        assert "Reviewer: ORCHESTRATOR" in result.stdout

    def test_repo_first_dispatch_message_omits_worktree_fields(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID, ["--execution-mode", "REPO_FIRST"])
        assert result.returncode == 0
        assert "Execution mode:" in result.stdout
        assert "- REPO_FIRST" in result.stdout
        assert "branch:" not in result.stdout
        assert "worktree_path:" not in result.stdout

    def test_worktree_dispatch_message_includes_provenance(self, dispatch_script: str) -> None:
        result = _run_dispatch(
            MSG_TASK_ID,
            [
                "--execution-mode", "WORKTREE",
                "--branch", "agent/test-branch",
                "--worktree-path", "worktrees/test-agent/task-01",
                "--machine-id", "workstation-a",
            ],
        )
        assert result.returncode == 0
        assert "- WORKTREE" in result.stdout
        assert "branch: agent/test-branch" in result.stdout
        assert "worktree_path: worktrees/test-agent/task-01" in result.stdout
        assert "machine_id: workstation-a" in result.stdout

    def test_worktree_dispatch_requires_branch_and_path(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID, ["--execution-mode", "WORKTREE", "--branch", "agent/test-branch"])
        assert result.returncode != 0
        assert "requires both --branch and --worktree-path" in result.stderr

    def test_no_message_flag(self, dispatch_script: str) -> None:
        result = _run_dispatch(MSG_TASK_ID, ["--no-message"])
        assert result.returncode == 0
        assert "--- Dispatch Message ---" not in result.stdout

    def test_output_writes_file(self, dispatch_script: str, tmp_path: Path) -> None:
        out_file = tmp_path / "dispatch.md"
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--task-id", MSG_TASK_ID,
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
                "--output", str(out_file),
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert MSG_TASK_ID in content
        assert "test-agent" in content

    def test_output_dash_prints_raw_to_stdout(self, dispatch_script: str) -> None:
        """--output - should print the raw message to stdout instead of writing a file."""
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--task-id", MSG_TASK_ID,
                "--owner", "test-agent",
                "--message-only",
                "--allow-terminal",
                "--output", "-",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert MSG_TASK_ID in result.stdout
        assert "--- Dispatch Message ---" not in result.stdout
        assert "Dispatch message written" not in result.stdout

    def test_unknown_task_returns_error(self, dispatch_script: str) -> None:
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--task-id", "nonexistent-task-999",
                "--owner", "test-agent",
                "--message-only",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


class TestDispatchFullFlow:
    """Integration test: dispatch a ready task and verify owner/reviewer are updated."""

    def test_dispatch_updates_owner_and_reviewer(self, dispatch_script: str) -> None:
        """Full dispatch should update the task card's owner and reviewer fields."""
        if not FLOW_TASK_FILE.exists():
            pytest.skip("test task card not in ready/")

        # Read original owner
        from coordination_common import load_task
        orig_fm, _ = load_task(FLOW_TASK_FILE)

        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--task-id", FLOW_TASK_ID,
                "--owner", "test-agent-dispatch-test",
                "--reviewer", "TEST-REVIEWER",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert "Dispatched task" in result.stdout
        assert "--- Dispatch Message ---" in result.stdout
        assert "test-agent-dispatch-test" in result.stdout

        # Verify owner/reviewer were updated in the file
        updated_fm, _ = load_task(FLOW_TASK_FILE)
        assert updated_fm["owner"] == "test-agent-dispatch-test"
        assert updated_fm["reviewer"] == "TEST-REVIEWER"

        # Restore original values
        from coordination_common import save_task
        orig_fm["owner"] = orig_fm.get("owner", "UNASSIGNED")
        orig_fm["reviewer"] = orig_fm.get("reviewer", "ORCHESTRATOR")
        save_task(FLOW_TASK_FILE, orig_fm, _)

    def test_dispatch_updates_worktree_metadata(self, dispatch_script: str) -> None:
        """Full dispatch should persist worktree provenance on the task card."""
        if not FLOW_TASK_FILE.exists():
            pytest.skip("test task card not in ready/")

        from coordination_common import load_task, save_task

        orig_fm, body = load_task(FLOW_TASK_FILE)

        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--task-id", FLOW_TASK_ID,
                "--owner", "test-agent-worktree",
                "--execution-mode", "WORKTREE",
                "--branch", "agent/test-agent-worktree-phase7-02",
                "--worktree-path", "worktrees/test-agent-worktree/phase7-02",
                "--machine-id", "lab-machine",
            ],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0

        updated_fm, _ = load_task(FLOW_TASK_FILE)
        assert updated_fm["execution_mode"] == "WORKTREE"
        assert updated_fm["branch"] == "agent/test-agent-worktree-phase7-02"
        assert updated_fm["worktree_path"] == "worktrees/test-agent-worktree/phase7-02"
        assert updated_fm["machine_id"] == "lab-machine"

        save_task(FLOW_TASK_FILE, orig_fm, body)


class TestDispatchProfileRecording:
    """Integration tests for --profile dispatch recording to task cards."""

    PROFILE_TASK_ID = "phase10-profile-enforcement-03"

    def _find_profile_task(self) -> tuple[Path, dict, str]:
        from coordination_common import find_task
        return find_task(self.PROFILE_TASK_ID)

    def _run_dispatch(self, extra_args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable, str(SCRIPT),
            "--task-id", self.PROFILE_TASK_ID,
            "--owner", "test-agent",
            "--allow-terminal",
        ]
        cmd.extend(extra_args)
        return subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=str(ROOT),
        )

    def test_profile_name_dispatch_persists_canonical_name(self) -> None:
        """Mutating dispatch with --profile writes canonical profile_name to task card."""
        path, orig_fm, body = self._find_profile_task()
        orig_profile = orig_fm.get("profile")
        try:
            result = self._run_dispatch(["--profile", "rental-rebuild"])
            assert result.returncode == 0
            assert "profile: rental-rebuild" in result.stdout

            from coordination_common import load_task
            updated_fm, _ = load_task(path)
            assert updated_fm["profile"] == "rental-rebuild"
        finally:
            from coordination_common import save_task
            if orig_profile:
                orig_fm["profile"] = orig_profile
            else:
                orig_fm.pop("profile", None)
            save_task(path, orig_fm, body)

    def test_profile_path_persists_canonical_name(self) -> None:
        """Mutating dispatch with --profile <path> writes canonical profile_name."""
        from coordination_common import load_task, save_task
        path, orig_fm, body = self._find_profile_task()
        orig_profile = orig_fm.get("profile")
        profile_file = str(PROFILES_DIR / "rental-rebuild-profile.md")
        try:
            result = self._run_dispatch(["--profile", profile_file])
            assert result.returncode == 0

            updated_fm, _ = load_task(path)
            assert updated_fm["profile"] == "rental-rebuild"
        finally:
            if orig_profile:
                orig_fm["profile"] = orig_profile
            else:
                orig_fm.pop("profile", None)
            save_task(path, orig_fm, body)

    def test_message_only_profile_does_not_write_metadata(self) -> None:
        """--message-only --profile must not write profile to task card."""
        path, orig_fm, body = self._find_profile_task()
        from coordination_common import load_task

        result = self._run_dispatch(["--message-only", "--profile", "rental-rebuild"])
        assert result.returncode == 0
        assert "Profile context: rental-rebuild" in result.stdout

        updated_fm, _ = load_task(path)
        assert updated_fm.get("profile") == orig_fm.get("profile")

    def test_invalid_profile_fails_before_mutation(self) -> None:
        """Unknown profile fails with error and no task card mutation."""
        path, orig_fm, body = self._find_profile_task()
        from coordination_common import load_task

        result = self._run_dispatch(["--profile", "nonexistent-profile-xyz"])
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

        updated_fm, _ = load_task(path)
        assert updated_fm.get("profile") == orig_fm.get("profile")

    def test_no_profile_retains_existing_profile(self) -> None:
        """Dispatch without --profile does not overwrite existing profile field."""
        path, orig_fm, body = self._find_profile_task()
        from coordination_common import save_task, load_task

        # Set a profile first
        orig_fm["profile"] = "rental-rebuild"
        save_task(path, orig_fm, body)

        try:
            result = self._run_dispatch([])
            assert result.returncode == 0

            updated_fm, _ = load_task(path)
            assert updated_fm["profile"] == "rental-rebuild"
        finally:
            orig_fm.pop("profile", None)
            save_task(path, orig_fm, body)
