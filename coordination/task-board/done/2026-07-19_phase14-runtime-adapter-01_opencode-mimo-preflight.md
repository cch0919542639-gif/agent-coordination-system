---
task_id: phase14-runtime-adapter-01
phase: phase14-runtime-adapters
status: DONE
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-local-03
execution_mode: REPO_FIRST
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/**
  - profiles/**
  - coordination/monitor/global-resource-registry.json
acceptance:
  - Add a deterministic, read-only runtime-adapter preflight for OpenCode and MiMo that reports executable discovery and the safe worker-handoff command without invoking an agent session or external network service.
  - Distinguish unavailable, discoverable-but-unverified, and opt-in probe failure states without exposing configuration paths, credentials, prompts, source code, or task-body content.
  - Use the existing owner-strict worker activation contract as the only handoff mechanism and document the explicit operator boundary before any runtime launch.
  - Add focused tests for safe output, command discovery, and unavailable/probe-failure diagnostics.
expected_artifacts:
  - runtime_adapter_preflight_command
  - focused_tests
  - operator_documentation
  - delivery_report
---
# Task Packet

## Objective

Add a bounded OpenCode and MiMo runtime-adapter preflight to the coordination
CLI. It must make integration readiness visible without launching either
runtime or modifying its configuration.

## Context

`phase14-local-03` is accepted but its implementation remains on an unrelated
worker history. The current supported same-machine contract is the bounded,
owner-strict `worker activate <worker-id> --json` handoff. On this machine,
OpenCode is not discoverable and `mimo` is discoverable but its help invocation
is not currently healthy; do not treat either runtime as launch-ready.

## Constraints

- Never invoke `opencode run`, `opencode serve`, `mimo`, or any other command
  that could start an interactive or model-backed agent session.
- The default preflight may inspect PATH only. Any executable probe must be
  separately opt-in, bounded, and report only a safe diagnostic category.
- Do not install software, change runtime configuration, create junctions,
  register workers, claim tasks, or mutate monitor delivery state.
- Do not make external runtime launch part of `worker activate`; the worker
  runtime remains responsible for reading a durable handoff and deciding to
  claim its own task.

## Implementation Notes

Use a small deterministic script and a thin `orchestrate.py` entrypoint.
Represent the two runtime contracts as data: OpenCode uses the `opencode`
executable and MiMo uses `mimo`. Output must name only runtime IDs, command
names, status categories, and repository-relative command templates.

## Token And Resource Impact (If Applicable)

Measured baseline: this adapter performs no model call, no polling loop, and
no transcript collection. Default mode only performs local command discovery.
Opt-in probing is explicitly documented and can be disabled by omitting its
flag. The existing worker activation cadence and delivery evidence remain
unchanged.

## Validation Steps

Run focused runtime-adapter tests, relevant worker-poller regressions,
`python scripts/orchestrate.py validate`, and inspect both human and JSON
output for unsafe data.

## Escalation Rules

Stop and open an incident if implementation requires an external runtime
launch, installation, credentials, configuration changes, shared-resource
junctions, lifecycle mutation, or a change outside allowed scope.
