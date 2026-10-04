"""Small, no-proxy HTTP adapter for the pinned OpenCode loopback API.

The caller must already have passed Task 49's approval and durable-consumption
gates. This module supplies transport callbacks only; it does not create or
validate authority and it is never run as a service.
"""

from __future__ import annotations

import http.client
import json
import math
import re
from typing import Callable, Mapping
from urllib.parse import urlsplit

from local_opencode_live_runner import (
    session_abort_request,
    session_create_request,
    session_prompt_request,
    session_status_request,
)
from opencode_live_api import permission_reply_request


RUN_FIELDS = ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref")
MAX_RESPONSE_BYTES = 512 * 1024
SESSION_MESSAGE_LIMIT = 20
MAX_FINAL_MESSAGE_BYTES = 16 * 1024
SESSION_ID = re.compile(r"ses[A-Za-z0-9_.:-]{0,253}\Z")
PERMISSION_ID = re.compile(r"per[A-Za-z0-9_.:-]{0,253}\Z")
PERMISSION_REPLY_PATH = re.compile(r"/permission/(per[A-Za-z0-9_.:-]{0,253})/reply\Z")
ConnectionFactory = Callable[..., object]


class TransportError(Exception):
    """A deliberately content-free transport or response-shape failure."""


class OpenCodeLoopbackTransport:
    """Task- and permission-runner callbacks for one exact 127.0.0.1 origin."""

    def __init__(
        self,
        origin: str,
        *,
        timeout: float = 3.0,
        connection_factory: ConnectionFactory = http.client.HTTPConnection,
    ) -> None:
        port = _port_for_origin(origin)
        if port is None or type(timeout) not in (int, float) or not 0 < timeout <= 10 or not callable(connection_factory):
            raise ValueError("invalid loopback transport configuration")
        self.origin = origin
        self._port = port
        self._timeout = float(timeout)
        self._connection_factory = connection_factory
        self._sessions: dict[str, str] = {}
        self._saw_activity: set[str] = set()
        self._completed: set[str] = set()

    def create_session(self, request: Mapping[str, object], directory: str) -> object:
        if not _bound_task_request(request):
            return None
        built = session_create_request(self.origin, directory)
        if built is None:
            return None
        response = self._request("POST", built["url"], {}, expected_status=200, json_response=True)
        if not isinstance(response, Mapping):
            return None
        session_id = response.get("id")
        if response.get("directory") != directory or not _session_id(session_id):
            return None
        session_id = str(session_id)
        self._sessions[session_id] = directory
        self._saw_activity.discard(session_id)
        self._completed.discard(session_id)
        return {"id": session_id, "directory": directory}

    def send_prompt(self, session_id: str, prompt: str) -> bool:
        if not self._owns_session(session_id):
            return False
        built = session_prompt_request(self.origin, session_id, prompt)
        if built is None:
            return False
        self._request("POST", built["url"], built["json"], expected_status=204)
        return True

    def session_state(self, session_id: str) -> str:
        if not self._owns_session(session_id):
            return "unavailable"
        built = session_status_request(self.origin)
        if built is None:
            return "unavailable"
        statuses = self._request("GET", built["url"], None, expected_status=200, json_response=True)
        if not isinstance(statuses, Mapping):
            return "unavailable"
        present = session_id in statuses
        status = statuses.get(session_id)
        # OpenCode omits idle sessions from this map; this is also the initial
        # state of a new session, so idle is not completion until activity was
        # observed for this exact session.
        if present and not _valid_session_status(status):
            self._completed.discard(session_id)
            return "unavailable"
        status_type = status["type"] if present else "idle"
        if status_type in ("busy", "retry"):
            self._saw_activity.add(session_id)
            self._completed.discard(session_id)
            return "running"
        if status_type == "idle":
            if session_id in self._saw_activity:
                self._completed.add(session_id)
                return "completed"
            return "running"
        return "unavailable"

    def session_messages(self, session_id: str) -> dict[str, str] | None:
        """Return a session-bound final text field for this completed owned session."""
        if not self._owns_session(session_id) or session_id not in self._completed:
            return None
        url = f"{self.origin}/session/{session_id}/message?limit={SESSION_MESSAGE_LIMIT}"
        messages = self._request("GET", url, None, expected_status=200, json_response=True)
        if not isinstance(messages, list) or len(messages) > SESSION_MESSAGE_LIMIT:
            raise TransportError("invalid message response")
        latest: tuple[float, str] | None = None
        for message in messages:
            if not isinstance(message, Mapping) or set(message) != {"info", "parts"}:
                raise TransportError("invalid message response")
            info, parts = message.get("info"), message.get("parts")
            if not isinstance(info, Mapping) or info.get("sessionID") != session_id or info.get("role") not in {"user", "assistant"} or not isinstance(info.get("time"), Mapping) or not isinstance(parts, list) or len(parts) > 256:
                raise TransportError("invalid message response")
            if info.get("role") != "assistant":
                continue
            completed = info["time"].get("completed")
            if type(completed) is int:
                valid_completed = 0 <= completed <= 10**16
            else:
                valid_completed = type(completed) is float and math.isfinite(completed) and 0 <= completed <= 10**16
            if not valid_completed:
                raise TransportError("invalid message response")
            text_parts: list[str] = []
            for part in parts:
                if not isinstance(part, Mapping):
                    raise TransportError("invalid message response")
                if part.get("type") == "text":
                    value = part.get("text")
                    if not isinstance(value, str):
                        raise TransportError("invalid message response")
                    text_parts.append(value)
            final_text = "\n".join(text_parts)
            try:
                final_size = len(final_text.encode("utf-8"))
            except UnicodeError:
                raise TransportError("invalid final message") from None
            if final_size > MAX_FINAL_MESSAGE_BYTES:
                raise TransportError("oversized final message")
            if latest is None or completed > latest[0]:
                latest = (completed, final_text)
            elif completed == latest[0]:
                raise TransportError("ambiguous final message")
        if latest is None or not latest[1].strip():
            return None
        return {"session_id": session_id, "text": latest[1]}

    def heartbeat(self, session_id: str) -> bool:
        directory = self._sessions.get(session_id) if _session_id(session_id) else None
        if directory is None:
            return False
        response = self._request("GET", f"{self.origin}/session/{session_id}", None, expected_status=200, json_response=True)
        return isinstance(response, Mapping) and response.get("id") == session_id and response.get("directory") == directory

    def abort_session(self, session_id: str) -> bool:
        if not self._owns_session(session_id):
            return False
        built = session_abort_request(self.origin, session_id)
        if built is None:
            return False
        result = self._request("POST", built["url"], None, expected_status=200, json_response=True)
        return result is True

    def fetch(self, origin: str) -> object:
        """Fetch the permission list only for the origin to which this instance is bound."""
        if origin != self.origin:
            raise TransportError("invalid target")
        return self._request("GET", f"{self.origin}/permission", None, expected_status=200, json_response=True)

    def send(self, request: object) -> bool:
        """Send only the existing controller's exact modern `once` reply."""
        if not isinstance(request, Mapping) or set(request) != {"method", "url", "json"} or request.get("method") != "POST" or request.get("json") != {"reply": "once"}:
            return False
        url = request.get("url")
        if not isinstance(url, str):
            return False
        parts = urlsplit(url)
        permission_match = PERMISSION_REPLY_PATH.fullmatch(parts.path)
        if parts.scheme != "http" or parts.netloc != f"127.0.0.1:{self._port}" or parts.query or parts.fragment or permission_match is None:
            return False
        permission_id = permission_match.group(1)
        if not _permission_id(permission_id) or permission_reply_request(self.origin, permission_id) != dict(request):
            return False
        result = self._request("POST", url, {"reply": "once"}, expected_status=200, json_response=True)
        return result is True

    def _owns_session(self, session_id: object) -> bool:
        return _session_id(session_id) and str(session_id) in self._sessions

    def _request(
        self,
        method: str,
        url: str,
        payload: object,
        *,
        expected_status: int,
        json_response: bool = False,
    ) -> object:
        if method not in {"GET", "POST"} or not isinstance(url, str):
            raise TransportError("invalid request")
        parts = urlsplit(url)
        if parts.scheme != "http" or parts.netloc != f"127.0.0.1:{self._port}" or not parts.path.startswith("/") or parts.path.startswith("//") or any(c in url for c in "\x00\r\n"):
            raise TransportError("invalid target")
        if not _allowed_route(method, url, payload, self.origin):
            raise TransportError("unknown route")
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        if len(target) > 4096 or parts.fragment:
            raise TransportError("invalid target")
        body = None
        headers = {"Accept": "application/json", "Connection": "close"}
        if payload is not None:
            if not isinstance(payload, Mapping):
                raise TransportError("invalid payload")
            try:
                body = json.dumps(dict(payload), ensure_ascii=True, separators=(",", ":")).encode("ascii")
            except (TypeError, ValueError, UnicodeError):
                raise TransportError("invalid payload") from None
            if len(body) > 20 * 1024:
                raise TransportError("oversized payload")
            headers["Content-Type"] = "application/json"

        connection = None
        try:
            connection = self._connection_factory("127.0.0.1", self._port, timeout=self._timeout)
            connection.request(method, target, body=body, headers=headers)
            response = connection.getresponse()
            if response.status != expected_status:
                raise TransportError("unexpected response status")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
                raise TransportError("oversized response")
            if expected_status == 204:
                if raw:
                    raise TransportError("unexpected response body")
                return None
            if not json_response:
                return None
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise TransportError("invalid JSON response") from None
        except TransportError:
            raise
        except Exception:
            # Do not leak server bodies, exception text, or local configuration.
            raise TransportError("loopback request failed") from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass


