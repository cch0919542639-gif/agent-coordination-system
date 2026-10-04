from __future__ import annotations

import json
from collections import deque
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from opencode_loopback_transport import OpenCodeLoopbackTransport, TransportError
from opencode_live_api import permission_reply_request


ORIGIN = "http://127.0.0.1:4096"
DIRECTORY = r"C:\worktrees\agent-01"
RUN = {
    "task_id": "task-01",
    "run_id": "run-01",
    "approval_id": "approval-01",
    "agent_id": "agent-01",
    "grant_id": "grant-01",
    "worktree_ref": "worktree-01",
}


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self.body = body

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]


class FakeConnection:
    def __init__(self, response: FakeResponse, calls: list[dict]) -> None:
        self.response = response
        self.calls = calls

    def request(self, method: str, target: str, *, body: bytes | None, headers: dict[str, str]) -> None:
        self.calls.append({"method": method, "target": target, "body": body, "headers": dict(headers)})

    def getresponse(self) -> FakeResponse:
        return self.response

    def close(self) -> None:
        pass


def transport_with(*responses: FakeResponse) -> tuple[OpenCodeLoopbackTransport, list[dict]]:
    queued = deque(responses)
    calls: list[dict] = []

    def factory(host: str, port: int, *, timeout: float) -> FakeConnection:
        assert (host, port, timeout) == ("127.0.0.1", 4096, 3.0)
        return FakeConnection(queued.popleft(), calls)

    return OpenCodeLoopbackTransport(ORIGIN, connection_factory=factory), calls


def json_response(value: object, status: int = 200) -> FakeResponse:
    return FakeResponse(status, json.dumps(value).encode("utf-8"))


def test_only_exact_loopback_origin_is_accepted_without_connecting() -> None:
    attempted = []

    def factory(*args: object, **kwargs: object) -> object:
        attempted.append((args, kwargs))
        raise AssertionError("invalid origin must fail before transport")

    for origin in (
        "http://localhost:4096", "http://127.0.0.2:4096", "https://127.0.0.1:4096",
        "http://user@127.0.0.1:4096", "http://127.0.0.1:4096/", "http://127.0.0.1:65536",
    ):
        with pytest.raises(ValueError):
            OpenCodeLoopbackTransport(origin, connection_factory=factory)
    assert attempted == []


def test_unknown_route_is_rejected_before_opening_a_connection() -> None:
    attempted = []

    def factory(*args: object, **kwargs: object) -> object:
        attempted.append((args, kwargs))
        raise AssertionError("unknown routes must fail before transport")

    transport = OpenCodeLoopbackTransport(ORIGIN, connection_factory=factory)
    with pytest.raises(TransportError):
        transport._request("GET", f"{ORIGIN}/config", None, expected_status=200, json_response=True)
    with pytest.raises(TransportError):
        transport._request("GET", f"{ORIGIN}/session/ses_task01/message?limit=21", None, expected_status=200, json_response=True)
    with pytest.raises(TransportError):
        transport._request("POST", f"{ORIGIN}/session/ses_task01/permissions/per_task01", {"response": "once"}, expected_status=200, json_response=True)
    assert attempted == []


def assistant_message(session_id: str, completed: int, text: str) -> dict:
    return {"info": {"id": f"msg-{completed}", "sessionID": session_id, "role": "assistant", "time": {"created": completed - 1, "completed": completed}}, "parts": [{"type": "text", "text": text}]}


def test_final_message_is_read_only_from_the_owned_session_after_idle_completion() -> None:
    transport, calls = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        json_response({"ses_task01": {"type": "busy"}}),
        json_response({}),
        json_response([assistant_message("ses_task01", 2, '{"summary":"old"}'), assistant_message("ses_task01", 3, '{"summary":"final"}')]),
    )
    assert transport.create_session(RUN, DIRECTORY)
    assert transport.session_messages("ses_task01") is None
    assert transport.session_state("ses_task01") == "running"
    assert transport.session_state("ses_task01") == "completed"
    assert transport.session_messages("ses_task01") == {"session_id": "ses_task01", "text": '{"summary":"final"}'}
    assert calls[-1]["target"] == "/session/ses_task01/message?limit=20"
    assert all(call["method"] == "GET" or call["method"] == "POST" for call in calls)


def test_final_message_rejects_cross_session_ambiguous_and_oversized_results() -> None:
    foreign = assistant_message("ses_foreign", 3, "{}")
    for messages in (
        [foreign],
        [assistant_message("ses_task01", 3, "one"), assistant_message("ses_task01", 3, "two")],
        [assistant_message("ses_task01", 3, "x" * (16 * 1024 + 1))],
    ):
        transport, _ = transport_with(
            json_response({"id": "ses_task01", "directory": DIRECTORY}),
            json_response({"ses_task01": {"type": "busy"}}),
            json_response({}),
            json_response(messages),
        )
        assert transport.create_session(RUN, DIRECTORY)
        assert transport.session_state("ses_task01") == "running"
        assert transport.session_state("ses_task01") == "completed"
        with pytest.raises(TransportError):
            transport.session_messages("ses_task01")


