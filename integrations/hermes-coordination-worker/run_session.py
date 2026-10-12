"""One bounded Hermes session using the installed runtime, without CLI context."""

import argparse
import json
import os
import re
import sys
import time
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

DIAGNOSTICS = (
    r"(?:HTTP|Error code:)\s*\d{3}|Limit \d+(?:, Used \d+)?, Requested \d+|"
    r"rate_limit_exceeded|tool_use_failed|payload too large|maximum context length|"
    r"tool call validation failed|failed to call a function|failed to generate|"
    r"invalid_request_error|failed_generation|context_length_exceeded|"
    r"tokens per (?:minute|day|second|hour)|requests per (?:minute|day|second|hour)|"
    r"\b(?:ITPM|OTPM|TPM|TPD|RPM|RPD|TPS|RPS)\b|try again in [0-9.hms ]{1,30}"
)


def bounded_compression(call, runtime, worker_model, **kwargs):
    """Keep native compaction within this worker's provider and output budget."""
    if kwargs.get("task") == "compression":
        kwargs.update(model=worker_model, provider=runtime.get("provider"),
                      base_url=runtime.get("base_url"), api_key=runtime.get("api_key"),
                      api_mode=runtime.get("api_mode"), max_tokens=768,
                      reasoning_config=None,
                      extra_body={**(kwargs.get("extra_body") or {}), "max_tokens": 768,
                                  "reasoning_effort": "none" if worker_model == "qwen/qwen3.8-27b" else "low"})
        kwargs["messages"] = [dict(message, content=re.sub(
            r"Target ~\d+ tokens\.", "Target ~400 tokens. Preserve task identity, constraints and next step; use concise bullets.",
            message["content"])) for message in kwargs["messages"]]
    result = call(**kwargs)
    if kwargs.get("task") == "compression" and getattr(result.choices[0], "finish_reason", None) == "length":
        raise RuntimeError("Controlled compression reached its output bound; incomplete summary rejected.")
    return result


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
            code = result.get("exit_code")
            codes.append({"exit_code": code if type(code) is int else None, "error": bool(result.get("error"))})
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
    import agent.context_compressor as compression_module
    import agent.verification_stop as verification_module

    if os.environ.get("HERMES_YOLO_MODE", "").lower() in {"1", "true", "yes", "on"}:
        raise RuntimeError("Controlled sessions cannot enable automatic approval.")
    config = load_config()
    provider = config.get("model", {}).get("provider", "auto")
    runtime = resolve_runtime_provider(requested=provider, target_model=model)
    set_approval_callback(lambda *_args, **_kwargs: "deny")
    output_limits = get_tool_output_limits()
    original_limits = output_limits.copy()
    output_limits["max_bytes"] = 2500
    original_compression = compression_module.call_llm
    original_verify_enabled = verification_module.verify_on_stop_enabled
    original_verify_nudge = verification_module.build_verify_on_stop_nudge
    def receipt_nudge(**kwargs):
        if kwargs.get("attempts", 0) >= 3 or submitted_receipt(task_id, payload_id):
            return None
        return (
            "The assigned task has no verified REVIEW receipt yet. Continue executing "
            "that same task with terminal: read required context, claim if READY, "
            "produce its artifact and templated delivery report, validate, and submit. "
            "Narration does not complete this task. Stop if actually blocked; record "
            "the blocker in your allowed progress file. Never process another task."
        )
    verification_module.verify_on_stop_enabled = lambda: True
    verification_module.build_verify_on_stop_nudge = receipt_nudge

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

        def _invoke_api_request_error_hook(self, **kwargs):
            error = f"HTTP {kwargs.get('status_code')} " + str(kwargs.get("error_message", ""))
            print(json.dumps({"diagnostics": re.findall(DIAGNOSTICS, error, re.IGNORECASE)}), flush=True)
            # Groq estimates a wait for the rejected request, while the SDK's
            # retry can grow by ~300 tokens. At8K TPM,5s adds ~667 tokens of
            # refill margin without raising the finite retry/session budgets.
            if kwargs.get("status_code") == 429 and re.search(r"tokens per minute|\b[IO]?TPM\b", error, re.IGNORECASE):
                time.sleep(5)

    agent = None
    compression_class = None
    original_input_bound = None
    def controlled_auxiliary(**kwargs):
        def direct(**bounded):
            if bounded.get("task") != "compression":
                return original_compression(**bounded)
            # Use the already-resolved client: the native auxiliary helper can
            # switch providers/models on capacity errors, even with explicit args.
            return agent.client.with_options(max_retries=2, timeout=60).chat.completions.create(
                model=model, messages=bounded["messages"], max_tokens=768,
                reasoning_effort="none" if model == "qwen/qwen3.8-27b" else "low", timeout=60,
            )
        return bounded_compression(direct, runtime, model, **kwargs)
    compression_module.call_llm = controlled_auxiliary
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
            max_tokens=768,
            reasoning_config={"effort": "low"},
            request_overrides={
                "parallel_tool_calls": False, "max_tokens": 768,
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
        agent.compression_enabled = True
        agent.max_compression_attempts = 24
        agent.context_compressor.threshold_tokens_cap = 5500
        agent.context_compressor.threshold_tokens = 5500
        # The default 20-message protected tail leaves short worker runs
        # with nothing eligible for compression before Groq rejects them.
        agent.context_compressor.protect_first_n = 1
        # This bounded session has one assignment; keep it out of tail anchoring
        # after every compaction, rather than the SDK's first-compaction decay.
        agent.context_compressor._effective_protect_first_n = lambda _messages=None: 1
        agent.context_compressor.protect_last_n = 2
        agent.context_compressor.summary_model = model
        agent.context_compressor._micro_compact_enabled = False
        compression_class = type(agent.context_compressor)
        original_input_bound = compression_class._SUMMARY_INPUT_MAX_CHARS
        compression_class._SUMMARY_INPUT_MAX_CHARS = 6000
        agent._api_max_retries = 3
        agent.suppress_status_output = True
        result = agent.run_conversation(prompt)
        receipt = submitted_receipt(task_id, payload_id)
        calls = result.get("api_calls")
        metadata = {"completed": receipt, "failed": not receipt,
                    "api_calls": calls if type(calls) is int else None}
        for key in ("input_tokens", "output_tokens", "last_prompt_tokens"):
            if type(result.get(key)) is int:
                metadata[key] = result[key]
        if receipt:
            metadata["stop_reason"] = "review_receipt"
        else:
            # SDK releases also return failed turns through the finalizer.
            # Extract only the diagnostic allowlist; never print these raw fields.
            error = " ".join(str(result.get(key, "")) for key in
                             ("error", "turn_exit_reason", "final_response"))
            reason = result.get("failure_reason")
            metadata["failure_reason"] = reason if isinstance(reason, str) and reason in {
                "rate_limit", "billing", "authentication", "context_length", "timeout", "server_error",
            } else "missing_review_receipt"
            metadata["diagnostics"] = re.findall(DIAGNOSTICS, error, re.IGNORECASE)
        reason = str(result.get("turn_exit_reason", ""))
        metadata["turn_exit_category"] = next((label for label in (
            "text_response", "empty_response_exhausted", "all_retries_exhausted_no_response",
            "max_iterations_reached", "interrupted", "local_processing_error",
        ) if reason.startswith(label)), "other")
        print(json.dumps(metadata))
        return 0 if receipt else 1
    finally:
        if agent is not None:
            agent.close()
        cleanup_all_environments()
        set_approval_callback(None)
        output_limits.clear()
        output_limits.update(original_limits)
        compression_module.call_llm = original_compression
        verification_module.verify_on_stop_enabled = original_verify_enabled
        verification_module.build_verify_on_stop_nudge = original_verify_nudge
        if compression_class is not None:
            compression_class._SUMMARY_INPUT_MAX_CHARS = original_input_bound


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--payload-id", required=True)
    args = parser.parse_args()
    raise SystemExit(run_session(args.model, args.prompt, args.task_id, args.payload_id))
