from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from bootstrap_handoff import (
    LAUNCH_AUTHORIZED,
    MAX_PAYLOAD_BYTES,
    SCHEMA_VERSION,
    SENSITIVITY_LABEL,
    approval_digest,
    build_handoff,
)


NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)


def valid_approval() -> dict[str, object]:
    approval: dict[str, object] = {
        "approval_id": "approval-bootstrap-01",
        "task_id": "phase14.5-bootstrap-01",
        "worker_id": "external-agent-platform-33",
        "worktree_ref": "worktrees/external-agent-platform-33/phase14.5-bootstrap-01",
        "issued_at": "2026-09-03T11:00:00Z",
        "expires_at": "2026-09-03T13:00:00Z",
        "approver_role": "ORCHESTRATOR",
        "one_shot": True,
        "enabled": True,
    }
    approval["approval_digest"] = approval_digest(approval)
    return approval


def valid_task_card() -> dict[str, object]:
    return {
        "task_id": "phase14.5-bootstrap-01",
        "phase": "phase14.5-bootstrap-connector",
        "status": "IN_PROGRESS",
        "owner": "external-agent-platform-33",
        "reviewer": "ORCHESTRATOR",
        "priority": "high",
        "dependencies": ["phase14.5-bootstrap-02"],
        "allowed_scope": ["scripts/**", "tests/scripts/**"],
        "forbidden_scope": ["services/**", "src/**"],
        "acceptance": ["Define and implement a local-only bootstrap handoff"],
    }


def WORKTREE_REF() -> str:
    return "worktrees/external-agent-platform-33/phase14.5-bootstrap-01"


def test_valid_one_shot_handoff_is_prepared() -> None:
    result = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "handoff_prepared"
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["one_shot"] is True
    assert result["launch_authorized"] is LAUNCH_AUTHORIZED
    assert result["launch_authorized"] is False
    assert result["sensitivity_label"] == SENSITIVITY_LABEL
    assert result["max_payload_bytes"] == MAX_PAYLOAD_BYTES
    assert isinstance(result["content_digest"], str) and len(result["content_digest"]) == 64
    assert isinstance(result["idempotency_key"], str) and len(result["idempotency_key"]) == 64
    assert result["worker_id"] == "external-agent-platform-33"
    assert result["worktree_ref"] == WORKTREE_REF()
    assert result["task_id"] == "phase14.5-bootstrap-01"
    assert result["approval_id"] == "approval-bootstrap-01"
    assert isinstance(result["task_card_projection"], dict)
    assert result["task_card_projection"]["task_id"] == "phase14.5-bootstrap-01"
    assert isinstance(result["protocol_references"], list) and len(result["protocol_references"]) >= 2


def test_handoff_contains_only_safe_relative_paths() -> None:
    result = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "handoff_prepared"
    for ref in result["protocol_references"]:
        assert ".." not in ref
        assert not ref.startswith("/")
        assert not ref.startswith("\\")
    assert not result["worktree_ref"].startswith("/")
    assert not result["worktree_ref"].startswith("\\")
    assert ".." not in result["worktree_ref"]


def test_handoff_omits_sensitive_fields() -> None:
    result = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "handoff_prepared"
    for forbidden in ("credentials", "prompts", "source_bodies", "argv", "branch", "executable_id"):
        assert forbidden not in result


def test_expiry_denies_handoff() -> None:
    expired_now = datetime(2026, 9, 3, 14, 0, tzinfo=timezone.utc)
    result = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=expired_now)
    assert result["decision"] == "deny_approval_expired"


def test_not_yet_issued_denies_handoff() -> None:
    early_now = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
    result = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=early_now)
    assert result["decision"] == "deny_approval_expired"


