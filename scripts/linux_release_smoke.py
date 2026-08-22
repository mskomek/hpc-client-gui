"""Linux packaged artifact smoke gate.

Runs against a packaged Linux build produced by scripts/release_linux.py on
the CI baseline:

    python scripts/linux_release_smoke.py --binary <path-to-binary>

It asserts the packaged CLI surface (--help, version, doctor environment) and
optional offscreen GUI startup/shutdown.  It never touches a real cluster and
never publishes anything.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _run(binary: Path, args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(binary), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def _require(proc: subprocess.CompletedProcess, label: str) -> None:
    if proc.returncode != 0:
        print(f"linux smoke: {label} FAILED (exit {proc.returncode})")
        print("stdout:", proc.stdout[-2000:])
        print("stderr:", proc.stderr[-2000:])
        raise SmokeFailure(label)


class SmokeFailure(Exception):
    """Raised internally so main() can return a clean exit code."""


def _assert_content(proc: subprocess.CompletedProcess, needle: str, label: str) -> None:
    combined = f"{proc.stdout}\n{proc.stderr}"
    if needle not in combined:
        print(f"linux smoke: {label} missing expected text {needle!r}")
        print(combined[-2000:])
        raise SmokeFailure(label)
    print(f"linux smoke: {label} OK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linux_release_smoke")
    parser.add_argument("--binary", required=True, help="Path to the packaged Linux binary.")
    parser.add_argument("--gui", action="store_true", help="Also start the packaged GUI offscreen and shut it down.")
    args = parser.parse_args(argv)

    binary = Path(args.binary).resolve()
    if not binary.is_file():
        print(f"linux smoke: binary not found: {binary}")
        return 1
    if not os.access(binary, os.X_OK):
        print(f"linux smoke: binary is not executable: {binary}")
        return 1

    try:
        _require(_run(binary, ["--help"]), "--help")
        version = _run(binary, ["version"])
        _require(version, "version")
        _assert_content(version, "hpc-client-gui", "version text")
        doctor = _run(binary, ["doctor", "environment"])
        _require(doctor, "doctor environment")
        _assert_content(doctor, "config_dir", "doctor config_dir")

        if args.gui:
            proc = subprocess.Popen(
                [str(binary)],
                env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                proc.wait(timeout=20)
                print("linux smoke: GUI exited during startup smoke (expected failure captured)")
                out, err = proc.communicate()
                print("stdout:", out[-2000:])
                print("stderr:", err[-2000:])
                return 1
            except subprocess.TimeoutExpired:
                print("linux smoke: GUI startup OK (still running after 20s)")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
    except SmokeFailure:
        return 1

    print("linux smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
