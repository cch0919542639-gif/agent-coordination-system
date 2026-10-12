"""Exercise the PowerShell entrypoint with fake Hermes and polling commands."""

import json
import importlib.util
import shutil
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


def test_hermes_launcher_boundaries(tmp_path, monkeypatch):
    monkeypatch.setenv("COORDINATION_PYTHON", sys.executable)
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is required for the Windows launcher")
    source = Path(__file__).resolve().parents[2] / "integrations/hermes-coordination-worker"
    integration = tmp_path / "integrations/hermes-coordination-worker"
    integration.mkdir(parents=True)
    for name in ("run-controlled-worker.ps1", "SKILL.md"):
        shutil.copyfile(source / name, integration / name)
    templates = tmp_path / "coordination/templates"
    templates.mkdir(parents=True)
    shutil.copyfile(source.parents[1] / "coordination/templates/delivery-report.md", templates / "delivery-report.md")
    (integration / "run-session.ps1").write_text(
        "param([string]$Model, [string]$Prompt, [string]$TaskId, [string]$PayloadId)\n"
        "hermes session --model $Model --query $Prompt\n"
        "exit $LASTEXITCODE\n"
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(source.parents[1] / "scripts/resolve-python.ps1", scripts / "resolve-python.ps1")
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

    ready_dir = tmp_path / "coordination/task-board/ready"
    ready_dir.mkdir(parents=True)
    (ready_dir / "assigned.md").write_text("---\ntask_id: assigned\nowner: hermes-coordination-pilot\nstatus: READY\nallowed_scope:\n  - coordination/evidence/result.json\n---\n## Objective\n\nProduce result.json with value21.\n")

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
            assert arguments[arguments.index("--model") + 1] == "openai/gpt-oss-20b"
            assert "--oneshot" not in arguments and "--yolo" not in arguments
            assert "worker activate hermes-coordination-pilot --json" in arguments[-1]
            assert "Produce result.json with value21." in arguments[-1]
            assert "coordination/evidence/result.json" in arguments[-1]
            assert "claim_task.py --task-id assigned --agent hermes-coordination-pilot" in arguments[-1]
            assert "- Task ID: assigned" in arguments[-1]
            assert "## Artifact Paths" in arguments[-1]
            assert "## Recommended Handoff" in arguments[-1]
        else:
            assert not calls

    payload_id = "0123456789abcdef"
    inbox = tmp_path / f"coordination/monitor/inbox/hermes-coordination-pilot/{payload_id}.json"
    inbox.parent.mkdir(parents=True)
    task = tmp_path / "coordination/task-board/ready/pilot.md"
    task.parent.mkdir(parents=True, exist_ok=True)
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
        task.write_text(f"---\ntask_id: pilot\nowner: {owner}\nstatus: {status}\nallowed_scope:\n  - coordination/evidence/result.json\n---\n## Objective\n\nProduce result.json.\n")
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
        claimed.write_text(f"---\ntask_id: pilot\nowner: hermes-coordination-pilot\nstatus: {status}\nallowed_scope:\n  - coordination/evidence/result.json\n---\n## Objective\n\nProduce result.json.\n")
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
    retry_margins = []
    monkeypatch.setattr(module.time, "sleep", lambda delay: retry_margins.append(delay))
    output_limits = {"max_bytes": 50000}
    receipt = {"ready": False}
    interrupted = []
    compression_calls = []
    auxiliary_calls = []
    client_options = []
    def original_compression(**kwargs):
        auxiliary_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop")])
    def direct_create(**kwargs):
        compression_calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop")])
    compression_module = SimpleNamespace(call_llm=original_compression)
    original_enabled = lambda: False
    original_nudge = lambda **kwargs: None
    verification_module = SimpleNamespace(verify_on_stop_enabled=original_enabled, build_verify_on_stop_nudge=original_nudge)
    monkeypatch.setitem(sys.modules, "agent", SimpleNamespace(context_compressor=compression_module, verification_stop=verification_module))
    monkeypatch.setitem(sys.modules, "agent.context_compressor", compression_module)
    monkeypatch.setitem(sys.modules, "agent.verification_stop", verification_module)
    monkeypatch.setattr(module, "submitted_receipt", lambda task, payload: receipt["ready"])
    results = [
        {"completed": False, "failed": True, "receipt": True},
        {"completed": True, "failed": False, "receipt": False, "failure_reason": "private-content",
         "final_response": "private-content HTTP 429 Limit 1000, Requested 1046 tokens per minute private-content",
         "input_tokens": 3000, "output_tokens": 900, "turn_exit_reason": "text_response(private-content)"},
    ]

    class FakeCompressor(SimpleNamespace):
        _SUMMARY_INPUT_MAX_CHARS = 160000

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=direct_create))

        def with_options(self, **kwargs):
            client_options.append(kwargs)
            return self

    class FakeAgent:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.kwargs = kwargs
            receipt["ready"] = False
            self.context_compressor = FakeCompressor(threshold_tokens=None)
            self.client = FakeClient()

        def run_conversation(self, prompt):
            assert verification_module.verify_on_stop_enabled() is True
            for attempt in range(3):
                assert "same task" in verification_module.build_verify_on_stop_nudge(attempts=attempt)
            assert verification_module.build_verify_on_stop_nudge(attempts=3) is None
            assert self.context_compressor.threshold_tokens_cap == 5500
            assert self.context_compressor.threshold_tokens == 5500
            assert self.compression_enabled is True and self.max_compression_attempts == 24
            assert output_limits["max_bytes"] == 2500
            assert self.context_compressor.protect_first_n == 1
            assert self.context_compressor._effective_protect_first_n([]) == 1
            assert self.context_compressor.protect_last_n == 2
            assert self.context_compressor.summary_model == self.kwargs["model"]
            assert self.context_compressor._SUMMARY_INPUT_MAX_CHARS == 6000
            assert self.context_compressor._micro_compact_enabled is False
            assert compression_module.call_llm is not original_compression
            compression_module.call_llm(task="compression", model="configured-default",
                                        messages=[{"role": "user", "content": "Target ~2000 tokens."}])
            compression_module.call_llm(task="title_generation", messages=[{"role": "user", "content": "title"}])
            assert self._api_max_retries == 3
            assert prompt == "bounded assigned task"
            assert self._build_system_prompt_parts("scoped context")["context"] == "scoped context"
            assert "one assigned task packet" in self._build_system_prompt()
            assert self._cached_system_prompt_static == module.WORKER_BRIEF
            self._invoke_api_request_error_hook(
                status_code=413,
                error_message="private-content Limit 8000, Requested 9200 tokens per minute private-content",
            )
            self._invoke_api_request_error_hook(status_code=429, error_message="private-content tokens per minute TPM")
            self._invoke_api_request_error_hook(status_code=429, error_message="private-content tokens per day TPD")
            result = results.pop(0)
            receipt["ready"] = result.pop("receipt")
            if receipt["ready"]:
                assert verification_module.build_verify_on_stop_nudge(attempts=0) is None
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
    assert compression_module.call_llm is original_compression
    assert verification_module.verify_on_stop_enabled is original_enabled
    assert verification_module.build_verify_on_stop_nudge is original_nudge
    assert FakeCompressor._SUMMARY_INPUT_MAX_CHARS == 160000
    assert module.run_session("openai/gpt-oss-120b", "bounded assigned task", "fake-task", "abcdef0123456789") == 1
    assert compression_module.call_llm is original_compression
    assert verification_module.verify_on_stop_enabled is original_enabled
    assert verification_module.build_verify_on_stop_nudge is original_nudge
    assert FakeCompressor._SUMMARY_INPUT_MAX_CHARS == 160000
    emitted = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert emitted[0] == {"diagnostics": ["HTTP 413", "Limit 8000, Requested 9200", "tokens per minute"]}
    assert "private-content" not in json.dumps(emitted)
    assert retry_margins == [5, 5]
    metadata = emitted[-1]
    assert metadata["diagnostics"] == ["HTTP 429", "Limit 1000, Requested 1046", "tokens per minute"]
    assert metadata["failure_reason"] == "missing_review_receipt"
    assert metadata["turn_exit_category"] == "text_response"
    assert metadata["input_tokens"] == 3000 and metadata["output_tokens"] == 900
    assert "private-content" not in json.dumps(metadata)
    assert interrupted == [True]
    assert len(compression_calls) == 2
    for call, model, effort in zip(compression_calls, ("qwen/qwen3.8-27b", "openai/gpt-oss-120b"), ("none", "low")):
        assert call["model"] == model and call["max_tokens"] == 768
        assert call["reasoning_effort"] == effort and call["timeout"] == 60
        assert "Target ~400 tokens." in call["messages"][0]["content"]
    assert len(auxiliary_calls) == 2 and all(call["task"] == "title_generation" for call in auxiliary_calls)
    assert client_options == [{"max_retries": 2, "timeout": 60}] * 2
    for kwargs, effort in zip((calls[0], calls[3]), ("none", "low")):
        assert kwargs["enabled_toolsets"] == ["terminal"]
        assert kwargs["max_iterations"] == 24 and kwargs["max_tokens"] == 768
        assert kwargs["request_overrides"] == {"parallel_tool_calls": False, "max_tokens": 768, "reasoning_effort": effort}
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


