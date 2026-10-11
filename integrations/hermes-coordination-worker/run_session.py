"""One bounded Hermes session using the installed runtime, without CLI context."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

WORKER_BRIEF = """You are Hermes, a controlled repository coordination worker.
Follow the supplied repository skill and the one assigned task packet.
Read required context before claiming. Use tools for real execution and record
only verifiable evidence. Preserve existing edits and task ownership. Stop
after submission to review. Never select another task, approve tools, accept,
review, merge, commit, push, launch agents, or disclose credentials/transcripts.
The terminal is Git Bash on Windows; use quoted forward-slash paths.
The only tool names are terminal and process. Use terminal with Python's
standard library for every file operation. Preserve the delivery template's
literal labels and replace inaccurate evidence rather than appending to it.
"""


def status_metadata(_kind, message):
    flags = re.findall(
        r"Rate limited|Provider overloaded|Waiting [0-9.]+s|attempt \d+/\d+|HTTP \d{3}",
        str(message), re.IGNORECASE,
    )
    if flags:
        print(json.dumps({"status": flags}), flush=True)


def step_metadata(count, tools):
    codes = []
    for tool in tools:
        try:
            result = json.loads(tool.get("result") or "{}")
        except (TypeError, ValueError):
            continue
        if isinstance(result, dict):
            codes.append({"exit_code": result.get("exit_code"), "error": bool(result.get("error"))})
    print(json.dumps({"api_step": count, "tool_results": codes}), flush=True)


def submitted_receipt(task_id, payload_id, root=None):
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", task_id) or not re.fullmatch(r"[a-f0-9]{16}", payload_id):
        return False
    root = root or Path(__file__).resolve().parents[2]
    scripts_path = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from coordination_common import load_task
    from event_routing import load_delivery_state_map

    delivery = load_delivery_state_map().get(payload_id)
    if delivery is None or any(getattr(delivery, key) != value for key, value in {
        "status": "acknowledged", "task_id": task_id, "project_id": "agent-coordination-system",
        "owner": "hermes-coordination-pilot", "destination": "registered_worker",
    }.items()):
        return False

    inbox = root / "coordination/monitor/inbox/hermes-coordination-pilot" / f"{payload_id}.json"
    try:
        payload = json.loads(inbox.read_text(encoding="utf-8"))
        if any(payload.get(key) != value for key, value in {
            "worker_id": "hermes-coordination-pilot", "project_id": "agent-coordination-system",
            "task_id": task_id, "payload_id": payload_id,
        }.items()):
            return False
        original = payload.get("task_card_path", "")
        if not re.fullmatch(r"coordination/task-board/ready/[^/\\]+\.md", original):
            return False
        card = root / original.replace("/ready/", "/review/")
        if (root / original).exists() or (root / original.replace("/ready/", "/in_progress/")).exists():
            return False
        header, _body = load_task(card)
        return (
            header.get("task_id") == task_id and header.get("owner") == "hermes-coordination-pilot"
            and header.get("status") == "REVIEW"
            and (root / "coordination/delivery" / f"{task_id}-delivery-report.md").is_file()
        )
    except (OSError, ValueError, TypeError):
        return False


def run_session(model, prompt, task_id, payload_id):
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from run_agent import AIAgent
    from tools.terminal_tool import cleanup_all_environments, set_approval_callback
    from tools.tool_output_limits import get_tool_output_limits

    if os.environ.get("HERMES_YOLO_MODE", "").lower() in {"1", "true", "yes", "on"}:
        raise RuntimeError("Controlled sessions cannot enable automatic approval.")
    config = load_config()
    provider = config.get("model", {}).get("provider", "auto")
    runtime = resolve_runtime_provider(requested=provider, target_model=model)
    set_approval_callback(lambda *_args, **_kwargs: "deny")
    output_limits = get_tool_output_limits()
    original_limits = output_limits.copy()
    output_limits["max_bytes"] = 2500

    class WorkerAgent(AIAgent):
        # The full interactive persona cannot fit this provider's worker budget.
        def _build_system_prompt_parts(self, system_message=None):
            return {"stable": WORKER_BRIEF, "context": system_message or "", "volatile": ""}

        def _build_system_prompt(self, system_message=None):
            self._cached_system_prompt_static = WORKER_BRIEF
            return WORKER_BRIEF + ("\n" + system_message if system_message else "")

        def _buffer_status(self, message):
            status_metadata("lifecycle", message)
            super()._buffer_status(message)

    agent = None
    def stop_on_review(*_args):
        if agent is not None and submitted_receipt(task_id, payload_id):
            agent.interrupt()

    try:
        agent = WorkerAgent(
            model=model,
            api_key=runtime.get("api_key"),
            base_url=runtime.get("base_url"),
            provider=runtime.get("provider"),
            requested_provider=runtime.get("requested_provider"),
            api_mode=runtime.get("api_mode"),
            credential_pool=runtime.get("credential_pool"),
            enabled_toolsets=["terminal"],
            max_iterations=24,
            max_tokens=4096,
            reasoning_config={"effort": "low"},
            request_overrides={
                "parallel_tool_calls": False, "max_tokens": 4096,
                "reasoning_effort": "none" if model == "qwen/qwen3.8-27b" else "low",
            },
            platform="cron",
            skip_context_files=True,
            skip_memory=True,
            load_soul_identity=False,
            session_db=None,
            save_trajectories=False,
            quiet_mode=True,
            step_callback=step_metadata,
            status_callback=status_metadata,
            tool_complete_callback=stop_on_review,
        )
        # Groq's observed 8K TPM cap is smaller than the model's context window.
        agent.context_compressor.threshold_tokens_cap = 3000
        agent.context_compressor.threshold_tokens = 3000
        # The default 20-message protected tail leaves short worker runs
        # with nothing eligible for compression before Groq rejects them.
        agent.context_compressor.protect_first_n = 1
        agent.context_compressor.protect_last_n = 2
        agent._api_max_retries = 3
        agent.suppress_status_output = True
        result = agent.run_conversation(prompt)
        receipt = submitted_receipt(task_id, payload_id)
        metadata = {"completed": receipt, "failed": not receipt, "api_calls": result.get("api_calls")}
        if receipt:
            metadata["stop_reason"] = "review_receipt"
        else:
            error = str(result.get("error", ""))
            metadata["failure_reason"] = result.get("failure_reason") or "missing_review_receipt"
            metadata["diagnostics"] = re.findall(
                r"(?:HTTP|Error code:)\s*\d{3}|Limit \d+(?:, Used \d+)?, Requested \d+|"
                r"rate_limit_exceeded|tool_use_failed|payload too large|maximum context length|"
                r"tool call validation failed|failed to call a function|failed to generate|"
                r"invalid_request_error|failed_generation|context_length_exceeded|"
                r"attempted to call tool '[a-zA-Z0-9_.-]{1,64}'",
                error,
                re.IGNORECASE,
            )
        print(json.dumps(metadata))
        return 0 if receipt else 1
    finally:
        if agent is not None:
            agent.close()
        cleanup_all_environments()
        set_approval_callback(None)
        output_limits.clear()
        output_limits.update(original_limits)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--payload-id", required=True)
    args = parser.parse_args()
    raise SystemExit(run_session(args.model, args.prompt, args.task_id, args.payload_id))
