"""The portable wrapper uses an explicit runtime and preserves quoted argv."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def test_wrapper_honors_runtime_override_and_rejects_missing_override(tmp_path):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell required")
    scripts = tmp_path / "checkout with spaces/scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[2] / "scripts"
    for name in ("run_python.ps1", "resolve-python.ps1"):
        shutil.copyfile(source / name, scripts / name)
    (scripts / "probe.py").write_text("import sys,json; print(json.dumps({'python':sys.executable,'argv':sys.argv[1:]}))")
    command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "run_python.ps1"), "scripts/probe.py", "argument with spaces"]
    environment = dict(os.environ, COORDINATION_PYTHON=sys.executable)
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert Path(value["python"]).resolve() == Path(sys.executable).resolve()
    assert value["argv"] == ["argument with spaces"]
    environment["COORDINATION_PYTHON"] = str(tmp_path / "missing-python.exe")
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and '"argv"' not in result.stdout
