from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from supervised_launch_validation import PILOT_BINDINGS, manifest_digest, validate_supervised_inputs


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def valid_manifest(*, mode: str = "dry_run") -> dict[str, object]:
    manifest: dict[str, object] = {
        **PILOT_BINDINGS,
        "manifest_id": "manifest-01",
        "run_id": "run-01",
        "task_id": "task-01",
        "inbox_payload_ref": "inbox-01",
        "executable_id": "opencode",
        "argv": ["a" * 64],
        "mode": mode,
        "timeout_seconds": 900,
        "enabled": True,
    }
    manifest["manifest_digest"] = manifest_digest(manifest)
    return manifest


def valid_inbox(manifest: dict[str, object]) -> dict[str, object]:
    return {key: manifest[key] for key in ("worker_id", "task_id", "project_id", "inbox_payload_ref")}


def valid_audit() -> dict[str, object]:
    return {"run_id": "run-01", "decision_category": "validated", "timeout_seconds": 900}


def valid_approval(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "approval_id": "approval-01",
        "manifest_id": manifest["manifest_id"],
        "manifest_digest": manifest["manifest_digest"],
        "run_id": manifest["run_id"],
        "approver_role": "ORCHESTRATOR",
        "issued_at": "2026-07-22T11:00:00Z",
        "expires_at": "2026-07-22T13:00:00Z",
        "mode": "supervised_one_shot",
        "enabled": True,
    }


def decide(manifest: object, approval: object = None, inbox: object = None, audit: object = None, **kwargs: object) -> dict[str, object]:
    if isinstance(manifest, dict) and all(key in manifest for key in ("worker_id", "task_id", "project_id", "inbox_payload_ref")):
        inbox = valid_inbox(manifest) if inbox is None else inbox
    return validate_supervised_inputs(manifest, approval, inbox, valid_audit() if audit is None else audit, now=NOW, **kwargs)


def test_valid_dry_run_returns_only_safe_values() -> None:
    result = decide(valid_manifest())
    assert result["decision"] == "dry_run_ready"
    assert result["dry_run"] is True
    assert "branch" not in result and "worktree_ref" not in result and "argv" not in result


def test_valid_supervised_request_still_cannot_execute() -> None:
    manifest = valid_manifest(mode="supervised_one_shot")
    assert decide(manifest, valid_approval(manifest))["decision"] == "supervised_launch_requires_future_executor"


def test_missing_malformed_altered_and_disabled_manifest_fail_closed() -> None:
    assert decide(None)["decision"] == "deny_missing_manifest"
    assert decide({"manifest_id": "x"})["decision"] == "deny_invalid_manifest"
    manifest = valid_manifest()
    manifest["task_id"] = "altered"
    assert decide(manifest)["decision"] == "deny_invalid_manifest"
    manifest = valid_manifest()
    manifest["enabled"] = False
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_disabled"
    assert decide(valid_manifest(), global_enabled=False)["decision"] == "deny_disabled"


def test_inbox_provenance_allowlist_timeout_and_audit_rejections() -> None:
    manifest = valid_manifest()
    assert decide(manifest, inbox={})["decision"] == "deny_inbox"
    inbox = valid_inbox(manifest)
    inbox["worker_id"] = "other"
    assert decide(manifest, inbox=inbox)["decision"] == "deny_inbox"
    manifest = valid_manifest()
    manifest["project_id"] = "other"
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_provenance_mismatch"
    manifest = valid_manifest()
    manifest["worktree_ref"] = "other"
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_worktree_mismatch"
    manifest = valid_manifest()
    manifest["runtime_id"] = "other"
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_allowlist"
    manifest = valid_manifest()
    manifest["executable_id"] = "other"
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_allowlist"
    manifest = valid_manifest()
    manifest["timeout_seconds"] = 901
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest)["decision"] == "deny_invalid_manifest"
    assert decide(valid_manifest(), audit={"credential": "not-allowed"})["decision"] == "deny_invalid_audit"


def test_extra_or_shell_like_argv_is_rejected_before_supervised_gate() -> None:
    manifest = valid_manifest(mode="supervised_one_shot")
    manifest["argv"] = ["a" * 64, "b" * 64]
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest, valid_approval(manifest))["decision"] == "deny_invalid_manifest"
    manifest = valid_manifest(mode="supervised_one_shot")
    manifest["argv"] = [";unsafe-extra"]
    manifest["manifest_digest"] = manifest_digest(manifest)
    assert decide(manifest, valid_approval(manifest))["decision"] == "deny_invalid_manifest"


def test_missing_expired_or_mismatched_approval_denies_supervised_request() -> None:
    manifest = valid_manifest(mode="supervised_one_shot")
    assert decide(manifest)["decision"] == "deny_approval"
    approval = valid_approval(manifest)
    approval["manifest_id"] = "other"
    assert decide(manifest, approval)["decision"] == "deny_approval"
    approval = valid_approval(manifest)
    approval["expires_at"] = "2026-07-22T11:30:00Z"
    assert decide(manifest, approval)["decision"] == "deny_approval"


def test_source_contains_no_execution_or_operational_artifact_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "supervised_launch_validation.py").read_text(encoding="utf-8")
    assert all(token not in source for token in ("subprocess", "os.system", "Popen", "shell=True", "Path(", "open("))
