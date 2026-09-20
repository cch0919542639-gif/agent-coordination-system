from copy import deepcopy
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_opencode_launch_projection import _identity, _request_projection, build_nonsecret_launch_projection, validate_nonsecret_launch_projection
from local_opencode_live_runner import PINNED_LAUNCHER, PINNED_RUNTIME_CONTENT_DIGEST, PINNED_WRAPPER_CONTENT_DIGEST


def draft():
    bindings = []
    for number in range(1, 7):
        agent = f"agent-{number:02d}"
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "heartbeat_interval_seconds": 5, "missed_heartbeat_threshold": 2, "per_child_hard_ceiling_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    return {"action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-29", "one_shot": True, "enabled": True, "issued_at": "2026-09-20T00:00:00+00:00", "expires_at": "2026-09-20T02:00:00+00:00", "run_window_start": "2026-09-20T00:30:00+00:00", "run_window_end": "2026-09-20T01:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "network_provider_exception": {"enabled": True, "network_access": "configured_model_service_only", "provider_configuration": "existing_local_opaque", "environment_keys": ["OPENCODE_PROJECT_WORKTREE"]}, "prohibited_actions": ["cleanup", "merge", "push"]}


def reviewed(source):
    return [{key: binding[key] for key in ("agent_id", "worktree_ref", "manifest_digest", "allocation_digest")} for binding in source["bindings"]]


def launcher():
    return {"runtime_id": "opencode", "launcher_id": PINNED_LAUNCHER["launcher_id"], "powershell_identity": "windows-powershell-v1", "wrapper_content_digest": PINNED_WRAPPER_CONTENT_DIGEST, "runtime_content_digest": PINNED_RUNTIME_CONTENT_DIGEST}


def test_projection_is_deterministic_nonsecret_and_runner_shaped_without_a_spawn_seam():
    source = draft()
    result = build_nonsecret_launch_projection(source, reviewed(source), launcher())
    assert result["decision"] == "projected_nonsecret_no_runtime" and validate_nonsecret_launch_projection(result)
    projection = result["projection"]
    assert len(projection["requests"]) == len(projection["binding_records"]) == 6
    assert projection["project_context_key_names"] == ("OPENCODE_PROJECT_WORKTREE",)
    rendered = repr(projection)
    for excluded in ("approval_id", "launch_id", "wrapper_path", "powershell_path", "provider_configuration", "network_access", "'argv_allowlist':", "'run'", "'restricted'"):
        assert excluded not in rendered


def test_missing_malformed_secret_or_crosswired_input_denies_without_a_projection():
    source = draft()
    crosswired = reviewed(source)
    crosswired[0]["allocation_digest"] = crosswired[1]["allocation_digest"]
    unsafe = deepcopy(source)
    unsafe["run_id"] = "token-bearer"
    malformed = deepcopy(source)
    malformed["bindings"][0]["worktree_ref"] = "worktrees/pilot/../agent-01"
    for bad_draft, identities, bad_launcher in ((unsafe, reviewed(source), launcher()), (malformed, reviewed(source), launcher()), (source, crosswired, launcher()), (source, reviewed(source), {**launcher(), "runtime_content_digest": "0" * 64})):
        result = build_nonsecret_launch_projection(bad_draft, identities, bad_launcher)
        assert result["decision"].startswith("deny_") and "projection" not in result


def test_validator_rejects_tampered_output_and_source_has_no_runtime_or_process_access():
    source = draft()
    result = build_nonsecret_launch_projection(source, reviewed(source), launcher())
    tampered = deepcopy(result)
    tampered["projection"]["binding_records"][0]["worktree_ref"] = "worktrees/pilot/agent-02"
    assert not validate_nonsecret_launch_projection(tampered)
    module_source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_launch_projection.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen(", "run_live_opencode_once", "run_opencode_once", "os.environ", "shutil.which", "socket", "urllib"):
        assert token not in module_source


def test_validator_rejects_a_recomputed_crosswired_worktree_request_against_the_reviewed_mapping():
    source = draft()
    result = build_nonsecret_launch_projection(source, reviewed(source), launcher())
    tampered = deepcopy(result)
    record = tampered["projection"]["binding_records"][0]
    record["worktree_ref"] = "worktrees/pilot/agent-99"
    record["binding_id"] = _identity({key: record[key] for key in record if key not in {"binding_id", "control_level", "process_tree_stop_handling"}})
    tampered["projection"]["requests"][0] = _request_projection(record)
    assert not validate_nonsecret_launch_projection(tampered)
