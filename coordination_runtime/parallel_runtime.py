"""Explicit finite Parallel Mode: native isolated mocks, never real providers."""
import argparse
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import time
import uuid

from .state_controller import StateController, StateError, _id, _integer
from .board_projection import BoardProjector, _sha
from .parallel_policy import scopes, identifiers, path_key, overlap
from .workspace import WorkspaceManager, META, digest, path_digest, read_small
from coordination_common import parallel_marker
from .resource_guard import preflight, require_resources


def encoded(value):
    return (json.dumps(value,sort_keys=True)+"\n").encode()


def publish_new(path,data):
    if path.resolve()!=path: raise StateError("Publication path alias refused.")
    if path.exists():
        if read_small(path)==data: return
        raise StateError("Publication conflicts with existing evidence.")
    fd,draft=tempfile.mkstemp(prefix=".parallel-",suffix=".tmp",dir=path.parent)
    with os.fdopen(fd,"wb") as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    try: os.link(draft,path)
    except FileExistsError:
        if read_small(path)!=data: raise StateError("Publication occupant changed.") from None
    Path(draft).unlink()


class ParallelController:
    def __init__(self,controller,repository,workspaces,project_id):
        self.controller=controller
        self.board=BoardProjector(controller,repository,project_id,_parallel=True)
        self.workspace=WorkspaceManager(repository,workspaces,project_id)
        self.root=self.board.root; self.project_id=project_id
        self.marker=parallel_marker(self.root)

    def _payload(self,capacity):
        return encoded(dict(schema_version=1,mode="parallel",project_id=self.project_id,
                            root_digest=self.board.root_digest,workspace_root_digest=path_digest(self.workspace.root),
                            controller_digest=path_digest(self.controller.path),capacity=capacity))

    def _settings(self,db):
        row=db.execute("SELECT * FROM parallel_projects WHERE project_id=?",(self.project_id,)).fetchone()
        if row and (row["root_digest"]!=self.board.root_digest or row["workspace_root_digest"]!=path_digest(self.workspace.root)):
            raise StateError("Parallel configuration binding mismatched.")
        return row

    def _active(self,db):
        row=self._settings(db)
        if (not row or row["mode"]!="parallel" or self.marker.resolve()!=self.marker
                or not self.marker.is_file() or read_small(self.marker)!=self._payload(row["capacity"])):
            raise StateError("Parallel Mode is not enabled for this controller.")
        return row

    def _now(self,db):
        now=self.controller._now()
        if now<db.execute("SELECT last_clock_ms FROM metadata WHERE id=1").fetchone()[0]:
            raise StateError("Clock moved backwards; recovery required.")
        return now

    def _audit(self,db,event,row=None):
        now=self._now(db); row=row or {}
        event_id=digest([self.project_id,row.get("run_id"),event,row.get("delivery_sha")]) if event=="delivery.published" else _sha(uuid.uuid4().bytes)
        db.execute("INSERT OR IGNORE INTO events(schema_version,event_id,project_id,task_id,run_id,agent_id,event_type,timestamp_ms,causation_id) VALUES(?,?,?,?,?,?,?,?,?)",
                   (1,event_id,self.project_id,row.get("task_id","controller"),row.get("run_id","controller"),
                    row.get("owner","controller"),event,now,row.get("claim_request","mode")))
        db.execute("UPDATE metadata SET last_clock_ms=? WHERE id=1",(now,))

    def _row(self,db,run):
        _id(run)
        row=db.execute("SELECT * FROM parallel_runs WHERE project_id=? AND run_id=?",(self.project_id,run)).fetchone()
        if not row: raise StateError("Parallel run is not registered.")
        return dict(row)

    def _update(self,db,row,event,**fields):
        if not set(fields)<={"status","process_json","delivery_sha","submit_request"}: raise StateError("Invalid parallel state update.")
        db.execute("UPDATE parallel_runs SET "+",".join(k+"=?" for k in fields)+" WHERE project_id=? AND run_id=?",
                   (*fields.values(),self.project_id,row["run_id"]))
        self._audit(db,event,row)

    def _quiescent(self,db):
        if (db.execute("SELECT 1 FROM runtime_tasks WHERE project_id=? AND active_run_id IS NOT NULL",(self.project_id,)).fetchone()
                or db.execute("SELECT 1 FROM parallel_runs WHERE project_id=? AND status!='released'",(self.project_id,)).fetchone()
                or db.execute("SELECT 1 FROM board_intents WHERE project_id=? AND status IN ('pending','recovery_required')",(self.project_id,)).fetchone()):
            raise StateError("Parallel board is not quiescent.")

    def enable(self,capacity=2,*,execute=False,quiesced=False):
        _integer(capacity,1,2)
        with self.controller._db(write=execute) as db:
            settings=self._settings(db)
            if settings and settings["mode"]=="parallel":
                self._active(db)
                if settings["capacity"]!=capacity: raise StateError("Disable before changing capacity.")
                return {"mode":"parallel","historical":True,"capacity":capacity}
            self._quiescent(db)
            bound=db.execute("SELECT root_digest FROM project_bindings WHERE project_id=?",(self.project_id,)).fetchone()
            if bound and bound[0]!=self.board.root_digest: raise StateError("Project board binding mismatched.")
            data=self._payload(capacity)
            if self.marker.resolve()!=self.marker:raise StateError("Mode marker alias refused.")
            if self.marker.exists() and read_small(self.marker)!=data: raise StateError("Unknown Parallel Mode marker.")
            if not execute: return {"would_enable":True,"capacity":capacity,"dry_run":True}
            if not quiesced: raise StateError("Explicit legacy-writer quiescence is required.")
            self._now(db)
            if self.marker.resolve()!=self.marker: raise StateError("Mode marker alias refused.")
            self.marker.parent.mkdir(parents=True,exist_ok=True)
            try:
                with self.marker.open("xb") as stream:
                    stream.write(data);stream.flush();os.fsync(stream.fileno())
            except FileExistsError:
                if read_small(self.marker)!=data: raise StateError("Parallel controller marker collision.") from None
            db.execute("INSERT OR IGNORE INTO project_bindings VALUES(?,?)",(self.project_id,self.board.root_digest))
            db.execute("INSERT INTO parallel_projects VALUES(?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET mode=excluded.mode,capacity=excluded.capacity",
                       (self.project_id,self.board.root_digest,path_digest(self.workspace.root),"parallel",capacity))
            self._audit(db,"parallel.enabled")
            return {"mode":"parallel","capacity":capacity}

    def disable(self,*,execute=False):
        with self.controller._db(write=execute) as db:
            row=self._settings(db)
            if not row: raise StateError("Parallel Mode configuration missing.")
            self._quiescent(db)
            if self.marker.exists() and read_small(self.marker)!=self._payload(row["capacity"]): raise StateError("Unknown mode marker.")
            if not execute: return {"would_disable":True,"dry_run":True}
            self._now(db)
            if row["mode"]!="disabled":
                db.execute("UPDATE parallel_projects SET mode='disabled' WHERE project_id=?",(self.project_id,))
                self._audit(db,"parallel.disabled")
        # Disabled is committed first. A re-enable between transactions prevents
        # this cleanup from removing the newly active controller's guard.
        with self.controller._db(write=True) as db:
            row=self._settings(db);self._quiescent(db)
            if row["mode"]!="disabled": raise StateError("Parallel mode changed during disable.")
            if self.marker.exists():
                if self.marker.resolve()!=self.marker or read_small(self.marker)!=self._payload(row["capacity"]):
                    raise StateError("Mode marker changed during disable.")
                self.marker.unlink()
        return {"mode":"disabled"}

    def _dependencies(self,fields,task):
        deps=identifiers(fields.get("dependencies",[]),32)
        visiting={task}; visited=set()
        def visit(value):
            if value in visiting: raise StateError("Task dependency cycle refused.")
            if value in visited:return
            if len(visited)+len(visiting)>128: raise StateError("Dependency graph exceeds bound.")
            cards=self.board._cards(value)
            if len(cards)!=1: raise StateError("Dependency identity is not unique.")
            path=next(iter(cards)); data=self.board._read(path); header=self.board._header(data)
            if path.parent.name!="done" or header.get("status")!="DONE": raise StateError("Dependency is not accepted DONE.")
            review=self.board._path(Path("coordination/reviews")/("review-"+value+".md"))
            raw=self.board._read(review)
            if raw is None:raise StateError("Dependency acceptance record missing.")
            prefix=raw.decode("utf-8").replace("\r\n","\n").partition("\n## ")[0]
            task_ids=re.findall(r"^- Task ID: (.+)$",prefix,re.M)
            decisions=re.findall(r"^- Decision: (.+)$",prefix,re.M)
            if task_ids!=[value] or decisions!=["accepted"]:raise StateError("Dependency review is not accepted for this task.")
            visiting.add(value)
            for child in identifiers(header.get("dependencies",[]),32):visit(child)
            visiting.remove(value);visited.add(value)
        for dep in deps:visit(dep)
        return deps

    def _plan(self,request,filename,expected,resources,output):
        source=self.board._path(Path("coordination/task-board/ready")/filename)
        data=self.board._read(source)
        if data is None or _sha(data)!=expected or self.board._cards(request["task_id"])!={source}:
            raise StateError("Parallel card preimage or identity mismatched.")
        header=self.board._header(data)
        if header.get("owner")!=request["owner"] or header.get("status")!="READY": raise StateError("Parallel assignment mismatched.")
        allowed=scopes(header.get("allowed_scope"))
        denied=header.get("forbidden_scope",[])
        if not isinstance(denied,list) or len(denied)>64: raise StateError("Invalid forbidden scope.")
        for item in denied:
            key=path_key(item);base=key.removesuffix("/**")
            if item=="**" or any(c in base for c in "*?[]{}") or any(overlap(key,a) for a in allowed):
                raise StateError("Worker and forbidden scopes conflict.")
        self.workspace.pinned(request["base_sha"])
        path=self.workspace.path(request["run_id"])
        if path.exists(): raise StateError("New run workspace path already exists.")
        return dict(root_digest=self.board.root_digest,workspace_root_digest=path_digest(self.workspace.root),
                    path_digest=path_digest(path),scope=allowed,resources=resources,
                    dependencies=self._dependencies(header,request["task_id"]),filename=filename,card_sha=expected,output=output)

    def prepare(self,request,filename,expected_sha256,resources,output,*,execute=False):
        required={"project_id","task_id","run_id","owner","request_id","expected_version","base_sha","lease_seconds"}
        if not isinstance(request,dict) or set(request)!=required: raise StateError("Invalid parallel request shape.")
        if request["project_id"]!=self.project_id: raise StateError("Parallel project mismatched.")
        # Validate command/digests/filename before using them as paths.
        command=dict(request,op="claim",contract_sha256="0"*64);self.controller._validate(command)
        from .state_controller import _projection
        _projection(command,dict(root_digest=self.board.root_digest,filename=filename,before_sha=expected_sha256,after_sha="0"*64))
        resources=identifiers(resources,16);path_key(output)
        with self.controller._db() as db:
            self._active(db)
            old=db.execute("SELECT * FROM parallel_runs WHERE project_id=? AND run_id=?",(self.project_id,request["run_id"])).fetchone()
        if not old:preflight(self,execute=execute)
        if old:
            r=dict(root_digest=self.board.root_digest,workspace_root_digest=path_digest(self.workspace.root),path_digest=old["path_digest"],
                   scope=json.loads(old["scope_json"]),resources=resources,dependencies=json.loads(old["dependencies_json"]),
                   filename=filename,card_sha=expected_sha256,output=output)
        else:r=self._plan(request,filename,expected_sha256,resources,output)
        from .parallel_policy import validate_reservation
        r=validate_reservation(r);command["contract_sha256"]=digest(r)
        if not execute:
            if not old:
                from .parallel_policy import check_admission
                with self.controller._db() as db:
                    self._active(db)
                    check_admission(db,command,dict(root_digest=r["root_digest"],filename=filename,before_sha=expected_sha256),r)
                    current=self.controller._snapshot(db,self.project_id,request["task_id"])
                    if current["version"]!=request["expected_version"] or current["active_run_id"] is not None:
                        raise StateError("Parallel version or authority conflicts.")
            return {"dry_run":True,"contract_sha256":command["contract_sha256"],"workspace_digest":r["path_digest"],"historical":bool(old)}
        def precondition():
            if self._plan(request,filename,expected_sha256,resources,output)!=r: raise StateError("Scheduling policy changed before admission.")
            preflight(self)  # Read-only fresh sample while the admission writer is held.
        return self.board.prepare(command,filename,expected_sha256,reservation=r,_admission_check=precondition)

    def _live(self,db,row):
        self._active(db);now=self._now(db)
        current=self.controller._snapshot(db,self.project_id,row["task_id"]);run=current["run"]
        if not run or run["run_id"]!=row["run_id"] or current["fence"]!=row["fence"] or run["owner"]!=row["owner"] or now>=run["lease_until_ms"]:
            raise StateError("Parallel run authority expired or revoked.")
        return current

    def provision(self,run_id,*,execute=False):
        preflight(self,execute=execute)
        with self.controller._db(write=execute) as db:
            self._active(db);row=self._row(db,run_id);self._live(db,row)
            require_resources(self,db)
            if row["status"] not in {"reserved","ready"}: raise StateError("Workspace is not provisionable.")
            if not execute:return {"dry_run":True,"would_provision":row["status"]=="reserved","workspace_digest":row["path_digest"]}
            try:
                result=self.workspace.provision(row)
                if row["status"]!="ready":self._update(db,row,"workspace.ready",status="ready")
                return dict(result,status="ready")
            except (OSError,StateError):
                self._update(db,row,"workspace.recovery_required",status="recovery_required")
                return {"status":"recovery_required","reason":"workspace_provision_refused"}

    def project(self,run_id,*,execute=False):
        with self.controller._db() as db:
            self._active(db);row=self._row(db,run_id);self._live(db,row)
            if row["status"]!="ready":raise StateError("Workspace is not ready for claim projection.")
            self.workspace.validate(row,clean=True)
        return self.board.reconcile(row["claim_request"],execute=execute)

    def cancel(self,run_id,*,execute=False):
        with self.controller._db() as db:
            self._active(db);row=self._row(db,run_id)
            if row["status"] not in {"reserved","ready","recovery_required"} or json.loads(row["process_json"]):
                raise StateError("Launched run cannot cancel its claim.")
        return self.board.cancel(row["claim_request"],execute=execute)

    def _transition(self,db,row,phase):
        current=self._live(db,row)
        command=dict(op="transition",project_id=self.project_id,task_id=row["task_id"],run_id=row["run_id"],owner=row["owner"],
                     fence=row["fence"],expected_version=current["version"],phase=phase,request_id=digest([row["run_id"],phase]))
        return self.controller.apply(command,_parallel=True,_connection=db)

    def inspect(self,run_id):
        with self.controller._db() as db:
            self._settings(db);row=self._row(db,run_id)
            return dict(self.workspace.validate(row),run_id=run_id,status=row["status"],process=json.loads(row["process_json"]))


    def mocks(self,run_ids,*,execute=False):
        runs=identifiers(run_ids,2)
        if not runs:raise StateError("Mock batch is empty.")
        if os.name!="nt":raise StateError("This passive mock adapter requires Windows JobProcess.")
        preflight(self,execute=execute)
        with self.controller._db(write=execute) as db:
            self._active(db);rows=[self._row(db,run) for run in runs]
            require_resources(self,db)
            for row in rows:
                current=self._live(db,row)
                if row["status"]!="ready" or current["run"]["phase"]!="claimed": raise StateError("Mock run is not ready.")
                intent=db.execute("SELECT status FROM board_intents WHERE project_id=? AND request_id=?",(self.project_id,row["claim_request"])).fetchone()
                if not intent or intent[0]!="applied":raise StateError("Claim projection is incomplete.")
                self.workspace.validate(row,clean=True)
                path=self.workspace.path(row["run_id"])/row["output"]
                if path.resolve()!=path:raise StateError("Mock output path alias refused.")
            if not execute:return {"dry_run":True,"would_launch":len(rows)}
            for row in rows:
                self._transition(db,row,"launching")
                self._update(db,row,"mock.launching",status="launching")
        from worker_process_guard import JobProcess
        jobs={};finished=set()
        try:
            for row in rows:
                path=self.workspace.path(row["run_id"])
                jobs[row["run_id"]]=JobProcess([sys.executable,"-c",MOCK_CODE,str(path),row["run_id"],row["output"]],cwd=path)
            # Commit identity while every owned launcher is still suspended.
            # A lost controller leaves a recognizable launch, never a free slot.
            with self.controller._db(write=True) as db:
                for row in rows:
                    current=self._row(db,row["run_id"]);self._live(db,current)
                    job=jobs[row["run_id"]]
                    self._update(db,current,"mock.identity",process_json=json.dumps(dict(pid=job.pid,creation_time=job.creation_time,tree_stopped=False),sort_keys=True))
            for row in rows:
                with self.controller._db(write=True) as db:
                    current=self._row(db,row["run_id"]);self._live(db,current)
                    if current["status"]!="launching":raise StateError("Mock launch state changed.")
                    require_resources(self,db)
                    jobs[row["run_id"]].resume()
                    self._transition(db,row,"running")
                    self._update(db,row,"mock.running",status="running")
            deadline=time.monotonic()+8
            while not all((self.workspace.path(row["run_id"])/META/"mock-ready").is_file() for row in rows):
                if time.monotonic()>=deadline:raise StateError("Mock readiness deadline exhausted.")
                time.sleep(.01)
            with self.controller._db(write=True) as db:
                for row in rows:self._live(db,self._row(db,row["run_id"]))
                for row in rows:
                    with (self.workspace.path(row["run_id"])/META/"mock-go").open("xb") as go:
                        go.write(b"go");go.flush();os.fsync(go.fileno())
            receipts=[]
            for row in rows:
                job=jobs[row["run_id"]];code=job.wait(timeout=8)
                stopped=job.wait_empty(timeout=1)
                if not stopped:job.stop();stopped=True
                raw=read_small(self.workspace.path(row["run_id"])/META/"mock-result.json")
                result=json.loads(raw)
                if (set(result)!={"run_id","started_ns","ended_ns"} or result["run_id"]!=row["run_id"]
                        or type(result["started_ns"]) is not int or type(result["ended_ns"]) is not int
                        or not 0<result["started_ns"]<result["ended_ns"]):raise StateError("Mock timing receipt mismatched.")
                receipt=dict(result,pid=job.pid,creation_time=job.creation_time,exit_code=code,tree_stopped=stopped,result_sha=_sha(raw))
                with self.controller._db(write=True) as db:
                    self._active(db);current=self._row(db,row["run_id"])
                    self._update(db,current,"mock.stopped",status="stopped",process_json=json.dumps(receipt,sort_keys=True))
                finished.add(row["run_id"]);receipts.append(receipt)
            if any(r["exit_code"]!=0 for r in receipts):raise StateError("Native mock failed.")
            overlap_ok=(len(receipts)==1 or max(r["started_ns"] for r in receipts)<min(r["ended_ns"] for r in receipts))
            if not overlap_ok:raise StateError("Native mock executions did not overlap.")
            return {"mock_only":True,"overlap_verified":overlap_ok,"receipts":receipts}
        except BaseException:
            for row in rows:
                if row["run_id"] in finished:continue
                job=jobs.get(row["run_id"]);proof={}
                if job is not None:
                    proof=dict(pid=job.pid,creation_time=job.creation_time,tree_stopped=False)
                    try:
                        code=job.stop()
                        proof.update(exit_code=code,tree_stopped=True)
                    except Exception:pass
                try:
                    with self.controller._db(write=True) as db:
                        current=self._row(db,row["run_id"])
                        self._update(db,current,"mock.recovery_required",status="stopped" if proof.get("tree_stopped") is True else "recovery_required",process_json=json.dumps(proof,sort_keys=True))
                except Exception:pass  # Keep committed launching state, never guess reusable.
            raise StateError("Native mock batch stopped; inspect preserved reservations.") from None
        finally:
            for job in jobs.values():job.close()

    def _submission_card(self,row):
        path=self.board._path(Path("coordination/task-board/in_progress")/row["filename"])
        data=self.board._read(path);intent=self.controller.intent(self.project_id,row["claim_request"])
        if data is None or not intent or _sha(data)!=intent["after_sha"] or self.board._cards(row["task_id"])!={path}:
            raise StateError("Shared card changed since claim projection.")
        return data,self.board._header(data)

    def _delivery(self,row,changed,phase):
        _id(phase)
        native=json.loads(row['process_json']).get('adapter')=='native-provider-v1'
        validation=('Finite native provider exited zero; owned tree stopped; output digest, scope and binding inspected. Independent checker/review still required.' if native else
                    'Finite passive native mock exited zero; owned tree stopped; scope and binding inspected.')
        residual=('Native synthetic code-generation pilot only; no product acceptance, general tool autonomy or publication authority.' if native else
                  'Mock isolation evidence only; no product tests, formal acceptance or provider pilot.')
        text=("# Delivery Report\n\n- Task ID: "+row["task_id"]+"\n- Agent: "+row["owner"]+"\n- Phase: "+phase+
              "\n- Status: DELIVERED\n\n## Changed Files\n\n"+"\n".join("- "+p for p in changed)+
              "\n\n## Artifact Paths\n\n- Run: "+row["run_id"]+"\n- Workspace digest: "+row["path_digest"]+
              "\n- Base SHA: "+row["base_sha"]+"\n- Fence: "+str(row["fence"])+
              "\n\n## Validation Steps Performed\n\n"+validation+"\n"
              "\n## Known Residual Risks\n\n"+residual+"\n"
              "\n## Acceptance Criteria Coverage\n\n"+('Native isolated provider proof' if native else 'Native isolated mock proof')+"; human review remains required.\n"
              "\n## Recommended Handoff\n\nPreserve candidate; retire authority, quiesce Parallel Mode and use authorized review workflow.\n")
        raw=text.encode()
        if len(raw)>65536:raise StateError("Delivery receipt exceeds bound.")
        return raw

    def submit(self,run_id,request_id,*,execute=False):
        _id(request_id)
        with self.controller._db(write=execute) as db:
            self._active(db);row=self._row(db,run_id);current=self._live(db,row)
            if row["submit_request"] and row["submit_request"]!=request_id:raise StateError("Submission request identity changed.")
            prior=db.execute("SELECT * FROM board_intents WHERE project_id=? AND request_id=?",(self.project_id,request_id)).fetchone()
            if prior:
                if prior["run_id"]!=run_id or prior["phase"]!="submitted":raise StateError("Submission intent identity conflicts.")
                resume=True
            else:
                resume=False
                receipt=json.loads(row["process_json"])
                if (row["status"]!="stopped" or receipt.get("exit_code")!=0 or receipt.get("tree_stopped") is not True
                        or receipt.get("run_id")!=run_id or not receipt.get("result_sha")
                        or receipt.get("adapter")=="native-provider-v1" and receipt.get("outcome")!="succeeded"):
                    raise StateError("Successful stopped mock receipt required.")
                checked=self.workspace.validate(row)
                data,header=self._submission_card(row)
                raw=self._delivery(row,checked["changed"],str(header.get("phase","")))
                report=self.board._path(Path("coordination/delivery")/(row["task_id"]+"-delivery-report.md"))
                if report.exists() and read_small(report)!=raw:raise StateError("Existing delivery receipt conflicts.")
                if row["delivery_sha"] and row["delivery_sha"]!=_sha(raw):raise StateError("Delivery candidate changed after preparation.")
                if not execute:return {"dry_run":True,"would_submit":True,"delivery_sha256":_sha(raw)}
                if not row["delivery_sha"]:
                    self._update(db,row,"delivery.pending",delivery_sha=_sha(raw),submit_request=request_id)
        if resume:return self.board.reconcile(request_id,execute=execute)
        with self.controller._db(write=True) as db:
            row=self._row(db,run_id);current=self._live(db,row)
            checked=self.workspace.validate(row);data,header=self._submission_card(row)
            raw=self._delivery(row,checked["changed"],str(header.get("phase","")))
            if _sha(raw)!=row["delivery_sha"]:raise StateError("Delivery changed before publication.")
            report=self.board._path(Path("coordination/delivery")/(row["task_id"]+"-delivery-report.md"))
            publish_new(report,raw)
            self._audit(db,"delivery.published",row)
        command=dict(op="transition",project_id=self.project_id,task_id=row["task_id"],run_id=run_id,owner=row["owner"],
                     request_id=request_id,expected_version=current["version"],fence=row["fence"],phase="submitted")
        self.board.prepare(command,row["filename"],_sha(data))
        return self.board.reconcile(request_id,execute=True)

    def retire(self,run_id,*,execute=False):
        with self.controller._db(write=execute) as db:
            self._active(db);row=self._row(db,run_id)
            if row["status"]=="released":return {"status":"released","historical":True}
            proof=json.loads(row["process_json"])
            if not (row["status"] in {"reserved","ready"} and not proof) and not (row["status"]=="stopped" and proof.get("tree_stopped") is True):
                raise StateError("Process stop is unknown; reservation remains held.")
            if db.execute("SELECT 1 FROM board_intents WHERE project_id=? AND task_id=? AND status IN ('pending','recovery_required')",(self.project_id,row["task_id"])).fetchone():
                raise StateError("Reconcile or explicitly cancel pending projection before retirement.")
            current=self.controller._snapshot(db,self.project_id,row["task_id"])
            if not execute:return {"dry_run":True,"would_retire":True,"candidate_preserved":True}
            if not current["run"] or current["run"]["run_id"]!=run_id or current["fence"]!=row["fence"]:
                raise StateError("Retirement runtime identity mismatched.")
            command=dict(op="revoke",project_id=self.project_id,task_id=row["task_id"],run_id=run_id,actor="parallel-controller",
                         reason="operator",fence=row["fence"],expected_version=current["version"],request_id=digest([run_id,"retire"]))
            self.controller.apply(command,_parallel=True,_connection=db)
            self._update(db,row,"reservation.released",status="released")
            return {"status":"released","candidate_preserved":True}


