# AgentMemory local synthetic trial (2026-10-29)

Two isolated WSL runs used the actual AgentMemory0.4.3 x86_64 binary from the
verified official image layer, a local Qwen2.5-3B model and the actual ACS
adapter. Each used a new synthetic Git source, temporary department/user and
database, numeric loopback endpoints and no real document or external model.

Both runs passed health, synthetic-source validation and adapter import. Both
produced one L1 atom with the intended Chinese synthetic task state, but neither
preserved the exact `[ACS-CARD:...]` source marker. The adapter correctly refused
verification, kept the receipt `submitted` and did not activate the batch.
On the second run direct upstream BM25 recall returned that synthetic task; this
does not mean adapter provenance or withdrawal checks passed.

One atom carried the deterministic session ID, but it is not yet adequate proof
of a source binding: the pinned upstream L1 implementation can update/merge into
an existing target and retains that target's other fields. The public atom JSON
does not expose its internal `source_message_ids`. The sample did not itself
exercise a cross-session merge. Do not weaken marker checks without a new
verified correlation contract covering merge, updates, replay and withdrawal.

The first simple model-only prompt previously passed four synthetic items; it
explicitly listed status rules and was not the actual upstream extraction prompt.
This real-pipeline result supersedes any assumption that marker preservation was
proven. One card and two runs do not establish recall quality, 8/10 benchmark,
independent review, NAS persistence or multi-device readiness. Formal source
cards remain unapproved; PR11 stays Draft and the task remains REVIEW.

## Unintended preliminary startup

Running `memory-server --version` unexpectedly started the default core instead
of printing a version. It listened on loopback without authentication for about
18 seconds and was stopped. Default WSL `.agent-memory` contained `audit.db`,
`system.db` and SQLite sidecars with modification times in that period. Their
prior existence and contents were not established; they were left untouched.
All subsequent trials explicitly used isolated temporary homes, data and ports.

Sources: [L1 merge implementation at v0.4.3](https://github.com/hsuanshao/AgentMemory/blob/f433d901de638444c56162d3bd5fc2a1280cf60d/crates/memory-application/src/pipeline/l1.rs#L364),
[atomic API serialization at v0.4.3](https://github.com/hsuanshao/AgentMemory/blob/f433d901de638444c56162d3bd5fc2a1280cf60d/crates/memory-gateway/src/handlers/memory.rs#L81).
