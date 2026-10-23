"""Pinned detached Git workspaces; preserve every existing candidate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
from .state_controller import StateError, _id
from .parallel_policy import allows, path_key

META = ".coordination-runtime"


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":")).encode()).hexdigest()


def path_digest(path):
    return hashlib.sha256(os.path.normcase(str(Path(path).resolve())).encode()).hexdigest()


def git(root, *args):
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", *map(str,args)], cwd=root,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        raise StateError("Workspace Git operation unavailable.") from None
    if result.returncode or len(result.stdout) > 262144:
        raise StateError("Workspace Git operation refused.")
    return result.stdout


def read_small(path):
    with Path(path).open("rb") as stream: raw=stream.read(65537)
    if len(raw)>65536: raise StateError("Workspace metadata exceeds size bound.")
    return raw


class WorkspaceManager:
    def __init__(self, repository, root, project):
        _id(project)
        self.repository = Path(repository).resolve()
        self.root = Path(root).resolve()
        self.project = project
        if self.root.is_relative_to(self.repository):
            raise StateError("Workspace storage must be outside authoritative repository.")

    def path(self, run):
        _id(run)
        path = self.root / self.project / run
        if (path.resolve()!=path or not path.is_relative_to(self.root)
                or path.is_relative_to(self.repository)):
            raise StateError("Workspace path is aliased or unsafe.")
        return path

    @staticmethod
    def manifest(row):
        keys=("project_id","run_id","task_id","owner","fence","base_sha","path_digest","scope_json","resources_json","dependencies_json","filename","card_sha","output","claim_request")
        return (json.dumps({k:row[k] for k in keys},sort_keys=True)+"\n").encode()

    def pinned(self, base):
        if git(self.repository,"rev-parse","HEAD").decode().strip()!=base:
            raise StateError("Authoritative base SHA changed.")
        if git(self.repository,"cat-file","-t",base).strip()!=b"commit":
            raise StateError("Workspace base is not a local commit.")

    def identity(self, row):
        path=self.path(row["run_id"])
        if path_digest(path)!=row["path_digest"]:
            raise StateError("Workspace path binding mismatched.")
        if Path(git(path,"rev-parse","--show-toplevel").decode().strip()).resolve()!=path:
            raise StateError("Workspace top-level mismatched.")
        common=git(self.repository,"rev-parse","--path-format=absolute","--git-common-dir").decode().strip()
        actual=git(path,"rev-parse","--path-format=absolute","--git-common-dir").decode().strip()
        if Path(common).resolve()!=Path(actual).resolve(): raise StateError("Workspace repository binding mismatched.")
        if git(path,"rev-parse","HEAD").decode().strip()!=row["base_sha"]:
            raise StateError("Workspace HEAD changed.")
        if git(path,"rev-parse","--abbrev-ref","HEAD").strip()!=b"HEAD":
            raise StateError("Workspace is no longer detached.")
        registered=git(self.repository,"worktree","list","--porcelain","-z").split(b"\0")
        if not any(x.startswith(b"worktree ") and Path(os.fsdecode(x[9:])).resolve()==path for x in registered):
            raise StateError("Workspace registration missing.")
        return path

    def validate(self, row, *, clean=False):
        path=self.identity(row)
        binding=path/META/"binding.json"
        if binding.resolve()!=binding or read_small(binding)!=self.manifest(row):
            raise StateError("Workspace manifest mismatched.")
        changed=set(os.fsdecode(x) for x in git(path,"diff","--name-only","--no-renames","-z",row["base_sha"],"--").split(b"\0") if x)
        for flags in (("--others","--exclude-standard"),("--others","--ignored","--exclude-standard")):
            changed.update(os.fsdecode(x) for x in git(path,"ls-files",*flags,"-z").split(b"\0") if x)
        if len(changed)>2048: raise StateError("Workspace change set exceeds bound.")
        process=json.loads(row["process_json"])
        native=process.get("adapter")=="native-provider-v1"
        metadata={META+"/binding.json"}
        metadata.update(META+"/"+name for name in (
            ("provider-spec.json","provider-ready","provider-go","provider-result.json") if native else
            ("mock-ready","mock-go","mock-result.json")))
        unknown=[n for n in changed if n.startswith(META+"/") and n not in metadata]
        if unknown: raise StateError("Unrecognized controller metadata.")
        for name in changed & metadata:
            file=path/name
            if file.resolve()!=file or not file.is_file(): raise StateError("Controller metadata alias refused.")
            raw=read_small(file)
            if name.endswith("mock-ready") and raw!=b"": raise StateError("Mock readiness metadata changed.")
            if name.endswith("mock-go") and raw!=b"go": raise StateError("Mock barrier metadata changed.")
            if name.endswith("mock-result.json") and (not process.get("result_sha") or hashlib.sha256(raw).hexdigest()!=process["result_sha"]):
                raise StateError("Mock result receipt changed.")
            if native:
                if name.endswith('provider-spec.json') and hashlib.sha256(raw).hexdigest()!=process.get('spec_sha256'):
                    raise StateError('Native specification changed.')
                if name.endswith('provider-ready') and raw!=b'':raise StateError('Native readiness changed.')
                if name.endswith('provider-go') and raw!=b'go':raise StateError('Native barrier changed.')
                if name.endswith('provider-result.json') and (not process.get('result_sha') or hashlib.sha256(raw).hexdigest()!=process['result_sha']):
                    raise StateError('Native result receipt changed.')
        if native and process.get('result_sha'):
            for required in ('provider-spec.json', 'provider-ready', 'provider-go', 'provider-result.json'):
                if META + '/' + required not in changed:
                    raise StateError('Native execution metadata is missing.')
        if process.get("result_sha"):
            result=path/META/("provider-result.json" if native else "mock-result.json")
            if result.resolve()!=result or hashlib.sha256(read_small(result)).hexdigest()!=process["result_sha"]:
                raise StateError("Mock execution result is missing or changed.")
        if native and process.get('output_sha256'):
            output=path/row['output']
            if output.resolve()!=output or hashlib.sha256(read_small(output)).hexdigest()!=process['output_sha256']:
                raise StateError('Native output changed after execution.')
        if clean and changed!={META+"/binding.json"}:
            raise StateError("Workspace is not pristine for launch.")
        allowed=json.loads(row["scope_json"])
        paths=sorted(changed-metadata)
        for name in paths:
            path_key(name)
            child=path/name
            if child.resolve()!=child or not allows(name,allowed):
                raise StateError("Workspace change exceeds assigned scope.")
        return {"workspace_digest":row["path_digest"],"base_sha":row["base_sha"],"changed":paths}

    def provision(self,row):
        path=self.path(row["run_id"])
        if path_digest(path)!=row["path_digest"]: raise StateError("Workspace path binding mismatched.")
        if not path.exists():
            self.pinned(row["base_sha"])
            path.parent.mkdir(parents=True,exist_ok=True)
            hooks=self.root/(".hooks-"+uuid.uuid4().hex)
            if hooks.resolve()!=hooks: raise StateError("Hook directory alias refused.")
            hooks.mkdir()
            try: git(self.repository,"-c","core.hooksPath="+str(hooks),"worktree","add","--detach",path,row["base_sha"])
            finally: hooks.rmdir()
        # Interrupted creation is adopted only when Git registration/base are exact
        # and every tracked/untracked file is pristine before the binding is created.
        self.identity(row)
        meta=path/META; binding=meta/"binding.json"
        if not binding.exists():
            if (git(path,"rev-parse","HEAD").decode().strip()!=row["base_sha"]
                    or git(path,"status","--porcelain","--untracked-files=all","--ignored").strip()):
                raise StateError("Unrecognized or dirty existing workspace.")
            common=git(self.repository,"rev-parse","--path-format=absolute","--git-common-dir").decode().strip()
            actual=git(path,"rev-parse","--path-format=absolute","--git-common-dir").decode().strip()
            if Path(actual).resolve()!=Path(common).resolve(): raise StateError("Foreign existing workspace.")
            if meta.resolve()!=meta: raise StateError("Workspace metadata alias refused.")
            meta.mkdir(exist_ok=True)
            with binding.open("xb") as stream:
                stream.write(self.manifest(row));stream.flush();os.fsync(stream.fileno())
        return self.validate(row,clean=True)
