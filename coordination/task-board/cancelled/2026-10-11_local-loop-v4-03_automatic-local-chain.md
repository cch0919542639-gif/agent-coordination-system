---
task_id: local-loop-v4-03
phase: phase14-local-agent-loop
status: CANCELLED
owner: opencode-coordination-pilot
reviewer: LOCAL_LOOP
priority: high
dependencies:
  - local-loop-v4-02
allowed_scope:
  - coordination/task-board/ready/2026-10-11_local-loop-v4-03_automatic-local-chain.md
  - coordination/task-board/in_progress/2026-10-11_local-loop-v4-03_automatic-local-chain.md
  - coordination/task-board/review/2026-10-11_local-loop-v4-03_automatic-local-chain.md
  - coordination/progress/opencode-coordination-pilot.md
  - coordination/delivery/local-loop-v4-03-delivery-report.md
  - coordination/evidence/local-loop-pilot-v4/final.json
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
local_loop_checks_sha256: 7efe3c1142acd472f9a5135b6b5a9625477aad2938a119348fe550b7721e8717
---
# Task Packet

## Objective

Read the accepted coordination/evidence/local-loop-pilot-v4/stage2.json and confirm value=21. Write final.json as {"status":"completed","value":21,"workers":["opencode","hermes"]}. Do not edit either prior-stage file.

## Context

The user authorized Codex-controlled local OpenCode/Hermes orchestration on
2026-10-11. This finite demonstration is managed by
`coordination/plans/local-agent-loop-pilot-v4.json`. Its LOCAL_LOOP reviewer may
accept only after exact owner/payload receipts, scope validation and the JSON
check signed by `local_loop_checks_sha256` pass. Dependencies must already be
accepted; the controller dispatches them in order. The expected final JSON is:

{"status": "completed", "value": 21, "workers": ["opencode", "hermes"]}

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
coordination/evidence/local-loop-pilot-v4/final.json to the expected JSON, verifies the acknowledged payload,
checks changed-file scope and writes the review.

## Escalation Rules

If ownership, expected payload, dependencies or allowed scope do not match,
stop. Record real provider/validation failures rather than claiming success.


## Recovery Context

Fresh packet after v3 Hermes submitted an incorrect report without the required stage2 artifact; the independent check returned needs_fix and its two-attempt budget was exhausted. Original receipts and reports remain. The launcher now retains the exact Objective and allowed paths in the initial assignment, plus explicit helper syntax. Accepted v2 OpenCode stage1 remains the dependency.


## Closure Evidence

Cancelled2026-10-12. Dependency not accepted; never dispatched. Superseded by local-loop-v5-03; old receipts and attempts retained without reset. Unaccepted report archived at coordination/evidence/local-loop-pilot-v4/unaccepted-delivery-report.md.
