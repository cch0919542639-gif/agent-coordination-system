- Task ID: `phase14.5-durable-one-shot-consumption-48`
- Agent: `ORCHESTRATOR`
- Phase: `phase14.5-phase-h-live-pilot`
- Status: submitted for independent review

## Changed Files

- `scripts/one_shot_consumption.py`
- `tests/scripts/test_one_shot_consumption.py`
- Task 48 card and this report.

## Acceptance Criteria Coverage

- `consume_once` creates a namespace-scoped SHA256 marker with exclusive file
  creation, so concurrent duplicates have one winner and later process calls
  deny replay.
- The ledger writes only a schema label, namespace, and identity digest; caller
  state directory remains injectable.
- Invalid namespace/identity, non-directory state path, symlink/junction path
  components, duplicate use, and write errors fail closed. Identity strings
  are hashed before they form any filename.
- Test coverage includes separate approved bindings, separate permission keys,
  restart-equivalent replay, and a concurrent duplicate race.

## Validation Steps Performed

- Focused tests: 3 passed, 1 explicit skip (Windows policy prevented symlink creation).
- `python scripts/orchestrate.py validate`: passed.
- `python -m py_compile scripts/one_shot_consumption.py`: passed.
- `git diff --check`: passed; only existing line-ending warnings were emitted.

## Known Residual Risks

This store is a caller-supplied local filesystem mechanism. It does not yet
replace the executor's in-memory set or Task 44's in-memory consumed set;
Task 49 must wire the durable claims before any side effect.