def test_missing_approval_denies() -> None:
    result = build_handoff(None, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_missing_approval"


def test_disabled_approval_denies() -> None:
    approval = valid_approval()
    approval["enabled"] = False
    approval["approval_digest"] = approval_digest(approval)
    result = build_handoff(approval, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_disabled"


def test_altered_task_id_in_approval_denies() -> None:
    approval = valid_approval()
    approval["task_id"] = "wrong-task"
    approval["approval_digest"] = approval_digest(approval)
    result = build_handoff(approval, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_task_mismatch"


def test_altered_approval_digest_denies() -> None:
    approval = valid_approval()
    approval["approval_digest"] = "0" * 64
    result = build_handoff(approval, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_invalid_approval"


def test_mismatched_worktree_ref_denies() -> None:
    result = build_handoff(valid_approval(), valid_task_card(), "worktrees/wrong", now=NOW)
    assert result["decision"] == "deny_worktree_mismatch"


def test_altered_approver_role_denies() -> None:
    approval = valid_approval()
    approval["approver_role"] = "SELF"
    result = build_handoff(approval, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_invalid_approval"


def test_non_one_shot_denies() -> None:
    approval = valid_approval()
    approval["one_shot"] = False
    result = build_handoff(approval, valid_task_card(), WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_invalid_approval"


def test_duplicate_replay_denied() -> None:
    store: set[str] = set()
    result1 = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW, idempotency_store=store)
    assert result1["decision"] == "handoff_prepared"
    assert len(store) == 1
    result2 = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW, idempotency_store=store)
    assert result2["decision"] == "deny_replay"
    assert result2["idempotency_key"] == result1["idempotency_key"]


def test_idempotency_key_is_stable_for_same_inputs() -> None:
    r1 = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW)
    r2 = build_handoff(valid_approval(), valid_task_card(), WORKTREE_REF(), now=NOW)
    assert r1["idempotency_key"] == r2["idempotency_key"]
    assert r1["content_digest"] == r2["content_digest"]


def test_unsafe_absolute_path_in_dependency_ref_denies() -> None:
    result = build_handoff(
        valid_approval(),
        valid_task_card(),
        WORKTREE_REF(),
        dependency_evidence_refs=["/etc/passwd"],
        now=NOW,
    )
    assert result["decision"] == "deny_unsafe_path"


def test_windows_path_in_dependency_ref_denies() -> None:
    result = build_handoff(
        valid_approval(),
        valid_task_card(),
        WORKTREE_REF(),
        dependency_evidence_refs=["evidence\\outside"],
        now=NOW,
    )
    assert result["decision"] == "deny_unsafe_path"


def test_windows_drive_worktree_ref_denies() -> None:
    approval = valid_approval()
    approval["worktree_ref"] = "C:\\outside"
    approval["approval_digest"] = approval_digest(approval)
    result = build_handoff(approval, valid_task_card(), "C:\\outside", now=NOW)
    assert result["decision"] == "deny_unsafe_path"


def test_unsafe_dotdot_path_in_dependency_ref_denies() -> None:
    result = build_handoff(
        valid_approval(),
        valid_task_card(),
        WORKTREE_REF(),
        dependency_evidence_refs=["../outside/scope"],
        now=NOW,
    )
    assert result["decision"] == "deny_unsafe_path"


def test_unsafe_absolute_worktree_ref_denies() -> None:
    result = build_handoff(valid_approval(), valid_task_card(), "/absolute/path", now=NOW)
    assert result["decision"] == "deny_worktree_mismatch"


def test_invalid_task_card_denies() -> None:
    result = build_handoff(valid_approval(), {}, WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_invalid_task"


def test_missing_task_card_denies() -> None:
    result = build_handoff(valid_approval(), None, WORKTREE_REF(), now=NOW)
    assert result["decision"] == "deny_invalid_task"


def test_source_contains_no_process_shell_or_network_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "bootstrap_handoff.py").read_text(encoding="utf-8")
    forbidden_tokens = ("subprocess", "os.system", "Popen", "shell=True", "os.popen", "socket", "urllib", "requests", "httpx")
    for token in forbidden_tokens:
        assert token not in source, f"forbidden token '{token}' found in source"


def test_source_contains_no_file_io_or_git_operations() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "bootstrap_handoff.py").read_text(encoding="utf-8")
    assert "open(" not in source
    assert "Path(" not in source
    assert "git " not in source
    assert "os.mkdir" not in source
    assert "os.makedirs" not in source
    assert "shutil" not in source


def test_runbook_documents_digest_and_current_dependency() -> None:
    runbook = Path(__file__).resolve().parents[2].joinpath(
        "docs", "operations", "phase14.5-bootstrap-handoff-operator-runbook.md"
    ).read_text(encoding="utf-8")
    assert "`approval_digest`" in runbook
    assert "phase14.5-bootstrap-02" in runbook
    assert "mismatched" in runbook
