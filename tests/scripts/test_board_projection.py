"""Real SQLite/filesystem intent, migration, conflict and passive native crash checks."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/scripts"))
from coordination_runtime import state_controller as state_module
from coordination_runtime.state_controller import StateController, StateError
from coordination_runtime.board_projection import BoardProjector, _sha, _intent_id
from test_state_controller import claim, action, start, wait_for

CARD = b"---\ntask_id: task\nstatus: READY\nowner: worker1\nexpected_artifacts: []\n---\n# Task\n\nKeep body unchanged.\n"
NAME = "2026-10-16_task_example.md"


@pytest.fixture
def board(tmp_path):
    root = tmp_path / "repo"
    for state in ("ready", "in_progress", "review", "blocked", "done", "cancelled"):
        (root / "coordination/task-board" / state).mkdir(parents=True)
    (root / "coordination/delivery").mkdir()
    source = root / "coordination/task-board/ready" / NAME
    source.write_bytes(CARD)
    clock = [10000]
    db = StateController(tmp_path / "state.db", _clock=lambda: clock[0]); db.initialize()
    return BoardProjector(db, root, "project"), db, clock, source


def prepare(board):
    projector, db, clock, source = board
    return projector.prepare(claim(), NAME, _sha(CARD))


def target(board, state="in_progress"):
    return board[0].root / "coordination/task-board" / state / NAME


def v1(db):
    result = db.apply(claim())
    with sqlite3.connect(db.path) as c:
        c.execute("DROP TABLE publication_queue");c.execute("DROP TABLE evidence_candidates");c.execute("DROP TABLE parallel_runs"); c.execute("DROP TABLE parallel_projects")
        c.execute("DROP TABLE board_intents"); c.execute("DROP TABLE project_bindings")
        c.execute("PRAGMA user_version=1")
    return result


def test_schema1_upgrade_is_explicit_backed_up_and_preserves_receipts(board, tmp_path):
    projector, db, _, _ = board
    result = v1(db); before = db.path.read_bytes()
    assert db.migrate() == {"schema_version": 1, "target_version": 4, "would_migrate": True}
    assert db.path.read_bytes() == before
    with pytest.raises(StateError): db.get("project", "task")
    with pytest.raises(StateError): db.migrate(execute=True)
    assert db.path.read_bytes() == before
    backup = tmp_path / "v1.db"
    assert db.migrate(backup, execute=True) == {"schema_version": 4, "migrated": True}
    assert db.apply(claim()) == result | {"replayed": True}
    assert db.get("project", "task")["fence"] == 1
    with sqlite3.connect(backup) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 1
    assert db.migrate(backup, execute=True)["migrated"] is False


def test_migration_failure_keeps_v1_and_backup(board, tmp_path, monkeypatch):
    _, db, _, _ = board
    v1(db)
    backup = tmp_path / "v1.db"
    monkeypatch.setattr(state_module, "INTENT_SCHEMA", state_module.INTENT_SCHEMA + "INVALID DDL;")
    with pytest.raises(StateError): db.migrate(backup, execute=True)
    assert backup.exists()
    with sqlite3.connect(db.path) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM runtime_tasks").fetchone()[0] == 1
        assert not c.execute("SELECT name FROM sqlite_master WHERE name='board_intents'").fetchall()
    with pytest.raises(FileExistsError): db.migrate(backup, execute=True)


def test_missing_store_and_readonly_queries_create_nothing(tmp_path):
    db = StateController(tmp_path / "missing" / "state.db")
    projector = BoardProjector(db, tmp_path / "repo", "project")
    with pytest.raises(StateError): db.migrate()
    with pytest.raises(StateError): projector.reconcile("request")
    with pytest.raises(StateError): db.intents("project")
    assert not list(tmp_path.iterdir())


def test_prepare_atomic_receipt_and_dryrun_then_exact_projection(board):
    projector, db, _, source = board
    result = prepare(board)
    assert result["recorded"]["version"] == 1 and source.read_bytes() == CARD
    assert db.intent("project", "claim1")["status"] == "pending"
    before = db.path.read_bytes()
    assert projector.reconcile("claim1")["would_status"] == "applied"
    assert db.path.read_bytes() == before and not target(board).exists()
    assert projector.reconcile("claim1", execute=True)["status"] == "applied"
    expected = CARD.replace(b"status: READY", b"status: IN_PROGRESS")
    expected += ("\n<!-- coordination-intent: " + _intent_id("project", "claim1") + " -->\n").encode()
    assert target(board).read_bytes() == expected and not source.exists()
    assert prepare(board)["replayed"] is True
    assert projector.reconcile("claim1", execute=True) == {"status": "applied", "historical": True}
    assert [e["event_type"] for e in db.events("project")] == ["claim", "intent.pending", "intent.applied"]
    with pytest.raises(StateError): projector.prepare(claim(lease_seconds=30), NAME, _sha(CARD))
    with pytest.raises(StateError): projector.prepare(claim(), NAME, "0" * 64)


def test_intent_insert_fault_rolls_back_all_runtime_state(board):
    _, db, _, source = board
    with sqlite3.connect(db.path) as c:
        c.execute("CREATE TRIGGER intent_fault BEFORE INSERT ON board_intents BEGIN SELECT RAISE(ABORT,'fault'); END")
    with pytest.raises(StateError): prepare(board)
    assert db.get("project", "task")["version"] == 0 and not db.events("project")
    assert not db.intents("project") and source.read_bytes() == CARD
    with sqlite3.connect(db.path) as c: c.execute("DROP TRIGGER intent_fault")
    assert prepare(board)["replayed"] is False


@pytest.mark.parametrize("field", ["source", "destination", "duplicate", "missing"])
def test_unknown_board_state_preserves_work_and_requires_recovery(board, field):
    projector, db, _, source = board
    prepare(board)
    if field == "source": source.write_bytes(CARD + b"new work")
    if field == "destination": target(board).write_bytes(b"other private work")
    if field == "duplicate":
        (source.parent / "duplicate.md").write_bytes(CARD)
    if field == "missing": source.unlink()
    snapshot = {p: p.read_bytes() for p in projector.root.rglob("*.md")}
    assert projector.reconcile("claim1")["would_status"] == "recovery_required"
    assert projector.reconcile("claim1", execute=True)["status"] == "recovery_required"
    assert projector.cancel("claim1", execute=True)["status"] == "recovery_required"
    assert snapshot == {p: p.read_bytes() for p in projector.root.rglob("*.md")}
    current = db.get("project", "task")
    with pytest.raises(StateError, match="Unresolved"):
        db.apply(action("transition", current, phase="launching"))


def test_pending_renew_then_expired_revoke_and_explicit_cancel(board):
    projector, db, clock, source = board
    s = prepare(board)["recorded"]
    s = db.apply(action("renew", s, lease_seconds=10))["recorded"]
    clock[0] = 20000
    assert projector.reconcile("claim1", execute=True)["status"] == "recovery_required"
    revoked = db.apply(action("revoke", s, reason="expired"))["recorded"]
    with pytest.raises(StateError, match="Unresolved"):
        db.apply(claim(run_id="run2", request_id="claim2", expected_version=revoked["version"]))
    assert projector.cancel("claim1")["would_status"] == "cancelled"
    assert projector.cancel("claim1", execute=True)["status"] == "cancelled"
    new = db.apply(claim(run_id="run2", request_id="claim2", expected_version=revoked["version"]))["recorded"]
    assert new["fence"] > revoked["fence"] > s["fence"] and source.read_bytes() == CARD


@pytest.mark.parametrize("stage", ["after_target", "after_source"])
def test_interruption_reconcile_or_compensation_preserves_runtime_history(board, stage):
    projector, db, clock, source = board
    prepare(board)
    def fail(current):
        if current == stage: raise RuntimeError("interrupted")
    projector._checkpoint = fail
    with pytest.raises(RuntimeError): projector.reconcile("claim1", execute=True)
    assert db.intent("project", "claim1")["status"] == "pending"
    projector._checkpoint = lambda _: None
    clock[0] = 20000
    if stage == "after_target":
        assert projector.reconcile("claim1", execute=True)["status"] == "recovery_required"
        assert projector.cancel("claim1", execute=True)["status"] == "cancelled"
        assert source.read_bytes() == CARD and not target(board).exists()
    else:
        assert projector.reconcile("claim1", execute=True)["status"] == "applied"
        assert not source.exists() and target(board).is_file()
    assert db.get("project", "task")["version"] == 1


def test_expiry_during_projection_preserves_source_and_cannot_delete_it(board):
    projector, db, clock, source = board
    prepare(board)
    projector._checkpoint = lambda stage: clock.__setitem__(0, 20000) if stage == "after_target" else None
    assert projector.reconcile("claim1", execute=True)["status"] == "recovery_required"
    assert source.read_bytes() == CARD and target(board).exists()
    assert projector.cancel("claim1", execute=True)["status"] == "cancelled"


def test_link_failure_never_overwrites_or_loses_original(board, monkeypatch):
    projector, db, _, source = board
    prepare(board)
    def denied(*a): raise PermissionError("private-marker")
    monkeypatch.setattr(os, "link", denied)
    assert projector.reconcile("claim1", execute=True)["status"] == "recovery_required"
    assert source.read_bytes() == CARD and not target(board).exists()
    assert projector.cancel("claim1", execute=True)["status"] == "cancelled"


def test_submit_projection_requires_report_and_never_accepts_done(board):
    projector, db, _, source = board
    source.write_bytes(CARD.replace(b"expected_artifacts: []", b"expected_artifacts:\n  - delivery_report"))
    projector.prepare(claim(), NAME, _sha(source.read_bytes()))
    projector.reconcile("claim1", execute=True)
    s = db.get("project", "task")
    for phase in ("launching", "running"): s = db.apply(action("transition", s, phase=phase))["recorded"]
    command = action("transition", s, phase="submitted")
    digest = _sha(target(board).read_bytes())
    with pytest.raises(StateError, match="report"): projector.prepare(command, NAME, digest)
    report = projector.root / "coordination/delivery/task-delivery-report.md"; report.write_bytes(b"# Delivery report\n")
    projector.prepare(command, NAME, digest)
    report.unlink()
    assert projector.reconcile(command["request_id"], execute=True)["status"] == "recovery_required"
    assert target(board).exists() and not target(board, "review").exists()
    report.write_bytes(b"# Delivery report\n")
    assert projector.reconcile(command["request_id"], execute=True)["status"] == "applied"
    assert target(board, "review").exists() and not target(board, "done").exists()
    s = db.get("project", "task")
    with pytest.raises(StateError): projector.prepare(action("transition", s, phase="verifying"), NAME, digest)


@pytest.mark.parametrize("filename", ["../escape.md", "a/b.md", "C:/bad.md", "README.md", ".hidden.md"])
def test_bad_filename_refuses_without_mutation(board, filename):
    projector, db, _, source = board
    with pytest.raises(StateError): projector.prepare(claim(), filename, _sha(CARD))
    assert db.get("project", "task")["version"] == 0 and source.read_bytes() == CARD


def test_bound_root_project_owner_clock_and_bounded_queries(board, tmp_path):
    projector, db, clock, source = board
    with pytest.raises(StateError): projector.prepare(claim(owner="wrong"), NAME, _sha(CARD))
    with pytest.raises(StateError): projector.prepare(claim(project_id="wrong"), NAME, _sha(CARD))
    prepare(board)
    wrong = BoardProjector(db, tmp_path / "other", "project")
    with pytest.raises(StateError): wrong.reconcile("claim1", execute=True)
    with pytest.raises(StateError): wrong.prepare(claim(), NAME, _sha(CARD))
    clock[0] -= 1
    with pytest.raises(StateError): projector.reconcile("claim1", execute=True)
    assert db.intent("project", "claim1")["status"] == "pending"
    assert len(db.intents("project", limit=1)) == 1
    with pytest.raises(StateError): db.intents("project", limit=101)
    assert not db.intents("other")


@pytest.mark.parametrize("stage", ["after_prepare", "after_target", "after_source"])
def test_native_crash_reconciles_durable_filesystem_stage_once(board, tmp_path, stage):
    projector, db, _, source = board
    body = """
