"""Fail-closed, transport-free core for one OpenCode permission reply."""

from __future__ import annotations

from typing import Callable, Mapping


BINDING_FIELDS = frozenset({"task_id", "run_id", "approval_id", "agent_id", "grant_id", "session_id", "permission_id", "action", "resource_digest"})
PENDING_FIELDS = frozenset({"session_id", "permission_id", "action", "resource_digest"})
UNSAFE_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")
Reply = Callable[[str, str, dict[str, object]], bool]


def reply_once(pending: object, binding: object, *, consumed: set[str], reply: Reply) -> dict[str, object]:
    """Reply once only when a pending permission exactly matches its binding."""
    if not _valid(pending, PENDING_FIELDS) or not _valid(binding, BINDING_FIELDS):
        return {"decision": "deny_invalid_permission"}
    assert isinstance(pending, Mapping) and isinstance(binding, Mapping)
    if any(pending[key] != binding[key] for key in PENDING_FIELDS):
        return {"decision": "deny_unbound_permission"}
    identity = ":".join(str(binding[key]) for key in ("run_id", "approval_id", "agent_id", "grant_id", "session_id", "permission_id"))
    if identity in consumed:
        return {"decision": "deny_consumed_permission"}
    consumed.add(identity)
    try:
        accepted = reply(str(binding["session_id"]), str(binding["permission_id"]), {"reply": "once"})
    except Exception:
        return {"decision": "stopped_safety_signal"}
    return {"decision": "approved_once" if accepted else "stopped_permission_reply", "task_id": binding["task_id"], "run_id": binding["run_id"], "agent_id": binding["agent_id"], "grant_id": binding["grant_id"]}


def _valid(value: object, fields: frozenset[str]) -> bool:
    if not isinstance(value, Mapping) or set(value) != fields or not all(isinstance(value[key], str) and value[key] and not _unsafe(value[key]) for key in fields) or not _digest(value.get("resource_digest")):
        return False
    return ("session_id" not in value or value["session_id"].startswith("ses")) and ("permission_id" not in value or value["permission_id"].startswith("per"))


def _unsafe(value: str) -> bool:
    return any(word in value.casefold() for word in UNSAFE_WORDS)


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
