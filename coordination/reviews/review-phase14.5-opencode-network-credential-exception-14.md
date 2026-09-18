# Independent Review: phase14.5-opencode-network-credential-exception-14

- Review ID: `review-phase14.5-opencode-network-credential-exception-14`
- Task ID: `phase14.5-opencode-network-credential-exception-14`
- Phase: `phase14.5-opencode-network-exception`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_10`
- Reviewed commits: `d50296d`, follow-up `a724282`
- Reviewed At: 2026-09-18
- Decision: accepted

## Summary

The submitted code is a narrow, in-memory preparation boundary. Its schema is
exact and default-deny, and it neither reads host configuration nor starts a
process, network request, credential operation, Git operation, or worktree.
The follow-up supplies the previously missing exception-specific denial and
redaction evidence.

## Required Changes

None. Follow-up `a724282` adds `enabled_inputs()`-based fake-spawn checks for
enabled-exception expiry, replay, and six-record cross-wiring, each with zero
spawn and no environment-value result leak. It also adds the distinct
credential-like supplied key (`API_KEY`) denial/redaction check.

## Findings

- `local_control_provision._approval()` requires the exact task, action,
  enabled one-shot flag, six distinct bindings, and a current run window.
  `network_provider_exception` has an exact four-field schema. The disabled
  form requires `deny`/`none` and no environment keys; the enabled form admits
  only `configured_model_service_only`, `existing_local_only`, and a sorted,
  distinct subset of six named Windows configuration-root variables.
- The default approval retains the original prohibition list. An enabled
  exception replaces only the credential/network prohibition needed for the
  documented existing-provider/configured-model-service path; cleanup, merge,
  and push remain required. No endpoint or credential is represented in the
  schema.
- `run_opencode_once()` validates the approval and all-six binding projection,
  builds an environment only from an exact caller-supplied key set, consumes
  the run before its injected spawn, uses fixed `opencode.exe` and
  `shell=False`, and returns only redacted safe identifiers. It does not read
  the user environment itself.
- `_child_environment()` rejects unknown/missing keys, non-string or oversized
  values, control characters, and credential-like content. It passes a copied
  mapping only to the injected fake spawn and never serializes it in a result.
- Timeout handling is still limited to the matching injected process object's
  `terminate_tree()` call. It performs no retry or fallback.
- Source scans and imports show no process-launch implementation, networking,
  credential store/environment read, filesystem persistence, Git, CLI, or
  worktree action. Documentation consistently calls L1 `best_effort`, not a
  sandbox or enforced isolation boundary.

## Validation Check

- `D:\\codex work\\.venv\\Scripts\\python.exe -m py_compile scripts/local_control_provision.py scripts/local_opencode_executor.py`: passed.
- Affected B.1--H fixture suite with isolated pytest base temp: **93 passed**.
- `D:\\codex work\\.venv\\Scripts\\python.exe scripts/orchestrate.py validate`: passed.
- `git diff --check d50296d a724282`: passed.
- Scope check: the implementation and follow-up changed paths are all within the task card's
  `allowed_scope`; no `services/`, `src/`, `database/`, `cloud/`, `profiles/`,
  or other forbidden path changed.

## Scope Compliance

This review does not change implementation, task lifecycle, Git history,
runtime state, credentials, network state, or worktrees. It adds only this
review record. The operations index requested by the repository agreement is
not present at `docs/operations/README.md`; the directly relevant execution,
lead-orchestration, and L1 contract documents were reviewed instead.

## Accepted Artifacts

- `scripts/local_control_provision.py`
- `scripts/local_opencode_executor.py`
- `tests/scripts/test_local_control_provision.py`
- `tests/scripts/test_local_opencode_executor.py`
- `docs/operations/phase14.5-local-control-adapter-contract.md`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-opencode-network-credential-exception-14-delivery-report.md`

## Residual Risks

Even after the test fix, this remains a fake-spawn, best-effort boundary. It
cannot verify a provider, endpoint behavior, host credential handling, or
host-level isolation. A real OpenCode start requires separately accepted live
runner evidence and an exact current Phase H approval.
