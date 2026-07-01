# Phase 3 Billing Wave 3 Intent

## Purpose

Wave 3 is the hardening phase for billing.

Wave 1 proved the billing flow exists.
Wave 2 proved the billing flow can persist and survive reopen cycles.
Wave 3 is where the billing module becomes safer to evolve, safer to operate, and safer to integrate into a larger system.

## What Wave 3 Means

Wave 3 is not primarily about adding more billing features.

It is about reducing the engineering risks that would otherwise block future work such as:

- HTTP or API exposure
- admin tooling
- deployment into longer-lived environments
- schema evolution
- concurrent access
- customer-specific access rules

Without this phase, the billing module can work in a local engineering sense but still be too fragile for realistic expansion.

## Why This Phase Matters

The billing module now has:

- a domain model
- service flows
- durable SQLite persistence
- a store protocol
- multi-customer durable smoke coverage

That is enough to support happy-path local use.

It is not yet enough to support safe long-term change.

The main remaining risks are:

1. **Schema evolution risk**
   The SQLite store has no migration path, so storage changes would be painful and error-prone.

2. **Concurrency risk**
   Local single-process behavior is covered, but write-conflict and locking behavior are not yet defined or tested.

3. **Access-boundary risk**
   Customer isolation is currently a data-query property, not an explicit access-control boundary.

Wave 3 exists to address those three risks directly.

## Wave 3 Goals

By the end of Wave 3, the billing module should:

- have an explicit story for schema evolution
- have documented and tested local concurrency guardrails
- have a defined access-boundary contract for customer-scoped reads

This does not mean the module becomes fully production-ready.

It means the next phase can safely build on it without immediately reworking persistence and safety assumptions.

## Recommended Scope

Wave 3 should stay inside billing-domain hardening.

### In Scope

- migration baseline for the SQLite store
- local concurrency behavior and failure-mode handling
- customer access-boundary rules and billing-local enforcement shape
- tests and documentation needed to prove those rules

### Out Of Scope

- full auth system integration
- HTTP API implementation
- distributed locking infrastructure
- third-party payment systems
- broader reporting or analytics

## Recommended Task Lines

Wave 3 breaks naturally into three task lines:

### 1. Schema Migration Baseline

Purpose:

- introduce a versioning and migration mechanism for the durable billing store
- make future schema change safer and more explicit

Why first:

- once persistence exists, migration debt starts accumulating immediately

### 2. Concurrency Safety Guardrails

Purpose:

- define what local concurrent access is supported
- detect or fail safely in the unsupported cases
- document the limits clearly

Why second:

- persistence without operational write-safety becomes a hidden failure source

### 3. Access-Boundary Contract

Purpose:

- move customer isolation from an implicit query convention into an explicit billing boundary
- create a clear contract for later auth and API layers

Why third:

- it depends on the durable store shape and benefits from the migration/concurrency assumptions being explicit first

## Expected Outcome

If Wave 3 succeeds, the billing module becomes:

- easier to change safely
- easier to reason about operationally
- easier to expose to higher-level application layers later

That is the practical value of this phase.
