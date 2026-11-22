# Delivery Report

- Task ID: direct-model-privacy-01
- Agent: ORCHESTRATOR
- Phase: agent-control-center
- Status: REVIEW

## Acceptance Criteria Coverage

Direct sessions default to ZDR and allow an explicitly chosen ordinary mode with
a retention notice. Catalogues filter chat-capable models and apply the selected
policy. The independent review found a cross-tab privacy race, now repaired by
binding every direct prompt to its displayed session and privacy mode.

## Changed Files

Direct model bridge, API, Agent snapshot, UI, tests and operator documentation.
Task and evidence records are included for portable review.

## Validation Steps Performed

Prior privacy integration checks are in `coordination/evidence/direct-model-privacy-01/`.
The repaired candidate's tests and independent re-review are tracked separately
under `coordination/evidence/console-privacy-lifetime-review-01/`.

## Known Residual Risks

Real provider success for the new mode was not verified. Account policies may
remain stricter than the selected mode. Older pages must be refreshed because
unbound direct prompts are now rejected rather than sent to the wrong session.
