# Review Report

- Review ID: review-direct-model-picker-01
- Reviewer: ORCHESTRATOR, with independent Codex review and re-review
- Task ID: direct-model-picker-01
- Phase: agent-control-center
- Decision: accepted
- Reviewed At: 2026-11-24

## Summary

Independent review of `74cf3d2` found two reproducible display mismatches:
privacy updated from another tab left a stale catalogue, and manual ID edits
left a different model selected in the dropdown. Repair `b16f1f3` clears stale
selection/catalogue and invalidates pending catalogue responses when privacy or
authentication changes. Independent re-review found no new actionable issue.

## Findings

The initial review reproduced both mismatches in isolated Node DOM fixtures.
The re-review checked cross-tab A-to-B-to-A privacy changes, manual ID changes,
logout with an in-flight response and subsequent login. Backend privacy binding
was not reported to be bypassed.

## Scope Compliance

No real credentials, private sessions, private transcripts or provider requests
were used. The existing local installation predates the final repair.

## Validation Check

On `b16f1f3`, lead tests passed 115 with one skip; independent tests passed 73
with one skip, plus isolated state and stale-response checks. Syntax and diff
checks passed. The skipped test requires the unavailable Hermes interpreter.

## Required Changes

None within scope. A real provider request remains unverified after HTTP 401;
merge and publication are separate actions.

## Accepted Artifacts

- coordination/delivery/direct-model-picker-01-delivery-report.md
- web/static/app.js
- web/static/index.html
- tests/scripts/test_direct_model.py