def _bound_task_request(request: object) -> bool:
    return isinstance(request, Mapping) and all(isinstance(request.get(key), str) and request.get(key) for key in RUN_FIELDS)


def _session_id(value: object) -> bool:
    return isinstance(value, str) and SESSION_ID.fullmatch(value) is not None


def _permission_id(value: object) -> bool:
    return isinstance(value, str) and PERMISSION_ID.fullmatch(value) is not None


def _valid_session_status(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    if value == {"type": "idle"} or value == {"type": "busy"}:
        return True
    required = {"type", "attempt", "message", "next"}
    if value.get("type") != "retry" or set(value) not in (required, required | {"action"}):
        return False
    if type(value.get("attempt")) is not int or value["attempt"] < 0 or type(value.get("next")) is not int or value["next"] < 0 or not isinstance(value.get("message"), str):
        return False
    if "action" not in value:
        return True
    action = value["action"]
    action_fields = {"reason", "provider", "title", "message", "label"}
    return isinstance(action, Mapping) and set(action) in (action_fields, action_fields | {"link"}) and all(isinstance(action.get(key), str) for key in action)


def _allowed_route(method: str, url: str, payload: object, origin: str) -> bool:
    parts = urlsplit(url)
    path = parts.path
    if method == "GET" and payload is None:
        if not parts.query and path in {"/permission", "/session/status"}:
            return True
        if not parts.query and re.fullmatch(r"/session/(ses[A-Za-z0-9_.:-]{0,253})", path):
            return True
        return parts.query == f"limit={SESSION_MESSAGE_LIMIT}" and re.fullmatch(r"/session/(ses[A-Za-z0-9_.:-]{0,253})/message", path) is not None
    if method != "POST" or parts.fragment:
        return False
    if path == "/session":
        # Require the unique URL produced by the existing directory-safe
        # request builder; this rejects alternate encodings and extra queries.
        try:
            from urllib.parse import parse_qs
            query = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
        except ValueError:
            return False
        values = query.get("directory")
        if set(query) != {"directory"} or not isinstance(values, list) or len(values) != 1 or payload != {}:
            return False
        expected = session_create_request(origin, values[0])
        return expected is not None and expected["url"] == url
    if not parts.query and payload is None and re.fullmatch(r"/session/(ses[A-Za-z0-9_.:-]{0,253})/abort", path):
        return True
    if not parts.query and re.fullmatch(r"/session/(ses[A-Za-z0-9_.:-]{0,253})/prompt_async", path):
        return isinstance(payload, Mapping) and set(payload) == {"parts"} and isinstance(payload.get("parts"), list) and len(payload["parts"]) == 1 and isinstance(payload["parts"][0], Mapping) and set(payload["parts"][0]) == {"type", "text"} and payload["parts"][0].get("type") == "text" and isinstance(payload["parts"][0].get("text"), str)
    permission_match = PERMISSION_REPLY_PATH.fullmatch(path)
    return not parts.query and permission_match is not None and _permission_id(permission_match.group(1)) and payload == {"reply": "once"}


def _port_for_origin(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", value)
    if match is None:
        return None
    port = int(match.group(1))
    return port if port <= 65535 else None
