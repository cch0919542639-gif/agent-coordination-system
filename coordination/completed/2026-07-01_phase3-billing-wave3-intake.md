# Phase Intake: Billing Hardening And Evolution Safety

## Phase ID

phase3-billing-wave3

## Objective

Harden the billing module so it can evolve safely after durable persistence has been introduced. This wave focuses on schema migration, local concurrency guardrails, and explicit customer access-boundary rules.

## Entry Criteria

List the conditions that must be true before the phase can begin:

- Phase 3 billing wave 2 (`phase3-billing-06` through `phase3-billing-08`) is accepted and committed
- `SqliteInvoiceStore`, `InvoiceStoreProtocol`, and durable multi-customer tests exist in the repo
- Billing API documentation is current through wave 2
- Repo-first coordination workflow, validator, and review flow remain active

## Exit Criteria

List the measurable conditions that define phase completion:

- Billing durable storage has an explicit schema-version and migration baseline
- Local concurrency behavior is documented and backed by targeted tests or guarded failure behavior
- Customer-scoped access expectations are explicit in the billing module and documented for future integration layers
- Wave 3 delivery reports are accepted and filed for all opened tasks

## Scope

### In Scope

- `src/billing/**`
- `tests/billing/**`
- `docs/api/billing.md`
- `docs/operations/**` when task outputs require billing-hardening documentation
- `coordination/**` when needed for task-card, progress, delivery, and review artifacts

### Out Of Scope

- full authentication or authorization system integration
- external API routes or admin UI
- distributed locking infrastructure
- third-party payment gateway behavior
- unrelated database or application domains

## Dependencies

List external dependencies, backbone references, or prerequisite phases:

- Accepted Phase 3 wave 2 billing artifacts
- `docs/operations/phase3-billing-wave3-intent.md`
- Existing billing module implementation and tests
- Coordination workflow docs and validator from earlier phases

## Artifact Expectations

Define what delivery artifacts every task in this phase must produce:

- delivery_report (required)
- code_changes or documentation changes
- tests or validation notes
- docs when operational or boundary assumptions change

## Task Packet Decomposition

List the candidate task packets that decompose this phase into executable work.

### Task 1: phase3-billing-09

- **Objective**: Introduce a schema-version and migration baseline for the SQLite billing store
- **Priority**: high
- **Dependencies**: `phase3-billing-06`, `phase3-billing-07`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: unrelated app domains, gateway code, non-billing database layers
- **Acceptance Criteria**: store tracks schema version; startup or open path applies a safe migration baseline; tests prove existing data remains readable across a versioned reopen path

### Task 2: phase3-billing-10

- **Objective**: Define and test local concurrency guardrails for the SQLite billing store
- **Priority**: high
- **Dependencies**: `phase3-billing-09`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `coordination/**`
- **Forbidden Scope**: distributed infra, unrelated queueing systems, non-billing global locking
- **Acceptance Criteria**: supported local concurrency behavior is explicit; unsupported contention paths fail predictably or are guarded; docs and tests explain the limits

### Task 3: phase3-billing-11

- **Objective**: Establish an explicit customer access-boundary contract for billing reads
- **Priority**: medium
- **Dependencies**: `phase3-billing-07`, `phase3-billing-08`
- **Allowed Scope**: `src/billing/**`, `tests/billing/**`, `docs/api/billing.md`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: auth framework integration, UI work, unrelated account systems
- **Acceptance Criteria**: customer-scoped read behavior is defined in billing-local interfaces or helper paths; tests prove intended boundary behavior; docs state what billing enforces and what higher layers must still provide

## Review and Acceptance

Describe how the orchestrator will validate phase completion:

- run `python scripts/orchestrate.py validate`
- run the billing test suite and inspect new hardening coverage
- compare each task result against its migration, concurrency, or boundary acceptance criteria
- accept tasks individually before opening any new outward-facing billing phase
