"""Version-pinned, transport-free OpenCode task and permission API shapes."""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Mapping
from urllib.parse import quote


TASK_FIELDS = frozenset({"task_id", "objective", "context", "constraints", "allowed_scope", "forbidden_scope", "acceptance", "validation"})
REQUEST_FIELDS = frozenset({"id", "sessionID", "permission", "patterns", "metadata", "always"})
FORBIDDEN_CONTENT = re.compile(r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b|[\"']?\b(?:[A-Za-z0-9-]+[_-])?(?:password|passwd|authorization|api[_-]?key|access[_-]?token|token|credential|credentials|secret(?:[_-]?access[_-]?key)?|private[ _-]?key)[\"']?\s*[:=]\s*[\"']?\S+|\bbearer\s+[A-Za-z0-9._~+/-]{8,})")
MAX_PROMPT_BYTES = 16 * 1024


def build_task_prompt(task: object, *, max_bytes: int = MAX_PROMPT_BYTES) -> str | None:
    """Render only named task-card fields into a bounded, deterministic prompt."""
    if not isinstance(task, Mapping) or set(task) != TASK_FIELDS:
        return None
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_PROMPT_BYTES:
        return None
    sections = []
    for field in ("task_id", "objective", "context", "constraints", "allowed_scope", "forbidden_scope", "acceptance", "validation"):
        value = task[field]
        if field in {"constraints", "allowed_scope", "forbidden_scope", "acceptance", "validation"}:
            if not isinstance(value, (list, tuple)) or not value or any(not _safe_text(item) for item in value):
                return None
            content = "\n".join(f"- {item}" for item in value)
        else:
            if not _safe_text(value):
                return None
            content = value
        sections.append(f"## {field.replace('_', ' ').title()}\n{content}")
    prompt = "\n\n".join(sections)
    return prompt if len(prompt.encode("utf-8")) <= max_bytes else None


def normalize_permission_request(raw: object) -> dict[str, str] | None:
    """Normalize the v1.18.32 PermissionRequest without retaining metadata."""
    if not isinstance(raw, Mapping) or set(raw) not in (REQUEST_FIELDS, REQUEST_FIELDS | {"tool"}):
        return None
    request_id, session_id, permission = (raw.get(key) for key in ("id", "sessionID", "permission"))
    patterns, metadata, always = raw.get("patterns"), raw.get("metadata"), raw.get("always")
    if not all(_safe_identifier(value) for value in (request_id, session_id, permission)) or not request_id.startswith("per") or not session_id.startswith("ses"):
        return None
    if not isinstance(patterns, list) or not patterns or not all(_safe_text(value) for value in patterns):
        return None
    if not isinstance(always, list) or not all(_safe_text(value) for value in always) or not isinstance(metadata, Mapping):
        return None
    tool = raw.get("tool")
    if "tool" in raw and (not isinstance(tool, Mapping) or set(tool) != {"messageID", "callID"} or not all(_safe_identifier(value) for value in tool.values())):
        return None
    digest = sha256(json.dumps({"permission": permission, "patterns": patterns}, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"session_id": session_id, "permission_id": request_id, "action": permission, "resource_digest": digest}


def select_pending_permission(raw: object, session_id: object, permission_id: object) -> dict[str, str] | None:
    """Select one exact request from GET /permission's array response."""
    if not isinstance(raw, list) or not raw or not _safe_identifier(session_id) or not _safe_identifier(permission_id):
        return None
    normalized = [normalize_permission_request(item) for item in raw]
    if any(item is None for item in normalized):
        return None
    matches = [item for item in normalized if item and item["session_id"] == session_id and item["permission_id"] == permission_id]
    return matches[0] if len(matches) == 1 else None


def permission_reply_request(origin: object, request_id: object) -> dict[str, object] | None:
    """Build the modern v1.18.32 reply request; this function performs no I/O."""
    if not _loopback_origin(origin) or not _safe_identifier(request_id):
        return None
    return {"method": "POST", "url": f"{origin}/permission/{quote(request_id, safe='')}/reply", "json": {"reply": "once"}}


def _safe_identifier(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 256 and re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is not None and not _sensitive(value)


def _safe_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value and not FORBIDDEN_CONTENT.search(value)


def _sensitive(value: str) -> bool:
    lowered = value.casefold()
    return any(word in lowered for word in ("api_key", "authorization", "bearer", "credential", "password", "secret", "token"))


def _loopback_origin(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("http://127.0.0.1:") or value.count(":") != 2:
        return False
    port = value.rsplit(":", 1)[1]
    return port.isascii() and port.isdecimal() and 1 <= int(port) <= 65535
