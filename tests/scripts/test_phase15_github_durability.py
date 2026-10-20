"""Additional local journal observations; synthetic fixtures, no child processes."""
import sqlite3
import time

import pytest

from test_offline_inbox import BODY, frame, inbox, state
from coordination_runtime.offline_inbox import InboxRefused


def test_reinitialize_populated_journal_preserves_multiple_receipts(tmp_path):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    first = receiver.receive(frame())
    second_body = BODY | dict(request_id="request-2", message_id="message-2",
                              run_id="run-2", task_id="task-2", sequence=2)
    second = inbox(path, second_body).receive(frame(second_body))
    before = state(path)
    del receiver
    for body, expected in [(BODY, first), (second_body, second)]:
        reopened = inbox(path, body)
        reopened.initialize()
        ack = reopened.receive(frame(body))
        assert ack == expected
        ack["phase"] = "client-mutated"
        assert reopened.receive(frame(body)) == expected
    assert state(path) == before
    assert len(before[1]) == 2 and before[0][0][2] == 2


def test_reopened_request_conflict_does_not_reserve_future_sequence(tmp_path):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    original = receiver.receive(frame())
    del receiver
    before = state(path)
    with pytest.raises(InboxRefused, match="^request_conflict$"):
        inbox(path).receive(frame(sequence=50))
    assert state(path) == before
    next_body = BODY | dict(request_id="request-2", message_id="message-2",
                            task_id="task-2", run_id="run-2", sequence=2)
    inbox(path, next_body).receive(frame(next_body))
    assert inbox(path).receive(frame()) == original
    assert state(path)[0][0][2] == 2 and len(state(path)[1]) == 2


def test_maximum_sequence_survives_reinitialization_without_wraparound(tmp_path):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    first = receiver.receive(frame())
    last_body = BODY | dict(request_id="request-max", message_id="message-max",
                            task_id="task-max", run_id="run-max", sequence=2**63 - 1)
    last = inbox(path, last_body).receive(frame(last_body))
    del receiver
    inbox(path).initialize()
    before = state(path)
    for sequence in [2, 2**63 - 2, 2**63 - 1]:
        unseen = BODY | dict(request_id="unseen", message_id="unseen",
                             task_id="unseen", run_id="unseen", sequence=sequence)
        with pytest.raises(InboxRefused, match="^sequence_stale$"):
            inbox(path, unseen).receive(frame(unseen))
        assert state(path) == before
    assert inbox(path).receive(frame()) == first
    assert inbox(path, last_body).receive(frame(last_body)) == last
    assert before[0][0][2] == 2**63 - 1 and len(before[1]) == 2


def test_real_write_lock_refuses_within_budget_then_recovers(tmp_path):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    before = state(path)
    locker = sqlite3.connect(path, isolation_level=None)
    try:
        locker.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        with pytest.raises(InboxRefused, match="^journal_unavailable$"):
            receiver.receive(frame())
        elapsed = time.monotonic() - started
        assert 4 <= elapsed < 15
        assert state(path) == before
    finally:
        locker.rollback()
        locker.close()
    ack = inbox(path).receive(frame())
    assert inbox(path).receive(frame()) == ack
    assert len(state(path)[1]) == 1 and state(path)[0][0][2] == 1


def test_receipt_insert_abort_preserves_existing_ack_and_retry(tmp_path):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    first = receiver.receive(frame())
    second_body = BODY | dict(request_id="request-2", message_id="message-2",
                              task_id="task-2", run_id="run-2", sequence=2)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON receipts "
                   "BEGIN SELECT RAISE(ABORT,'synthetic-insert-fault'); END")
    before = state(path)
    with pytest.raises(InboxRefused, match="^journal_unavailable$"):
        inbox(path, second_body).receive(frame(second_body))
    assert state(path) == before
    assert inbox(path).receive(frame()) == first
    with sqlite3.connect(path) as db:
        db.execute("DROP TRIGGER fail_receipt")
    ack = inbox(path, second_body).receive(frame(second_body))
    assert inbox(path, second_body).receive(frame(second_body)) == ack
    assert len(state(path)[1]) == 2 and state(path)[0][0][2] == 2


def test_commit_exception_rolls_back_both_writes_before_successful_retry(tmp_path, monkeypatch):
    path = tmp_path / "journal.db"
    receiver = inbox(path)
    receiver.initialize()
    before = state(path)
    connect = sqlite3.connect
    observed = []

    class RefuseCommit(sqlite3.Connection):
        def commit(self):
            observed.append((self.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
                             self.execute("SELECT sequence FROM metadata").fetchone()[0]))
            raise sqlite3.OperationalError("synthetic-commit-fault")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **kw: connect(
            *a, **(kw | dict(factory=RefuseCommit))))
        with pytest.raises(InboxRefused, match="^journal_unavailable$"):
            receiver.receive(frame())
    assert observed == [(1, 1)]
    assert state(path) == before
    ack = inbox(path).receive(frame())
    assert inbox(path).receive(frame()) == ack
    assert len(state(path)[1]) == 1 and state(path)[0][0][2] == 1
