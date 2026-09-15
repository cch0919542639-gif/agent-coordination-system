# Independent Review: phase14.5-worktree-context-04
- Review ID: review-phase14.5-worktree-context-04
- Task ID: phase14.5-worktree-context-04
- Phase: phase14.5-worktree-context
- Reviewer: INDEPENDENT_PLATFORM_REVIEWER
- Reviewed commit: 93544ac
- Reviewed At: 2026-09-15
- Decision: accepted

## Summary

The Phase D fixture-only allocation and context implementation meets its
accepted contract. No runtime, network, credential, persistence, or real Git
worktree capability was introduced.

## Findings

- Six-identity dry-run allocation is deterministic and collision-free without creating a worktree. `plan_worktree_allocations()` (`scripts/worktree_context.py:83-120`) requires a non-empty sequence of exact four-field identity mappings (`set(identity) != IDENTITY_FIELDS` → `deny_invalid_identity`), rejects duplicate task/branch/worktree (`deny_allocation_collision`), sorts by task ID, and binds each identity to a stable SHA-256 `allocation_id` over canonical JSON. `test_six_identity_plan_is_deterministic_and_collision_free` proves reversed input yields identical output with 6 distinct relative worktree paths; `test_duplicate_task_branch_or_worktree_is_denied` covers all three collision axes.
- Input schema is exact and fail-closed; branch/worktree are relative and owner-bound. `_identifier()` / `_relative_ref()` (`34-49`) reject empty, oversized, traversal (`..`), backslash, drive-colon, URL, and `@{` forms; identities failing them yield `deny_unsafe_provenance`, and branch/worktree outside `agent/<owner>/` / `worktrees/<owner>/` yield `deny_provenance_policy` (`107-111`). Extra keys (e.g. `command`) yield `deny_invalid_identity` via exact-set check plus recursive `_unsafe_content`; covered by `test_identity_schema_and_unsafe_provenance_fail_closed`.
- Allocation SHA-256 binding is re-verified before snapshot. `build_bounded_context_snapshot()` (`123-175`) requires the exact five-field allocation set, hex64 `allocation_id`, relative branch/worktree, owner-prefix policy, then recomputes `sha256(canonical(identity))` and returns `deny_invalid_allocation` on mismatch (`139-141`). Provenance mismatch between task projection and allocation yields `deny_provenance_mismatch` (`152-153`); covered by `test_snapshot_rejects_untrusted_refs_expiry_limit_and_provenance` (mutated `task_id` and `allocation_id` both denied).
- Context contains only allowlisted projection, relative dependency refs, vetted allocation, and schema/hash/size/sensitivity/expiry. Projection is built strictly from `TASK_CARD_ALLOWLIST` (`151`), dependency refs must each pass `_relative_ref` (`144-145`), and the returned body carries `schema_version`, `sensitivity_label`, `max_bytes`, canonical SHA-256 `snapshot_hash`, `byte_size`, and `expires_at` (`154-175`). `test_snapshot_is_hash_bound_allowlisted_and_immutable` proves extra card text (`untrusted_body`) is excluded while the hash stays stable, and the emitted `allocation` uses `branch_ref`/`worktree_ref` relative forms.
- Unsafe content fails closed. Recursive `_unsafe_content()` (`66-76`) denies forbidden keys (prompt, command, credential, secret, token, transcript, source/source_body/body, output, logs, argv, env, …) and absolute-path values anywhere in task card, allocation, or identity; `snapshot_ref`, dependency refs, expiry (`deny_expired` for missing/naive/past), `max_bytes` bounds (`deny_invalid_limit` outside 1..8192), and oversize canonical bodies (`deny_context_too_large`) are all denied. Covered by `test_snapshot_rejects_sensitive_absolute_and_oversize_content` and `test_snapshot_rejects_untrusted_refs_expiry_limit_and_provenance`.
- Success records carry no sensitive values, prompts, source/transcript, or absolute paths. Success output holds only the allowlisted projection, relative `snapshot_ref`/dependency refs, the vetted allocation subset, hash/size/schema/sensitivity/expiry metadata; `_unsafe_content` gates both inputs so a `prompt` key or `C:/…` value can never reach a `snapshot_ready` record. Consistent with the Run Manifest Contract (safe IDs only; no bodies, credentials, prompts, transcripts, absolute paths) and the Dependency and Context Contracts (untrusted text is data, never expanded into configuration — this module takes no body-text input at all).
- No runtime, network, credential, filesystem-persistence, or git-worktree behavior. Module docstring states fixture-only planning; imports are `hashlib/json/datetime/typing` only. Negative API scan over `scripts/worktree_context.py` finds no `subprocess/Popen/os.system/socket/requests/urllib/open(/Path(/mkdir/shutil/getpass/os.environ/git worktree` tokens (scan exit clean); `test_source_has_no_filesystem_git_or_runtime_apis` enforces the boundary in-repo.

## Required Changes

- none

## Validation Check

- `py_compile scripts/worktree_context.py` — passed.
- `pytest -p no:cacheprovider tests/scripts/test_worktree_context.py` — 7 passed.
- `pytest -p no:cacheprovider test_worktree_context + test_durable_scheduler + test_controlplane_admission + test_supervised_opencode_launcher` — 58 passed (no scheduler/admission/launcher regression).
- `python scripts/orchestrate.py validate` — passed ("Coordination validation passed.").
- `git diff 6321d66..93544ac --check` — passed (no whitespace errors).
- `git diff --name-only 6321d66..93544ac` — 6 files: `coordination/delivery/phase14.5-worktree-context-04-delivery-report.md`, `coordination/progress/orchestrator.md`, `coordination/task-board/review/2026-09-03_phase14.5-worktree-context-04_isolated-worktrees-and-context.md`, `docs/operations/phase14.5-worktree-context-contract.md`, `scripts/worktree_context.py`, `tests/scripts/test_worktree_context.py`.
- Note: the default pytest basetemp under `C:\Users\angel\AppData\Local\Temp\pytest-of-angel` is permission-denied in this environment (pre-existing, unrelated to the change); runs above used `--basetemp` under `...\Temp\opencode\wc-ctx-*` and pass.

## Scope Compliance

- All changed files fall inside the task-card `allowed_scope` (`scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/task-board/**`, `coordination/progress/**`, `coordination/delivery/**`); no `forbidden_scope` paths (`services/`, `src/`, `database/`, `cloud/`, `profiles/`) are touched — verified by name-only diff filter (no matches).
- Task card remains `REVIEW`; reviewer performed no lifecycle transition and added only this review record. No implementation, Git history, runtime state, or credentials were modified, read, or transmitted during review (read-only inspection plus local deterministic test execution).

## Accepted Artifacts

- `scripts/worktree_context.py`
- `tests/scripts/test_worktree_context.py`
- `docs/operations/phase14.5-worktree-context-contract.md`
- `coordination/delivery/phase14.5-worktree-context-04-delivery-report.md`

## Residual Risks

- Fixture-only planning: nothing here provisions or verifies a real Git worktree, persists a runtime manifest, launches a connector, reads credentials, or uses network transport — a later execution phase must bind any real provisioner to these vetted allocation records instead of treating task-card text as configuration (as the delivery report notes).
- Owner-prefix binding lowercases the owner for comparison; identifier charset prevents case-collision tricks at this layer, but a later provisioner must preserve the same normalization.
- `max_bytes` upper bound (8192) aligns with the scheduler snapshot bound; any future bound change must be updated in both modules together.
