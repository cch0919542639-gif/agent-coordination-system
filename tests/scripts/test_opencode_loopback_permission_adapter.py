from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from opencode_loopback_permission_adapter import reply_loopback_once
from opencode_live_api import normalize_permission_request


ORIGIN = "http://127.0.0.1:4096"
RAW = {"id": "per_01", "sessionID": "ses_01", "permission": "bash", "patterns": ["git status"], "metadata": {}, "always": []}


def binding():
    pending = normalize_permission_request(RAW)
    return {"task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-45", "approval_id": "approval-45", "agent_id": "agent-01", "grant_id": "grant-01", **pending}


def test_exact_loopback_request_delegates_once_without_remembering():
    calls = []
    result = reply_loopback_once(ORIGIN, binding(), consumed=set(), fetch=lambda *_: [RAW], send=lambda request: calls.append(request) is None)
    assert result["decision"] == "approved_once"
    assert calls == [{"method": "POST", "url": f"{ORIGIN}/permission/per_01/reply", "json": {"reply": "once"}}]


def test_nonloopback_malformed_mismatch_and_replay_never_send():
    calls, consumed = [], set()
    send = lambda *_: calls.append(1) or True
    assert reply_loopback_once("http://localhost:4096", binding(), consumed=consumed, fetch=lambda *_: [RAW], send=send)["decision"] == "deny_invalid_loopback"
    bad = {**RAW, "metadata": []}
    assert reply_loopback_once(ORIGIN, binding(), consumed=consumed, fetch=lambda *_: [bad], send=send)["decision"] == "deny_invalid_permission"
    mismatch = {**RAW, "patterns": ["git diff"]}
    assert reply_loopback_once(ORIGIN, binding(), consumed=consumed, fetch=lambda *_: [mismatch], send=send)["decision"] == "deny_unbound_permission"
    assert reply_loopback_once(ORIGIN, binding(), consumed=consumed, fetch=lambda *_: [RAW], send=send)["decision"] == "approved_once"
    assert reply_loopback_once(ORIGIN, binding(), consumed=consumed, fetch=lambda *_: [RAW], send=send)["decision"] == "deny_consumed_permission"
    assert calls == [1]


def test_unicode_loopback_ports_never_fetch_or_send():
    calls = []
    for origin in ("http://127.0.0.1:１２３", "http://127.0.0.1:²"):
        assert reply_loopback_once(origin, binding(), consumed=set(), fetch=lambda *_: calls.append("fetch") or [RAW], send=lambda *_: calls.append("send") or True)["decision"] == "deny_invalid_loopback"
    assert calls == []


def test_permission_list_duplicates_or_malformed_neighbors_fail_closed():
    calls = []
    bad_neighbor = {**RAW, "id": "wrong"}
    result = reply_loopback_once(ORIGIN, binding(), consumed=set(), fetch=lambda *_: [RAW, bad_neighbor], send=lambda *_: calls.append(1) or True)
    assert result["decision"] == "deny_invalid_permission" and calls == []
    duplicate = reply_loopback_once(ORIGIN, binding(), consumed=set(), fetch=lambda *_: [RAW, RAW], send=lambda *_: calls.append(1) or True)
    assert duplicate["decision"] == "deny_invalid_permission" and calls == []


def test_adapter_has_no_http_server_runtime_or_configuration_access():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "opencode_loopback_permission_adapter.py").read_text(encoding="utf-8")
    for token in ("requests", "urllib", "socket", "subprocess", "Popen", "os.environ", "getenv", "open("):
        assert token not in source
