"""Real detached worktrees, transactional scheduling and finite native parallel mocks."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"scripts"));sys.path.insert(0,str(ROOT/"tests/scripts"))
from coordination_runtime.state_controller import StateController,StateError
from coordination_runtime.parallel_runtime import ParallelController
from coordination_runtime.workspace import read_small,META
from coordination_runtime.board_projection import BoardProjector,_sha
from test_state_controller import claim,start,wait_for
import coordination_common as common


def git(repo,*args):
    return subprocess.check_output(["git",*args],cwd=repo,stderr=subprocess.DEVNULL).decode().strip()


def card(task,scope=None,deps=None):
    scope=scope or ["src/"+task+".txt"]
    return ("---\ntask_id: "+task+"\nphase: phase2\nstatus: READY\nowner: worker\nreviewer: ORCHESTRATOR\npriority: high\ndependencies:"+
            ("\n"+"\n".join("  - "+d for d in deps) if deps else " []")+"\nallowed_scope:\n"+
            "\n".join("  - "+s for s in scope)+"\nforbidden_scope: []\nacceptance:\n  - Passive mock isolation\nexpected_artifacts:\n  - delivery_report\nexecution_mode: WORKTREE\n---\n# Task\n").encode()


@pytest.fixture
def system(tmp_path):
    repo=tmp_path/"repo";repo.mkdir()
    git(repo,"init","-q");git(repo,"config","user.name","Fixture");git(repo,"config","user.email","fixture@example.invalid")
    for state in ("ready","in_progress","review","blocked","done","cancelled"):(repo/"coordination/task-board"/state).mkdir(parents=True)
    (repo/"coordination/delivery").mkdir();(repo/"coordination/reviews").mkdir();(repo/"coordination/progress").mkdir()
    (repo/"src").mkdir();(repo/".gitignore").write_text("coordination/monitor/runtime/\n")
    for task in ("task-a","task-b","task-c"):
        (repo/"coordination/task-board/ready"/(task+".md")).write_bytes(card(task))
        (repo/"src"/(task+".txt")).write_text("base "+task)
    git(repo,"add",".");git(repo,"commit","-qm","fixture base")
    clock=[10000];db=StateController(tmp_path/"state.db",_clock=lambda:clock[0]);db.initialize()
    p=ParallelController(db,repo,tmp_path/"workspaces","project");p.enable(execute=True,quiesced=True)
    return p,db,clock


def request(p,task):
    return dict(project_id="project",task_id=task,run_id="run-"+task,owner="worker",request_id="claim-"+task,
                expected_version=0,base_sha=git(p.root,"rev-parse","HEAD"),lease_seconds=120)


def prepare(system,task="task-a",resources=None,execute=True):
    p,db,clock=system;source=p.root/"coordination/task-board/ready"/(task+".md")
    expected=_sha(source.read_bytes()) if source.exists() else db.intent("project","claim-"+task)["before_sha"]
    return p.prepare(request(p,task),source.name,expected,resources or [],"src/"+task+".txt",execute=execute)


def ready(system,task="task-a"):
    p,_,_=system;prepare(system,task)
    assert p.provision("run-"+task,execute=True)["status"]=="ready"
    assert p.project("run-"+task,execute=True)["status"]=="applied"


def test_mode_preview_guards_and_quiescent_disable(system,tmp_path,monkeypatch):
    p,db,clock=system
    source=p.root/"coordination/task-board/ready/task-a.md"
    before=source.read_bytes()
    for path in (source,p.root/"coordination/delivery/blocked.md",p.root/"coordination/reviews/blocked.md",p.root/"coordination/progress/blocked.md"):
        with pytest.raises(ValueError,match="controller"):common.write_text(path,"blocked")
    fields,body=common.load_task(source)
    with pytest.raises(ValueError):common.move_task(source,"in_progress",fields,body)
    import local_agent_loop as loop
    monkeypatch.setattr(loop,"ROOT",p.root)
    with pytest.raises(ValueError):loop.launch_worker("task-a","worker","payload",1)
    monkeypatch.setattr(loop,"load_plan",lambda path:{})
    with pytest.raises(ValueError):loop.run_loop(tmp_path/"unused",execute=True)
    import worker_poller,project_registry
    monkeypatch.setattr(project_registry,"get_project",lambda *a:SimpleNamespace(local_path=str(p.root)))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):worker_poller._build_activation_payload(dict(task_id="task-a",project_id="project"))
    assert source.read_bytes()==before
    assert p.disable()["dry_run"] and p.marker.exists()
    assert p.disable(execute=True)["mode"]=="disabled" and not p.marker.exists()
    common.write_text(source,before.decode())
    old=db.path.read_bytes()
    assert p.enable()["would_enable"] and not p.marker.exists() and db.path.read_bytes()==old
    with pytest.raises(StateError):p.enable(execute=True)
    assert not p.marker.exists()
    assert p.enable(1,execute=True,quiesced=True)["capacity"]==1


@pytest.mark.parametrize("marker",["enabled","corrupt","absent"])
def test_registered_project_activation_checks_real_root_before_inbox_ack(system,tmp_path,monkeypatch,capsys,marker):
    p,db,_=system
    import worker_poller,project_registry,event_routing
    central=tmp_path/"central";central.mkdir();monitor=central/"coordination/monitor"
    monkeypatch.chdir(central)
    monkeypatch.setattr(worker_poller,"MONITOR_DIR",monitor)
    monkeypatch.setattr(worker_poller,"WORKERS_FILE",monitor/"workers.json")
    monkeypatch.setattr(project_registry,"get_project",lambda *a:SimpleNamespace(local_path=str(p.root)))
    delivery=monitor/"delivery/delivery_state.jsonl"
    monkeypatch.setattr(event_routing,"MONITOR_DIR",monitor)
    monkeypatch.setattr(event_routing,"DELIVERY_DIR",delivery.parent)
    monkeypatch.setattr(event_routing,"DELIVERY_FILE",delivery)
    assert worker_poller.register_worker("worker","project")
    record=dict(project_id="project",task_id="task-a",owner="worker",payload_id="payload",
                event_type="ready_assigned",destination="registered_worker",status="pending")
    delivery.parent.mkdir();delivery.write_text(json.dumps(record)+"\n",encoding="utf-8")
    before=delivery.read_bytes();source=p.root/"coordination/task-board/ready/task-a.md";card_before=source.read_bytes()
    if marker=="corrupt":p.marker.write_bytes(b"unknown")
    if marker=="absent":p.disable(execute=True)
    result=worker_poller.activate_worker("worker",output_json=True)
    payload=json.loads(capsys.readouterr().out)
    if marker=="absent":
        assert result==0 and payload["activated"]
        assert payload["task_card_path"]=="coordination/task-board/ready/task-a.md"
        assert str(p.root) not in json.dumps(payload)
        assert (monitor/"inbox/worker/payload.json").is_file()
        assert json.loads(delivery.read_text(encoding="utf-8"))["status"]=="acknowledged"
    else:
        assert result==1 and payload["activated"] is False
        assert delivery.read_bytes()==before and not (monitor/"inbox").exists()
    assert source.read_bytes()==card_before


def test_corrupt_marker_blocks_helpers_and_other_database(system,tmp_path):
    p,db,_=system
    other=StateController(tmp_path/"other.db");other.initialize()
    source=p.root/"coordination/task-board/ready/task-a.md"
    with pytest.raises(StateError):
        BoardProjector(other,p.root,"project").prepare(claim(task_id="task-a",owner="worker"),source.name,_sha(source.read_bytes()))
    assert other.get("project","task-a")["version"]==0
    p.marker.write_bytes(b"unknown")
    with pytest.raises(ValueError):common.write_text(p.root/"coordination/task-board/ready/task-a.md","bad")
    with pytest.raises(StateError):prepare(system)
    other=StateController(tmp_path/"other.db");other.initialize()
    second=ParallelController(other,p.root,p.workspace.root,"project")
    with pytest.raises(StateError):second.enable(execute=True,quiesced=True)
    assert p.marker.read_bytes()==b"unknown"


def test_atomic_admission_and_unqualified_routes_refuse(system):
    p,db,_=system
    before=db.path.read_bytes()
    assert prepare(system,execute=False)["dry_run"] and db.path.read_bytes()==before
    result=prepare(system)
    assert result["recorded"]["fence"]==1
    with db._db() as c:
        row=dict(c.execute("SELECT * FROM parallel_runs").fetchone())
        assert row["status"]=="reserved" and row["fence"]==1
        assert c.execute("SELECT COUNT(*) FROM board_intents").fetchone()[0]==1
    assert prepare(system)["replayed"]
    with pytest.raises(StateError):prepare(system,resources=["changed"])
    with pytest.raises(StateError,match="controller"):db.apply(claim(task_id="other",run_id="other",request_id="other"))
    with pytest.raises(StateError):BoardProjector(db,p.root,"project").reconcile("claim-task-a",execute=True)
    with pytest.raises(StateError):p.disable(execute=True)


def test_reservation_insert_failure_rolls_back_everything(system):
    p,db,_=system
    with db._db(write=True) as c:
        c.execute("CREATE TRIGGER reservation_fault BEFORE INSERT ON parallel_runs BEGIN SELECT RAISE(ABORT,'fault'); END")
    with pytest.raises(StateError):prepare(system)
    assert db.get("project","task-a")["version"]==0
    with db._db() as c:
        assert not c.execute("SELECT 1 FROM parallel_runs").fetchall()
        assert not c.execute("SELECT 1 FROM board_intents").fetchall()
        assert not c.execute("SELECT 1 FROM requests").fetchall()


@pytest.mark.parametrize("conflict",["scope","resource","forbidden","dependency","cycle"])
def test_scheduling_refusals_preserve_ready_card(system,conflict):
    p,db,_=system
    a=p.root/"coordination/task-board/ready/task-a.md";b=p.root/"coordination/task-board/ready/task-b.md"
    prepare(system,resources=["database"])
    if conflict=="scope":b.write_bytes(card("task-b",scope=["src/**"]))
    if conflict=="forbidden":b.write_bytes(card("task-b").replace(b"forbidden_scope: []",b"forbidden_scope:\n  - src/**"))
    if conflict=="dependency":b.write_bytes(card("task-b",deps=["task-a"]))
    if conflict=="cycle":
        b.write_bytes(card("task-b",deps=["dep"]))
        (p.root/"coordination/task-board/done/dep.md").write_bytes(card("dep",deps=["task-b"]).replace(b"status: READY",b"status: DONE"))
    before=b.read_bytes()
    with pytest.raises(StateError):prepare(system,"task-b",["database"] if conflict=="resource" else [])
    assert b.read_bytes()==before and db.get("project","task-b")["version"]==0


def test_accepted_dependency_and_expired_capacity_are_conservative(system):
    p,db,clock=system
    dep=p.root/"coordination/task-board/done/dep.md";dep.write_bytes(card("dep").replace(b"status: READY",b"status: DONE"))
    (p.root/"coordination/reviews/review-dep.md").write_text("# Review Report\n\n- Task ID: dep\n- Decision: accepted\n")
    source=p.root/"coordination/task-board/ready/task-a.md";source.write_bytes(card("task-a",deps=["dep"]))
    prepare(system);prepare(system,"task-b")
    clock[0]+=120000
    with pytest.raises(StateError,match="capacity"):prepare(system,"task-c")
    assert p.cancel("run-task-a",execute=True)["status"]=="cancelled"
    assert p.retire("run-task-a",execute=True)["status"]=="released"
    assert prepare(system,"task-c")["recorded"]["fence"]==1


def test_git_workspaces_are_pinned_isolated_and_candidates_preserved(system):
    p,db,_=system
    ready(system);ready(system,"task-b")
    a=p.workspace.path("run-task-a");b=p.workspace.path("run-task-b")
    assert a!=b and git(a,"rev-parse","--abbrev-ref","HEAD")=="HEAD"
    assert git(a,"rev-parse","HEAD")==git(b,"rev-parse","HEAD")==git(p.root,"rev-parse","HEAD")
    (a/"src/task-a.txt").write_text("candidate")
    assert (b/"src/task-a.txt").read_text()=="base task-a"
    assert (p.root/"src/task-a.txt").read_text()=="base task-a"
    assert p.inspect("run-task-a")["changed"]==["src/task-a.txt"]
    assert p.retire("run-task-a",execute=True)["candidate_preserved"]
    assert (a/"src/task-a.txt").read_text()=="candidate"
    assert prepare(system,"task-a")["replayed"]


def test_unknown_workspace_is_not_adopted_or_deleted(system):
    p,db,_=system;prepare(system)
    path=p.workspace.path("run-task-a");path.mkdir(parents=True);(path/"sentinel").write_text("keep")
    assert p.provision("run-task-a",execute=True)["status"]=="recovery_required"
    assert (path/"sentinel").read_text()=="keep"
    with pytest.raises(StateError):p.retire("run-task-a",execute=True)


def test_interrupted_clean_provision_can_be_adopted_once(system,monkeypatch):
    p,db,_=system;prepare(system)
    original=p.workspace.provision
    def interrupted(row):
        original(row);raise RuntimeError("interrupted before SQL receipt")
    monkeypatch.setattr(p.workspace,"provision",interrupted)
    with pytest.raises(RuntimeError):p.provision("run-task-a",execute=True)
    with db._db() as c:assert c.execute("SELECT status FROM parallel_runs").fetchone()[0]=="reserved"
    monkeypatch.setattr(p.workspace,"provision",original)
    assert p.provision("run-task-a",execute=True)["status"]=="ready"
    assert p.provision("run-task-a",execute=True)["status"]=="ready"


@pytest.mark.parametrize("change",["outside","head","binding","ignored"])
def test_workspace_drift_blocks_launch_and_preserves_files(system,change):
    p,db,_=system;ready(system)
    path=p.workspace.path("run-task-a")
    if change=="outside":(path/"src/task-b.txt").write_text("unapproved")
    if change=="binding":(path/META/"binding.json").write_bytes(b"unknown")
    if change=="ignored":
        (path/"coordination/monitor/runtime").mkdir(parents=True);(path/"coordination/monitor/runtime/work").write_text("unapproved")
    if change=="head":git(path,"switch","-c","codex/probe")
    with pytest.raises(StateError):p.mocks(["run-task-a"],execute=True)
    assert path.exists()
    with db._db() as c:assert c.execute("SELECT status FROM parallel_runs").fetchone()[0]=="ready"


def test_two_real_native_mocks_overlap_collect_via_controller_and_retire(system,monkeypatch):
    p,db,_=system;ready(system);ready(system,"task-b")
    old=db.path.read_bytes();assert p.mocks(["run-task-a","run-task-b"])["would_launch"]==2
    assert db.path.read_bytes()==old
    from worker_process_guard import JobProcess
    resume=JobProcess.resume;durable=set()
    def verify_before_resume(job):
        with db._db() as connection:
            receipts=[json.loads(r[0]) for r in connection.execute("SELECT process_json FROM parallel_runs")]
            assert any(r.get("pid")==job.pid and r.get("creation_time")==job.creation_time and r.get("tree_stopped") is False for r in receipts)
        durable.add(job.pid)
        resume(job)
    monkeypatch.setattr(JobProcess,"resume",verify_before_resume)
    result=p.mocks(["run-task-a","run-task-b"],execute=True)
    assert len(durable)==2
    assert result["mock_only"] and result["overlap_verified"]
    receipts=result["receipts"];assert len({r["pid"] for r in receipts})==2
    assert all(r["exit_code"]==0 and r["tree_stopped"] and r["creation_time"]>0 for r in receipts)
    assert max(r["started_ns"] for r in receipts)<min(r["ended_ns"] for r in receipts)
    for task in ("task-a","task-b"):
        run="run-"+task;candidate=p.workspace.path(run)
        assert p.inspect(run)["changed"]==["src/"+task+".txt"]
        assert (p.root/"src"/(task+".txt")).read_text()=="base "+task
        assert p.submit(run,"submit-"+task)["dry_run"]
        assert p.submit(run,"submit-"+task,execute=True)["status"]=="applied"
        assert p.submit(run,"submit-"+task,execute=True)["historical"]
        report=p.root/"coordination/delivery"/(task+"-delivery-report.md")
        assert report.exists() and b"Mock isolation evidence only" in report.read_bytes()
        assert (p.root/"coordination/task-board/review"/(task+".md")).exists()
        assert p.retire(run,execute=True)["status"]=="released" and candidate.exists()
    assert not list((p.root/"coordination/task-board/done").glob("*.md"))
    assert p.disable(execute=True)["mode"]=="disabled"


@pytest.mark.parametrize("failure",["spawn","cleanup"])
def test_failed_or_unknown_launch_is_never_retried_or_freed(system,monkeypatch,failure):
    p,db,_=system;ready(system)
    import worker_process_guard
    def fail(*a,**k):raise OSError("spawn failure")
    class UnconfirmedJob:
        # No real process: simulate lost resume and cleanup responses.
        pid=123;creation_time=456
        resume=fail;stop=fail
        def close(self):pass
    monkeypatch.setattr(worker_process_guard,"JobProcess",fail if failure=="spawn" else lambda *a,**k:UnconfirmedJob())
    with pytest.raises(StateError):p.mocks(["run-task-a"],execute=True)
    with pytest.raises(StateError):p.mocks(["run-task-a"],execute=True)
    with pytest.raises(StateError):p.retire("run-task-a",execute=True)
    with pytest.raises(StateError):p.disable(execute=True)
    assert p.workspace.path("run-task-a").exists()
    if failure=="cleanup":
        with db._db() as c:
            row=c.execute("SELECT status,process_json FROM parallel_runs").fetchone()
            assert row["status"]=="recovery_required"
            assert json.loads(row["process_json"])==dict(pid=123,creation_time=456,tree_stopped=False)


def test_native_competing_admissions_respect_single_slot(system,tmp_path):
    p,db,_=system;p.disable(execute=True);p.enable(1,execute=True,quiesced=True)
    body="""
