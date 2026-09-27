"""Small durable, fail-closed claims for one-shot runtime side effects."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping


NAMESPACES = frozenset({"approval", "binding", "permission", "session"})


def consume_once(state_dir: str | Path, namespace: object, identity: object) -> bool:
    """Atomically claim an exact opaque identity; return false on replay/error."""
    if not isinstance(namespace, str) or namespace not in NAMESPACES or not isinstance(identity, Mapping) or not identity:
        return False
    if any(not _safe_atom(key) or not _safe_atom(value) for key, value in identity.items()):
        return False
    try:
        directory = Path(os.path.abspath(state_dir))
        _reject_reparse_path(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        _reject_reparse_path(directory)
        if not directory.is_dir():
            return False
        digest = _identity_digest(identity)
        marker = directory / f"{namespace}-{digest}.json"
        if marker.is_symlink():
            return False
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        descriptor = os.open(marker, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as record:
            record.write(json.dumps({"schema": "one-shot-v1", "namespace": namespace, "identity_sha256": digest}, sort_keys=True, separators=(",", ":")) + "\n")
            record.flush()
            os.fsync(record.fileno())
        return True
    except (OSError, TypeError, ValueError):
        return False


def has_claim(state_dir: str | Path, namespace: object, identity: object) -> bool:
    """Verify an exact durable claim without creating or consuming another one."""
    if not isinstance(namespace, str) or namespace not in NAMESPACES or not isinstance(identity, Mapping) or not identity:
        return False
    if any(not _safe_atom(key) or not _safe_atom(value) for key, value in identity.items()):
        return False
    try:
        directory = Path(os.path.abspath(state_dir))
        _reject_reparse_path(directory)
        marker = directory / f"{namespace}-{_identity_digest(identity)}.json"
        if marker.is_symlink() or not marker.is_file():
            return False
        _reject_reparse_path(directory)
        value = json.loads(marker.read_text(encoding="ascii"))
        return value == {"schema": "one-shot-v1", "namespace": namespace, "identity_sha256": _identity_digest(identity)}
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _identity_digest(identity: Mapping[str, object]) -> str:
    canonical = json.dumps(dict(identity), sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _safe_atom(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 512 and re.fullmatch(r"[A-Za-z0-9_.:/\\-]+", value) is not None


def _reject_reparse_path(directory: Path) -> None:
    is_junction = getattr(Path, "is_junction", lambda self: False)
    if any(part.is_symlink() or is_junction(part) for part in (directory, *directory.parents)):
        raise OSError("reparse_point_state_path")
