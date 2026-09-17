# Phase 14.5 Effectful Adapter Contract

`scripts/effectful_adapter.py` is the sole reviewed local process boundary.
It creates only a caller-injected process and only after exact request,
one-shot approval, admitted grant, and current enforcement-attestation bindings
validate.  It consumes the run before calling the factory, has no retry, and
waits for at most 900 seconds.  Timeout terminates only the returned process.

An attestation must be enabled, current, and exact for task, run, grant,
agent, and worktree.  It must explicitly assert restricted writes and process
identity and state `network_egress: deny`; a grant's deny-network policy alone
cannot satisfy this check.  The adapter does not establish or verify platform
enforcement itself: that remains the provisioning task and independent review.

Results are allowlisted IDs, timeout, and a terminal decision only.  The
adapter has no CLI, persistence, network, credential, Git, worktree, prompt,
command/argv, output, or transcript handling.  Tests use fake factories only.