def test_compression_pins_worker_runtime_and_rejects_truncated_summary():
    source = Path(__file__).resolve().parents[2] / "integrations/hermes-coordination-worker/run_session.py"
    spec = importlib.util.spec_from_file_location("hermes_compression", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runtime = {"provider": "custom", "base_url": "https://api.groq.com/openai/v1",
               "api_key": "fake-test-only", "api_mode": "chat_completions"}
    messages = [{"role": "user", "content": "Target ~2000 tokens. Preserve task-one."}]
    calls = []
    result = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop")])

    def native_call(**kwargs):
        calls.append(kwargs)
        return result

    assert module.bounded_compression(native_call, runtime, "qwen/qwen3.8-27b",
                                      task="compression", model="other-model", provider="other-provider",
                                      messages=messages, extra_body={"test_flag": True}, max_tokens=5000) is result
    request = calls[-1]
    assert all(request[key] == value for key, value in runtime.items())
    assert request["model"] == "qwen/qwen3.8-27b" and request["max_tokens"] == 768
    # Groq's native auxiliary builder drops ordinary max_tokens, so the
    # extra_body wire cap is required as well as the call argument.
    assert request["extra_body"] == {"test_flag": True, "max_tokens": 768, "reasoning_effort": "none"}
    assert "Target ~400 tokens." in request["messages"][0]["content"]
    assert messages[0]["content"] == "Target ~2000 tokens. Preserve task-one."

    result.choices[0].finish_reason = "length"
    with pytest.raises(RuntimeError, match="incomplete summary rejected"):
        module.bounded_compression(native_call, runtime, "qwen/qwen3.8-27b", task="compression", messages=messages)
    passthrough = {"task": "title_generation", "messages": messages, "max_tokens": 321}
    assert module.bounded_compression(native_call, runtime, "qwen/qwen3.8-27b", **passthrough) is result
    assert calls[-1] == passthrough


def test_installed_sdk_two_compactions_keep_the_single_assignment_offline():
    hermes = shutil.which("hermes")
    python = Path(hermes).with_name("python.exe") if hermes else None
    if python is None or not python.is_file():
        pytest.skip("Installed Hermes SDK Python is required for the native compaction regression")
    # An explicit context size and fake summarizer isolate the native splitter.
    # Block connections as well, so this test cannot consume provider quota.
    probe = '''
import json
import socket
from agent.context_compressor import ContextCompressor

network_attempts = []
def deny_network(*args, **kwargs):
    network_attempts.append(True)
    raise AssertionError("Offline regression cannot contact a provider")
socket.socket.connect = deny_network
socket.create_connection = deny_network

compressor = ContextCompressor(model="openai/gpt-oss-120b", config_context_length=16000,
    protect_first_n=1, protect_last_n=2, quiet_mode=True, min_tail_user_messages=0)
compressor._effective_protect_first_n = lambda _messages=None: 1
compressor.tail_token_budget = 400
compressor._generate_summary = lambda *args, **kwargs: "Accepted first stage. Pending exact assigned task."
head = {"role": "user", "content": "Process ONLY task offline-one, preserve owner and allowed scope."}
messages = [{"role": "system", "content": "Bounded worker."}, head]
results = []
for cycle in range(2):
    for step in range(15):
        call_id = f"call-{cycle}-{step}"
        messages.extend([
            {"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function",
                "function": {"name": "terminal", "arguments": '{"command":"echo stage"}'}}]},
            {"role": "tool", "tool_call_id": call_id, "name": "terminal", "content": "observation " * 300},
        ])
    before = len(messages)
    messages = compressor.compress(messages, current_tokens=9000, force=True)
    assert messages[0]["role"] == "system" and messages[1] == head
    assert sum(message == head for message in messages) == 1
    assert len(messages) < before
    results.append({"before": before, "after": len(messages)})
assert compressor.compression_count == 2
assert not network_attempts
print(json.dumps(results))
'''
    result = subprocess.run([str(python), "-c", probe], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    passes = json.loads(result.stdout.strip().splitlines()[-1])
    assert len(passes) == 2 and all(item["after"] < item["before"] for item in passes)


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
