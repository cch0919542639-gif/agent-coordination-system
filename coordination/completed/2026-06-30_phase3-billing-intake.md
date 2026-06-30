# Phase Intake: Billing Flow

## Phase ID

phase3-billing

## Objective

Implement the minimum billing feature set needed for an internal alpha workflow: invoice generation, payment recording, balance querying, and a small integration test path that proves the pieces work together.

## Entry Criteria

List the conditions that must be true before the phase can begin:

- Phase 2 productionization workflow is complete and validated
- Repo-first coordination workflow, delivery report standard, and review flow are active
- Billing phase packet set is committed to `coordination/task-board/ready/`
- Orchestrator is available to review the first wave closely

## Exit Criteria

List the measurable conditions that define phase completion:

- Invoice model and persistence layer support draft invoice creation
- Invoice generation service can create an invoice payload for a test customer
- Payment recording endpoint or service can record a payment against an invoice
- Balance query path can return invoice balance information for test scenarios
- Integration smoke tests and delivery reports are accepted for the first wave tasks

## Scope

### In Scope

- `src/billing/**`
- `tests/billing/**`
- `docs/api/billing.md`
- `coordination/**` when required for task card, progress, delivery, and review artifacts

### Out Of Scope

- third-party payment gateway integration
- recurring billing and subscriptions
- billing admin UI
- tax engine logic
- non-billing database migrations outside the billing domain

## Dependencies

List external dependencies, backbone references, or prerequisite phases:

- Phase 1 and Phase 2 workflow artifacts
- Existing repo-first coordination scripts and validator
- Any future schema or framework conventions used by the implementation repo

## Artifact Expectations

Define what delivery artifacts every task in this phase must produce:

- delivery_report (required)
- code_changes
- tests or validation notes
- docs when API or behavior changes require explanation

## Task Packet Decomposition

List the candidate task packets that decompose this phase into executable work.

### Task 1: phase3-billing-01

- **Objective**: Create the billing invoice model and persistence layer
- **Priority**: high
- **Dependencies**: none
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: `src/payments/**`, `infra/**`, unrelated domains
- **Acceptance Criteria**: invoice data model exists; persistence path supports create/load for invoices; tests or validation notes cover happy path

### Task 2: phase3-billing-02

- **Objective**: Implement invoice generation service or endpoint
- **Priority**: high
- **Dependencies**: `phase3-billing-01`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: payment gateway code, unrelated API domains
- **Acceptance Criteria**: generation path returns valid invoice payload; tests or validation notes cover at least one success path and one failure path

### Task 3: phase3-billing-03

- **Objective**: Implement payment recording endpoint or service
- **Priority**: high
- **Dependencies**: `phase3-billing-01`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: third-party gateway integration, unrelated account systems
- **Acceptance Criteria**: payments can be recorded against an invoice; invoice state or balance updates accordingly; tests or validation notes cover success and invalid-input behavior

### Task 4: phase3-billing-04

- **Objective**: Implement balance query path for invoice state
- **Priority**: medium
- **Dependencies**: `phase3-billing-01`, `phase3-billing-03`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: unrelated reporting systems, admin UI
- **Acceptance Criteria**: query returns correct balance information for test scenarios; docs or validation notes explain output shape

### Task 5: phase3-billing-05

- **Objective**: Add billing integration smoke tests and end-to-end validation notes
- **Priority**: medium
- **Dependencies**: `phase3-billing-02`, `phase3-billing-03`, `phase3-billing-04`
- **Allowed Scope**: `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: unrelated domain tests, infra changes
- **Acceptance Criteria**: one smoke path covers create invoice -> record payment -> query balance; delivery report includes residual risks and next gaps

## Review and Acceptance

Describe how the orchestrator will validate phase completion:

- run `python scripts/validate_coordination_files.py`
- inspect each task delivery report
- review code/test artifacts against task acceptance criteria
- accept tasks individually before declaring the phase stable enough to expand

