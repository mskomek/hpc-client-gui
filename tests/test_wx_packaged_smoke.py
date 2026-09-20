import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.packaging


@pytest.mark.reporting
def test_missing_artifact_report_fails_critical_stages(tmp_path):
    root = Path(__file__).parents[1]
    artifact = tmp_path / "missing-wx-artifact.exe"
    output = tmp_path / "smoke-evidence.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/wx_packaged_smoke.py",
            "--artifact",
            str(artifact),
            "--platform",
            "windows",
            "--output",
            str(output),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["schema"] == "wx-packaged-smoke/1"
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["result"] == "FAIL"
    assert {"process_started", "wx_runtime_started", "main_frame_created", "clean_shutdown"} <= report["checks"].keys()
    assert set(report["checks"].values()) == {"FAIL"}
    assert "artifact not found" in report["details"]["artifact"]
    assert "MFA" in report["manual_required"]


# --- W16 stub-artifact proofs ---------------------------------------------
# Real code exercised: run_packaged_smoke check mapping, runtime preservation,
# timeout kill, CLI stdout contract. Mocked boundary: the child artifact only
# (a stub .py writing a canned runtime payload); the loopback SSH fixture is
# real. What this does NOT prove: real wx behavior (proven by packaged runs).

STUB_ARTIFACT = """\
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    nap = float(os.environ.get("HPC_STUB_SLEEP", "0") or 0)
    if nap:
        time.sleep(nap)
    out = os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT", "")
    if out:
        payload = json.loads(os.environ.get("HPC_STUB_PAYLOAD", "{}"))
        Path(out).write_text(json.dumps(payload), encoding="utf-8")
    return int(os.environ.get("HPC_STUB_EXIT", "0") or 0)


raise SystemExit(main())
"""


def _runner_module():
    root = Path(__file__).parents[1]
    if str(root / "scripts") not in sys.path:
        sys.path.insert(0, str(root / "scripts"))
    if str(root / "tests") not in sys.path:
        sys.path.insert(0, str(root / "tests"))
    import wx_packaged_smoke as runner
    return runner


def _stub(tmp_path, monkeypatch, *, payload=None, exit_code=0, sleep=0):
    artifact = tmp_path / "stub-artifact.py"
    artifact.write_text(STUB_ARTIFACT, encoding="utf-8")
    monkeypatch.setenv("HPC_STUB_PAYLOAD", json.dumps(payload or {}))
    monkeypatch.setenv("HPC_STUB_EXIT", str(exit_code))
    monkeypatch.setenv("HPC_STUB_SLEEP", str(sleep))
    return artifact


def _canned_checks(runner, **overrides):
    names = [n for n in runner.REQUIRED_CHECKS if n not in ("process_started", "clean_shutdown")]
    return {n: overrides.get(n, "PASS") for n in names}


def test_stub_settings_pass_maps_to_parent(tmp_path, monkeypatch):  # REQ-W16-SETTINGS
    runner = _runner_module()
    payload = {"schema": "wx-packaged-runtime/1", "result": "PASS",
               "checks": _canned_checks(runner)}
    artifact = _stub(tmp_path, monkeypatch, payload=payload)
    output = tmp_path / "smoke.json"
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=20)
    assert evidence["checks"]["settings_opened"] == "PASS"
    # The stub performs no wire I/O, so the server-side resize proof stays
    # FAIL by design; every other mapped check must be PASS.
    assert evidence["checks"]["pty_resize"] == "FAIL"
    assert evidence["result"] == "FAIL"
    for name, value in evidence["checks"].items():
        if name not in ("pty_resize",):
            assert value == "PASS", name
    assert evidence["details"]["workdir_outside_repo"] is True


def test_stub_settings_fail_maps_to_parent(tmp_path, monkeypatch):  # NEG-W16-SETTINGS
    runner = _runner_module()
    payload = {"schema": "wx-packaged-runtime/1", "result": "FAIL",
               "checks": _canned_checks(runner, settings_opened="FAIL")}
    artifact = _stub(tmp_path, monkeypatch, payload=payload)
    output = tmp_path / "smoke.json"
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=20)
    assert evidence["checks"]["settings_opened"] == "FAIL"
    assert evidence["result"] == "FAIL"


def test_stub_runtime_payload_preserved(tmp_path, monkeypatch):  # REQ-W16-RUNTIME-KEPT
    runner = _runner_module()
    payload = {"schema": "wx-packaged-runtime/1", "result": "FAIL",
               "checks": _canned_checks(runner, settings_opened="FAIL")}
    artifact = _stub(tmp_path, monkeypatch, payload=payload)
    output = tmp_path / "smoke.json"
    runner.run_packaged_smoke(artifact, "windows", output, timeout=20)
    runtime_path = tmp_path / "smoke.runtime.json"
    assert runtime_path.is_file()
    assert json.loads(runtime_path.read_text(encoding="utf-8")) == payload


def test_cli_stdout_parseable_on_stub_path(tmp_path, monkeypatch):  # REQ-W16-STDOUT
    root = Path(__file__).parents[1]
    runner = _runner_module()
    payload = {"schema": "wx-packaged-runtime/1", "result": "FAIL",
               "checks": _canned_checks(runner, settings_opened="FAIL")}
    artifact = tmp_path / "stub-artifact.py"
    artifact.write_text(STUB_ARTIFACT, encoding="utf-8")
    output = tmp_path / "smoke.json"
    import os
    env = dict(os.environ, HPC_STUB_PAYLOAD=json.dumps(payload), HPC_STUB_EXIT="0", HPC_STUB_SLEEP="0")
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "scripts/wx_packaged_smoke.py", "--artifact", str(artifact),
         "--platform", "windows", "--output", str(output)],
        cwd=root, capture_output=True, text=True, env=env, timeout=120,
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["schema"] == "wx-packaged-smoke/1"
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["checks"]["settings_opened"] == "FAIL"


def test_sleeper_child_killed_on_timeout(tmp_path, monkeypatch):  # NEG-W16-TIMEOUT-KILL
    import time
    runner = _runner_module()
    artifact = _stub(tmp_path, monkeypatch, payload={}, sleep=60)
    output = tmp_path / "smoke.json"
    started = time.monotonic()
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=3)
    elapsed = time.monotonic() - started
    assert evidence["result"] == "FAIL"
    assert "did not exit within 3s" in evidence["details"]["timeout"]
    assert evidence["details"]["child_killed"] is True
    # Without the kill the sleeper would hold communicate() for 60s.
    assert elapsed < 30
