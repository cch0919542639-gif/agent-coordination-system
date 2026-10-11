"""Exercise the PowerShell entrypoint with fake Hermes and polling commands."""

import json
import importlib.util
import shutil
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


def test_hermes_launcher_boundaries(tmp_path):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is required for the Windows launcher")
    source = Path(__file__).resolve().parents[2] / "integrations/hermes-coordination-worker"
    integration = tmp_path / "integrations/hermes-coordination-worker"
    integration.mkdir(parents=True)
    for name in ("run-controlled-worker.ps1", "SKILL.md"):
        shutil.copyfile(source / name, integration / name)
    (integration / "run-session.ps1").write_text(
        "param([string]$Model, [string]$Prompt, [string]$TaskId, [string]$PayloadId)\n"
        "hermes session --model $Model --query $Prompt\n"
        "exit $LASTEXITCODE\n"
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    poll = scripts / "run_python.ps1"
    log = tmp_path / "calls.jsonl"
    runner = tmp_path / "runner.ps1"
    runner.write_text(
        "param([switch]$Run, [string]$ResumePayload)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "function hermes {\n"
        "  ConvertTo-Json -Compress -InputObject @($args) | Add-Content -LiteralPath "
        "(Join-Path $PSScriptRoot 'calls.jsonl')\n"
        "  $global:LASTEXITCODE = 0\n"
        "}\n"
        "$parameters = @{Run = $Run}\n"
        "if ($ResumePayload) { $parameters.ResumePayload = $ResumePayload }\n"
        "& (Join-Path $PSScriptRoot 'integrations/hermes-coordination-worker/run-controlled-worker.ps1') @parameters\n"
        "exit $LASTEXITCODE\n",
        encoding="utf-8",
    )

    cases = [
        (False, None, 0, 0, "version"),
        (True, {"worker_id": "hermes-coordination-pilot", "notifications": []}, 0, 0, "idle"),
        (True, {"worker_id": "hermes-coordination-pilot", "notifications": [{"task_id": "assigned", "payload_id": "abcdef0123456789", "project_id": "agent-coordination-system"}]}, 0, 0, "run"),
        (True, {"worker_id": "hermes-coordination-pilot", "notifications": [{"task_id": "assigned", "payload_id": "abcdef0123456789", "project_id": "other-project"}]}, 0, 1, "denied"),
        (True, {"worker_id": "hermes-coordination-pilot", "notifications": [{"task_id": "assigned"}]}, 0, 1, "denied"),
        (True, {"worker_id": "other", "notifications": []}, 0, 1, "denied"),
        (True, "invalid JSON", 0, 1, "denied"),
        (True, None, 7, 7, "denied"),
    ]
    for run, response, poll_exit, expected_exit, mode in cases:
        log.unlink(missing_ok=True)
        poll.write_text(
            "Write-Output '" + json.dumps(response).replace("'", "''") + "'\n"
            f"exit {poll_exit}\n",
            encoding="utf-8",
        )
        command = [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(runner)]
        if run:
            command.append("-Run")
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        assert result.returncode == expected_exit, result.stderr
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        if mode == "version":
            assert calls == [["--version"]]
        elif mode == "run":
            assert len(calls) == 1
            arguments = calls[0]
            assert arguments[0] == "session"
            assert arguments[arguments.index("--model") + 1] == "qwen/qwen3.8-27b"
            assert "--oneshot" not in arguments and "--yolo" not in arguments
            assert "worker activate hermes-coordination-pilot --json" in arguments[-1]
        else:
            assert not calls

    payload_id = "0123456789abcdef"
    inbox = tmp_path / f"coordination/monitor/inbox/hermes-coordination-pilot/{payload_id}.json"
    inbox.parent.mkdir(parents=True)
    task = tmp_path / "coordination/task-board/ready/pilot.md"
    task.parent.mkdir(parents=True)
    for owner, status, path, expected_exit in [
        ("hermes-coordination-pilot", "READY", "coordination/task-board/ready/pilot.md", 0),
        ("other", "READY", "coordination/task-board/ready/pilot.md", 1),
        ("hermes-coordination-pilot", "IN_PROGRESS", "coordination/task-board/ready/pilot.md", 1),
        ("hermes-coordination-pilot", "READY", "coordination/task-board/ready/../../pilot.md", 1),
    ]:
        log.unlink(missing_ok=True)
        inbox.write_text(json.dumps({
            "worker_id": "hermes-coordination-pilot", "project_id": "agent-coordination-system",
            "payload_id": payload_id, "task_id": "pilot", "task_card_path": path,
        }))
        task.write_text(f"---\ntask_id: pilot\nowner: {owner}\nstatus: {status}\n---\n")
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(runner), "-Run", "-ResumePayload", payload_id],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == expected_exit, result.stderr
        if expected_exit == 0:
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            assert len(calls) == 1
            assert "Do not activate again" in calls[0][-1]
        else:
            assert not log.exists()

    # Claim moved the original card; recovery must not activate or claim again.
    task.unlink()
    claimed = tmp_path / "coordination/task-board/in_progress/pilot.md"
    claimed.parent.mkdir()
    inbox.write_text(json.dumps({
        "worker_id": "hermes-coordination-pilot", "project_id": "agent-coordination-system",
        "payload_id": payload_id, "task_id": "pilot", "task_card_path": "coordination/task-board/ready/pilot.md",
    }))
    for status, expected_exit in [("IN_PROGRESS", 0), ("REVIEW", 1)]:
        log.unlink(missing_ok=True)
        claimed.write_text(f"---\ntask_id: pilot\nowner: hermes-coordination-pilot\nstatus: {status}\n---\n")
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(runner), "-Run", "-ResumePayload", payload_id],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == expected_exit, result.stderr
        if expected_exit == 0:
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            assert len(calls) == 1 and "do not claim again" in calls[0][-1]
        else:
            assert not log.exists()


