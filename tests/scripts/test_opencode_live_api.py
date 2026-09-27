from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from opencode_live_api import build_task_prompt, normalize_permission_request, permission_reply_request, select_pending_permission


def valid_task():
    return {
        "task_id": "phase-x-01", "objective": "Implement bounded code changes.", "context": "Use the assigned repository state.",
        "constraints": ["Do not launch external services."], "allowed_scope": ["scripts/**"],
        "forbidden_scope": ["credentials", "merge"], "acceptance": ["The payload is exact and bounded."],
        "validation": ["Run the focused checks."],
    }


def valid_request():
    return {"id": "per_123", "sessionID": "ses_123", "permission": "read", "patterns": ["src/**"], "metadata": {"raw": "not returned"}, "always": []}


def test_task_prompt_is_stable_bounded_and_rejects_extra_or_secret_material():
    task = valid_task()
    rendered = build_task_prompt(task)
    assert rendered and rendered == build_task_prompt(task)
    assert "Implement bounded code changes." in rendered and "credentials" in rendered
    assert build_task_prompt({**task, "api_key": "secret"}) is None
    assert build_task_prompt({**task, "objective": "Use sk-1234567890123456789012345678"}) is None
    for value in ("password=hunter2", "Authorization: Basic dXNlcjpwYXNz", "AWS_SECRET_ACCESS_KEY=abcd", "OPENAI_TOKEN=abc123", "CREDENTIAL=abc123", '{"token": "abc123"}'):
        assert build_task_prompt({**task, "context": value}) is None
    assert build_task_prompt(task, max_bytes=10) is None


def test_permission_schema_normalizes_only_safe_binding_fields_and_hides_metadata():
    pending = normalize_permission_request(valid_request())
    assert pending and pending["session_id"] == "ses_123" and pending["permission_id"] == "per_123"
    assert pending["action"] == "read" and len(pending["resource_digest"]) == 64
    assert "metadata" not in repr(pending) and "patterns" not in repr(pending)
    assert normalize_permission_request({**valid_request(), "resources": []}) is None
    assert normalize_permission_request({**valid_request(), "tool": {"messageID": "msg_1", "callID": "call_1"}})
    assert normalize_permission_request({**valid_request(), "tool": {"messageID": "msg_1"}}) is None
    assert normalize_permission_request({**valid_request(), "id": "x"}) is None
    assert normalize_permission_request({**valid_request(), "sessionID": "x"}) is None


def test_get_permission_array_selects_exact_request_and_rejects_bad_neighbors_or_duplicates():
    raw = valid_request()
    selected = select_pending_permission([raw, {**raw, "id": "per_other", "sessionID": "ses_other"}], "ses_123", "per_123")
    assert selected and selected["permission_id"] == "per_123"
    assert select_pending_permission([raw, raw], "ses_123", "per_123") is None
    assert select_pending_permission([raw, {**raw, "id": "x"}], "ses_123", "per_123") is None


def test_modern_permission_reply_request_is_exact_and_loopback_only():
    assert permission_reply_request("http://127.0.0.1:4096", "per_123") == {
        "method": "POST", "url": "http://127.0.0.1:4096/permission/per_123/reply", "json": {"reply": "once"},
    }
    for origin in ("http://localhost:4096", "http://127.0.0.1:4096/path", "https://127.0.0.1:4096", "http://127.0.0.1:65536"):
        assert permission_reply_request(origin, "per_123") is None
