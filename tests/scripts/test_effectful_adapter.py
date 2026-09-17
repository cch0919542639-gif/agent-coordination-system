from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from controlplane_admission import grant_digest
from effectful_adapter import run_once


NOW = datetime.fromisoformat("2026-09-17T08:00:00+00:00")


class FakeProcess:
    def __init__(self, code=0, timeout=False, terminate_fails=False): self.code, self.timeout, self.terminate_fails, self.terminated = code, timeout, terminate_fails, False
    def wait(self, timeout):
        if self.timeout: raise TimeoutError()
        return self.code
    def terminate(self):
        self.terminated = True
        if self.terminate_fails: raise RuntimeError()


def inputs():
    request = {"task_id":"phase14.5-six-agent-pilot-08", "run_id":"run-01", "approval_id":"approval-01", "grant_id":"grant-01", "agent_id":"agent-01", "project_id":"project-01", "worktree_ref":"worktrees/agent-01/run-01", "timeout_seconds":30}
    approval = {"approval_id":"approval-01", "action":"external_runtime_launch", "task_id":request["task_id"], "run_id":"run-01", "grant_id":"grant-01", "agent_id":"agent-01", "worktree_ref":request["worktree_ref"], "issued_at":"2026-09-17T07:00:00+00:00", "expires_at":"2026-09-17T09:00:00+00:00", "enabled":True}
    grant = {"grant_id":"grant-01", "agent_id":"agent-01", "project_id":"project-01", "adapter_id":"effectful-adapter", "adapter_version":"v1", "allowed_task_classes":["external-runtime-pilot"], "max_concurrent_runs":1, "worktree_root":"worktrees/agent-01", "network_policy":"deny", "expires_at":"2026-09-17T09:00:00+00:00", "revoked":False, "enabled":True}
    grant["grant_digest"] = grant_digest(grant)
    attestation = {"attestation_id":"attest-01", "task_id":request["task_id"], "run_id":"run-01", "grant_id":"grant-01", "agent_id":"agent-01", "worktree_ref":request["worktree_ref"], "restricted_writes":True, "process_identity":True, "network_egress":"deny", "issued_at":"2026-09-17T07:00:00+00:00", "expires_at":"2026-09-17T09:00:00+00:00", "enabled":True}
    return request, approval, grant, attestation


def invoke(request=None, approval=None, grant=None, attestation=None, process=None, consumed=None):
    values = inputs(); request, approval, grant, attestation = (request or values[0], approval or values[1], grant or values[2], attestation or values[3])
    calls=[]; process = process or FakeProcess()
    result = run_once(request, approval, grant, attestation, now=NOW, consumed_run_ids=consumed if consumed is not None else set(), process_factory=lambda: calls.append(True) or process)
    return result, calls, process


def test_success_is_single_call_and_redacted():
    result, calls, _ = invoke()
    assert result["decision"] == "completed" and calls == [True]
    assert set(result) == {"decision", "dry_run", "task_id", "run_id", "approval_id", "grant_id", "agent_id", "timeout_seconds"}


def test_all_exact_binding_denials_skip_factory():
    for field, value in (("task_id", "other-task"), ("run_id", "other-run"), ("grant_id", "other-grant"), ("agent_id", "other-agent"), ("worktree_ref", "worktrees/agent-01/other")):
        request, approval, grant, attestation = inputs(); approval[field] = value
        result, calls, _ = invoke(request, approval, grant, attestation)
        assert result["decision"] == "deny_approval" and not calls


def test_grant_and_attestation_denials_skip_factory():
    request, approval, grant, attestation = inputs(); grant["network_policy"] = "allow"
    assert invoke(request, approval, grant, attestation)[0]["decision"] == "deny_invalid_grant"
    request, approval, grant, attestation = inputs(); attestation["network_egress"] = "deny"; attestation["restricted_writes"] = False
    assert invoke(request, approval, grant, attestation)[0]["decision"] == "deny_enforcement_attestation"


def test_malformed_and_expired_attestations_deny():
    request, approval, grant, attestation = inputs(); attestation["extra"] = "x"
    assert invoke(request, approval, grant, attestation)[0]["decision"] == "deny_enforcement_attestation"
    request, approval, grant, attestation = inputs(); attestation["expires_at"] = "2026-09-17T08:00:00+00:00"
    assert invoke(request, approval, grant, attestation)[0]["decision"] == "deny_enforcement_attestation"


def test_timeout_terminates_only_factory_process_and_consumes_run():
    consumed=set(); result, calls, process = invoke(process=FakeProcess(timeout=True), consumed=consumed)
    assert result["decision"] == "stopped_timeout" and calls == [True] and process.terminated and consumed == {"run-01"}


def test_termination_failure_is_safe_and_consumed():
    consumed=set(); result, _, _ = invoke(process=FakeProcess(timeout=True, terminate_fails=True), consumed=consumed)
    assert result["decision"] == "stopped_safety_signal" and consumed == {"run-01"}


def test_duplicate_run_never_calls_factory():
    result, calls, _ = invoke(consumed={"run-01"})
    assert result["decision"] == "deny_duplicate_run" and not calls


def test_source_has_no_network_runtime_or_secret_apis():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "effectful_adapter.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "credentials", "argv"):
        assert token not in source
