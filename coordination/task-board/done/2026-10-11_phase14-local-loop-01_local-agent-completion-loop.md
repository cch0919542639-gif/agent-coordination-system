---
task_id: phase14-local-loop-01
phase: phase14-local-agent-loop
status: DONE
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-hermes-pilot-04
allowed_scope:
  - scripts/**
  - integrations/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
  - PLAN.md
  - PROGRESS.md
  - TASKS.md
  - DECISIONS.md
forbidden_scope:
  - products/**
  - agent-usage-collector/**
  - unrelated_existing_task_cards
  - credentials
  - git_merge
acceptance:
  - Execute an explicit finite local task plan through actual OpenCode and Hermes workers.
  - Automatically collect and independently check deliveries before accepting and dispatching dependent work.
  - Demonstrate bounded needs-fix repair, owner isolation, durable resume and a final completion report.
  - Stop on missing receipts, out-of-scope changes, provider failure or exhausted retries.
  - Preserve existing edits and record independent review and focused validation.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Complete the user's requested local dispatch, execution, automatic report,
follow-up dispatch and completion loop. Codex owns the control plane;
OpenCode and Hermes execute one explicitly assigned packet at a time.

## Context

The 2026-10-11 user request authorizes this finite local orchestration loop,
including actual worker calls using their existing providers. Reuse the task
board, durable activation, claim, submit and review helpers. Read the lead-agent
orchestration protocol and worker-assignment policy. Cross-machine transport
remains deferred.

## Constraints

Preserve all pre-existing work. Only tasks explicitly listed in an approved
plan and assigned to the deterministic LOCAL_LOOP reviewer may be automatically
accepted, after independent checks and scope validation. General qualitative
or high-risk tasks retain their designated review gate. No merge, credentials,
production change, global skill installation, or unbounded queue draining.

## Implementation Notes

Use a single serial controller, immutable plan identity, bounded attempts,
process timeouts and a local lock. An acknowledged handoff may be reused only
for explicitly authorized repair of that same task; never reset acknowledgements.
Retain old review evidence when retrying. Use a small three-task cross-worker
chain, with an intentional first-submission defect, to test the actual loop.

## Token And Resource Impact (If Applicable)

At most two attempts per demonstration task with existing OpenCode free and
Hermes existing Groq worker models (Qwen, then configured GPT-OSS after daily quota exhaustion). The run is finite and foreground-controlled;
existing native and legacy schedules stay disabled. Output remains bounded,
and durable metadata/reports remain available after exit. Stop the controller
to prevent new launches; it must terminate any owned child process on timeout.

## Validation Steps

Run focused controller, activation and launcher tests; validate coordination
documents; execute the actual chain and confirm accepted DONE evidence for all
listed tasks. Verify a repeated completed run launches no worker. Obtain
independent review, fix actionable findings and rerun affected checks.

## Escalation Rules

Stop the affected run on unexpected ownership, unsafe scope, an unverified
receipt, exhausted attempts or unavailable provider. Do not accept by inference
or operate unrelated task cards to make the loop appear successful.
