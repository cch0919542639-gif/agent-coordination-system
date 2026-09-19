"""L1 live OpenCode seam; callers must supply the exact reviewed launcher."""

from __future__ import annotations

import ntpath
import subprocess
import hashlib
import json
import threading
from datetime import datetime
from typing import Callable, Mapping

from local_opencode_executor import Process, Spawn, run_opencode_once


POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TASKKILL = r"C:\Windows\System32\taskkill.exe"
LAUNCHER_FIELDS = frozenset({"runtime_id", "powershell_path", "wrapper_path", "launcher_id", "approval_id", "run_id"})
PINNED_LAUNCHER = {"runtime_id": "opencode", "powershell_path": POWERSHELL, "launcher_id": "opencode-powershell-wrapper-v1"}
PINNED_WRAPPER_PATH_DIGEST = "e1b87ce69411c64305ebcddf3403b982e1d264af45f5bffbbd505c5c1d00766b"


Popen = Callable[..., object]


class StartAttestationState:
    """In-memory, caller-owned safe ordering state for one pilot attempt."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_order = 0
        self._active: set[str] = set()

    def start(self, binding_digest: str) -> tuple[dict[str, object], dict[str, object]]:
        with self._lock:
            if binding_digest in self._active:
                raise ValueError("duplicate active binding")
            self._next_order += 1
            overlaps = tuple(sorted(self._active))
            self._active.add(binding_digest)
            attestation = {"schema_version": "phase14.5-start-v1", "binding_digest": binding_digest, "launch_order": self._next_order}
            projection = {"schema_version": "phase14.5-concurrency-v1", "binding_digest": binding_digest, "launch_order": self._next_order, "overlap_count": len(overlaps), "overlaps_binding_digests": overlaps}
        return attestation, projection

    def finish(self, binding_digest: str) -> None:
        with self._lock:
            self._active.discard(binding_digest)


def run_live_opencode_once(request: object, approval: object, records: object, launcher: object, *, now: datetime, consumed_run_ids: set[str], popen: Popen = subprocess.Popen, provider_environment: object = None, attestation_state: StartAttestationState | None = None) -> dict[str, object]:
    """Start one reviewed request through the pinned PowerShell wrapper only."""
    if not _launcher(launcher, request):
        return {"decision": "deny_invalid_launcher", "dry_run": True, "control_level": "best_effort"}
    assert isinstance(launcher, Mapping)
    if not isinstance(request, Mapping):
        return {"decision": "deny_invalid_request", "dry_run": True, "control_level": "best_effort"}
    captured: list[tuple[dict[str, object], dict[str, object]]] = []
    result = run_opencode_once(request, approval, records, now=now, consumed_run_ids=consumed_run_ids, spawn=_spawn(popen, str(launcher["wrapper_path"]), request, attestation_state or StartAttestationState(), captured), provider_environment=provider_environment)
    if captured:
        result["safe_start_attestation"], result["concurrency_projection"] = captured[0]
    return result


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


def _spawn(popen: Popen, wrapper_path: str, request: Mapping[str, object], state: StartAttestationState, captured: list[tuple[dict[str, object], dict[str, object]]]) -> Spawn:
    def spawn(_: str, argv: tuple[str, ...], *, cwd_ref: str, env: dict[str, str], shell: bool) -> Process:
        child = popen((POWERSHELL, "-NoProfile", "-NonInteractive", "-File", wrapper_path, *argv), cwd=cwd_ref, env=env, shell=shell, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not _live_child_identity(child):
            raise RuntimeError("child is not live")
        tree = _ProcessTree(child, popen, state, _binding_digest(request))
        captured.append(tree.start_evidence)
        return tree
    return spawn


def _live_child_identity(child: object) -> bool:
    """Require a live returned child while keeping its identity private."""
    pid = getattr(child, "pid", None)
    poll = getattr(child, "poll", None)
    if type(pid) is not int or pid < 1 or not callable(poll):
        return False
    try:
        return poll() is None
    except Exception:
        return False


def _binding_digest(request: Mapping[str, object]) -> str:
    values = {key: request[key] for key in ("approval_id", "agent_id", "grant_id", "worktree_ref")}
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class _ProcessTree:
    def __init__(self, child: object, popen: Popen, state: StartAttestationState, binding_digest: str) -> None:
        self._child, self._popen = child, popen
        self._state, self._binding_digest = state, binding_digest
        self._finished = False
        self.start_evidence = state.start(binding_digest)

    def _finish(self) -> None:
        if not self._finished:
            self._state.finish(self._binding_digest)
            self._finished = True

    def wait(self, timeout: int) -> int:
        try:
            return self._child.wait(timeout=timeout)  # type: ignore[union-attr,no-any-return]
        finally:
            self._finish()

    def terminate_tree(self) -> None:
        try:
            self._popen((TASKKILL, "/pid", str(self._child.pid), "/t", "/f"), env={}, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=5)  # type: ignore[union-attr]
        finally:
            self._finish()
