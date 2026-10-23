"""Real SQLite transactions and hidden passive competing processes for Phase1b."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coordination_runtime.state_controller import StateController, StateError


def claim(**changes):
    return dict(op="claim", project_id="project", task_id="task", run_id="run1",
                owner="worker1", request_id="claim1", expected_version=0,
                base_sha="a" * 40, contract_sha256="b" * 64, lease_seconds=10) | changes


def action(op, snapshot, **changes):
    run = snapshot["run"]
    value = dict(op=op, project_id=snapshot["project_id"], task_id=snapshot["task_id"],
                 run_id=run["run_id"], fence=run["fence"], expected_version=snapshot["version"],
                 request_id=f"{op}{snapshot['version']}")
    value.update(dict(actor="controller", reason="operator") if op == "revoke" else dict(owner=run["owner"]))
    return value | changes


@pytest.fixture
def state(tmp_path):
    clock = [10000]
    controller = StateController(tmp_path / "state.db", _clock=lambda: clock[0])
    controller.initialize()
    return controller, clock


def test_construction_and_missing_query_never_create_state(tmp_path):
    path = tmp_path / "absent" / "state.db"
    controller = StateController(path)
    with pytest.raises(StateError): controller.get("project", "task")
    assert not path.parent.exists()


def test_schema_init_idempotence_and_foreign_future_refusal(tmp_path):
    db = StateController(tmp_path / "state.db")
    assert db.initialize() == db.initialize() == {"schema_version": 4}
    with sqlite3.connect(db.path) as c: c.execute("PRAGMA user_version=5")
    old = db.path.read_bytes()
    with pytest.raises(StateError, match="Unsupported"): db.initialize()
    assert db.path.read_bytes() == old
    foreign = tmp_path / "foreign.db"
    with sqlite3.connect(foreign) as c: c.execute("CREATE TABLE business(value)")
    old = foreign.read_bytes()
    with pytest.raises(StateError, match="Unsupported"): StateController(foreign).initialize()
    assert foreign.read_bytes() == old


@pytest.mark.parametrize("kind", ["table", "view"])
def test_foreign_sqlite_prefix_is_not_a_reserved_name(tmp_path, kind):
    path = tmp_path / "foreign.db"
    sql = ("CREATE TABLE sqliteXdata(value)" if kind == "table"
           else "CREATE VIEW sqliteXdata AS SELECT 1 AS value")
    with sqlite3.connect(path) as connection: connection.execute(sql)
    before = path.read_bytes()
    with pytest.raises(StateError, match="Unsupported"):
        StateController(path).initialize()
    assert path.read_bytes() == before


def test_foreign_sqlite_prefix_in_runtime_schema_refuses_every_write(state):
    db, _ = state
    with sqlite3.connect(db.path) as connection:
        connection.execute("CREATE TABLE sqliteXdata(value)")
    before = db.path.read_bytes()
    for operation in (db.initialize, lambda: db.get("project", "task"),
                      lambda: db.apply(claim())):
        with pytest.raises(StateError, match="Unsupported"): operation()
        assert db.path.read_bytes() == before


def test_claim_replay_conflict_and_project_isolation(state):
    db, clock = state
    result = db.apply(claim())
    assert result["recorded"]["fence"] == result["recorded"]["version"] == 1
    clock[0] += 500
    assert db.apply(claim()) == result | {"replayed": True}
    assert len(db.events("project")) == 1
    with pytest.raises(StateError, match="Idempotency"): db.apply(claim(lease_seconds=20))
    assert db.apply(claim(project_id="other"))["recorded"]["fence"] == 1
    assert len(db.events("project")) == len(db.events("other")) == 1


def test_expiry_requires_revocation_and_fences_late_reports(state):
    db, clock = state
    old = db.apply(claim())["recorded"]
    clock[0] = 20000
    assert not db.get("project", "task")["lease_valid"]
    with pytest.raises(StateError): db.apply(action("renew", old, lease_seconds=10))
    with pytest.raises(StateError, match="revocation"):
        db.apply(claim(run_id="run2", request_id="claim2", expected_version=1))
    revoked = db.apply(action("revoke", old, reason="expired"))["recorded"]
    new = db.apply(claim(run_id="run2", owner="worker2", request_id="claim2", expected_version=revoked["version"]))["recorded"]
    assert new["fence"] > revoked["fence"] > old["fence"]
    with pytest.raises(StateError, match="stale"):
        db.apply(action("transition", old, request_id="late", expected_version=new["version"], phase="launching"))
    assert db.apply(claim())["replayed"] is True  # Historical receipt grants no lease.
    assert db.get("project", "task")["run"]["owner"] == "worker2"
    assert len(db.history("project", "task")) == 2


def test_version_owner_token_and_reused_run_refuse(state):
    db, _ = state
    old = db.apply(claim())["recorded"]
    for extra in ({"owner": "other"}, {"fence": 99}, {"run_id": "wrong"}, {"expected_version": 0}):
        with pytest.raises(StateError): db.apply(action("renew", old, lease_seconds=10, **extra))
    db.apply(action("revoke", old))
    with pytest.raises(StateError, match="reused"):
        db.apply(claim(task_id="other-task", request_id="reuse"))
    assert db.get("project", "other-task")["version"] == 0


def test_renew_does_not_shorten_and_terminal_requires_retirement(state):
    db, clock = state
    s = db.apply(claim())["recorded"]
    clock[0] += 500
    s = db.apply(action("renew", s, lease_seconds=1))["recorded"]
    assert s["run"]["lease_until_ms"] == 20000
    with pytest.raises(StateError, match="transition"):
        db.apply(action("transition", s, phase="completed"))
    for phase in ("launching", "running", "submitted", "verifying", "completed"):
        s = db.apply(action("transition", s, phase=phase))["recorded"]
    assert not db.get("project", "task")["lease_valid"]
    with pytest.raises(StateError, match="Terminal"): db.apply(action("renew", s, lease_seconds=10))
    with pytest.raises(StateError): db.apply(claim(run_id="run2", request_id="claim2", expected_version=s["version"]))
    db.apply(action("revoke", s, reason="completed"))
    assert db.history("project", "task")[0]["phase"] == "completed"
    assert db.events("project")[-1]["event_type"] == "revoke.completed"


def test_reopen_clock_rollback_and_historical_replay(state):
    db, clock = state
    s = db.apply(claim())["recorded"]
    reopened = StateController(db.path, _clock=lambda: 9999)
    assert not reopened.get("project", "task")["lease_valid"]
    with pytest.raises(StateError, match="Clock"): reopened.apply(action("renew", s, lease_seconds=10))
    assert reopened.apply(claim())["replayed"] is True


def test_audit_failure_rolls_back_run_request_and_version(state):
    db, _ = state
    with sqlite3.connect(db.path) as c:
        c.execute("CREATE TRIGGER audit_fault BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'fault'); END")
    with pytest.raises(StateError): db.apply(claim())
    assert db.get("project", "task")["version"] == 0
    assert not db.history("project", "task") and not db.events("project")
    with sqlite3.connect(db.path) as c: c.execute("DROP TRIGGER audit_fault")
    assert db.apply(claim())["replayed"] is False


def test_consistent_backup_and_no_overwrite(state, tmp_path):
    db, _ = state
    db.apply(claim())
    target = tmp_path / "backup.db"
    assert db.backup(target)["backup_verified"]
    copy = StateController(target, _clock=lambda: 10000)
    assert copy.get("project", "task") == db.get("project", "task")
    assert copy.events("project") == db.events("project")
    with pytest.raises(FileExistsError): db.backup(target)
    with pytest.raises(StateError): db.backup(db.path)


@pytest.mark.parametrize("change", [{"owner": "private/path"}, {"lease_seconds": True},
                                    {"expected_version": -1}, {"base_sha": "x"*40},
                                    {"contract_sha256": []}, {"extra": "private-marker"}])
def test_invalid_commands_never_change_state(state, change):
    db, _ = state
    with pytest.raises(StateError) as error: db.apply(claim(**change))
    assert "private-marker" not in str(error.value)
    assert db.get("project", "task")["version"] == 0


def test_bounded_read_pagination(state):
    db, _ = state
    s = db.apply(claim())["recorded"]
    db.apply(action("renew", s, lease_seconds=10))
    first = db.events("project", limit=1)
    second = db.events("project", after_sequence=first[0]["sequence"], limit=1)
    assert first[0]["sequence"] < second[0]["sequence"]
    assert not db.events("other")
    with pytest.raises(StateError): db.events("project", limit=101)


def start(stack, code, *args):
    command = [sys.executable, "-c", f"import sys;sys.path.insert(0,{str(ROOT)!r})\n" + code, *map(str,args)]
    if os.name == "nt":
        sys.path.insert(0, str(ROOT / "scripts"))
        from worker_process_guard import JobProcess
        p = JobProcess(command, cwd=ROOT)
        def cleanup():
            try: p.stop()
            finally: p.close()
        stack.callback(cleanup); p.resume()
    else:
        p = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def cleanup():
            if p.poll() is None: p.kill()
            p.wait(timeout=3)
        stack.callback(cleanup)
    return p


def wait_for(predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        assert time.monotonic() < deadline
        time.sleep(.01)


def test_native_competing_claims_have_one_valid_owner(tmp_path):
    db = StateController(tmp_path / "state.db"); db.initialize()
    body = """
