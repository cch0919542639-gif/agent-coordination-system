# Independent review: Phase15 GitHub handoff

- Reviewer: codex-phase15-github-review
- Decision: accepted for local packet/publication preparation only.
- Exact reviewed bytes: independent-checks.json snapshot_sha256.
- Publication branch: codex/phase15-github-handoff-01, base bfc5163af6dca4b9b7dec6b599563e3cbf984cac.

The user direction is correctly expressed as independent host-local tasks exchanged through GitHub. No TLS, SSH, direct peer access, root-trust installation, runtime DB exchange, new provider calls or remote launcher is required. Both worker cards remain BLOCKED pending publication and explicit lead assignment; no second-host execution or wave completion is accepted here. The original direct-host pilot is CANCELLED by scope supersession in the integration tree, not marked successful.

Resolved findings:

1. The unchanged baseline imported StateController but that file was initially missing. The candidate now includes a fifth byte-identical pinned source solely for initialize and monkeypatch(apply). I independently exercised that fixture initialization. OfflineInbox imports stdlib only. The plan and source-pins explicitly exclude unsupported lazy parallel/resource APIs and CLI/runtime integration; this is not a complete runtime distribution.
2. Narrow .gitattributes entries now mark the five pinned inputs -text; git check-attr confirms all five, protecting their bytes despite core.autocrlf=true.
3. The lead card now explicitly allows the five source inputs and .gitattributes. Candidate paths match the current allowlist, with no imported TLS/private artifacts or the unrelated integration history.
4. Process budgets now distinguish one concurrent top-level pytest from the fixed baseline children (six concurrent/twelve total per invocation, thirty-six across three attempts); new tests must not launch processes.
5. Oversized initial failure XML was replaced with compact evidence plus raw archive hash/history. No initial failure was relabeled as success. Published evidence currently meets file/total caps.

Validation: independent coordination validator passed; all fifteen checks in independent-checks.json passed. Five pins match both the integration tree and source commit 501da4e5d6fb209a27a8fb8d54811f574d008e72. Plan/guide/worker cards match between trees. Guide links resolve and worker write scopes are disjoint. Lead baseline attempt 2 records 88 passed; I inspected its JUnit counts, 88 testcase elements, exit code and source pins rather than rerunning the suite. Attempt 1 preserves 88 setup errors/zero bodies caused by local temp permissions and a capture decoding failure. A task-specific temp path and UTF-8 capture fixed the environment without permissions changes.

The A and B packets have independent objectives and unique test/progress/delivery/evidence files. Their shared input is frozen, and a production defect stops the worker rather than authorizing a shared-module fix. The six validation and five durability requirements are actionable; the distinct-coverage rule prevents cosmetic duplication of baseline tests. Useful distinct observations include duplicate authentication-key rejection against an already populated journal, booleans in currently unparametrized integer fields, a held write lock followed by recovery, and an INSERT-receipt failure trigger rather than the baseline UPDATE-metadata failure trigger. Workers must verify their exact new coverage themselves.

Release conditions remain operational: reviewed publication authority and exact origin/branch; a fresh release commit after READY-card migration; explicit task/owner/machine/branch assignment; source pin verification; host-local evidence; independent candidate review; then combined integration validation. Task withdrawal/PR closure is not process-stop proof. Finite retry/time/evidence budgets, preservation of failures, local stop and revert-PR recovery are stated. Any implementation/doc/source change invalidates the corresponding reviewed hashes; lifecycle-only metadata moves require lead verification. No push, dispatch, merge or two-host success is authorized by this review.
