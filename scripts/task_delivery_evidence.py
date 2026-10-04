"""Capture bounded, in-memory file-path evidence for one supervised task run."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import stat
from functools import lru_cache
from pathlib import Path
from typing import Mapping


MAX_FILES = 5000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
SAFE_SCOPE = re.compile(r"[A-Za-z0-9_./*?@+\[\]-]+\Z")


def capture_snapshot(directory: str, allowed_scope: object) -> dict[str, str]:
    """Return path-to-digest data for regular files matching allowed_scope."""
    root = Path(directory)
    if not root.is_absolute() or _is_link(root) or not root.is_dir():
        raise ValueError("worktree is unavailable")
    scopes = _validated_scopes(allowed_scope)
    files: set[Path] = set()

    for scope in scopes:
        target = root.joinpath(*scope.split("/"))
        if _has_magic(scope):
            prefix = _static_prefix(scope)
            anchor = root.joinpath(*prefix.split("/")) if prefix else root
            _ensure_no_link_components(root, anchor)
            if anchor.is_dir():
                files.update(_walk_scope(root, anchor, scope))
            if len(files) > MAX_FILES:
                raise ValueError("worktree snapshot file limit exceeded")
            continue
        _ensure_no_link_components(root, target)
        if target.is_file():
            files.add(target)
        elif target.is_dir():
            files.update(_walk_scope(root, target, scope + "/**"))
        if len(files) > MAX_FILES:
            raise ValueError("worktree snapshot file limit exceeded")

    if len(files) > MAX_FILES:
        raise ValueError("worktree snapshot file limit exceeded")

    snapshot: dict[str, str] = {}
    total_bytes = 0
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        if _is_link(path):
            raise ValueError("allowed worktree path is a symlink")
        try:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("allowed worktree path is not a regular file")
            total_bytes += before.st_size
            if total_bytes > MAX_TOTAL_BYTES:
                raise ValueError("worktree snapshot byte limit exceeded")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.stat()
        except OSError as exc:
            raise ValueError("worktree snapshot could not be read") from exc
        if (before.st_size, before.st_mtime_ns, before.st_mode) != (after.st_size, after.st_mtime_ns, after.st_mode):
            raise ValueError("worktree changed during snapshot")
        snapshot[relative] = digest.hexdigest()
    return snapshot


def changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, list[str]]:
    """Classify added, modified, and deleted paths without exposing digests."""
    if not _valid_snapshot(before) or not _valid_snapshot(after):
        raise ValueError("invalid worktree snapshot")
    old, new = set(before), set(after)
    return {
        "added": sorted(new - old),
        "modified": sorted(path for path in old & new if before[path] != after[path]),
        "deleted": sorted(old - new),
    }


def _validated_scopes(value: object) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 200:
        raise ValueError("invalid allowed scope")
    scopes: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 512 or SAFE_SCOPE.fullmatch(item) is None or item.startswith("/") or "\\" in item:
            raise ValueError("invalid allowed scope")
        parts = item.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("invalid allowed scope")
        scopes.append(item)
    return scopes


def _walk_scope(root: Path, anchor: Path, pattern: str) -> set[Path]:
    _ensure_no_link_components(root, anchor)
    matches: set[Path] = set()
    for current, directories, filenames in os.walk(anchor, topdown=True, onerror=_raise_walk_error, followlinks=False):
        current_path = Path(current)
        directories.sort()
        filenames.sort()
        for name in tuple(directories):
            directory = current_path / name
            relative = directory.relative_to(root).as_posix()
            if _is_link(directory):
                if _scope_matches(relative, pattern):
                    raise ValueError("allowed worktree path is a symlink")
                directories.remove(name)
        for name in filenames:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if not _scope_matches(relative, pattern):
                continue
            if _is_link(path):
                raise ValueError("allowed worktree path is a symlink")
            matches.add(path)
            if len(matches) > MAX_FILES:
                raise ValueError("worktree snapshot file limit exceeded")
    return matches


def _scope_matches(relative: str, pattern: str) -> bool:
    path_parts = relative.split("/")
    pattern_parts = pattern.split("/")

    @lru_cache(maxsize=None)
    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        expected = pattern_parts[pattern_index]
        if expected == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_parts)
            and fnmatch.fnmatchcase(path_parts[path_index], expected)
            and match(path_index + 1, pattern_index + 1)
        )

    return match(0, 0)


def _has_magic(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def _static_prefix(pattern: str) -> str:
    parts = []
    for part in pattern.split("/"):
        if _has_magic(part):
            break
        parts.append(part)
    return "/".join(parts)


def _ensure_no_link_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError("allowed scope escaped the worktree") from exc
    current = root
    if _is_link(current):
        raise ValueError("worktree path is a symlink")
    for part in relative.parts:
        current = current / part
        if _is_link(current):
            raise ValueError("allowed worktree path is a symlink")


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return callable(is_junction) and bool(is_junction())


def _raise_walk_error(error: OSError) -> None:
    raise ValueError("allowed worktree path could not be enumerated") from error


def _valid_snapshot(value: Mapping[str, str]) -> bool:
    return all(
        isinstance(path, str)
        and path
        and "\\" not in path
        and not path.startswith("/")
        and all(part not in {"", ".", ".."} for part in path.split("/"))
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        for path, digest in value.items()
    )
