# Team summary diagnostics candidate

- Task ID: team-summary-diagnostics-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Status: validated; independent review pending

## Changed Files

Team summary handling, direct-model safe network error categories, isolated
tests, the task card and the original-failure incident.

## Acceptance Criteria Coverage

The historical provider cause remains unknown because the prior summary handler
discarded the underlying error. The candidate retains a safe fixed category for
future failures and preserves successful worker results without forwarding raw
provider errors or automatically retrying.

## Validation Steps Performed

Isolated tests exercise successful summaries, HTTP errors, transport errors,
timeouts, length limits, worker result preservation and secret redaction.
Focused final regression passed 28 tests; broader Agent/team/direct regression
passed 106 with two skips. A synthetic owned-bridge test reproduced HTTP 429 in
the final summary and verified that the status is displayed without private
provider text or credential disclosure.

## Known Residual Risks

The original error cannot be reconstructed from retained evidence. The candidate
has not yet been independently reviewed, merged or installed; a future live
failure may expose a category but not necessarily the provider's full cause.