from pathlib import Path
import json,time
from coordination_runtime.state_controller import StateController,StateError
root=Path(sys.argv[1]);n=sys.argv[2]; command=json.loads(sys.argv[3])
command.update(run_id='run'+n,owner='worker'+n,request_id='claim'+n)
(root/('ready'+n)).touch()
deadline=time.monotonic()+10
while not (root/'go').exists():
 if time.monotonic()>deadline: raise SystemExit(2)
 time.sleep(.01)
try: StateController(root/'state.db').apply(command); won=True
except StateError: won=False
(root/('result'+n)).write_text(json.dumps(won))
"""
    with ExitStack() as stack:
        ps = [start(stack, body, tmp_path, n, json.dumps(claim())) for n in range(6)]
        wait_for(lambda: len(list(tmp_path.glob("ready*"))) == 6); (tmp_path/"go").touch()
        assert [p.wait(timeout=10) for p in ps] == [0]*6
    assert sum(json.loads(p.read_text()) for p in tmp_path.glob("result*")) == 1
    assert db.get("project", "task")["lease_valid"]
    assert len(db.history("project", "task")) == len(db.events("project")) == 1


def test_native_first_init_race(tmp_path):
    path = tmp_path / "state.db"
    code = "from coordination_runtime.state_controller import StateController\nStateController(sys.argv[1]).initialize()"
    with ExitStack() as stack:
        ps = [start(stack, code, path) for _ in range(4)]
        assert [p.wait(timeout=10) for p in ps] == [0]*4
    assert StateController(path).get("project", "task")["version"] == 0


@pytest.mark.parametrize("committed", [False, True])
def test_native_crash_before_or_after_commit_is_recoverable(tmp_path, committed):
    db = StateController(tmp_path/"state.db"); db.initialize()
    body = """
