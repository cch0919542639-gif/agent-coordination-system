---
task_id: console-bootstrap-01
phase: console-delivery-01
status: DONE
owner: console-bootstrap-platform-01
reviewer: console-bootstrap-review-01
priority: high
dependencies:
  - console-package-01
allowed_scope:
  - scripts/console_setup.py
  - tests/scripts/test_console_setup.py
  - docs/operations/console-download-guide.md
  - coordination/evidence/console-bootstrap-01/**
  - coordination/delivery/console-bootstrap-01-delivery-report.md
  - coordination/progress/console-bootstrap-platform-01.md
  - .gitattributes
forbidden_scope:
  - existing web and runtime source changes
  - live credentials or runtime database
  - historical task cards
  - provider activation or remote publication
acceptance:
  - Add a small stdlib-only init and foreground serve entrypoint using existing web and runtime APIs from the accepted candidate.
  - Init explicitly binds canonical repository/workspace/project paths to schema4 with mode disabled and creates external private Viewer credentials by default; no account or DB is created by serve or query.
  - Repeated identical init preserves token and database bytes; foreign or mismatching configuration/schema/bindings fail before mutation and do not overwrite existing files.
  - Credentials stay outside repository/workspace roots and never appear in logs URLs reports or command-line arguments; follow Windows canonical-path behavior and private file permissions.
  - Foreground finite serve reports address PID duration and shutdown instructions; port conflict and invalid duration return clear errors without killing another process.
  - New-directory tests cover initialization replay mismatch failure and HTTP login with seven runtime-available views; Viewer remains read-only and source task byte pins remain unchanged.
  - Provide clone/version selection and setup/start/stop/restart documentation with explicit local-only and no-remote-publication boundaries.
expected_artifacts:
  - bootstrap_entrypoint
  - bootstrap_tests
  - operator_guide
  - delivery_report
execution_mode: WORKTREE
machine_id: angeline
branch: codex/console-bootstrap-01
worktree_path: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work
---
# Task Packet

## Objective

Implement P1b once P1a console-package-01 is independently accepted DONE. A simple explicit init plus foreground finite serve is sufficient; no custom daemon, scheduler or new service manager is requested. Candidate branch and exact base will be recorded by the orchestrator on release from BLOCKED.

## Context

Read the accepted source packet, candidate manifest, source review and docs/roadmap/console-delivery-and-dispatch-plan.md. The parent session successfully configured a private Viewer and disabled schema4 binding on angeline; reuse the source APIs, not its credentials, DB, local runtime files or app-specific paths. Documents must work on a fresh Windows Python3.12+ setup without manual source changes.

## Constraints

Current card is dependency-BLOCKED, not permission to start. Authoritative lifecycle/evidence remains in the integration-context-01 board; new code/docs/tests go only into the designated candidate worktree. init is an explicit user command; serve never creates/migrates a DB or changes accounts/mode. Validate all IDs/path containment/aliases/auth format and existing config before mutation. Default Viewer; any other existing role must be explicitly chosen. Do not add auto source scanning, network requests beyond loopback, worker launch, push, merge or browser credential storage. Synthetic tests only. Never print tokens; provide a private local login file location. Preserve failures and avoid partially published credentials/configs; explain interrupted-init recovery. Local-only candidate commits after verification are authorized.

## Implementation Notes

Prefer one Python stdlib entrypoint and a concise operator guide. Use StateController.initialize and the existing typed digest/schema formats. Initial disabled project binding is configuration, not a temporary enable/disable cycle. Use transactions for DB binding, no migrations or fence resets. Config/auth/database locations must be canonical and isolated from source and workspace. Keep preflight and refusal paths side-effect free. A new empty DB is valid; do not invent historical runs. Foreground serve makes Ctrl+C and finite expiration the stop mechanisms. Do not implement background PID kill/restart or autostart as speculative features.

## Token And Resource Impact (If Applicable)

One implementation agent followed by independent reviewer; no provider calls, no polling service and no new dependency. Up to three pytest invocations, at most300seconds each; reuse source suite selectively only if code changes affect it. Tests use new system-temp directories and bounded fixture HTTP listeners. Retain JUnit and logs. No alteration of the current live Viewer account or console service for implementation tests.

## Validation Steps

Focused bootstrap tests must cover replay byte preservation, malformed/foreign DB and project/root mismatches, path aliases/containment, incomplete initialization and occupied port. Exercise the explicit init and authenticated seven-view flow from a new local directory, never another host's DB. Check existing source pins unchanged, diff whitespace, and coordination validator. Submit canonical report, progress and exact candidate commit for independent review.

## Escalation Rules

Report any need to modify existing runtime/API or accepted source; don't silently patch dependencies. Raise an incident for unavailable Windows permission APIs, ambiguous replay/partial setup recovery or out-of-scope schema migration. Do not claim second-host acceptance from an angeline test.

## Release From Dependency Block (2026-10-23)

P1a source console-package-01 and independent assessment console-package-review-01 are canonical accepted DONE. Candidate base is 5daa318d2d9c2b4dd4ff93081396bd452212c4a1, worktree C:/Users/angel/.codex/worktrees/console-download-candidate/codex work, branch codex/console-bootstrap-01. Source/archive task board remains authoritative. Append explicit -text .gitattributes rules for the three new code/test/guide paths to preserve tested raw bytes across clone; keep all26 P1a source pins unchanged. No other modifications to accepted source. Initial P1a reviewer wrapper interruption remains documented and is not carried as an unqualified exit0 claim.

## Orchestrator Repair Verification Authorization (2026-10-23)

Before submission, self-review found load(state_dir) did not explicitly bind the supplied canonical state directory to stored state_dir. Authorize a one-line refusal plus copied-state-directory regression and one additional bootstrap-only pytest invocation, hard timeout300seconds (fourth total; approximately23 cases). This is a repair-driven exception after the original3invocations, not a new broad rerun. Preserve initial14fail/7pass, repaired61pass and prior62pass logs separately; unchanged40web checks need not rerun. Final exact repaired code must pass focused checks before REVIEW. Guide may clarify installed3.13+ interpreter selection alongside3.12examples.
