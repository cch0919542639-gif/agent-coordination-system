# Angeline validation coverage

Tested candidate ff18ea99922ece71432c0b73a7158170ef53ff25. Fourteen new
cases supplement existing88;the production module and five frozen inputs are unchanged.

| New observation | Cases | Distinction from baseline |
| --- | ---: | --- |
| Malformed JSON against a recorded request | 1 | Exact json_invalid and no DB open;old receipt cannot authorize bypass |
| Escaped duplicate body key | 1 | JSON unicode escape resolves to duplicate existing field |
| Duplicate authentication key_epoch | 1 | Duplicate inside authentication against populated journal |
| Boolean in previously unparametrized integer fields | 6 | controller/machine epochs,fence,version,protocol,budget;exact integer_invalid |
| Wrong destination or source base with existing request | 2 | Re-signed synthetic frame still refuses before verifier/DB access |
| Bad signature or verifier exception on existing request | 2 | Replay still invokes verifier once;fixed signature_invalid,no DB open |
| MAX_BYTES exact and one-byte-over boundary | 1 | Valid whitespace-padded replay succeeds at limit;over-limit refuses before verifier/DB |

All refusal cases preserve row/sequence snapshot and original ACK. The size
boundary test additionally proves identical ACK and unchanged state at exact limit.
Synthetic HMAC/helper fixtures are reused from the pinned existing test module.
No network,extra process,new package,production verifier or B result is supplied.

Attempt1:collection import failure preserved;corrected package-qualified fixture
import only. Attempt2:102passed (88existing+14new),zero errors/failures/skips,
pytest28.19s,outer30.078s. Two of three allowed invocations used;no silent rerun.
