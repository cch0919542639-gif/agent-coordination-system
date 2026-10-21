# Lead independent review: B durability delivery and local combination

- Task: phase15-github-durability-01
- Reviewer: codex-phase15-github-review
- Decision: accepted for B implementation/evidence and the local combined candidate.
- B PR: #5; submitted head 2a76667b19df281d0893bd0bf422cf5187331adf.
- B tested candidate: 79ea5112a6e56956bf980ed1f4c43e09894807cf.
- Worker base: 910cb9175870fd6f3df6e699b632f85cb0a97bf4.
- Local combined candidate: 9114fe64bfdac65fc483187dfd23bf5f201cd6ba.
- Exact file and evidence hashes: lead-independent-checks.json.

No unresolved finding requiring a code change. The five source pins are unchanged in the B tested candidate, B submitted head and combined candidate. B test raw bytes and Git blobs match SHA256 a74f5eec77d047ba75e073f6bdf8c8b53eedfcd9173e15e09ce2eb9b93fef826. The B branch diff is within its assigned test/card/progress/delivery/incident/evidence scope; it does not change A or shared production inputs. Changes after the B tested candidate are reporting/evidence/lifecycle metadata, with no test/source changes.

All six new tests add distinct observations beyond the pinned eighty-eight:

1. Reinitialize a journal with two receipts and replay both; mutating the caller's returned ACK cannot alter the stored ACK or sequence.
2. A changed known request at sequence 50 refuses after reopening, then a valid fresh request at sequence 2 succeeds. The refused request cannot reserve a future high-water mark.
3. Persist and reopen the signed-64-bit maximum sequence without wraparound; unseen lower/equal sequences refuse while previously known ACKs remain replayable.
4. Hold an actual separate SQLite BEGIN IMMEDIATE writer lock. The receive path reaches its real finite busy timeout and refuses; state stays unchanged; rollback/close releases the lock and exact retry succeeds. The 4 <= elapsed < 15 tolerance brackets the current five-second timeout. It is a test assertion plus the outer invocation limit, not proof of a hard real-time scheduler guarantee. B JUnit records 5.549 seconds for this case, consistent with the intended path.
5. A BEFORE INSERT trigger aborts a second receipt after a first accepted receipt. Existing ACK/state survive and dropping the trigger allows the same request to succeed. This differs from the baseline metadata UPDATE trigger.
6. The injected Connection.commit observes both uncommitted writes (receipt count 1 and sequence 1), then raises a SQLite OperationalError. OfflineInbox catches the error, closes the connection and rolls back; independently reopened state matches the original empty journal and the exact retry succeeds after removing the patch. This exercises commit-method failure after both writes rather than a process exit or earlier statement failure.

B execution evidence is consistent: reported hostname 技嘉202509, Windows 11 and Python 3.13.15; its JUnit hostname matches the JSON report. Passing attempt 2 has 94 successful testcase elements (88 baseline + 6 new), zero errors/failures/skips, exit zero and 9.755 seconds outer runtime. Two of three allowed pytest invocations were used; recorded implementation work was 207.890 seconds within the thirty-minute window. Initial attempt 1 remains preserved as one collection error/exit 2 from the unqualified helper import, repaired to the repository-qualified import. The first coordination validation failure and corrected pass also remain recorded. New tests create no child processes, network or provider calls. Evidence is compact and under the file/total caps; the retained failure trace contains ordinary local paths, not key material, credentials, DBs, environment dumps or private transcripts.

The lead's local combined execution binds the reviewed A and B test hashes and five source pins to candidate 9114fe64bfdac65fc483187dfd23bf5f201cd6ba. JUnit contains 108 successful testcase elements (88 + 14 + 6), zero errors/failures/skips, and its attributes match pair-execution.json. Exit zero, no timeout, outer elapsed 38.657 seconds. This used angeline's third and final allowed pytest invocation; no further retry is allowed under this packet. A driver UTF-8 preflight failure is separately retained and records that pytest had not started.

I independently inspected the sources and baseline differences, Git scopes/commit bytes, XML/JSON consistency, budgets and evidence caps, and ran the coordination validator successfully. Fifteen checks pass in lead-independent-checks.json. I did not run pytest, change sources/cards, post GitHub comments/reviews, commit, push or perform peer/provider actions.

Acceptance is limited to B's cooperative host report and the tested local combination. It does not prove adversarial host identity, hardware crash/power-loss behavior, remote process custody or a formal PR merge. PR acceptance/merge, publication and canonical task completion remain separate lead/operator actions; no such authority is granted by this review. Pending root summaries that still describe B as READY are historical and need lead updates when canonical acceptance is recorded.
