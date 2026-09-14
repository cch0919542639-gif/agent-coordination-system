# Review Report: phase14.5-scheduler-03

- Review ID: review-phase14.5-scheduler-03
- Reviewer: INDEPENDENT_PLATFORM_REVIEWER
- Task ID: phase14.5-scheduler-03
- Phase: phase14.5-durable-scheduler
- Decision: accepted
- Reviewed At: 2026-09-14
- Reviewed commit: `134bbfb` (feat: add durable scheduler control plane)
- Worktree: `D:\codex work\worktrees\orchestrator\phase14.5-controlplane-02`
- Task card: `coordination/task-board/review/2026-09-03_phase14.5-scheduler-03_durable-scheduler.md` (status: REVIEW, unchanged by reviewer)
- Dependencies: [connector admission review](coordination/reviews/review-phase14.5-controlplane-02.md) (accepted), [launcher review](coordination/reviews/review-phase14.5-launcher-09.md) (accepted)

## Summary

Phase C durable scheduler is accepted. `scripts/durable_scheduler.py` implements the sole revision-guarded lifecycle writer with HMAC-authenticated immutable envelopes, atomic inbox/outbox persistence, sanitized append-only event projections, and deterministic restart/replay recovery. All 7 review acceptance criteria have direct code plus focused-test evidence. No runtime launch, network, credential access, Git mutation, push, or merge behavior was found.

## Findings

| # | Acceptance | Verdict | Code evidence | Test evidence |
| --- | --- | --- | --- | --- |
| 1 | Only scheduler writes lifecycle state via expected revision; conflict fail-closed with `reconciliation_required` | PASS | `TaskCardStore.compare_and_swap()` (`scripts/durable_scheduler.py:663-691`) enforces expected==stored under exclusive dir lock, tmp-file + rename commit; `Scheduler.ingest()` pre-check (`796-809`) returns `deny_revision_conflict` + `incident: reconciliation_required` without state overwrite, plus CAS-race path (`834-850`) re-reading store on conflict | `test_dispatch_accepts_and_advances_guarded_revision`, `test_revision_conflict_creates_incident_without_overwrite`, `test_store_compare_and_swap_rejects_stale_revision`, `test_task_card_transition_persists_through_owned_store` (incl. stale-revision denial after restart) |
| 2 | Envelope precisely validates schema, HMAC, sender, token reference, expiry, idempotency key, lease epoch | PASS | `ENVELOPE_FIELDS` exact-set check (`38-55`, `189-235`); `validate_envelope()` enforces exact keys, safe identifiers, hex64 `idempotency_key`/`context_snapshot_hash`/`auth_tag`, known `MESSAGE_TYPES`, int attempt/epoch >= 1, relative refs, hash-bound snapshot, `issued <= now < expires`; `sign_envelope`/`verify_envelope_auth` HMAC-SHA256 with `hmac.compare_digest` (`244-259`); `ingest()` verifies scheduler-owned secret per `sender_agent_id` (`772-775`) then constant-time `sender` + `capability_token_ref` equality (`777-781`); reference-only copies without valid tag denied | `test_missing_auth_tag_is_invalid_envelope`, `test_malformed_envelopes_are_denied`, `test_forged_copied_references_without_scheduler_secret_are_denied`, `test_tampered_canonical_data_invalidates_auth_tag`, `test_unknown_sender_without_scheduler_secret_is_denied`, `test_unauthenticated_sender_and_token_are_denied`, `test_expired_and_not_yet_valid_envelopes_are_rejected` |
| 3 | Replay, duplicate, expired, unauthenticated, stale-epoch messages cause no second dispatch or state mutation | PASS | `seen_message_ids` exact replay denial (`783-784`, no event/state change); cross-ID idempotency-key denial with event only (`785-787`); epoch fencing `epoch < current` → `deny_stale_epoch` (`789-794`); immutable `message_id` rewrite refused (`372-399`, `ingest 828-832`); denied paths return before inbox write / CAS; `recover()` replays outbox with hydrate + accepted-ID set (`944-987`), interrupted inbox-only commits complete exactly once | `test_duplicate_message_replay_never_duplicates_dispatch` (inbox file set unchanged), `test_duplicate_idempotency_key_with_new_message_is_denied`, `test_expired_and_not_yet_valid_envelopes_are_rejected`, `test_unauthenticated_sender_and_token_are_denied`, `test_stale_lease_epoch_denied_and_new_epoch_accepted`, `test_restart_recovery_never_duplicates_accepted_dispatch`, `test_restart_recovery_delivers_pending_outbox_exactly_once`, `test_recover_completes_interrupted_inbox_commit_exactly_once` |
| 4 | inbox/outbox atomic writes; event feed only safe projections, rebuildable, not a second lifecycle authority | PASS | `write_envelope_atomic()` tmp-file + fsync + atomic rename + fsync-dir, identical-bytes idempotent, different-bytes `ValueError` (`372-399`); `append_event_atomic()` per-path in-process lock + cross-process `.lockdir`, torn-tail repair, `event_id` dedup, single `O_APPEND` + fsync (`471-532`); `build_event_projection()` safe IDs/refs/hashes/decision/timestamp only, excludes `capability_token_ref`/`auth_tag`/bodies (`318-342`); `rebuild_run_view()` derived `task/run` view (`345-369`); `TaskCardStore` is the single lifecycle adapter (`593-704`); contract + architecture confirm feed is evidence only | `test_atomic_envelope_write_is_idempotent_and_immutable`, `test_event_append_is_idempotent_and_rebuilds_run_view` (incl. `capability_token_ref` absence), `test_task_card_transition_persists_through_owned_store`, `test_interrupted_event_append_heals_on_next_append`, `test_concurrent_event_appends_are_exclusive_and_idempotent` (12 + 4 dup threads, 12 lines, no interleave) |
| 5 | No persistent record contains credential, secret, prompt, task body, transcript, absolute path, or raw runtime output | PASS | `FORBIDDEN_KEYS` bare-material denylist (`75-94`, `*_ref`/`*_hash` safe forms excluded); `_safe_relative()` rejects absolute/traversal/Windows-drive/URL forms (`120-138`); `_has_absolute_path` + `_forbidden_key/value_present` enforced in `validate_envelope`, `append_event_atomic`, `build_context_snapshot`; `TASK_CARD_ALLOWLIST` projection only (`59-70`); snapshot bounded by `MAX_SNAPSHOT_BYTES` with hash (`271-311`); run manifest non-goal per contract | `test_forbidden_material_and_absolute_paths_are_denied`, `test_context_snapshot_is_bounded_and_safe` (prompt stripped, traversal/absolute denied), `test_persisted_records_carry_no_forbidden_content`, `test_auth_tag_and_card_store_carry_no_forbidden_content` (scheduler secret absent from envelope/event/card) |
| 6 | No runtime launch, network, credential access, Git mutation, push, or merge | PASS | Module docstring non-goals (`1-17`); imports limited to `hashlib/hmac/json/os/tempfile/threading/time/datetime/pathlib` — `os` used only for fd/file/dir-lock/fsync primitives; no `subprocess/socket/requests/urllib/Popen/os.system/shutil/getpass/pty/git`; secrets arrive via injected `auth_secrets` mapping, never read from a store; contract Non-Goals section restates boundary | `test_source_has_no_launch_network_or_credential_apis` (source scan) + all tests use fake clock + fixture dirs, no live process/network |
| 7 | Task card + delivery report acceptance items each have code + test evidence | PASS | Task-card acceptance (4 bullets) maps to rows 1-4 above; delivery-report coverage table rows map to `Scheduler.ingest`/`TaskCardStore.compare_and_swap`, HMAC + atomic helpers + projection tests, 29 fake-clock tests, sanitization denials — all confirmed present, no orphan claim | Delivery-report validation claims re-verified below |

