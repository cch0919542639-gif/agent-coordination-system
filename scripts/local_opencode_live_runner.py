"""L1 live OpenCode seam; callers must supply the exact reviewed launcher."""

from __future__ import annotations

import ntpath
import subprocess
import hashlib
from datetime import datetime
from typing import Callable, Mapping

from local_opencode_executor import Process, Spawn, run_opencode_once


POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TASKKILL = r"C:\Windows\System32\taskkill.exe"
LAUNCHER_FIELDS = frozenset({"runtime_id", "powershell_path", "wrapper_path", "launcher_id", "approval_id", "run_id"})
PINNED_LAUNCHER = {"runtime_id": "opencode", "powershell_path": POWERSHELL, "launcher_id": "opencode-powershell-wrapper-v1"}
PINNED_WRAPPER_PATH_DIGEST = "e1b87ce69411c64305ebcddf3403b982e1d264af45f5bffbbd505c5c1d00766b"


Popen = Callable[..., object]


def run_live_opencode_once(request: object, approval: object, records: object, launcher: object, *, now: datetime, consumed_run_ids: set[str], popen: Popen = subprocess.Popen, provider_environment: object = None) -> dict[str, object]:
    """Start one reviewed request through the pinned PowerShell wrapper only."""
    if not _launcher(launcher, request):
        return {"decision": "deny_invalid_launcher", "dry_run": True, "control_level": "best_effort"}
    assert isinstance(launcher, Mapping)
    return run_opencode_once(request, approval, records, now=now, consumed_run_ids=consumed_run_ids, spawn=_spawn(popen, str(launcher["wrapper_path"])), provider_environment=provider_environment)


def _launcher(value: object, request: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != LAUNCHER_FIELDS:
        return False
    if not isinstance(request, Mapping) or any(value.get(key) != request.get(key) for key in ("approval_id", "run_id")):
        return False
    return all(value.get(key) == expected for key, expected in PINNED_LAUNCHER.items()) and _wrapper_path(value.get("wrapper_path")) and _wrapper_digest(str(value["wrapper_path"])) == PINNED_WRAPPER_PATH_DIGEST


def _wrapper_path(value: object) -> bool:
    if not isinstance(value, str) or not (1 <= len(value) <= 512) or not ntpath.isabs(value) or ntpath.normpath(value) != value:
        return False
    drive, _ = ntpath.splitdrive(value)
    return len(drive) == 2 and drive[0].isalpha() and drive[1] == ":" and value.casefold().endswith(".ps1") and all(part not in {"", ".", ".."} for part in value.split("\\")[1:]) and not any(char in value for char in "\x00\r\n\"'`|;&")


def _wrapper_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _spawn(popen: Popen, wrapper_path: str) -> Spawn:
    def spawn(_: str, argv: tuple[str, ...], *, cwd_ref: str, env: dict[str, str], shell: bool) -> Process:
        child = popen((POWERSHELL, "-NoProfile", "-NonInteractive", "-File", wrapper_path, *argv), cwd=cwd_ref, env=env, shell=shell, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return _ProcessTree(child, popen)
    return spawn


class _ProcessTree:
    def __init__(self, child: object, popen: Popen) -> None:
        self._child, self._popen = child, popen

    def wait(self, timeout: int) -> int:
        return self._child.wait(timeout=timeout)  # type: ignore[union-attr,no-any-return]

    def terminate_tree(self) -> None:
        self._popen((TASKKILL, "/pid", str(self._child.pid), "/t", "/f"), env={}, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=5)  # type: ignore[union-attr]
