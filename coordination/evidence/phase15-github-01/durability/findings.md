# Durability observations

Task: phase15-github-durability-01. Host: 技嘉202509.
Worker base: 910cb9175870fd6f3df6e699b632f85cb0a97bf4.
Dispatch: 7e2d2fc492f023fc6e6b30f0147be4d0ed20a7f6.
Tested candidate: 79ea5112a6e56956bf980ed1f4c43e09894807cf.

## Additional coverage beyond the pinned 88 tests

1. Explicitly reinitialize a populated journal containing two receipts, replay
   both through new inbox instances, and mutate a returned ACK. Stored receipts
   and sequence remain unchanged. Baseline replay did not exercise this combined
   reinitialization/multiple-receipt/client-mutation boundary.
2. After reopening, reject a changed known request proposing sequence 50; then
   admit a fresh request at sequence 2. The refused conflict reserves no future
   sequence, and the original ACK remains replayable.
3. Persist the signed-64-bit maximum sequence, reinitialize, reject unseen lower
   and equal sequences, and replay both the original and maximum-sequence ACKs.
   Baseline used a small floor, not the maximum representable persisted value.
4. Hold a real SQLite BEGIN IMMEDIATE write lock in a separate connection.
   Receive refuses with journal_unavailable after the finite five-second wait
   (test tolerance 4..15 seconds), leaves state intact, and succeeds after unlock.
   Baseline had process concurrency but no held-lock timeout/recovery observation.
5. Abort INSERT on receipts with a temporary trigger after one successful
   receipt. Existing state/ACK survive; dropping the trigger permits the exact
   failed request to succeed. Baseline faulted UPDATE metadata instead.
6. Inject a commit exception after observing both uncommitted writes (receipt
   count 1 and sequence 1). Closing the connection rolls both back; restoring
   the real connection permits retry. Baseline tested abrupt process exit and
   statement failure, not a commit method raising a SQLite exception.

All new cases use tmp_path databases, existing synthetic HMAC fixture helpers
from the pinned baseline, and no child process or external service.

## Execution history

- Attempt 1: collection error, 0 passed / 1 error; unqualified baseline fixture
  import was incompatible with the repository's test package. Preserved in
  attempt-1.execution.json, attempt-1.junit.xml and attempt-1.txt.
- Repair: one import changed to tests.scripts.test_offline_inbox; no source edit.
- Attempt 2: 94 passed, 0 failed/errors/skipped, pytest runtime 8.83 seconds.
  Full metadata and digests are in execution.json; JUnit is attempt-2.junit.xml.
- Two of three allowed pytest invocations used. No third invocation needed.
  Only the passing attempt reached the existing synthetic subprocess tests;
  their fixed budget is six concurrent / twelve total. New tests launch zero.

## Limits

Reopening means new SQLite connections/inbox instances; the new tests do not
claim OS restart or power-loss evidence. Synthetic commit injection is not a
hardware failure. Host information is self-reported collaboration evidence.
Independent review and two-host integration remain lead-owned and pending.
