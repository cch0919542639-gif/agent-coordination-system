---
task_id: phase11-runtime-safety-01
phase: phase11-orchestration-runtime-safety
status: REVIEW
owner: external-agent-platform-21
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add an orchestrate doctor subcommand that returns deterministic read-only preflight results.
  - Check repository identity, Git availability and remote, Python runtime, required coordination directories, and an optional task/profile argument.
  - Report actionable failures and use a non-zero exit status on failed checks without mutating task cards, profiles, branches, or worktrees.
  - Add focused tests for success and representative failure paths, including explicit no-mutation coverage.
  - Document command usage, exit behavior, and operator recovery steps.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Implement the first Phase 11 safety boundary: a read-only `orchestrate doctor`
preflight that detects the wrong clone, unavailable runtime, incomplete
coordination structure, and invalid explicit task/profile references before a
lead agent dispatches work.

## Context

External agents have repeatedly started in unrelated directories such as
`D:\mimo`; they then cannot find task cards or protocol files. The system must
turn that situation into a precise, recoverable diagnostic before any dispatch
or lifecycle operation begins.

Read before changing files:

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/agent-task-execution-protocol.md`
- `scripts/orchestrate.py`
- `scripts/profile_resolver.py`

## Constraints

- The command is diagnostic only. It must not write, move, claim, dispatch,
  commit, push, create worktrees, or change task-card fields.
- Reuse existing runtime and profile-resolution helpers where appropriate;
  do not duplicate profile parsing.
- Do not require network access for the default diagnostic path.
- An optional task/profile check must be explicit command input, not automatic
  profile activation.
- Keep default-mode repositories compatible.

## Implementation Notes

Add the command through `scripts/orchestrate.py` using the existing delegated
subcommand pattern. Prefer structured, human-readable output with a final
overall result and a distinct non-zero exit status when any required check
fails. Document the precise checks and recovery actions; do not claim that the
command repairs an environment.

## Validation Steps

1. Add focused tests covering a healthy repository and representative missing
   repository/runtime/task/profile inputs.
2. Assert all test fixtures leave task cards and profile files byte-for-byte
   unchanged after doctor runs.
3. Run focused script tests.
4. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
5. Include commands and results in the delivery report.

## Escalation Rules

Create an incident and stop if the expected orchestration entrypoint or
protocol documents are missing, if the required diagnostics would need network
or destructive operations, or if the task cannot be completed without changing
the lifecycle semantics.
