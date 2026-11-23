---
task_id: console-manual-lifetime-01
phase: agent-control-center
status: DONE
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/console_setup.py
  - web/**
  - tests/scripts/test_console_setup.py
  - tests/scripts/test_console_monitor.py
  - tests/scripts/test_web_console.py
  - tests/scripts/test_agent_control.py
  - tests/scripts/test_direct_model.py
  - docs/operations/console-download-guide.md
  - docs/operations/console-monitor-guide.md
  - docs/operations/web-console-guide.md
  - docs/operations/web-console-contract.md
  - docs/operations/agent-control-center-guide.md
  - PLAN.md
  - DECISIONS.md
  - PROGRESS.md
  - coordination/task-board/**
  - coordination/progress/console-manual-lifetime.md
  - coordination/evidence/console-manual-lifetime-01/**
  - coordination/delivery/console-manual-lifetime-01-delivery-report.md
forbidden_scope:
  - exposing secrets or private transcripts
  - terminating unrelated running services or sessions
  - automatic worker dispatch execution merge push or publication
acceptance:
  - Foreground console defaults to no automatic server shutdown and supports manual stop.
  - Explicit finite durations and read-only monitor behavior remain testable and compatible.
  - Apply the user's choice about login and Agent session expiry and document the behavior.
  - Run focused security and lifecycle regressions without disturbing existing running instances.
expected_artifacts:
  - code_changes
  - tests
  - operator_guide
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Remove the unwanted automatic console lifetime and support manual shutdown.

## Context
The normal console launcher currently passes 1800 seconds. The user wants to close
the console manually when finished. Privacy-mode work in this checkout is preserved.

## Constraints
Maintain authentication, authorization, monitor read-only and owned-process cleanup.
Do not stop other sessions. Changes to user-owned launcher require a verified target.

## Implementation Notes
Keep explicit finite mode for tests and callers. Choose session lifetime only from
the user's answer, and report any remaining independently imposed time limits.

## Validation Steps
Check both entry points, normal and read-only modes, manual stop and cleanup,
explicit finite operation, and relevant existing role and model tests.

## Escalation Rules
Do not claim a running installation was updated unless the candidate was started
and verified; do not terminate any other owner's running console.
