---
task_id: console-encoding-fix-01
phase: console-delivery-01
status: DONE
owner: console-encoding-platform-01
reviewer: console-encoding-review-01
priority: high
dependencies:
  - console-bootstrap-01
allowed_scope:
  - scripts/console_setup.py
  - tests/scripts/test_console_setup.py
  - docs/operations/console-download-guide.md
  - coordination/evidence/console-encoding-fix-01/**
  - coordination/delivery/console-encoding-fix-01-delivery-report.md
  - coordination/progress/console-encoding-platform-01.md
forbidden_scope:
  - source archive program files
  - live accounts permissions and runtime databases
  - other accepted runtime or web modules
  - remote publication or merge
acceptance:
  - Reproduce and preserve the whoami non-ASCII output/default-encoding bug from published verification evidence without reading or logging a real account name.
  - Make Windows SID acquisition independent of console/locale text decoding without forcing global UTF8 mode or weakening private directory/file ACL checks.
  - Add meaningful synthetic non-ASCII and isolated -I child regressions plus safe failure-path coverage; original implementation must fail the new regression.
  - Verify exact repaired code with focused tests and proportionate existing console/state/board checks, no product dependency additions or live state changes.
  - Preserve original c7f7dee verification failure and workaround as separate evidence; report exact local fix commit and do not claim P1 or second-host acceptance completed.
expected_artifacts:
  - encoding_fix
  - regression_tests
  - validation_evidence
  - delivery_report
execution_mode: WORKTREE
branch: codex/console-bootstrap-01
worktree_path: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work
machine_id: angeline
---
# Task Packet

## Objective

Repair this acceptance round before further P2/P3 planning. User raised the suspected acceptance error and asked to correct first. Fix only the Windows SID locale dependency and submit for independent review. Local commits are authorized; no push is authorized by this packet.

## Context

Board/source: C:/Users/angel/.codex/worktrees/integration-context-01/codex work; candidate: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work on codex/console-bootstrap-01 at published c7f7dee. PR6 is draft/unmerged, origin/main bfc5163. New remote evidence branch origin/docs/console-download-verification-20261024 at4a0f61d documents original init FAIL: CP950 decoding whoami UTF8 bytes, stdout None then AttributeError, final state absent.114passed/1failed; UTF8 workaround functional checks pass but -I ignores PYTHONUTF8 and reproduces failure. Read its coordination/delivery/console-download-verification-20261024-report.md and encoding-diagnosis.json with git show; do not merge that evidence branch. Host physical identity is not proven by that sanitized report.

## Constraints

Read board context and task card before coding. Lifecycle and reports live on authoritative board; code/test/guide changes only in candidate checkout. Do not touch live parent auth or DB, change system locale/codepage, weaken ACL checks, or log actual user identity/token. Existing worktree is clean. Prefer stdlib and existing ctypes facilities or narrowly extract only validated ASCII SID bytes; do not assume all Windows whoami output uses UTF8. No new framework, browser install, model/provider or auto-worker service. Old DONE cards remain historical; full P1 acceptance is currently held by this new blocker.

## Implementation Notes

Claim via board scripts as console-encoding-platform-01. Trace every current_sid caller. Use a minimal robust identity acquisition strategy; native Windows token APIs may avoid textual process output entirely, or safely handle raw bytes without decoding account names. Test invalid/missing output/API refusal as well as success. Explain the choice and required platform support without security theater. Published portable manifest still pins old source until independent repair acceptance; leave it unchanged in this source packet and note a metadata refresh is required before any repaired release.

## Token And Resource Impact (If Applicable)

One implementation agent followed by independent reviewer. At most3pytest invocations, each timeout300seconds in fresh system-temp locations; first may be a focused red regression, then repaired focused plus affected checks as proportionate. Preserve logs and JUnit and capture child exit. Do not interrupt wrapper while a child runs except real timeout/safety. No provider calls or recurring jobs.

## Validation Steps

1. Freeze c7f7dee base and evidence4a0f61d; make a synthetic non-ASCII regression fail on original code and retain the result.
2. Repair acquisition and verify no default-encoding dependence under -I; raw SID validation and fail-closed permissions behavior remain intact.
3. Run focused and affected existing suites within budget; record interpreter, exact file hashes, exit codes and limitations. Actual Python3.13 execution if already installed, otherwise explicitly pending.
4. Candidate diff and source-board coordination validator pass; write canonical report/progress, make local code/test commit and submit REVIEW. Do not refresh release manifest or accept own task.

## Escalation Rules

Report if fix requires unrelated runtime/API/schema or live permission changes. Ask orchestrator for a narrowly justified extra run only if a newly discovered repair consumes the budget. No publication or weakening validation to pass.