def test_hermes_session_runtime_boundary(monkeypatch, capsys):
    source = Path(__file__).resolve().parents[2] / "integrations/hermes-coordination-worker/run_session.py"
    spec = importlib.util.spec_from_file_location("hermes_worker_session", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.status_metadata("lifecycle", "private-content Rate limited. Waiting 12.5s (attempt 1/2)")
    status = json.loads(capsys.readouterr().out)
    assert status == {"status": ["Rate limited", "Waiting 12.5s", "attempt 1/2"]}
    module.step_metadata(2, [{"result": '{"exit_code": 1, "output": "private-content"}'}])
    assert json.loads(capsys.readouterr().out) == {"api_step": 2, "tool_results": [{"exit_code": 1, "error": False}]}
    calls = []
    output_limits = {"max_bytes": 50000}
    receipt = {"ready": False}
    interrupted = []
    monkeypatch.setattr(module, "submitted_receipt", lambda task, payload: receipt["ready"])
    results = [
        {"completed": False, "failed": True, "receipt": True},
        {"completed": True, "failed": False, "receipt": False},
    ]

    class FakeAgent:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.kwargs = kwargs
            receipt["ready"] = False
            self.context_compressor = SimpleNamespace(threshold_tokens=None)

        def run_conversation(self, prompt):
            assert self.context_compressor.threshold_tokens_cap == 3000
            assert self.context_compressor.threshold_tokens == 3000
            assert output_limits["max_bytes"] == 2500
            assert self.context_compressor.protect_first_n == 1
            assert self.context_compressor.protect_last_n == 2
            assert self._api_max_retries == 3
            assert prompt == "bounded assigned task"
            assert self._build_system_prompt_parts("scoped context")["context"] == "scoped context"
            assert "one assigned task packet" in self._build_system_prompt()
            assert self._cached_system_prompt_static == module.WORKER_BRIEF
            result = results.pop(0)
            receipt["ready"] = result.pop("receipt")
            self.kwargs["tool_complete_callback"]("tool-id", "terminal", {}, "private-output")
            return result

        def interrupt(self):
            interrupted.append(True)

        def close(self):
            calls.append("closed")

    approvals = []
    monkeypatch.setitem(sys.modules, "hermes_cli.config", SimpleNamespace(load_config=lambda: {"model": {"provider": "groq"}}))
    monkeypatch.setitem(sys.modules, "hermes_cli.runtime_provider", SimpleNamespace(resolve_runtime_provider=lambda **_: {"provider": "custom", "api_key": "fake-only"}))
    monkeypatch.setitem(sys.modules, "run_agent", SimpleNamespace(AIAgent=FakeAgent))
    monkeypatch.setitem(sys.modules, "tools.tool_output_limits", SimpleNamespace(get_tool_output_limits=lambda: output_limits))
    monkeypatch.setitem(sys.modules, "tools.terminal_tool", SimpleNamespace(
        cleanup_all_environments=lambda: calls.append("cleaned"),
        set_approval_callback=lambda callback: approvals.append(callback),
    ))
    monkeypatch.delenv("HERMES_YOLO_MODE", raising=False)
    assert module.run_session("qwen/qwen3.8-27b", "bounded assigned task", "fake-task", "abcdef0123456789") == 0
    assert module.run_session("qwen/qwen3.8-27b", "bounded assigned task", "fake-task", "abcdef0123456789") == 1
    assert interrupted == [True]
    for kwargs in (calls[0], calls[3]):
        assert kwargs["enabled_toolsets"] == ["terminal"]
        assert kwargs["max_iterations"] == 24 and kwargs["max_tokens"] == 4096
        assert kwargs["request_overrides"] == {"parallel_tool_calls": False, "max_tokens": 4096, "reasoning_effort": "none"}
        assert kwargs["platform"] == "cron" and kwargs["skip_context_files"]
        assert kwargs["skip_memory"] and not kwargs["save_trajectories"]
        assert kwargs["session_db"] is None
    assert approvals[0]("dangerous command", "description") == "deny"
    assert approvals[-1] is None
    assert output_limits == {"max_bytes": 50000}
    monkeypatch.setenv("HERMES_YOLO_MODE", "1")
    with pytest.raises(RuntimeError, match="automatic approval"):
        module.run_session("openai/gpt-oss-20b", "bounded assigned task", "fake-task", "abcdef0123456789")
    assert len(calls) == 6


def test_review_receipt_requires_matching_handoff(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "integrations/hermes-coordination-worker/run_session.py"
    spec = importlib.util.spec_from_file_location("hermes_receipt", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload_id = "abcdef0123456789"
    delivery = {"status": "acknowledged", "task_id": "fake-task", "project_id": "agent-coordination-system", "owner": "hermes-coordination-pilot", "destination": "registered_worker"}
    records = {payload_id: SimpleNamespace(**delivery)}
    monkeypatch.setitem(sys.modules, "event_routing", SimpleNamespace(load_delivery_state_map=lambda: records))
    inbox = tmp_path / "coordination/monitor/inbox/hermes-coordination-pilot" / f"{payload_id}.json"
    inbox.parent.mkdir(parents=True)
    original = "coordination/task-board/ready/2026-10-11_fake-task_handoff.md"
    card = tmp_path / original.replace("/ready/", "/review/")
    card.parent.mkdir(parents=True)
    report = tmp_path / "coordination/delivery/fake-task-delivery-report.md"
    report.parent.mkdir(parents=True)
    report.write_text("delivery evidence")
    payload = {"task_id": "fake-task", "payload_id": payload_id, "worker_id": "hermes-coordination-pilot", "project_id": "agent-coordination-system", "task_card_path": original}
    card.write_text("---\ntask_id: fake-task\nowner: hermes-coordination-pilot\nstatus: REVIEW\n---\n")
    inbox.write_text(json.dumps(payload))
    assert module.submitted_receipt("fake-task", payload_id, tmp_path)
    for key, bad in (("status", "pending"), ("task_id", "other-task"), ("project_id", "other-project"), ("owner", "other-worker"), ("destination", "orchestrator")):
        records[payload_id] = SimpleNamespace(**{**delivery, key: bad})
        assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    records.clear()
    assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    records[payload_id] = SimpleNamespace(**delivery)
    for key, bad in (("worker_id", "another-worker"), ("project_id", "another-project"), ("task_id", "another-task"), ("payload_id", "0000000000000000"), ("task_card_path", "coordination/task-board/ready/../other.md")):
        inbox.write_text(json.dumps({**payload, key: bad}))
        assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    inbox.write_text(json.dumps(payload))
    card.write_text("---\ntask_id: fake-task\nowner: another-worker\nstatus: REVIEW\n---\n")
    assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    card.write_text("---\ntask_id: fake-task\nowner: hermes-coordination-pilot\nstatus: IN_PROGRESS\n---\n")
    assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    card.write_text("---\ntask_id: fake-task\nowner: hermes-coordination-pilot\nstatus: REVIEW\n---\n")
    ready = tmp_path / original
    ready.parent.mkdir(parents=True)
    ready.write_text("duplicate")
    assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
    ready.unlink()
    report.unlink()
    assert not module.submitted_receipt("fake-task", payload_id, tmp_path)