MOCK_CODE = r"""
from pathlib import Path
import json,sys,time
root=Path(sys.argv[1]); run=sys.argv[2]; target=root/sys.argv[3]; meta=root/'.coordination-runtime'
(meta/'mock-ready').touch()
deadline=time.monotonic()+10
while not (meta/'mock-go').exists():
 if time.monotonic()>deadline: raise SystemExit(2)
 time.sleep(.01)
started=time.monotonic_ns()
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text('passive mock '+run+'\\n',encoding='utf-8')
time.sleep(.3)
(meta/'mock-result.json').write_text(json.dumps(dict(run_id=run,started_ns=started,ended_ns=time.monotonic_ns())),encoding='utf-8')
"""


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,required=True);parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--workspaces",type=Path,required=True);parser.add_argument("--project-id",required=True)
    subs=parser.add_subparsers(dest="action",required=True)
    enable=subs.add_parser("enable");enable.add_argument("--capacity",type=int,default=2);enable.add_argument("--quiesced",action="store_true");enable.add_argument("--execute",action="store_true")
    disable=subs.add_parser("disable");disable.add_argument("--execute",action="store_true")
    prepare=subs.add_parser("prepare");prepare.add_argument("--request-file",type=Path,required=True);prepare.add_argument("--filename",required=True)
    prepare.add_argument("--expected-sha256",required=True);prepare.add_argument("--output",required=True);prepare.add_argument("--resource",action="append",default=[]);prepare.add_argument("--execute",action="store_true")
    for action in ("provision","project","submit","retire","cancel","inspect"):
        sub=subs.add_parser(action);sub.add_argument("--run-id",required=True)
        if action!="inspect":sub.add_argument("--execute",action="store_true")
        if action=="submit":sub.add_argument("--request-id",required=True)
    mock=subs.add_parser("mocks");mock.add_argument("--run-id",action="append",required=True);mock.add_argument("--execute",action="store_true")
    args=parser.parse_args(argv)
    try:
        p=ParallelController(StateController(args.db),args.repo,args.workspaces,args.project_id)
        if args.action=="enable":result=p.enable(args.capacity,execute=args.execute,quiesced=args.quiesced)
        elif args.action=="disable":result=p.disable(execute=args.execute)
        elif args.action=="prepare":
            with args.request_file.open("rb") as stream:raw=stream.read(16385)
            if len(raw)>16384:raise StateError("Parallel request exceeds size bound.")
            result=p.prepare(json.loads(raw),args.filename,args.expected_sha256,args.resource,args.output,execute=args.execute)
        elif args.action=="mocks":result=p.mocks(args.run_id,execute=args.execute)
        elif args.action=="inspect":result=p.inspect(args.run_id)
        elif args.action=="submit":result=p.submit(args.run_id,args.request_id,execute=args.execute)
        else:result=getattr(p,args.action)(args.run_id,execute=args.execute)
        print(json.dumps(result,sort_keys=True))
        return 1 if isinstance(result,dict) and result.get("status")=="recovery_required" else 0
    except (StateError,OSError,ValueError,RecursionError) as error:
        print(json.dumps({"error":"parallel_controller_refused","reason":str(error) if isinstance(error,StateError) else "input_or_io_error"}))
        return 1


if __name__=="__main__":raise SystemExit(main())