## Validation Check

- `pytest -p no:cacheprovider --basetemp=<clean tmp> tests/scripts/test_durable_scheduler.py` — **29 passed**.
- `pytest ... test_durable_scheduler.py test_controlplane_admission.py test_supervised_opencode_launcher.py` — **51 passed** (no regressions in Phase B / B.1).
- `python scripts/orchestrate.py validate` — **passed** ("Coordination validation passed.").
- `git diff 7e475a0..134bbfb --check` — **passed** (no whitespace errors).
- `rg -n "(subprocess|socket|requests|urllib|http|Popen|os\.system)" scripts/durable_scheduler.py` — **no matches**.
- Extended source scan for `credential|secret|password|getpass|os.environ|merge|push|network|launch` hits are limited to: docstring boundary statement, `FORBIDDEN_KEYS` denylist entries, and the injected HMAC `secret` parameter — no credential-store read, no network/launch, no Git mutation.
- `git diff 7e475a0..134bbfb --stat`: 6 files, all inside task-card `allowed_scope` (`scripts/`, `tests/scripts/`, `docs/operations/`, `coordination/task-board/`, `coordination/progress/`, `coordination/delivery/`); no `forbidden_scope` paths (`services/`, `src/`, `database/`, `cloud/`, `profiles/`).
- Note: default pytest basetemp `C:\Users\angel\AppData\Local\Temp\pytest-of-angel` is currently permission-denied in this environment (pre-existing, unrelated to the change); rerun with `--basetemp` under `...\Temp\opencode\pytest-tmp*` passes as above.

## Scope Compliance

- Task card remains `REVIEW`; reviewer made no lifecycle transition and edited no implementation files — only this review record is added, per the review assignment.
- No runtime started, no credentials read, no network transmission, no push/merge performed during review (read-only inspection plus local deterministic test execution).
- Architecture (`controlled-orchestration-architecture.md`: Durable Scheduler Protocol) vs contract (`phase14.5-durable-scheduler-contract.md`) vs implementation envelope fields, `reconciliation_required` semantics, atomic-file transport, and event-as-projection rule are consistent.

## Residual Risks

- Deterministic and fixture-driven: no real runtime launch, lease timers, worktree provisioning, review bundling, or operator commands — deferred to Phase D–G per contract non-goals and delivery report.
- Concurrency boundary is single-machine (in-process lock + dir lock, `O_APPEND` + fsync); cross-machine transport is an explicit non-goal for a later design approval.
- `auth_secrets` correctness rests with the scheduler owner/caller; a wrong-secret mapping fails closed (denial) but secret lifecycle itself is out of scope here.
- Torn-tail repair heuristic treats a newline-terminated complete-JSON tail as intact; interrupted mid-line bytes are dropped and healed on next append (covered by test).
- Repository task-card mutation beyond the scheduler-owned JSON store shape, and real lease timing, remain subject to later Phase D/E contracts.

## Accepted Artifacts

- `scripts/durable_scheduler.py`
- `tests/scripts/test_durable_scheduler.py`
- `docs/operations/phase14.5-durable-scheduler-contract.md`
- `coordination/delivery/phase14.5-scheduler-03-delivery-report.md`

## Required Changes

- None.
