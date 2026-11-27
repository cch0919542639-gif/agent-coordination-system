# Console credential storage candidate

- Task ID: console-key-storage-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Status: independently reviewed; awaiting integration

## Changed Files

Windows credential store, direct/team APIs, both console panels, tests and guide.

## Acceptance Criteria Coverage

Optional credentials are persisted to Windows Credential Manager for the local
Windows user, scoped by console project, console user, provider and endpoint.
The browser may save, delete and request use but cannot retrieve key plaintext.

## Validation Steps Performed

Synthetic Windows cross-process credential write/read/delete passed; direct/team
API and UI fixtures exercised saved credentials without exposing secrets. The
final focused run passed 15 tests. Final broader Agent/team/console regression
passed 144 tests with two skips. Independent backend and UI reviewers separately
validated the affected paths and re-reviewed the repairs. No real user credentials
were read.

## Known Residual Risks

The current console runs native agents as the same Windows user; they may access
that user's credentials. This is not strict identity isolation. The candidate
has not been published or installed.
