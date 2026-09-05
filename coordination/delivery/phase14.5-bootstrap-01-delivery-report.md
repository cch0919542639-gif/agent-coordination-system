- Task ID: phase14.5-bootstrap-01
- Agent: external-agent-platform-33; corrective fix reassigned to ORCHESTRATOR
- Phase: phase14.5-bootstrap-connector
- Status: REVIEW

## Changed Files

- `scripts/bootstrap_handoff.py` (new) — deterministic, local-only bootstrap handoff module
- `tests/scripts/test_bootstrap_handoff.py` (new) — 23 focused safety, expiry, replay, integrity, path, and source-level tests
- `coordination/incidents/20260905-02_opencode-b0-corrective-session-no-delivery.md` — external corrective-session capability incident
- `docs/operations/phase14.5-bootstrap-handoff-operator-runbook.md` (new) — manual operator steps for handoff preparation

## Validation Steps Performed

- `D:\\codex work\\.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider tests\\scripts\\test_bootstrap_handoff.py -q` — 23/23 tests pass
- `python scripts/validate_coordination_files.py` — coordination validation passed
- `git diff --check` — no whitespace or path issues
- Source-level review confirms no subprocess, os.system, Popen, shell=True, socket, urllib, requests, httpx, open(), Path(), shutil, os.mkdir, os.makedirs, or git invocations in `bootstrap_handoff.py`
- Deterministic fake-clock testing proves expiry, pre-issued, and replay denials
- Approval digest verification proves terminal denial for altered records
- Unsafe path rejection covers absolute paths, dotdot sequences, Windows drive paths, and backslash paths
- Handoff envelope contains only safe identifiers, digests, and project-relative paths
- `launch_authorized` is explicitly `False` in every produced envelope

## Known Residual Risks

- The bootstrap handoff is a context-envelope producer only; it does not verify
  that the OpenCode runtime is actually available at the worktree reference.
  Runtime availability must be rechecked by the operator before any manual use.
- The idempotency store is an in-memory set for testing; a production
  implementation would persist it. This is intentional for this task scope.
- Cross-machine delivery and supervised launch remain deferred and are not
  in scope for this task.

## Acceptance Criteria Coverage

| Criterion | Evidence |
| --- | --- |
| Local-only, operator-invoked bootstrap handoff producing one bounded, immutable, single-use envelope | `build_handoff()` in `scripts/bootstrap_handoff.py` returns one `handoff_prepared` envelope with `one_shot: True`, content digest, and size limit. |
| Explicit operator approval record required | `_validate_approval()` requires all required fields, canonical approval digest, exact approver role, one_shot and enabled flags, and non-expired timestamp window. |
| Safe task-relative references, expiry, idempotency, replay denial | Path safety checked by `_is_relative_safe()`, expiry by timestamp window, idempotency by `_idempotency_key()` and `idempotency_store`, replay denied on duplicate key. |
| Emit only safe identifiers, digests, and relative paths | Envelope contains `handoff_id`, `content_digest`, `idempotency_key`, and project-relative `protocol_references` and `worktree_ref`. No absolute paths, credentials, or raw content. |
| No code path invokes process, shell, runtime, network, credential, Git, or lifecycle mutation | Source-level tests (`test_source_contains_no_process_shell_or_network_apis`, `test_source_contains_no_file_io_or_git_operations`) confirm zero forbidden tokens. |
| Document human steps | `docs/operations/phase14.5-bootstrap-handoff-operator-runbook.md` describes all five operator steps. |
