#!/usr/bin/env python3
"""Safe, bounded discovery for optional local agent runtime adapters.

The default command only asks the operating system whether a configured CLI is
on PATH.  It does not start a session, use a model, read runtime configuration,
or change any local state.  An explicit --probe performs a short --version
check only and intentionally keeps the underlying diagnostic private.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from collections.abc import Callable


RUNTIMES = {
    "opencode": {"command": "opencode", "documented_entry": "opencode run <message>"},
    "mimo": {"command": "mimo", "documented_entry": "mimo"},
}
DEFAULT_WORKER_ID = "<worker-id>"


def _handoff_command(worker_id: str) -> str:
    return f"python scripts/orchestrate.py worker activate {worker_id} --json"


def _probe_version(executable: str) -> str:
    args = [executable, "--version"]
    if os.name == "nt":
        # Python cannot directly CreateProcess a discovered .cmd wrapper. Use
        # the resolved PATH entry, never user input, through a noninteractive
        # PowerShell host that can invoke it consistently.
        escaped = executable.replace("'", "''")
        args = [
            "powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile",
            "-NonInteractive", "-Command", f"& '{escaped}' --version",
        ]
    try:
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "probe_failed"
    return "available" if result.returncode == 0 else "probe_failed"


def build_preflight(
    runtime_names: list[str], worker_id: str = DEFAULT_WORKER_ID, *,
    probe: bool = False, command_lookup: Callable[[str], str | None] = shutil.which,
    version_probe: Callable[[str], str] = _probe_version,
) -> dict:
    """Return only safe runtime readiness categories and handoff templates."""
    rows = []
    for runtime_name in runtime_names:
        spec = RUNTIMES[runtime_name]
        command = spec["command"]
        executable = command_lookup(command)
        discovered = bool(executable)
        status = "discoverable_unverified" if discovered else "unavailable"
        if discovered and probe:
            status = version_probe(str(executable))
        rows.append({
            "runtime": runtime_name,
            "command": command,
            "status": status,
            "documented_entry": spec["documented_entry"],
            "handoff_command": _handoff_command(worker_id),
            "launch_policy": "manual_operator_action_required",
        })
    return {"runtimes": rows, "probe_requested": probe}


def _render_human(result: dict) -> str:
    lines = ["Runtime adapter preflight (no runtime launched)"]
    for row in result["runtimes"]:
        lines.append(f"- {row['runtime']}: {row['status']} (command: {row['command']})")
        lines.append(f"  handoff: {row['handoff_command']}")
    if result["probe_requested"]:
        lines.append("Probe used only '--version'; its output is intentionally not retained.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only OpenCode/MiMo runtime adapter preflight.")
    parser.add_argument("--runtime", choices=sorted(RUNTIMES), action="append", help="Check only one runtime; repeatable.")
    parser.add_argument("--worker-id", default=DEFAULT_WORKER_ID, help="Worker ID rendered into the safe handoff template.")
    parser.add_argument("--probe", action="store_true", help="Opt in to a bounded '<command> --version' health probe.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable safe output.")
    args = parser.parse_args()
    result = build_preflight(args.runtime or list(RUNTIMES), args.worker_id, probe=args.probe)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else _render_human(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
