# Delivery Report

- Task ID: console-entry-guards-01
- Agent: CODEX
- Phase: console-delivery-01
- Status: DELIVERED FOR REVIEW

## Changed Files

Two legacy entry scripts, PROGRESS.md, this delivery, REVIEW task card and scoped
evidence directory. Source diff reuses the existing require_serial guard.

## Artifact Paths

- coordination/evidence/console-entry-guards-20261025/repair.md
- coordination/evidence/console-entry-guards-20261025/regression-result.json
- coordination/evidence/console-entry-guards-20261025/regression.xml
- coordination/evidence/console-entry-guards-20261025/entry-guards.patch

## Validation Steps Performed

110passed/native0 on Python3.12 in99.938seconds,300second limit. All three original
failures now pass; marker-absent activation still writes inbox and ACK, while enabled
and corrupt markers preserve delivery bytes and create no inbox. Exact tested raw
source hashes are retained. Validator and diff checks pass. No product changes after
this test execution; publication metadata does not change source/test bytes.

## Known Residual Risks

Existing marker gate is not a new cross-process activation lock. Core131 suite was
not rerun in this repair. Independent acceptance and integration are pending.
Original47release pins remain intact; this is a repair branch, not a refreshed
portable release. Git normalization of the two legacy scripts is recorded separately.

## Acceptance Criteria Coverage

Original failure cases and adjacent loop/poller/activation/parallel behaviors are
covered. Report is a submission, not formal acceptance.

## Recommended Handoff

Review the repair PR targeting codex/console-bootstrap-01; separately integrate and
refresh publication evidence if accepted. Existing PR6/PR9 and main remain unchanged.
