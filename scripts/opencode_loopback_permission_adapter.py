"""Injected loopback adapter for the Task 44 permission controller."""

from __future__ import annotations

from typing import Callable, Mapping

from opencode_live_api import permission_reply_request, select_pending_permission
from opencode_permission_controller import reply_once


Fetch = Callable[[str], object]
Send = Callable[[dict[str, object]], bool]
UNSAFE_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")


def reply_loopback_once(origin: object, binding: object, *, consumed: set[str], fetch: Fetch, send: Send) -> dict[str, object]:
    """Fetch one exact request through an injected loopback transport."""
    if not _origin(origin) or not isinstance(binding, Mapping):
        return {"decision": "deny_invalid_loopback"}
    session_id, permission_id = binding.get("session_id"), binding.get("permission_id")
    if not _safe_identifier(session_id) or not _safe_identifier(permission_id):
        return {"decision": "deny_invalid_permission"}
    try:
        raw = fetch(origin)
    except Exception:
        return {"decision": "stopped_safety_signal"}
    pending = select_pending_permission(raw, session_id, permission_id)
    if pending is None:
        return {"decision": "deny_invalid_permission"}
    def send_once(_: str, permission: str, body: dict[str, object]) -> bool:
        request = permission_reply_request(origin, permission)
        return request is not None and body == {"reply": "once"} and send(request)
    return reply_once(pending, binding, consumed=consumed, reply=send_once)


def _origin(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("http://127.0.0.1:") or value.count(":") != 2:
        return False
    port = value.rsplit(":", 1)[1]
    return port.isascii() and port.isdecimal() and 1 <= int(port) <= 65535


def _safe_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and not any(word in value.casefold() for word in UNSAFE_WORDS)
