import json
import shutil
import subprocess
import sys
import tempfile
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


def test_workdir_outside_repo_excludes_repo_tmp(tmp_path):  # NEG-W16-WORKDIR-SCOPE
    runner = _runner_module()
    assert runner._outside_repo(runner.ROOT / ".tmp" / "os" / "run") is False
    assert runner._outside_repo(Path("C:/Windows/Temp")) is True
    assert runner._outside_source_tree(runner.ROOT / ".tmp" / "os" / "run") is True
    clean_room = runner._clean_room_dir("test-clean-room-")
    try:
        assert clean_room.is_relative_to(runner.ROOT / ".tmp")
    finally:
        shutil.rmtree(clean_room)


def test_stub_settings_pass_maps_to_parent(tmp_path, monkeypatch):  # REQ-W16-SETTINGS
    runner = _runner_module()
    payload = {"schema": "wx-packaged-runtime/1", "result": "PASS",
               "checks": _canned_checks(runner)}
    artifact = _stub(tmp_path, monkeypatch, payload=payload)
    output = tmp_path / "smoke.json"
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=20)
    assert evidence["checks"]["settings_opened"] == "PASS"
    # The stub performs no wire I/O or in-process teardown, so both critical
    # checks stay FAIL even though it claims PASS for the other checks.
    assert evidence["checks"]["pty_resize"] == "FAIL"
    assert evidence["checks"]["clean_shutdown"] == "FAIL"
    assert evidence["result"] == "FAIL"
    for name, value in evidence["checks"].items():
        if name not in ("pty_resize", "clean_shutdown"):
            assert value == "PASS", name
    # Clean-room state follows the project .tmp contract and stays outside src.
    assert evidence["details"]["workdir_outside_repo"] is False
    assert evidence["details"]["workdir_outside_source_tree"] is True
    assert evidence["details"]["workdir_under_temp_root"] is True


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
    finalized = json.loads(runtime_path.read_text(encoding="utf-8"))
    assert finalized["schema"] == payload["schema"]
    assert finalized["checks"]["settings_opened"] == "FAIL"
    assert finalized["checks"]["pty_resize"] == "FAIL"
    assert finalized["checks"]["clean_shutdown"] == "FAIL"
    assert finalized["result"] == "FAIL"
    assert finalized["finalized_by"] == "parent-transport-and-process-observer/1"


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


# --- W16 timeout evidence retention (HPC-W04-HARNESS-025) -----------------
# The kill above proves the child is reaped.  These three close the remaining
# gap: a killed child may already have written its runtime payload and stdout,
# and the parent must score that proof instead of discarding it.  The verdict
# stays FAIL; only the evidence survives.
#
# Real code exercised: run_packaged_smoke timeout branch evidence scoring and
# the main() --timeout wiring.  Mocked boundary: the child artifact only.

STUB_WRITE_THEN_SLEEP_ARTIFACT = """\
import os
import sys
import time
from pathlib import Path


def main() -> int:
    out = os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT", "")
    if out:
        Path(out).write_text(os.environ.get("HPC_STUB_PAYLOAD", "{}"), encoding="utf-8")
    print("stub-runtime-proved", flush=True)
    time.sleep(float(os.environ.get("HPC_STUB_SLEEP", "0") or 0))
    return 0


raise SystemExit(main())
"""


def _write_then_sleep_stub(tmp_path, monkeypatch, *, payload, sleep=60):
    """Stub that proves its checks FIRST and only then hangs until killed."""
    artifact = tmp_path / "stub-write-then-sleep.py"
    artifact.write_text(STUB_WRITE_THEN_SLEEP_ARTIFACT, encoding="utf-8")
    monkeypatch.setenv("HPC_STUB_PAYLOAD", json.dumps(payload))
    monkeypatch.setenv("HPC_STUB_SLEEP", str(sleep))
    return artifact


def _passing_payload(runner):
    return {"schema": "wx-packaged-runtime/1", "result": "PASS",
            "checks": _canned_checks(runner)}


def test_timeout_retains_child_runtime_evidence(tmp_path, monkeypatch):  # REQ-W16-TIMEOUT-EVIDENCE
    runner = _runner_module()
    artifact = _write_then_sleep_stub(tmp_path, monkeypatch, payload=_passing_payload(runner))
    output = tmp_path / "smoke.json"
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=3)
    assert (tmp_path / "smoke.runtime.json").is_file()
    for name in _canned_checks(runner):
        if name == "pty_resize":
            # Server-side wire proof only; the stub performs no wire I/O.
            continue
        assert evidence["checks"][name] == "PASS", name
    assert evidence["checks"]["process_started"] == "PASS"
    # A killed child never shut down cleanly, and never passes acceptance.
    assert evidence["checks"]["pty_resize"] == "FAIL"
    assert evidence["checks"]["clean_shutdown"] == "FAIL"
    assert evidence["result"] == "FAIL"


def test_25_second_gate_timeout_retains_evidence_and_fails(tmp_path, monkeypatch):
    """Exercise the gate's 25s timeout contract without waiting 25 seconds."""
    runner = _runner_module()
    artifact = _write_then_sleep_stub(tmp_path, monkeypatch, payload=_passing_payload(runner))
    output = tmp_path / "smoke.json"
    run_child = runner._run_child
    observed_timeout = []

    def accelerated_child(cmd, *, cwd, env, timeout):
        observed_timeout.append(timeout)
        # Preserve actual kill/reap and evidence production while keeping this
        # regression fast; the packaged-gate's requested deadline stays 25s.
        return run_child(cmd, cwd=cwd, env=env, timeout=1)

    monkeypatch.setattr(runner, "_run_child", accelerated_child)
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=25)

    assert observed_timeout == [25]
    assert evidence["result"] == "FAIL"
    assert evidence["details"]["timeout"] == "artifact did not exit within 25s"
    assert evidence["checks"]["settings_opened"] == "PASS"
    assert evidence["checks"]["clean_shutdown"] == "FAIL"


