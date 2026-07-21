# Phase 14.5 Supervised Validation Boundary

`scripts/supervised_launch_validation.py` is a pure, in-memory validation
foundation for the frozen Phase 14.5 pilot. It validates JSON-shaped manifest,
approval, provenance, timeout, allowlist, and safe-audit inputs, then emits a
deterministic decision record containing only safe identifiers, a timeout, and
a branch/worktree digest.

The in-memory `argv` field is accepted only as a one-item opaque SHA-256
digest. It is not a command or executable identifier, and multi-item,
shell-like, or otherwise unapproved structures are rejected before a
supervised request reaches the future-executor gate.

It cannot read or write a manifest, inbox, approval, scheduler record, or task
lifecycle artifact. It has no runtime invocation, command definition,
executable path, environment, network, or process behavior. A schema-valid
`supervised_one_shot` request returns
`supervised_launch_requires_future_executor`; it is not eligible to run here.

Any future launch-executor task requires the accepted design's separate
one-shot operator approval for the exact immutable manifest, a separately
approved executable and argument design, independently reviewed audit,
incident, stop, rollback, and test plans, plus explicit acceptance of the
external-runtime/provider/credential/data-handling risk. It must not reuse
this validation task as launch authority.
