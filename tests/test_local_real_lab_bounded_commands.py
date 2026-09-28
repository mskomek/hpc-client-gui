"""Regression coverage for DEF-W57-017.

The maintained real-cluster lab harness used to run every remote command through
a bare ``& ssh @args`` call. That has no wall-clock bound: ``ConnectTimeout``
only bounds the TCP connect, and ``ServerAliveInterval``/``ServerAliveCountMax``
only fire when the transport dies. When a required Slurm node is DOWN the
controller keeps the allocation PENDING, the SSH channel stays perfectly healthy
and ``& ssh`` never returns, so ``lab-test.ps1`` could neither PASS nor FAIL.

These tests pin the bound itself. They are hermetic: they exercise the bounded
runner against a local child process and never touch the real lab.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
COMMON = (ROOT / "lab/lab-common.ps1").read_text(encoding="utf-8-sig")
LAB_TEST = (ROOT / "lab/lab-test.ps1").read_text(encoding="utf-8-sig")
CONFIG = json.loads((ROOT / "lab/config.json").read_text(encoding="utf-8"))


def _powershell() -> str:
    return shutil.which("pwsh") or shutil.which("powershell") or ""


def test_every_remote_lab_command_is_wall_clock_bounded():
    # The capture helper must route through the bounded runner, never a bare ssh.
    assert "function Invoke-LabBoundedCommand" in COMMON
    assert "$r = Invoke-LabBoundedCommand -FilePath 'ssh'" in COMMON
    assert "$startInfo.RedirectStandardOutput = $true" in COMMON
    assert "$startInfo.RedirectStandardError = $true" in COMMON
    # A hard bound that actually waits, then kills the tree on expiry.
    assert "if (-not $process.WaitForExit(($TimeoutSeconds * 1000)))" in COMMON
    assert "$process.Kill($true)" in COMMON
    # A timeout must be a truthful failure, never a silent pass.
    assert "$code = if ($timedOut) { 124 } else { $process.ExitCode }" in COMMON
    assert "timed_out" in COMMON
    # The remote side is bounded too, so a killed client cannot orphan a Slurm
    # allocation that stays PENDING on the controller.
    assert "base64 -d | timeout -k 5" in COMMON
    # Unbounded `& ssh` must not remain anywhere in the shared helper.
    assert "& ssh @args" not in COMMON


def test_lab_timeouts_are_configured_with_safe_fallbacks():
    assert CONFIG["timeouts"]["command_seconds"] > 0
    assert CONFIG["timeouts"]["allocation_seconds"] >= CONFIG["timeouts"]["command_seconds"]
    assert "return 180" in COMMON
    assert "return 300" in COMMON
    # The allocation-bound gates get the longer budget, passed by name so the
    # override is actually bound (a positional override after a [switch] is not).
    assert "$allocationTimeout = Get-LabAllocationTimeoutSeconds" in LAB_TEST
    assert LAB_TEST.count("-TimeoutSeconds $allocationTimeout") == 3


def test_argument_requoting_survives_spaces_quotes_and_empty():
    # ssh.exe is a CommandLineToArgvW consumer, so the argument vector must be
    # re-quoted deterministically instead of relying on PowerShell array joining.
    assert "function ConvertTo-LabProcessArguments" in COMMON
    # Backslashes are doubled before an embedded quote, and trailing backslashes
    # are doubled before the closing quote (the CommandLineToArgvW rules).
    assert r"""-replace '(\\*)"', '$1$1\"'""" in COMMON
    assert r"""-replace '(\\+)$', '$1$1'""" in COMMON


BOUNDED_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
. (Join-Path $env:LOCAL_REAL_TEST_LAB_DIR 'lab-common.ps1')
$out = [IO.Path]::GetTempFileName()
$err = [IO.Path]::GetTempFileName()
$py  = $env:LOCAL_REAL_TEST_PYTHON

# 1. A child that would run ~29s is terminated at a 3s bound.
$sw = [Diagnostics.Stopwatch]::StartNew()
$r1 = Invoke-LabBoundedCommand -FilePath 'ping.exe' -ArgumentList @('-n','30','127.0.0.1') -StdoutPath $out -StderrPath $err -TimeoutSeconds 3
$sw.Stop()

# 2. A fast child still succeeds with its real output.
$r2 = Invoke-LabBoundedCommand -FilePath 'cmd.exe' -ArgumentList @('/c','echo LOCAL_REAL_BOUND_OK') -StdoutPath $out -StderrPath $err -TimeoutSeconds 60

# 3. Argument vector round-trips through the Windows quoting rules.
$r3 = Invoke-LabBoundedCommand -FilePath $py -ArgumentList @('-c','import json,sys;print(json.dumps(sys.argv[1:]))','plain','a b c d','has"quote','') -StdoutPath $out -StderrPath $err -TimeoutSeconds 60

# 4. A zero/negative bound is coerced to the default, never treated as "unbounded".
$r4 = Invoke-LabBoundedCommand -FilePath 'ping.exe' -ArgumentList @('-n','6','127.0.0.1') -StdoutPath $out -StderrPath $err -TimeoutSeconds 0
Remove-Item $out,$err -Force -ErrorAction SilentlyContinue

[pscustomobject]@{
  slow_timed_out    = $r1.timed_out
  slow_exit         = $r1.exit_code
  slow_elapsed      = [math]::Round($sw.Elapsed.TotalSeconds,1)
  slow_stderr       = $r1.stderr
  fast_timed_out    = $r2.timed_out
  fast_exit         = $r2.exit_code
  fast_output       = $r2.output.Trim()
  argv_exit         = $r3.exit_code
  argv              = $r3.output.Trim()
  zero_bound        = $r4.timeout_seconds
} | ConvertTo-Json -Compress
"""


@pytest.mark.subprocess
def test_bounded_command_terminates_and_preserves_normal_behaviour(tmp_path):
    shell = _powershell()
    if not shell:
        pytest.skip("no PowerShell available to exercise the lab bounded runner")

    script = tmp_path / "bounded.ps1"
    script.write_text(BOUNDED_SCRIPT, encoding="utf-8")

    completed = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
        ],
        cwd=str(ROOT / "lab"),
        capture_output=True,
        text=True,
        timeout=180,
        env={
            **os.environ,
            "LOCAL_REAL_TEST_PYTHON": sys.executable,
            "LOCAL_REAL_TEST_LAB_DIR": str(ROOT / "lab"),
        },
    )
    assert completed.returncode == 0, (
        f"bounded runner script failed ({completed.returncode}):\n"
        f"stdout={completed.stdout}\nstderr={completed.stderr}"
    )
    report = json.loads(completed.stdout.strip().splitlines()[-1])

    # A non-completing child is terminated at the bound, reported as a failure.
    assert report["slow_timed_out"] is True
    assert report["slow_exit"] == 124
    assert report["slow_elapsed"] < 25
    assert "wall-clock bound" in report["slow_stderr"]

    # A normal child is unaffected by the hardening.
    assert report["fast_timed_out"] is False
    assert report["fast_exit"] == 0
    assert report["fast_output"] == "LOCAL_REAL_BOUND_OK"

    # Spaces, embedded quotes and an empty argument all survive re-quoting.
    assert report["argv_exit"] == 0
    assert json.loads(report["argv"]) == ["plain", "a b c d", 'has"quote', ""]

    # A zero bound is coerced to the default rather than silently unbounded.
    assert report["zero_bound"] == 180
