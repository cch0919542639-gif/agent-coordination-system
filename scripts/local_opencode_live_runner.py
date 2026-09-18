"""L1 live OpenCode seam; callers must supply the exact reviewed launcher."""

from __future__ import annotations

import ntpath
import subprocess
from datetime import datetime
from typing import Callable, Mapping

from local_opencode_executor import Process, Spawn, run_opencode_once


POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
OPENCODE_WRAPPER = r"C:\Users\angel\AppData\Local\hermes\node\opencode.ps1"
TASKKILL = r"C:\Windows\System32\taskkill.exe"
LAUNCHER_FIELDS = frozenset({"runtime_id", "powershell_path", "wrapper_path", "launcher_id"})
PINNED_LAUNCHER = {"runtime_id": "opencode", "powershell_path": POWERSHELL, "wrapper_path": OPENCODE_WRAPPER, "launcher_id": "opencode-powershell-wrapper-v1"}


Popen = Callable[..., object]


def run_live_opencode_once(request: object, approval: object, records: object, launcher: object, *, now: datetime, consumed_run_ids: set[str], popen: Popen = subprocess.Popen, provider_environment: object = None) -> dict[str, object]:
    """Start one reviewed request through the pinned PowerShell wrapper only."""
    if not _launcher(launcher):
        return {"decision": "deny_invalid_launcher", "dry_run": True, "control_level": "best_effort"}
    return run_opencode_once(request, approval, records, now=now, consumed_run_ids=consumed_run_ids, spawn=_spawn(popen), provider_environment=provider_environment)


def _launcher(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != LAUNCHER_FIELDS:
        return False
    return all(value.get(key) == expected for key, expected in PINNED_LAUNCHER.items()) and all(ntpath.isabs(str(value[key])) and ntpath.normpath(str(value[key])) == value[key] for key in ("powershell_path", "wrapper_path"))


def _spawn(popen: Popen) -> Spawn:
    def spawn(_: str, argv: tuple[str, ...], *, cwd_ref: str, env: dict[str, str], shell: bool) -> Process:
        child = popen((POWERSHELL, "-NoProfile", "-NonInteractive", "-File", OPENCODE_WRAPPER, *argv), cwd=cwd_ref, env=env, shell=shell, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return _ProcessTree(child, popen)
    return spawn


class _ProcessTree:
    def __init__(self, child: object, popen: Popen) -> None:
        self._child, self._popen = child, popen

    def wait(self, timeout: int) -> int:
        return self._child.wait(timeout=timeout)  # type: ignore[union-attr,no-any-return]

    def terminate_tree(self) -> None:
        self._popen((TASKKILL, "/pid", str(self._child.pid), "/t", "/f"), env={}, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=5)  # type: ignore[union-attr]
