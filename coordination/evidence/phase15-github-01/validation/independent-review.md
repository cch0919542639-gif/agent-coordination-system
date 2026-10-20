# Independent implementation review: angeline validation task

- Task: phase15-github-validation-01
- Reviewer: codex-phase15-github-review
- Decision: accepted for the reviewed implementation; lead owns task acceptance.
- Worker base: 910cb9175870fd6f3df6e699b632f85cb0a97bf4.
- Tested candidate: ff18ea99922ece71432c0b73a7158170ef53ff25.
- New test SHA256: 38f707647e2e8e85ac95569f1500b0801b3bdcd4908bb66484ebbda609dc968b.
- Exact source/evidence/card snapshot and checks: independent-checks.json.

No unresolved implementation finding. One initial finding was fixed: importing the sibling helper as test_offline_inbox failed collection under this repository's pytest package context. The final candidate uses tests.scripts.test_offline_inbox. The five frozen inputs are unchanged; neither production code nor the B task was changed. The candidate diff stays within A's assigned test/card/progress/evidence scope.

The fourteen new cases are not renamed copies of the existing eighty-eight. Existing malformed/type/binding/authentication tests mostly exercise an empty initialized journal. Thirteen new parameter cases first durably admit a request and then demonstrate that the presence of its receipt cannot shortcut validation. They patch SQLite connection to fail if reached, assert exact refusal categories, inspect verifier call counts (zero for structural/type/binding rejection; one for invalid signatures and verifier exceptions), compare complete metadata/receipt state after refusal, and confirm the valid replay returns the original ACK.

Specific additional boundaries are escaped duplicate outer body keys, duplicate authentication key_epoch, booleans in six integer fields absent from the original type parametrization, and truncated JSON with fixed json_invalid. Destination/base mismatch and authentication failures gain the already-recorded-receipt precondition, before-DB proof, verifier order observation and preserved ACK checks. The fourteenth case proves a valid canonical replay padded exactly to MAX_BYTES is admitted, while one more byte refuses before either verifier or SQLite and leaves state unchanged. Thus the tests cover a potential unsafe dedup-before-auth fast path and an exact size-limit edge, beyond the old empty-journal refusal checks.

Evidence verification: attempt 1 is preserved as exit 2/one collection error at candidate 37618094f323ca240858c418659fd74145a9c38f. Attempt 2 binds the corrected candidate and new test digest, records exit 0 and no timeout, and its JUnit contains exactly 102 successful testcase elements: 88 baseline plus 14 new, zero errors/failures/skips. JUnit suite attributes match execution.json. Attempt 2 used 30.078 seconds outer elapsed within the 180-second limit; two of three pytest invocations are consumed and claim-to-result is within the 30-minute window. Host evidence reports angeline and records no B execution. Evidence file/total sizes remain under the assigned caps.

I independently inspected source, candidate diff, baseline distinctions, Git pins, execution/JUnit consistency and scope, and ran the coordination validator successfully. I did not rerun pytest or consume a third invocation. Baseline runtime, helper fixtures and callbacks remain synthetic/local; the new tests initiate no subprocess, network or provider work. Host evidence remains cooperative execution evidence, not adversarial identity proof.

This review accepts A's tested code and evidence only. It does not claim B execution, dual-host integration success, publication authorization or final task acceptance. Lead must preserve the reviewed test bytes through integration (the planned narrow -text attribute is a publication-side concern), update final delivery/lifecycle metadata separately and perform any required combined integration validation. Any subsequent test/source change needs affected verification and renewed candidate binding.
