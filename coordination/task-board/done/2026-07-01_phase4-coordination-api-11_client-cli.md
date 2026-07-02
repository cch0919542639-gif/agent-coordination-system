---
task_id: phase4-coordination-api-11
phase: phase4-coordination-api-wave2
status: DONE
owner: external-agent-platform-11
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-03
  - phase4-coordination-api-10
allowed_scope:
  - clients/coordination_agent/**
  - services/coordination_api/**
  - tests/**
  - docs/specs/coordination-api-v1.md
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - dashboard UI
  - repo sync
  - unrelated domains
acceptance:
  - Add minimal clients/coordination_agent/** CLI
  - Support commands for poll, claim, heartbeat, progress, incident, artifact, submit
  - Read API base URL and API key from environment variables
  - Print clear command-line output for success and failure
  - Include at least one end-to-end happy-path test or focused client tests
  - Add usage documentation
  - Create/update delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Build the first agent CLI/client so an external agent can poll, claim, heartbeat, report progress, raise incidents, attach artifacts, and submit without hand-built command sequences.

## Context

All coordination API endpoints exist but require raw HTTP calls. A dedicated CLI enables agents to interact with the control plane without curl commands or custom scripts.

## Constraints

Keep scope to the agent client package. Do not build dashboard UI, repo sync, or unrelated domains.

## Implementation Notes

Provide a CoordinationClient class wrapping httpx calls and an argparse CLI. Use environment variables for configuration. Print JSON responses for success, error messages for failures.

## Validation Steps

Run the client test suite and the coordination API test suite. Run the validator.

## Escalation Rules

Raise an incident if the environment variable configuration or client design is too ambiguous to implement safely.
