# Phase Intake: Billing Persistence And Reliability

## Phase ID

phase3-billing-wave2

## Objective

Push the billing module from a first-wave in-memory demo flow into a more durable and reusable engineering baseline. This wave focuses on persistent storage, store abstraction, and stronger multi-customer integration coverage.

## Entry Criteria

List the conditions that must be true before the phase can begin:

- Phase 3 billing first wave (`phase3-billing-01` through `phase3-billing-05`) is accepted and committed
- Billing model, generation, payment, query, and smoke-path docs are available in the repo
- Repo-first coordination workflow, validator, review template, and delivery-report standard remain active
- Orchestrator is ready to review persistence-related scope carefully before widening the billing surface area

## Exit Criteria

List the measurable conditions that define phase completion:

- Billing supports a durable persistence option beyond the in-memory `InvoiceStore`
- Billing services can operate against an explicit store contract instead of an implicit in-memory-only assumption
- Multi-customer durable scenarios are tested and documented
- Second-wave delivery reports are accepted and filed for all opened tasks

## Scope

### In Scope

- `src/billing/**`
- `tests/billing/**`
- `docs/api/billing.md`
- `coordination/**` when needed for task-card, progress, delivery, and review artifacts

### Out Of Scope

- third-party payment gateway integration
- HTTP API or UI exposure for billing
- tax calculation logic
- recurring billing and subscription management
- distributed locking or true multi-process concurrency guarantees outside clearly documented local constraints

## Dependencies

List external dependencies, backbone references, or prerequisite phases:

- Accepted Phase 3 first-wave billing artifacts
- Existing billing module files under `src/billing/`
- Existing billing tests and `docs/api/billing.md`
- Coordination workflow docs and validator from Phase 1 and Phase 2

## Artifact Expectations

Define what delivery artifacts every task in this phase must produce:

- delivery_report (required)
- code_changes
- tests or validation notes
- docs when API, storage, or operational behavior changes

## Task Packet Decomposition

List the candidate task packets that decompose this phase into executable work.

### Task 1: phase3-billing-06

- **Objective**: Add a durable billing persistence implementation and keep parity with the current invoice store behavior
- **Priority**: high
- **Dependencies**: `phase3-billing-01`, `phase3-billing-05`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: `src/payments/**`, `infra/**`, unrelated app domains
- **Acceptance Criteria**: durable store supports save/load/delete/list_by_customer/count; reopened store can still read prior invoices; tests cover persistence parity and reopen behavior

### Task 2: phase3-billing-07

- **Objective**: Make billing services run cleanly against a defined store contract rather than an in-memory-only assumption
- **Priority**: high
- **Dependencies**: `phase3-billing-06`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: unrelated repositories, framework-wide refactors, gateway code
- **Acceptance Criteria**: generation/payment/query services accept the shared store contract; tests prove the core service flow works with the durable store; docs explain supported store types

### Task 3: phase3-billing-08

- **Objective**: Add durable multi-customer integration coverage and document the remaining operational limits
- **Priority**: medium
- **Dependencies**: `phase3-billing-06`, `phase3-billing-07`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: admin UI, unrelated reporting, infrastructure provisioning
- **Acceptance Criteria**: integration tests cover more than one customer and more than one invoice using durable storage; docs capture isolation expectations and known concurrency limits; delivery report identifies next production gaps

## Review and Acceptance

Describe how the orchestrator will validate phase completion:

- run `python scripts/orchestrate.py validate`
- run the billing test suite and inspect any new durable-store coverage
- compare store behavior and service behavior against the second-wave acceptance criteria
- accept tasks individually before opening any further billing expansion phase