from pathlib import Path
import json,time
from coordination_runtime.state_controller import StateController
from coordination_runtime.board_projection import BoardProjector
root=Path(sys.argv[1]); path=Path(sys.argv[2]); signal=Path(sys.argv[3]); stage=sys.argv[4]
def checkpoint(current):
 if current==stage: signal.touch(); time.sleep(30)
p=BoardProjector(StateController(path,_clock=lambda:10000),root,'project',_checkpoint=checkpoint)
p.prepare(json.loads(sys.argv[5]),sys.argv[6],sys.argv[7])
p.reconcile('claim1',execute=True)
"""
    signal = tmp_path / "held"
    with ExitStack() as stack:
        p = start(stack, body, projector.root, db.path, signal, stage, json.dumps(claim()), NAME, _sha(CARD))
        wait_for(signal.exists)
        if os.name == "nt": p.stop()
        else: p.kill(); p.wait(timeout=3)
    assert db.intent("project", "claim1")["status"] == "pending"
    assert projector.reconcile("claim1", execute=True)["status"] == "applied"
    assert projector.reconcile("claim1", execute=True)["historical"]
    assert not source.exists() and target(board).is_file()
    assert len(db.events("project")) == 3


def test_native_competing_prepares_and_reconcilers_have_single_receipt(board, tmp_path):
    projector, db, _, source = board
    body = """
