# Original team summary failure

- Incident ID: team-summary-original-failure-01
- Task ID: team-summary-diagnostics-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Category: missing diagnostic evidence
- Severity: medium
- Status: open
- Created At: 2026-11-28

## Summary

The first three-worker live test completed all worker subtasks but the final
summary failed. A shorter independent repeat completed successfully.

## What Was Attempted

Reviewed the observed UI state and the matching released source. The original
summary handler catches every exception and displays the same fixed generic
message. The later team replaced the earlier team's in-memory session state.
No credentials, private transcripts, raw provider responses or logs were read.

## Exact Blocker

The first summary's underlying error category was not retained, so the available
evidence cannot distinguish provider errors, timeout, response limits or another
failure. A subsequent success does not establish the first failure's cause.

## Scope / Risk Impact

The user can inspect the first worker artifacts, but the historical root cause
cannot be verified from the available evidence. Do not infer a specific cause.

## Recommended Next Action

Use the candidate's sanitized category on any new failure. It preserves worker
results and does not log provider message bodies or credentials. Qualify the
candidate via review before integration; investigate the newly visible category
if the problem recurs.