def test_runner_callbacks_bind_session_and_require_activity_before_idle_completion() -> None:
    transport, calls = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        FakeResponse(204),
        json_response({}),
        json_response({"ses_task01": {"type": "retry", "attempt": 1, "message": "temporary failure", "next": 2}}),
        json_response({}),
        json_response({"id": "ses_task01", "directory": DIRECTORY, "title": "not retained"}),
        json_response(True),
    )

    assert transport.create_session(RUN, DIRECTORY) == {"id": "ses_task01", "directory": DIRECTORY}
    assert transport.send_prompt("ses_task01", "bounded assigned task") is True
    assert transport.session_state("ses_task01") == "running"  # initial idle is not completion
    assert transport.session_state("ses_task01") == "running"
    assert transport.session_state("ses_task01") == "completed"
    assert transport.heartbeat("ses_task01") is True
    assert transport.abort_session("ses_task01") is True

    assert [call["method"] for call in calls] == ["POST", "POST", "GET", "GET", "GET", "GET", "POST"]
    assert calls[0]["target"] == "/session?directory=C%3A%5Cworktrees%5Cagent-01"
    assert calls[1]["target"] == "/session/ses_task01/prompt_async"
    assert json.loads(calls[1]["body"]) == {"parts": [{"type": "text", "text": "bounded assigned task"}]}
    assert calls[2]["target"] == "/session/status"
    assert calls[5]["target"] == "/session/ses_task01"
    assert all("Authorization" not in call["headers"] for call in calls)


def test_transport_rejects_unbound_requests_and_cross_directory_session() -> None:
    transport, calls = transport_with(json_response({"id": "ses_foreign", "directory": r"C:\other"}))
    assert transport.create_session(RUN, DIRECTORY) is None
    assert transport.send_prompt("ses_foreign", "a bounded task") is False
    assert transport.heartbeat("ses_foreign") is False
    assert transport.abort_session("ses_foreign") is False
    assert len(calls) == 1

    transport, calls = transport_with(json_response({"id": "ses_task01", "directory": DIRECTORY}))
    assert transport.create_session({"task_id": "task-01"}, DIRECTORY) is None
    assert calls == []


def test_unknown_or_malformed_session_status_never_counts_as_completion() -> None:
    transport, _ = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        json_response({"ses_task01": {"type": "finished"}}),
    )
    assert transport.create_session(RUN, DIRECTORY)
    assert transport.session_state("ses_task01") == "unavailable"

    transport, _ = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        json_response({"ses_task01": {"type": "retry"}}),
    )
    assert transport.create_session(RUN, DIRECTORY)
    assert transport.session_state("ses_task01") == "unavailable"

    transport, _ = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        json_response({"ses_task01": {"type": "busy"}}),
        json_response({"ses_task01": {"type": "idle", "extra": "unknown"}}),
    )
    assert transport.create_session(RUN, DIRECTORY)
    assert transport.session_state("ses_task01") == "running"
    assert transport.session_state("ses_task01") == "unavailable"

    transport, _ = transport_with(
        json_response({"id": "ses_task01", "directory": DIRECTORY}),
        json_response({}),
        json_response({}),
    )
    assert transport.create_session(RUN, DIRECTORY)
    assert transport.session_state("ses_task01") == "running"
    assert transport.session_state("ses_task01") == "running"


def test_permission_callbacks_are_bound_to_modern_once_reply_and_origin() -> None:
    pending = [{"id": "per_task01", "sessionID": "ses_task01", "permission": "read", "patterns": ["README.md"], "metadata": {}, "always": []}]
    transport, calls = transport_with(json_response(pending), json_response(True))
    request = permission_reply_request(ORIGIN, "per_task01")
    assert transport.fetch(ORIGIN) == pending
    assert transport.send(request) is True
    assert calls[0]["target"] == "/permission"
    assert calls[1]["target"] == "/permission/per_task01/reply"
    assert json.loads(calls[1]["body"]) == {"reply": "once"}

    before = len(calls)
    assert transport.send({**request, "json": {"reply": "always"}}) is False
    assert transport.send({**request, "url": "http://example.com/permission/per_task01/reply"}) is False
    with pytest.raises(TransportError):
        transport.fetch("http://127.0.0.1:4097")
    assert len(calls) == before


def test_redirect_error_body_and_oversized_response_fail_without_retry() -> None:
    transport, calls = transport_with(FakeResponse(302, b"redirect"))
    with pytest.raises(TransportError):
        transport.fetch(ORIGIN)
    assert len(calls) == 1

    transport, calls = transport_with(FakeResponse(200, b"x" * (512 * 1024 + 1)))
    with pytest.raises(TransportError):
        transport.fetch(ORIGIN)
    assert len(calls) == 1

    transport, calls = transport_with(FakeResponse(204, b"unexpected"))
    with pytest.raises(TransportError):
        transport.create_session(RUN, DIRECTORY)
    assert len(calls) == 1
