from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from launcher_dry_run import EXPECTED, decide


def valid() -> tuple[dict, dict]:
    manifest = {**EXPECTED, "run_id": "run-1", "task_id": "pilot-1", "manifest_id": "m-1", "enabled": True, "executable": "opencode", "mode": "dry_run"}
    return manifest, {"worker_id": "external-agent-platform-33", "task_id": "pilot-1"}


def test_ready_is_safe_and_deterministic() -> None:
    manifest, inbox = valid()
    assert decide(manifest, inbox) == {"decision": "dry_run_ready", "dry_run": True, "runtime": "opencode", "task_id": "pilot-1", "run_id": "run-1"}


def test_missing_or_malformed_inputs_fail_closed() -> None:
    manifest, _ = valid()
    assert decide(None, {})["decision"] == "deny_missing_manifest"
    assert decide({"run_id": "x"}, {})["decision"] == "deny_invalid_manifest"
    assert decide(manifest, None)["decision"] == "deny_inbox"
    assert decide(manifest, {})["decision"] == "deny_inbox"


def test_disabled_allowlist_approval_and_provenance_fail_closed() -> None:
    manifest, inbox = valid()
    assert decide(manifest, inbox, disabled=True)["decision"] == "deny_disabled"
    manifest["executable"] = "other"
    assert decide(manifest, inbox)["decision"] == "deny_allowlist"
    manifest["executable"], manifest["mode"] = "opencode", "supervised_one_shot"
    assert decide(manifest, inbox)["decision"] == "deny_approval"
    manifest["mode"], manifest["worktree"] = "dry_run", "wrong"
    assert decide(manifest, inbox)["decision"] == "deny_worktree_mismatch"
    manifest, inbox = valid()
    manifest["branch"] = "wrong"
    assert decide(manifest, inbox)["decision"] == "deny_provenance_mismatch"


def test_worker_and_safety_signals_fail_closed() -> None:
    manifest, inbox = valid()
    inbox["worker_id"] = "wrong"
    assert decide(manifest, inbox)["decision"] == "deny_provenance_mismatch"
    for signal, decision in (("timeout", "stopped_timeout"), ("nonzero_exit", "stopped_nonzero_exit"), ("credential_prompt", "stopped_safety_signal"), ("monitor_anomaly", "stopped_safety_signal")):
        manifest, inbox = valid()
        manifest["safety_signal"] = signal
        assert decide(manifest, inbox)["decision"] == decision


def test_source_has_no_process_launch_api() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "launcher_dry_run.py").read_text(encoding="utf-8")
    assert "subprocess" not in source and "os.system" not in source and "Popen" not in source
