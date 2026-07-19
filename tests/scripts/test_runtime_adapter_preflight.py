"""Focused safety coverage for optional local runtime adapter discovery."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from runtime_adapter_preflight import _probe_version, build_preflight


def test_default_preflight_discovers_without_running_probe() -> None:
    def lookup(command: str) -> str | None:
        return "present" if command == "mimo" else None

    def forbidden_probe(_command: str) -> str:
        raise AssertionError("default preflight must not invoke a runtime")

    result = build_preflight(["opencode", "mimo"], "worker-a", command_lookup=lookup, version_probe=forbidden_probe)

    assert [row["status"] for row in result["runtimes"]] == ["unavailable", "discoverable_unverified"]
    assert result["runtimes"][1]["handoff_command"].endswith("worker-a --json")
    assert all(row["launch_policy"] == "manual_operator_action_required" for row in result["runtimes"])


def test_opt_in_probe_reports_only_safe_category() -> None:
    result = build_preflight(
        ["mimo"], probe=True, command_lookup=lambda _command: "present",
        version_probe=lambda _command: "probe_failed",
    )

    assert result["probe_requested"] is True
    assert result["runtimes"][0]["status"] == "probe_failed"
    assert "present" not in str(result)


def test_unavailable_runtime_is_not_probed() -> None:
    def forbidden_probe(_command: str) -> str:
        raise AssertionError("unavailable executable must not be invoked")

    result = build_preflight(["opencode"], probe=True, command_lookup=lambda _command: None, version_probe=forbidden_probe)

    assert result["runtimes"][0]["status"] == "unavailable"


def test_windows_probe_uses_resolved_wrapper_in_powershell() -> None:
    completed = type("Completed", (), {"returncode": 0})()
    with patch("runtime_adapter_preflight.os.name", "nt"), patch(
        "runtime_adapter_preflight.subprocess.run", return_value=completed
    ) as run:
        assert _probe_version(r"C:\tools\mimo.cmd") == "available"

    assert run.call_args.args[0][-1] == "& 'C:\\tools\\mimo.cmd' --version"
