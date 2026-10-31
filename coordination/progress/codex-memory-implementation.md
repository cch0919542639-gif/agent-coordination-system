# Progress Report

- Agent: codex-memory-implementation
- Active Task: acs-memory-preflight-01
- Phase: acs-memory-pilot
- Status: REVIEW
- Last Updated: 2026-10-29

## Current Step

Source-pinned curated-memory adapter implemented and submitted for review. This
does not mark the larger NAS/model integration accepted.

## Changes So Far

- Added optional stdlib CLI/MCP adapter and synthetic HTTP/Git regression tests.
- Preserved approved plan/glossary and documented exact operator boundaries.
- Prepared10source candidates and question expectations, all pending review.
- Final focused suite51passed/native0 in21.60seconds. Earlier49pass/1fail on
  deep JSON revealed reliance on the interpreter recursion threshold; fixed with
  an explicit64level bound and retained failed evidence.

## Blocker Status

Default upstream extraction omitted source markers; a dedicated synthetic
instance using an agent-scoped marker strategy and L1 dedup disabled passed a
ten-card preliminary trial. Real card review, formal benchmark, NAS persistence
and two-machine acceptance remain HOLD.

## Next Step

Historical integration checkpoint: on2026-10-28 the user authorized integration of d6c4578,
resolved the sole progress conflict and verified the combined branch:343tests
pass/native0,73fresh-clone raw/blob pins pass. Publish the verified integration
and evidence to existing Draft PR11; do not merge to main or self-accept. Await
review. Sources remain pending-human-review and actual processing/NAS stays HOLD.
See coordination/evidence/acs-memory-preflight-01/integration-20261028/report.md.

## Synthetic upstream trial (2026-10-29)

Two temporary WSL runs of real0.4.3 and local3B model produced an L1 atom but omitted the exact marker. Adapter verification correctly refused activation; direct upstream recall succeeded once. Source correlation and deployment remain HOLD. See upstream-synthetic-20261029/report.md, including the unintended preliminary default startup. Task remains REVIEW and PR11 Draft.

Next: evaluate a source-correlation design that covers upstream deduplication,
updates and withdrawal; keep the marker requirement until another contract is
proven. Do not enable real-document processing or persistent NAS service.

## Synthetic marker strategy candidate (2026-10-29)

A dedicated test instance with L1 dedup disabled and an agent-scoped marker strategy passed10/10 synthetic top3, replay, adapter withdrawal and one supersession. Dedup-enabled three-card trial merged distinct facts and lost markers. The trial is non-blind and does not authorize global settings, real documents or NAS deployment. See marker-strategy-20261029/report.md; PR11 stays Draft and task REVIEW.

Current next step: independent review of the candidate configuration and its
instance-wide deduplication tradeoff, followed by source-card review and the
separate deployment and two-device gates. Preserve fail-closed marker checks.
