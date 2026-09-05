from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from controlplane_admission import grant_digest
from supervised_opencode_launcher import PILOT, manifest_digest, prepare, run_once


NOW = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)


def manifest() -> dict[str, object]:
    value: dict[str, object] = {**PILOT, "manifest_id": "manifest-01", "run_id": "run-01", "task_id": "pilot-01", "executable_id": "opencode", "argv": ["opencode", "task-token"], "timeout_seconds": 60, "mode": "supervised_one_shot", "enabled": True}
    value["manifest_digest"] = manifest_digest(value)
    return value


def approval(value: dict[str, object]) -> dict[str, object]:
    return {"approval_id": "approval-01", "manifest_id": value["manifest_id"], "manifest_digest": value["manifest_digest"], "run_id": value["run_id"], "approver_role": "ORCHESTRATOR", "issued_at": "2026-09-06T08:59:00Z", "expires_at": "2026-09-06T09:01:00Z", "mode": "supervised_one_shot", "enabled": True}


def grant() -> dict[str, object]:
    value: dict[str, object] = {"grant_id": "grant-01", "agent_id": "external-agent-platform-33", "project_id": "agent-coordination-system", "adapter_id": "opencode", "adapter_version": "1", "allowed_task_classes": ["external-runtime-pilot"], "max_concurrent_runs": 1, "worktree_root": "worktrees", "network_policy": "deny", "expires_at": "2026-09-06T10:00:00Z", "revoked": False, "enabled": True, "one_shot": True}
    value["grant_digest"] = grant_digest(value)
    return value


def task() -> dict[str, object]:
    return {"task_id": "pilot-01", "project_id": "agent-coordination-system", "owner": "external-agent-platform-33", "task_class": "external-runtime-pilot", "branch": PILOT["branch"], "worktree_path": PILOT["worktree_ref"], "dependencies": ["phase14.5-controlplane-02"]}


def options(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {"done_task_ids": {"phase14.5-controlplane-02"}, "active_agent_ids": set(), "existing_owners": {}, "consumed_run_ids": set(), "now": NOW}
    value.update(extra)
    return value


class FakeProcess:
    def __init__(self, result: int = 0, timeout: bool = False) -> None:
        self.result, self.timeout, self.calls, self.terminated = result, timeout, 0, False
        self.returncode: int | None = None

    def wait(self, timeout: int) -> int:
        self.calls += 1
        if self.timeout:
            raise TimeoutError
        self.returncode = self.result
        return self.result

    def terminate(self) -> None:
        self.terminated = True


def test_exact_bound_request_is_launch_ready_without_process() -> None:
    assert prepare(manifest(), approval(manifest()), grant(), task(), **options())["decision"] == "launch_ready"


def test_denials_never_call_process_factory() -> None:
    calls: list[tuple[str, ...]] = []
    value = manifest(); value["manifest_digest"] = "0" * 64
    result = run_once(value, approval(value), grant(), task(), **options(), process_factory=lambda argv: calls.append(argv))
    assert result["decision"] == "deny_invalid_manifest" and calls == []


def test_expired_revoked_mismatched_and_duplicate_inputs_deny() -> None:
    value = manifest(); bad_approval = approval(value); bad_approval["expires_at"] = "2026-09-06T08:59:00Z"
    assert prepare(value, bad_approval, grant(), task(), **options())["decision"] == "deny_approval"
    stale_approval = approval(value); stale_approval["issued_at"] = "2026-09-06T08:54:00Z"
    assert prepare(value, stale_approval, grant(), task(), **options())["decision"] == "deny_approval"
    bad_grant = grant(); bad_grant["revoked"] = True; bad_grant["grant_digest"] = grant_digest(bad_grant)
    assert prepare(value, approval(value), bad_grant, task(), **options())["decision"] == "deny_revoked_grant"
    assert prepare(value, approval(value), grant(), task(), **options(consumed_run_ids={"run-01"}))["decision"] == "deny_duplicate"
    bad_task = task(); bad_task["owner"] = "other"
    assert prepare(value, approval(value), grant(), bad_task, **options())["decision"] == "deny_identity_mismatch"


def test_disabled_stop_capacity_and_nonallowlisted_inputs_deny() -> None:
    value = manifest(); value["enabled"] = False; value["manifest_digest"] = manifest_digest(value)
    assert prepare(value, approval(value), grant(), task(), **options())["decision"] == "deny_disabled"
    assert prepare(manifest(), approval(manifest()), grant(), task(), **options(stop_requested=True))["decision"] == "stopped_safety_signal"
    assert prepare(manifest(), approval(manifest()), grant(), task(), **options(active_agent_ids={"x"}))["decision"] == "deny_capacity"
    value = manifest(); value["executable_id"] = "other"; value["manifest_digest"] = manifest_digest(value)
    assert prepare(value, approval(value), grant(), task(), **options())["decision"] == "deny_allowlist"


def test_one_process_success_and_safe_result() -> None:
    process = FakeProcess(); received: list[tuple[str, ...]] = []
    result = run_once(manifest(), approval(manifest()), grant(), task(), **options(), process_factory=lambda argv: received.append(argv) or process)
    assert result["decision"] == "completed" and received == [("opencode", "task-token")] and process.calls == 1
    assert "argv" not in result and "worktree_ref" not in result


def test_timeout_and_nonzero_are_terminal_and_single_process() -> None:
    for process, expected in ((FakeProcess(timeout=True), "stopped_timeout"), (FakeProcess(result=7), "stopped_nonzero_exit")):
        result = run_once(manifest(), approval(manifest()), grant(), task(), **options(), process_factory=lambda argv, p=process: p)
        assert result["decision"] == expected and process.calls == 1
    assert process.terminated is False
    timeout = FakeProcess(timeout=True)
    run_once(manifest(), approval(manifest()), grant(), task(), **options(), process_factory=lambda argv: timeout)
    assert timeout.terminated is True


def test_manifest_rejects_shellish_argv_and_sensitive_fields() -> None:
    value = manifest(); value["argv"] = ["opencode", ";unsafe"]; value["manifest_digest"] = manifest_digest(value)
    assert prepare(value, approval(value), grant(), task(), **options())["decision"] == "deny_invalid_manifest"
    value = manifest(); value["token"] = "forbidden"; value["manifest_digest"] = manifest_digest(value)
    assert prepare(value, approval(value), grant(), task(), **options())["decision"] == "deny_invalid_manifest"


def test_source_has_no_filesystem_network_shell_or_real_process_factory() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "supervised_opencode_launcher.py").read_text(encoding="utf-8")
    for token in ("subprocess", "os.system", "shell=True", "Path(", "open(", "socket", "requests", "urllib", "Popen"):
        assert token not in source
