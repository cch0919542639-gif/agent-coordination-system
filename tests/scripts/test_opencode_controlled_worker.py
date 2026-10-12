"""Exercise the Windows launcher without invoking an installed model."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def test_opencode_launcher_requires_a_verified_exact_handoff(tmp_path):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is required for the Windows launcher")
    source = Path(__file__).resolve().parents[2]
    integration = tmp_path / "integrations/opencode-coordination-worker"
    integration.mkdir(parents=True)
    launcher = integration / "run-controlled-worker.ps1"
    shutil.copyfile(source / "integrations/opencode-coordination-worker/run-controlled-worker.ps1", launcher)
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    (binary_dir / "opencode.ps1").write_text(
        "ConvertTo-Json -Compress -InputObject @($args) | Add-Content -LiteralPath $env:OPENCODE_TEST_CALLS\n"
        "exit ([int]$env:OPENCODE_TEST_EXIT)\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(source / "scripts/resolve-python.ps1", scripts / "resolve-python.ps1")
    (scripts / "run_python.ps1").write_text(
        "ConvertTo-Json -Compress -InputObject @($args) | Add-Content -LiteralPath $env:OPENCODE_TEST_VERIFY\n"
        "exit ([int]$env:OPENCODE_TEST_VERIFY_EXIT)\n", encoding="utf-8")
    calls_file, verify_file = tmp_path / "calls.jsonl", tmp_path / "verify.jsonl"
    payload_id = "abcdef0123456789"
    owner = "opencode-coordination-pilot"
    inbox = tmp_path / f"coordination/monitor/inbox/{owner}/{payload_id}.json"
    inbox.parent.mkdir(parents=True)
    ready = tmp_path / "coordination/task-board/ready/assigned.md"
    claimed = tmp_path / "coordination/task-board/in_progress/assigned.md"
    ready.parent.mkdir(parents=True)
    claimed.parent.mkdir(parents=True)

    def invoke(*arguments, model_exit=0, verified=True):
        calls_file.unlink(missing_ok=True)
        verify_file.unlink(missing_ok=True)
        environment = dict(os.environ,
                           COORDINATION_PYTHON=sys.executable,
                           PATH=str(binary_dir) + os.pathsep + os.environ.get("PATH", ""),
                           OPENCODE_TEST_CALLS=str(calls_file), OPENCODE_TEST_EXIT=str(model_exit),
                           OPENCODE_TEST_VERIFY=str(verify_file), OPENCODE_TEST_VERIFY_EXIT="0" if verified else "1")
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(launcher), *arguments],
            env=environment, capture_output=True, text=True, timeout=30)
        calls = [json.loads(line) for line in calls_file.read_text(encoding="utf-8-sig").splitlines()] if calls_file.exists() else []
        verifications = [json.loads(line) for line in verify_file.read_text(encoding="utf-8-sig").splitlines()] if verify_file.exists() else []
        return result, calls, verifications

    def handoff(*, state="READY", payload_changes=None, card_changes=None):
        payload = {"worker_id": owner, "project_id": "agent-coordination-system",
                   "payload_id": payload_id, "task_id": "assigned",
                   "task_card_path": "coordination/task-board/ready/assigned.md"}
        payload.update(payload_changes or {})
        inbox.write_text(json.dumps(payload), encoding="utf-8")
        ready.unlink(missing_ok=True)
        claimed.unlink(missing_ok=True)
        card = {"task_id": "assigned", "owner": owner, "status": state}
        card.update(card_changes or {})
        path = claimed if state == "IN_PROGRESS" else ready
        path.write_text("---\n" + "\n".join(f"{key}: {value}" for key, value in card.items()) + "\n---\n", encoding="utf-8")

    result, calls, verification = invoke()
    assert result.returncode == 0 and calls == [["--version"]] and verification == []
    result, calls, verification = invoke("-ResumePayload", payload_id)
    assert result.returncode != 0 and calls == [] and verification == []

    # Normal invocation remains one owner-strict activation; a fake CLI only
    # records its prompt and never touches a production inbox or model.
    result, calls, verification = invoke("-Run")
    assert result.returncode == 0 and len(calls) == 1 and verification == []
    assert "worker activate opencode-coordination-pilot --json" in calls[0][-1]

    for state in ("READY", "IN_PROGRESS"):
        handoff(state=state)
        result, calls, verification = invoke("-Run", "-ResumePayload", payload_id)
        assert result.returncode == 0, result.stderr
        assert len(calls) == len(verification) == 1
        arguments = calls[0]
        assert arguments[:4] == ["run", "--pure", "--dir", str(tmp_path)]
        assert arguments[arguments.index("--model") + 1] == "opencode/space-bunny-free"
        assert "Never activate again" in arguments[-1]
        assert "Process ONLY task assigned" in arguments[-1]
        if state == "IN_PROGRESS":
            assert "Do not claim again" in arguments[-1]
            assert "review-assigned.md" in arguments[-1]
        assert verification[0] == ["scripts/verify_worker_handoff.py", "--task-id", "assigned",
                                    "--owner", owner, "--payload-id", payload_id]

    for payload_changes, card_changes in [
        ({"worker_id": "other-worker"}, {}),
        ({"project_id": "other-project"}, {}),
        ({"payload_id": "0123456789abcdef"}, {}),
        ({"task_id": "../foreign-task"}, {}),
        ({"task_card_path": "coordination/task-board/ready/../../foreign.md"}, {}),
        ({"task_card_path": "coordination/task-board/review/assigned.md"}, {}),
        ({}, {"owner": "other-worker"}),
        ({}, {"task_id": "foreign-task"}),
        ({}, {"status": "REVIEW"}),
    ]:
        handoff(payload_changes=payload_changes, card_changes=card_changes)
        result, calls, verification = invoke("-Run", "-ResumePayload", payload_id)
        assert result.returncode != 0 and calls == [] and verification == [], result.stderr

    handoff()
    result, calls, verification = invoke("-Run", "-ResumePayload", payload_id, verified=False)
    assert result.returncode != 0 and calls == [] and len(verification) == 1
    result, calls, verification = invoke("-Run", "-ResumePayload", "invalid-id")
    assert result.returncode != 0 and calls == [] and verification == []
    ready.unlink()
    result, calls, verification = invoke("-Run", "-ResumePayload", payload_id)
    assert result.returncode != 0 and calls == [] and verification == []

    handoff()
    result, calls, verification = invoke("-Run", "-ResumePayload", payload_id, model_exit=23)
    assert result.returncode == 23 and len(calls) == len(verification) == 1
