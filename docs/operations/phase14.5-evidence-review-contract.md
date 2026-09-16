# Phase 14.5 Evidence Review Contract

`scripts/evidence_review.py` is a pure, in-memory projection helper.  It
accepts caller-provided mappings only; it does not read repository state,
persist records, start a runtime, contact a network, invoke Git, or access
credentials.

`build_review_bundle()` accepts an exact review-task identity and exact safe
evidence references, then returns a task-keyed deterministic bundle. References
are project-relative slash paths made only of alphanumeric, dot, underscore,
and hyphen path components; whitespace and prompt-like scalar values fail
closed. Bundle
fields are limited to task-card, branch, changed-file, validation, delivery,
review, and incident references.  Raw logs, prompts, source bodies,
credentials, and absolute paths fail closed.

`queue_submission()` only produces a reviewer-targeted queue projection.  It
does not accept, merge, push, or change lifecycle state.

`dependency_unlock()` walks an exact caller-provided hard-dependency graph.
It returns `dependency_unlocked` only when the subject is `READY` and every
transitive dependency is non-conflicted `DONE`.  Missing, cyclic, malformed,
revision-conflicted, blocked, rejected, cancelled, and other non-DONE nodes
deny the unlock.  A future scheduler integration remains the sole writer of
task-card lifecycle state.
