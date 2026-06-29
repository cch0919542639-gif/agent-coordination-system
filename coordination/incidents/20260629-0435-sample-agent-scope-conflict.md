# Incident Report

- Incident ID: 20260629-0435-SAMPLE-AGENT-SCOPE-CONFLICT
- Agent: sample-agent
- Task ID: phase1-sample-01
- Phase: phase1-foundation
- Severity: medium
- Category: scope_conflict
- Status: OPEN
- Created At: 2026-06-29 04:35

## Summary

The task appears to need an example under `src/`, but the current task packet forbids application source code changes.

## What Was Attempted

Reviewed the task packet, checked the allowed and forbidden scope, and confirmed the sample objective can still be completed using documentation-only artifacts.

## Exact Blocker

There is a possible conflict between adding a more realistic demonstration and the task rule that forbids changes inside `src/**`.

## Scope / Risk Impact

If source code changes are required, the task scope must be expanded or split. Continuing without approval would violate the task packet.

## Recommended Next Action

Keep this sample task documentation-only, or create a separate follow-up task that explicitly allows source-level demonstration changes.

