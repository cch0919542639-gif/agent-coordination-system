---
task_id: local-loop-v5-02
phase: phase14-local-agent-loop
status: DONE
owner: hermes-coordination-pilot
reviewer: LOCAL_LOOP
priority: high
dependencies:
  - local-loop-v2-01
allowed_scope:
  - coordination/task-board/ready/2026-10-11_local-loop-v5-02_automatic-local-chain.md
  - coordination/task-board/in_progress/2026-10-11_local-loop-v5-02_automatic-local-chain.md
  - coordination/task-board/review/2026-10-11_local-loop-v5-02_automatic-local-chain.md
  - coordination/progress/hermes-coordination-pilot.md
  - coordination/delivery/local-loop-v5-02-delivery-report.md
  - coordination/evidence/local-loop-pilot-v5/stage2.json
forbidden_scope:
  - scripts/**
  - integrations/**
  - docs/**
  - coordination/plans/**
  - coordination/reviews/**
  - other_task_cards
  - git_commit_push_merge
  - credentials
acceptance:
  - Activate only this acknowledged owner-matching payload and preserve its task identity.
  - Write the specified JSON artifact; final accepted delivery satisfies the independently pinned check.
  - Write truthful templated delivery evidence, validate, submit and stop.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
local_loop_checks_sha256: bef5f3a468280c9899bea8a6764fb805e945621217ff88d8299a90bfaced2512
---
# Task Packet

## Objective

Read the accepted coordination/evidence/local-loop-pilot-v2/stage1.json. Multiply its value by 3 and write coordination/evidence/local-loop-pilot-v5/stage2.json as {"stage":2,"agent":"hermes","value":21}. Do not change stage1.json.

## Context

The user authorized Codex-controlled local OpenCode/Hermes orchestration on
2026-10-11. This finite demonstration is managed by
`coordination/plans/local-agent-loop-pilot-v5.json`. Its LOCAL_LOOP reviewer may
accept only after exact owner/payload receipts, scope validation and the JSON
check signed by `local_loop_checks_sha256` pass. Dependencies must already be
accepted; the controller dispatches them in order. The expected final JSON is:

{"stage": 2, "agent": "hermes", "value": 21}

## Constraints

Handle this task only. Preserve all existing work. Write only allowed paths;
never change controller/checks, accept or review tasks, dispatch other tasks,
read credentials/transcripts, enable approval bypass, commit, push or merge.
Stop immediately after verifying submission to review. JSON whitespace does
not affect the independent semantic check.

## Implementation Notes

The controller has already activated the exact durable payload. Read this
packet and the task execution protocol before claiming a READY task with
claim_task.py. For IN_PROGRESS repair, skip claim and read your review findings.
Create the artifact's parent directory if necessary. Keep delivery evidence
under 250 words using coordination/templates/delivery-report.md and the actual
payload ID. Use submit_task.py, then verify the card is in review/ and stop.

## Token And Resource Impact (If Applicable)

Existing worker model and credentials only, maximum two attempts. No scheduler
activation or task beyond this card. Keep tool output concise. The controller
stops on failure and preserves durable receipts and review feedback.

## Validation Steps

Run scripts/orchestrate.py validate. The controller independently compares
coordination/evidence/local-loop-pilot-v5/stage2.json to the expected JSON, verifies the acknowledged payload,
checks changed-file scope and writes the review.

## Escalation Rules

If ownership, expected payload, dependencies or allowed scope do not match,
stop. Record real provider/validation failures rather than claiming success.


## Recovery Context

Fresh packet after v4 Hermes produced stage2=21 but exhausted one minute-rate retry and then stopped after an invalid-format report without REVIEW. The launcher now preserves the literal delivery template, exact Objective and scope. Previously accepted Groq Qwen passed a fresh forced-tool probe after quota refill; Desktop stays unchanged. Accepted v2 OpenCode stage1 remains the dependency. Existing receipts and failed reports are retained.
