---
task_id: phase14-opencode-01
phase: phase14-opencode-controlled-worker-pilot
status: DONE
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-runtime-adapter-01
allowed_scope:
  - docs/operations/**
  - coordination/**
  - integrations/opencode-coordination-worker/**
  - requirements.txt
forbidden_scope:
  - services/**
  - src/**
  - clients/**
  - profiles/**
  - automatic_review_or_merge
acceptance:
  - Provide an OpenCode launcher that uses the existing owner-strict activation payload and processes at most one assigned task per invocation.
  - Isolate OpenCode runtime state from the incompatible global config path without deleting or changing that path.
  - Ensure the launcher never enables auto-approval, Kanban, automatic acceptance, merge, commit, push, or unassigned-task selection.
  - Document explicit launch, rollback, and the separate model-data-transfer authorization required before a supervised pilot.
  - Verify OpenCode preflight succeeds through the isolated runtime configuration and record results.
expected_artifacts:
  - opencode_controlled_launcher
  - operator_guide
  - preflight_evidence
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Prepare a bounded OpenCode controlled-worker integration compatible with the
existing repo-first, owner-strict activation contract. Do not run a model task
until separately authorized.

## Context

Read `docs/operations/runtime-adapter-preflight-guide.md`,
`docs/operations/agent-task-execution-protocol.md`, and the completed Hermes
pilot guide for the shared safety boundary.

## Constraints

- Reuse `python scripts/orchestrate.py worker activate <worker-id> --json`.
- Process at most one owner-matching task per explicit invocation.
- Do not use `--auto`, Kanban, automatic review, merge, commit, or push.
- Keep OpenCode configuration under an isolated local runtime directory; do
  not modify `C:\Users\angel\.config\opencode`.
- Do not invoke `opencode run` until the user separately authorizes the data
  transfer for the selected task.

## Implementation Notes

Use the verified `XDG_CONFIG_HOME` isolation workaround. The launcher must be
explicitly invoked by an operator and should emit no task content unless
OpenCode is deliberately started for an authorized pilot.

## Token And Resource Impact (If Applicable)

No model call during setup. A future explicit pilot uses one OpenCode run for
one assigned task. Rollback is removal of the local launcher/config directory;
the existing global OpenCode configuration is untouched.

## Validation Steps

1. Run the bounded OpenCode version preflight using the isolated config path.
2. Inspect the launcher for one-task and no-auto boundaries.
3. Run coordination validation.

## Escalation Rules

Stop and open an incident if the workaround requires editing global OpenCode
configuration, exposes credentials, launches a model without authorization,
or needs a second dispatcher.