from pathlib import Path
import json,time
from coordination_runtime.state_controller import StateController,StateError
from coordination_runtime.parallel_runtime import ParallelController
p=ParallelController(StateController(sys.argv[1],_clock=lambda:10000),sys.argv[2],sys.argv[3],'project')
signal=Path(sys.argv[4]); n=sys.argv[5]; request=json.loads(sys.argv[6])
(signal/('ready'+n)).touch()
deadline=time.monotonic()+10
while not (signal/'go').exists():
 if time.monotonic()>deadline:raise SystemExit(2)
 time.sleep(.01)
try:p.prepare(request,sys.argv[7],sys.argv[8],[],sys.argv[9],execute=True);win=True
except StateError:win=False
(signal/('result'+n)).write_text(json.dumps(win))
"""
    signals=tmp_path/"signals";signals.mkdir()
    with ExitStack() as stack:
        ps=[]
        for n,task in enumerate(("task-a","task-b")):
            source=p.root/"coordination/task-board/ready"/(task+".md")
            ps.append(start(stack,body,db.path,p.root,p.workspace.root,signals,n,json.dumps(request(p,task)),source.name,_sha(source.read_bytes()),"src/"+task+".txt"))
        wait_for(lambda:len(list(signals.glob("ready*")))==2);(signals/"go").touch()
        assert [child.wait(timeout=15) for child in ps]==[0,0]
    assert sum(json.loads(f.read_text()) for f in signals.glob("result*"))==1
    with db._db() as c:assert c.execute("SELECT COUNT(*) FROM parallel_runs").fetchone()[0]==1


def test_schema2_explicit_upgrade_keeps_old_rows_and_marker_absent(system,tmp_path):
    p,db,_=system;p.disable(execute=True)
    with db._db(write=True) as c:
        c.execute("DROP TABLE publication_queue");c.execute("DROP TABLE evidence_candidates");c.execute("DROP TABLE parallel_runs");c.execute("DROP TABLE parallel_projects");c.execute("PRAGMA user_version=2")
    before=db.path.read_bytes();assert db.migrate()["target_version"]==4 and db.path.read_bytes()==before
    backup=tmp_path/"schema2.db";assert db.migrate(backup,execute=True)["schema_version"]==4
    assert backup.exists() and not p.marker.exists()
    with db._db() as c:assert c.execute("SELECT root_digest FROM project_bindings").fetchone()[0]==p.board.root_digest


def test_cli_bad_request_is_private_and_no_real_activation(system,tmp_path,capsys):
    from coordination_runtime.parallel_runtime import main
    p,db,_=system
    f=tmp_path/"bad.json";f.write_text('{"private-marker":true}')
    args=["--db",str(db.path),"--repo",str(p.root),"--workspaces",str(p.workspace.root),"--project-id","project","prepare",
          "--request-file",str(f),"--filename","task-a.md","--expected-sha256","0"*64,"--output","src/task-a.txt"]
    assert main(args)==1 and "private-marker" not in capsys.readouterr().out
    assert not p.workspace.root.exists()
