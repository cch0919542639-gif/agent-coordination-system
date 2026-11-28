# Team summary diagnostics candidate

- Task ID: team-summary-diagnostics-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Status: independently reviewed; awaiting integration

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
Final focused regression passed 34 tests; broader Agent/team/credential/console
regression passed 157 with two skips. A synthetic owned-bridge test reproduced
HTTP 429 in the final summary and verified that the status is displayed without
private provider text or credential disclosure. Independent reviewers verified
the repairs to cancellation, attribution, reserved text and safe 404 reasons.

## Known Residual Risks

The original error cannot be reconstructed from retained evidence. The candidate
has not been merged or installed; a future live failure may expose a category
but not necessarily the provider's full cause.
