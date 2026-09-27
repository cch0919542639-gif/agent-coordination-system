from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from one_shot_consumption import consume_once, has_claim


def test_claim_persists_across_calls_without_storing_raw_identity(tmp_path):
    identity = {"run_id": "run-1", "approval_id": "approval-1", "agent_id": "agent-1", "grant_id": "grant-1"}
    assert consume_once(tmp_path, "binding", identity)
    assert not consume_once(tmp_path, "binding", dict(identity))
    record = next(tmp_path.glob("binding-*.json"))
    content = record.read_text(encoding="ascii")
    assert "identity_sha256" in content and "approval-1" not in content


def test_separate_approved_bindings_and_permission_identities_are_independent(tmp_path):
    assert consume_once(tmp_path, "binding", {"run_id": "run-1", "agent_id": "agent-1"})
    assert consume_once(tmp_path, "binding", {"run_id": "run-1", "agent_id": "agent-2"})
    assert consume_once(tmp_path, "permission", {"run_id": "run-1", "permission_id": "per-1"})


def test_session_claim_can_be_verified_without_reconsuming_or_exposing_identity(tmp_path):
    identity = {"task_id": "task-01", "run_id": "run-01", "approval_id": "approval-01", "agent_id": "agent-01", "grant_id": "grant-01", "session_id": "ses_01", "permission_policy_digest": "a" * 64}
    assert not has_claim(tmp_path, "session", identity)
    assert consume_once(tmp_path, "session", identity)
    assert has_claim(tmp_path, "session", identity)
    assert not has_claim(tmp_path, "session", {**identity, "session_id": "ses_foreign"})
    assert not consume_once(tmp_path, "session", identity)
    marker = next(tmp_path.glob("session-*.json"))
    assert "task-01" not in marker.read_text(encoding="ascii")


def test_exact_duplicate_race_has_one_winner(tmp_path):
    identity = {"run_id": "run-2", "approval_id": "approval-2"}
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: consume_once(tmp_path, "approval", identity), range(24)))
    assert sum(results) == 1


def test_malformed_identity_symlink_and_path_errors_fail_closed(tmp_path):
    assert not consume_once(tmp_path, "unknown", {"run_id": "run-1"})
    assert not consume_once(tmp_path, [], {"run_id": "run-1"})
    assert not consume_once(tmp_path, "approval", {"run_id": "bad id"})
    not_directory = tmp_path / "file"
    not_directory.write_text("x", encoding="ascii")
    assert not consume_once(not_directory, "approval", {"run_id": "run-3"})
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable to this Windows account.")
    assert not consume_once(link, "approval", {"run_id": "run-4"})
