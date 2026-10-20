"""Reject attacks against an already admitted request, before reading its receipt."""
import json
import sqlite3

import pytest

from tests.scripts.test_offline_inbox import (
    BODY, MAX_BYTES, InboxRefused, canonical, frame, inbox, journal, state, verify,
)


@pytest.mark.parametrize("attack,error,verifier_calls", [
    ("truncated_json", "json_invalid", 0),
    ("escaped_duplicate_body", "duplicate_key", 0),
    ("duplicate_authentication_epoch", "duplicate_key", 0),
    *[(field, "integer_invalid", 0) for field in (
        "controller_epoch", "machine_epoch", "fence", "expected_version",
        "protocol_version", "execution_budget_ms",
    )],
    ("wrong_destination", "binding_mismatch", 0),
    ("wrong_base", "binding_mismatch", 0),
    ("invalid_signature", "signature_invalid", 1),
    ("verifier_exception", "signature_invalid", 1),
])
def test_existing_receipt_cannot_bypass_validation(
        journal, monkeypatch, attack, error, verifier_calls):
    receiver, path = journal
    original_ack = receiver.receive(frame())
    before = state(path)
    calls = []

    def checked_verifier(signature, signed):
        calls.append((signature, signed))
        if attack == "verifier_exception":
            raise ValueError("synthetic-private-verifier-detail")
        return verify(signature, signed)

    raw = frame()
    if attack == "truncated_json":
        raw = raw[:-1]
    elif attack == "escaped_duplicate_body":
        raw = raw[:-1] + b',"\\u0062ody":{}}'
    elif attack == "duplicate_authentication_epoch":
        raw = raw.replace(b'"key_epoch":1', b'"key_epoch":1,"key_epoch":1', 1)
    elif attack in BODY:
        raw = frame(**{attack: True})
    elif attack == "wrong_destination":
        raw = frame(machine_id="executor-C")
    elif attack == "wrong_base":
        raw = frame(base_sha="d" * 40)
    elif attack == "invalid_signature":
        envelope = json.loads(raw)
        envelope["authentication"]["signature"] = "0" * 128
        raw = canonical(envelope)

    guarded_receiver = inbox(path, verify_signature=checked_verifier)
    with monkeypatch.context() as patch:
        def forbidden_connect(*args, **kwargs):
            pytest.fail("invalid replay accessed the existing journal")
        patch.setattr(sqlite3, "connect", forbidden_connect)
        with pytest.raises(InboxRefused, match="^" + error + "$"):
            guarded_receiver.receive(raw)

    assert len(calls) == verifier_calls
    assert state(path) == before
    assert receiver.receive(frame()) == original_ack


def test_exact_frame_limit_replays_but_one_more_byte_refuses_before_verifier(
        journal, monkeypatch):
    receiver, path = journal
    ack = receiver.receive(frame())
    before = state(path)
    raw = frame()
    padded = raw + b" " * (MAX_BYTES - len(raw))
    assert len(padded) == MAX_BYTES
    assert receiver.receive(padded) == ack
    assert state(path) == before

    def forbidden(*args, **kwargs):
        pytest.fail("oversized replay reached verifier or database")

    guarded_receiver = inbox(path, verify_signature=forbidden)
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", forbidden)
        with pytest.raises(InboxRefused, match="^frame_invalid$"):
            guarded_receiver.receive(padded + b" ")
    assert state(path) == before
