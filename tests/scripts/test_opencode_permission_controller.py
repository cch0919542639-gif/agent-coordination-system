from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from opencode_permission_controller import reply_once


def binding():
    return {"task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-44", "approval_id": "approval-44", "agent_id": "agent-01", "grant_id": "grant-01", "session_id": "ses_01", "permission_id": "per_01", "action": "bash", "resource_digest": "a" * 64}


def pending():
    source = binding()
    return {key: source[key] for key in ("session_id", "permission_id", "action", "resource_digest")}


def test_exact_pending_permission_replies_once_without_remembering():
    calls = []
    result = reply_once(pending(), binding(), consumed=set(), reply=lambda session, permission, body: calls.append((session, permission, body)) is None)
    assert result["decision"] == "approved_once"
    assert calls == [("ses_01", "per_01", {"reply": "once"})]


def test_mismatch_malformed_and_replay_never_reply():
    calls, consumed = [], set()
    request = pending(); request["resource_digest"] = "b" * 64
    assert reply_once(request, binding(), consumed=consumed, reply=lambda *_: calls.append(1) or True)["decision"] == "deny_unbound_permission"
    malformed = binding(); malformed["extra"] = "x"
    assert reply_once(malformed, binding(), consumed=consumed, reply=lambda *_: calls.append(1) or True)["decision"] == "deny_invalid_permission"
    assert reply_once(pending(), binding(), consumed=consumed, reply=lambda *_: calls.append(1) or True)["decision"] == "approved_once"
    assert reply_once(pending(), binding(), consumed=consumed, reply=lambda *_: calls.append(1) or True)["decision"] == "deny_consumed_permission"
    assert calls == [1]


def test_malformed_or_cross_wired_resource_digest_never_replies():
    calls = []
    for digest in ("x", "g" * 64, "A" * 64):
        request = pending(); request["resource_digest"] = digest
        assert reply_once(request, binding(), consumed=set(), reply=lambda *_: calls.append(1) or True)["decision"] == "deny_invalid_permission"
    request = pending(); request["resource_digest"] = "b" * 64
    assert reply_once(request, binding(), consumed=set(), reply=lambda *_: calls.append(1) or True)["decision"] == "deny_unbound_permission"
    assert calls == []


def test_non_schema_session_and_permission_prefixes_never_reply():
    request, source = pending(), binding()
    calls = []
    for field, value in (("session_id", "x"), ("permission_id", "x")):
        malformed = dict(source); malformed[field] = value
        assert reply_once(request, malformed, consumed=set(), reply=lambda *_: calls.append(1) or True)["decision"] == "deny_invalid_permission"
    assert calls == []


def test_controller_has_no_transport_or_configuration_access():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "opencode_permission_controller.py").read_text(encoding="utf-8")
    for token in ("requests", "urllib", "socket", "subprocess", "Popen", "os.environ", "getenv", "open("):
        assert token not in source