from pathlib import Path
import json,time
from coordination_runtime.state_controller import StateController,StateError
from coordination_runtime.board_projection import BoardProjector
p=BoardProjector(StateController(sys.argv[1],_clock=lambda:10000),sys.argv[2],'project')
root=Path(sys.argv[3]); n=sys.argv[4]; mode=sys.argv[5]
(root/('ready'+n)).touch()
deadline=time.monotonic()+10
while not (root/'go').exists():
 if time.monotonic()>deadline: raise SystemExit(2)
 time.sleep(.01)
try:
 if mode=='prepare': p.prepare(json.loads(sys.argv[6]),sys.argv[7],sys.argv[8]); value=True
 else: value=p.reconcile(sys.argv[6],execute=True)['status']=='applied'
except StateError: value=False
(root/('result'+n)).write_text(json.dumps(value))
"""
    for mode in ("prepare", "reconcile"):
        signals = tmp_path / mode; signals.mkdir()
        with ExitStack() as stack:
            ps = []
            for n in range(4):
                command = claim(run_id="run"+str(n), request_id="claim"+str(n))
                value = json.dumps(command) if mode == "prepare" else db.intents("project")[0]["request_id"]
                ps.append(start(stack, body, db.path, projector.root, signals, n, mode, value, NAME, _sha(CARD)))
            wait_for(lambda: len(list(signals.glob("ready*"))) == 4); (signals/"go").touch()
            assert [p.wait(timeout=10) for p in ps] == [0]*4
        wins = sum(json.loads(p.read_text()) for p in signals.glob("result*"))
        assert wins == (1 if mode == "prepare" else 4)
    assert db.get("project", "task")["fence"] == 1
    assert len(db.intents("project")) == 1 and len(db.events("project")) == 3


def test_cli_dryrun_and_private_error_output(board, tmp_path, capsys):
    from coordination_runtime.board_projection import main
    projector, db, _, source = board
    common = ["--db", str(db.path), "--repo", str(projector.root), "--project-id", "project"]
    command = tmp_path / "command.json"; command.write_text(json.dumps(claim()))
    assert main(common + ["prepare", "--command-file",str(command), "--filename",NAME,"--expected-sha256",_sha(CARD)]) == 0
    before = db.path.read_bytes()
    assert main(common + ["reconcile", "--request-id", "claim1"]) == 0
    assert db.path.read_bytes() == before and source.exists()
    command.write_text('{"private-marker":true}')
    assert main(common + ["prepare", "--command-file",str(command), "--filename",NAME,"--expected-sha256",_sha(CARD)]) == 1
    assert "private-marker" not in capsys.readouterr().out


def test_completed_receipt_never_reprojects_after_later_board_edits(board):
    projector, db, _, source = board
    prepare(board); projector.reconcile("claim1", execute=True)
    edited = target(board).read_bytes() + b"later review work"
    target(board).write_bytes(edited)
    assert projector.reconcile("claim1", execute=True)["historical"]
    assert prepare(board)["replayed"]
    assert target(board).read_bytes() == edited and not source.exists()


def test_exception_projection_is_blocked_not_accepted(board):
    projector, db, _, source = board
    prepare(board); projector.reconcile("claim1", execute=True)
    current = db.get("project", "task")
    command = action("transition", current, phase="failed")
    projector.prepare(command, NAME, _sha(target(board).read_bytes()))
    assert projector.reconcile(command["request_id"], execute=True)["status"] == "applied"
    assert target(board, "blocked").exists() and not target(board, "done").exists()
    assert db.get("project", "task")["run"]["phase"] == "failed"