def test_packaged_smoke_function_and_cli_defaults_are_25_seconds():
    import inspect
    runner = _runner_module()
    assert inspect.signature(runner.run_packaged_smoke).parameters["timeout"].default == 25
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "wx_packaged_smoke.py"), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "default: 25 packaged, 240 fresh-user" in " ".join(result.stdout.split())


def test_cli_timeout_defaults_follow_smoke_mode(tmp_path, monkeypatch, capsys):
    runner = _runner_module()
    seen = []

    def evidence_for(_artifact, _platform, _output, *, timeout):
        seen.append(timeout)
        return {"result": "PASS", "identity_header": "stub"}

    monkeypatch.setattr(runner, "run_fresh_user_smoke", evidence_for)
    monkeypatch.setattr(runner, "run_packaged_smoke", evidence_for)
    script = str(Path(__file__).parents[1] / "scripts" / "wx_packaged_smoke.py")
    artifact = str(tmp_path / "stub.exe")
    output = str(tmp_path / "evidence.json")

    monkeypatch.setattr(sys, "argv", [script, "--artifact", artifact, "--output", output, "--fresh-user"])
    assert runner.main() == 0
    monkeypatch.setattr(sys, "argv", [script, "--artifact", artifact, "--output", output])
    assert runner.main() == 0
    monkeypatch.setattr(sys, "argv", [script, "--artifact", artifact, "--output", output,
                                       "--fresh-user", "--timeout", "17"])
    assert runner.main() == 0

    assert seen == [240, 25, 17]
    assert capsys.readouterr().out.count('"result": "PASS"') == 3


def test_timeout_details_score_flag_and_kill_keys_intact(tmp_path, monkeypatch):  # NEG-W16-TIMEOUT-KILL
    runner = _runner_module()
    artifact = _write_then_sleep_stub(tmp_path, monkeypatch, payload=_passing_payload(runner))
    output = tmp_path / "smoke.json"
    evidence = runner.run_packaged_smoke(artifact, "windows", output, timeout=3)
    details = evidence["details"]
    assert details["evidence_scored_on_timeout"] is True
    # The pre-existing kill contract stays byte-identical.
    assert details["timeout"] == "artifact did not exit within 3s"
    assert details["child_killed"] is True
    assert "exit_code" not in details
    # Bounded child output, not an unbounded blob.
    assert "stub-runtime-proved" in details["output_tail"]
    assert len(details["output_tail"]) <= 2000


def test_cli_timeout_argument_honored_end_to_end(tmp_path, monkeypatch):  # REQ-W16-TIMEOUT-ARG
    import os
    import time
    root = Path(__file__).parents[1]
    runner = _runner_module()
    artifact = _write_then_sleep_stub(tmp_path, monkeypatch, payload=_passing_payload(runner))
    output = tmp_path / "smoke.json"
    env = dict(os.environ, HPC_STUB_PAYLOAD=json.dumps(_passing_payload(runner)), HPC_STUB_SLEEP="60")
    env.pop("PYTHONPATH", None)
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "scripts/wx_packaged_smoke.py", "--artifact", str(artifact),
         "--platform", "windows", "--output", str(output), "--timeout", "3"],
        cwd=root, capture_output=True, text=True, env=env, timeout=120,
    )
    elapsed = time.monotonic() - started
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["details"]["timeout"] == "artifact did not exit within 3s"
    assert report["details"]["evidence_scored_on_timeout"] is True
    # The 3s kill is what ended the run; the 240s default never applied.
    assert elapsed < 60


def test_fresh_user_smoke_removes_disposable_state_but_keeps_evidence(tmp_path, monkeypatch):
    import importlib

    _runner_module()
    fresh = importlib.import_module("wx_fresh_user_smoke")
    artifact = tmp_path / "stub.exe"
    artifact.write_bytes(b"stub")
    output = tmp_path / "fresh-user.json"

    class FixtureRoot:
        name = str(tmp_path / "ssh")

        def cleanup(self):
            pass

    class FixtureServer:
        port = 2222

        def __exit__(self, *_args):
            pass

    monkeypatch.setattr(fresh, "start_loopback_ssh", lambda _output: (
        FixtureRoot(), FixtureServer(), "user", "password",
    ))

    def successful_child(_cmd, *, env, **_kwargs):
        names = (*fresh.FRESH_RUN1_CHECKS, *fresh.FRESH_RUN2_CHECKS)
        payload = {"result": "PASS", "checks": {name: "PASS" for name in names}}
        Path(env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"]).write_text(json.dumps(payload), encoding="utf-8")
        return 0, "", "", False

    monkeypatch.setattr(fresh, "run_child", successful_child)
    evidence = fresh.run_fresh_user_smoke(artifact, "windows", output)

    fresh_parent = Path(evidence["details"]["fresh_root"]).parent
    assert evidence["result"] == "PASS"
    assert evidence["details"]["fresh_parent_cleaned"] is True
    assert not fresh_parent.exists()
    assert output.is_file()
    assert output.with_name("fresh-user.run1.runtime.json").is_file()
    assert output.with_name("fresh-user.run2.runtime.json").is_file()
