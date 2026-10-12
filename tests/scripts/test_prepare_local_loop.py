"""Fresh-download preparation uses real isolated registrations and card helpers."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2]


@pytest.fixture
def checkout(tmp_path):
    shutil.copytree(SOURCE / "scripts", tmp_path / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def invoke(root, name="download-check"):
    return subprocess.run([sys.executable, str(root / "scripts/prepare_local_loop.py"), "--run-id", name],
                          capture_output=True, text=True, timeout=15)


def test_fresh_prepare_and_duplicate_leave_receipts_untouched(checkout):
    result = invoke(checkout)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["workers_launched"] == 0
    monitor = checkout / "coordination/monitor"
    registry = json.loads((monitor / "projects.json").read_text())
    assert Path(registry[0]["local_path"]).resolve() == checkout.resolve()
    assert len(json.loads((monitor / "workers.json").read_text())) == 2
    plan = json.loads((checkout / "coordination/plans/download-check.json").read_text())
    assert [task["owner"] for task in plan["tasks"]] == ["opencode-coordination-pilot", "hermes-coordination-pilot", "opencode-coordination-pilot"]
    assert plan["max_attempts"] == 2 and len(list((checkout / "coordination/task-board/ready").glob("*.md"))) == 3
    assert not (monitor / "delivery").exists()  # No activation or forged ACK.
    before = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert invoke(checkout).returncode == 1
    assert before == {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


@pytest.mark.parametrize("conflict", ["project", "worker", "policy", "malformed"])
def test_conflicting_machine_configuration_is_preserved(checkout, conflict):
    monitor = checkout / "coordination/monitor"
    monitor.mkdir(parents=True)
    files = {
        "project": ("projects.json", [{"project_id": "agent-coordination-system", "local_path": str(checkout / "another")}]),
        "worker": ("workers.json", [{"worker_id": "hermes-coordination-pilot", "project_id": "agent-coordination-system", "enabled": False}]),
        "policy": ("routing_policy.json", [{"project_id": "agent-coordination-system", "routes": [], "enabled": False}]),
        "malformed": ("workers.json", {"invalid": True}),
    }
    name, value = files[conflict]
    target = monitor / name
    target.write_text(json.dumps(value))
    before = target.read_bytes()
    assert invoke(checkout).returncode == 1
    assert target.read_bytes() == before and not (checkout / "coordination/plans").exists()


def test_other_registrations_and_routes_are_preserved(checkout):
    assert invoke(checkout).returncode == 0
    monitor = checkout / "coordination/monitor"
    policy = monitor / "routing_policy.json"
    data = json.loads(policy.read_text())
    data[0]["routes"].append({"event_type": "incident_opened", "destination": "orchestrator"})
    data.append({"project_id": "other-project", "routes": [], "enabled": False})
    policy.write_text(json.dumps(data))
    assert invoke(checkout, "second-check").returncode == 0
    assert json.loads(policy.read_text()) == data