from pathlib import Path
import json,time
from coordination_runtime.state_controller import StateController
root=Path(sys.argv[1]); db=StateController(root/'state.db'); command=json.loads(sys.argv[2])
if sys.argv[3]=='True':
 db.apply(command); (root/'held').touch(); time.sleep(30)
else:
 with db._db(write=True) as c:
  c.execute("INSERT INTO runtime_tasks VALUES('project','task',99,99,NULL)")
  (root/'held').touch(); time.sleep(30)
"""
    with ExitStack() as stack:
        p = start(stack, body, tmp_path, json.dumps(claim()), committed)
        wait_for(lambda: (tmp_path/"held").exists())
        if os.name == "nt": p.stop()
        else: p.kill(); p.wait(timeout=3)
    reply = db.apply(claim())
    assert reply["replayed"] is committed
    assert reply["recorded"]["version"] == 1
    assert len(db.events("project")) == 1


def test_cli_explicit_init_apply_get_and_safe_refusal(tmp_path, capsys):
    from coordination_runtime.state_controller import main
    path = tmp_path/"cli.db"; command = tmp_path/"command.json"
    command.write_text(json.dumps(claim()))
    assert main(["--db",str(path),"init"]) == 0
    assert main(["--db",str(path),"apply","--command-file",str(command)]) == 0
    assert main(["--db",str(path),"get","--project-id","project","--task-id","task"]) == 0
    command.write_text('{"private-marker":true}')
    assert main(["--db",str(path),"apply","--command-file",str(command)]) == 1
    assert "private-marker" not in capsys.readouterr().out
