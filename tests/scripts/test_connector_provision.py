from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from connector_provision import provision_connectors
from controlplane_admission import grant_digest


NOW = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
AGENTS = [f"agent-{number:02d}" for number in range(1, 7)]


def inputs():
    approval = {"approval_id":"phaseh-approval-01", "action":"external_runtime_launch", "task_id":"phase14.5-six-agent-pilot-08", "run_id":"phaseh-run-01", "one_shot":True, "enabled":True, "issued_at":"2026-09-17T07:59:00+00:00", "expires_at":"2026-09-17T09:00:00+00:00", "run_window_start":"2026-09-17T08:00:00+00:00", "run_window_end":"2026-09-17T08:30:00+00:00", "timeout_seconds":900, "stop_authority":"operator-01", "grant_ids":[f"grant-{agent}" for agent in AGENTS], "agent_ids":list(AGENTS), "worktree_root":"worktrees/phaseh", "worktree_refs":[f"worktrees/phaseh/{agent}" for agent in AGENTS], "network_policy":"deny", "adapter_id":"opencode", "adapter_version":"1", "enforcement_evidence_refs":[f"coordination/evidence/{agent}" for agent in AGENTS], "manifest_digests":[f"{number:064x}" for number in range(1, 7)], "allocation_digests":[f"{number:064x}" for number in range(7, 13)], "prohibited_actions":["cleanup", "credential_access", "merge", "push"]}
    grants = []
    evidence = []
    for agent, grant_id, worktree, ref in zip(approval["agent_ids"], approval["grant_ids"], approval["worktree_refs"], approval["enforcement_evidence_refs"]):
        grant = {"grant_id":grant_id, "agent_id":agent, "project_id":"project-01", "adapter_id":"opencode", "adapter_version":"1", "allowed_task_classes":["external-runtime-pilot"], "max_concurrent_runs":1, "worktree_root":"worktrees/phaseh", "network_policy":"deny", "expires_at":"2026-09-17T09:00:00+00:00", "revoked":False, "enabled":True}
        grant["grant_digest"] = grant_digest(grant)
        grants.append(grant)
        evidence.append({"enforcement_evidence_ref":ref, "attestation":{"attestation_id":f"attest-{agent}", "task_id":"phase14.5-six-agent-pilot-08", "run_id":"phaseh-run-01", "grant_id":grant_id, "agent_id":agent, "worktree_ref":worktree, "restricted_writes":True, "process_identity":True, "network_egress":"deny", "issued_at":"2026-09-17T07:59:00+00:00", "expires_at":"2026-09-17T09:00:00+00:00", "enabled":True}})
    adapter = {"adapter_id":"opencode", "adapter_version":"1", "task_id":"phase14.5-effectful-adapter-09", "review_decision":"accepted", "review_ref":"coordination/reviews/effectful-adapter-09", "implementation_ref":"scripts/effectful-adapter-09", "enforcement_capability":"sandboxed_one_shot", "reviewed_commit":"f" * 64, "expires_at":"2026-09-17T09:00:00+00:00"}
    return approval, grants, evidence, adapter


def invoke(approval=None, grants=None, evidence=None, adapter=None):
    original = inputs()
    return provision_connectors(approval or original[0], grants or original[1], evidence or original[2], adapter or original[3], now=NOW)


def test_provisions_exactly_six_deterministic_redacted_records_without_runtime():
    first = invoke(); second = invoke()
    assert first == second and first["decision"] == "provisioned_no_runtime"
    records = first["records"]
    assert isinstance(records, list) and len(records) == 6
    assert {record["agent_id"] for record in records} == set(AGENTS)
    assert all(set(record) == {"task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref", "network_policy", "adapter_id", "adapter_version", "enforcement_evidence_ref", "attestation_id", "manifest_digest", "allocation_digest", "admitted", "enforcement_verified"} for record in records)
    assert "credential" not in repr(records).lower() and "prompt" not in repr(records).lower() and "source" not in repr(records).lower()


def test_invalid_approval_adapter_and_grant_bindings_deny_without_records():
    approval, grants, evidence, adapter = inputs(); approval["command"] = "unsafe"
    assert invoke(approval, grants, evidence, adapter) == {"decision": "deny_invalid_approval"}
    approval, grants, evidence, adapter = inputs(); adapter["adapter_version"] = "2"
    assert invoke(approval, grants, evidence, adapter) == {"decision": "deny_effectful_adapter_evidence"}
    approval, grants, evidence, adapter = inputs(); grants[0]["agent_id"] = "agent-02"
    assert invoke(approval, grants, evidence, adapter) == {"decision": "deny_connector_bindings"}


def test_duplicate_stale_cross_wired_or_unsafe_bindings_fail_closed():
    approval, grants, evidence, adapter = inputs(); grants[1] = deepcopy(grants[0])
    assert invoke(approval, grants, evidence, adapter)["decision"] == "deny_connector_bindings"
    approval, grants, evidence, adapter = inputs(); evidence[0]["attestation"]["expires_at"] = "2026-09-17T08:00:00+00:00"
    assert invoke(approval, grants, evidence, adapter)["decision"] == "deny_platform_enforcement"
    approval, grants, evidence, adapter = inputs(); evidence[0]["attestation"]["worktree_ref"] = "worktrees/phaseh/agent-02"
    assert invoke(approval, grants, evidence, adapter)["decision"] == "deny_platform_enforcement"
    approval, grants, evidence, adapter = inputs(); approval["worktree_refs"][0] = "worktrees/./phaseh/agent-01"
    assert invoke(approval, grants, evidence, adapter) == {"decision": "deny_invalid_approval"}


def test_missing_or_unrepresentable_platform_enforcement_returns_bounded_incident():
    approval, grants, evidence, adapter = inputs()
    assert invoke(approval, grants, evidence[:5], adapter)["incident"] == {"category":"capability_mismatch", "task_id":"phase14.5-six-agent-pilot-08", "run_id":"phaseh-run-01", "approval_id":"phaseh-approval-01"}
    evidence[0]["attestation"]["network_egress"] = "allow"
    assert invoke(approval, grants, evidence, adapter)["decision"] == "deny_platform_enforcement"


def test_source_has_no_runtime_network_filesystem_or_secret_apis():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "connector_provision.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "credentials", "argv", "write_"):
        assert token not in source
