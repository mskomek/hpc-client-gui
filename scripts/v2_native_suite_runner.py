"""Evidence-only subprocess runner for F-03/F-04 native pytest investigation.

One process for each requested group; no test edits, skipped-result promotion,
forced app exits, remote hosts or release actions. A timeout kills only the
process group this runner created. Returns nonzero unless the JUnit is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
_LAST_TEST = re.compile(r"^tests[/\\].+::test_[^\\r\\n]*", re.MULTILINE)


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def _stop_owned_tree(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        # taskkill is scoped to the child PID, including descendants.
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=20, check=False,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.wait(timeout=5)


def _junit_receipt(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        return {"complete": False, "reason": "NO_FINAL_JUNIT"}
    try:
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        if not suites:
            return {"complete": False, "reason": "MISSING_TESTSUITE"}
        totals = {
            key: sum(int(suite.get(key, "0")) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        # testsuites may include aggregate parent with child suite elements;
        # pytest emits one flat testsuite, but reject nested double-counting.
        if any(child.tag == "testsuite" for suite in suites for child in suite):
            return {"complete": False, "reason": "NESTED_SUITES_UNSUPPORTED"}
        return {"complete": totals["tests"] > 0, "counts": totals}
    except (OSError, ValueError, ET.ParseError) as exc:
        return {"complete": False, "reason": type(exc).__name__}


def run(label: str, output: Path, seconds: int, selections: list[str]) -> int:
    output.mkdir(parents=True, exist_ok=True)
    log = output / f"{label}.stdout.log"
    junit = output / f"{label}.junit.xml"
    command = [
        sys.executable, "-X", "faulthandler", "-m", "pytest",
        "-vv", "--tb=short", "--maxfail=1",
        f"--junitxml={junit}", *selections,
    ]
    env = os.environ.copy()
    env.setdefault("HPC_GUI_DISABLE_WEBENGINE", "1")
    env["PYTHONFAULTHANDLER"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    started = time.monotonic()
    timed_out = False
    rc: int | None = None
    with log.open("wb") as stdout:
        try:
            proc = subprocess.Popen(
                command, cwd=ROOT, env=env, stdout=stdout,
                stderr=subprocess.STDOUT,
                start_new_session=(os.name != "nt"),
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                ),
            )
            try:
                rc = proc.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _stop_owned_tree(proc)
                rc = proc.poll()
        except OSError as exc:
            stdout.write(f"LAUNCH_FAILED:{type(exc).__name__}\\n".encode("utf-8"))
    duration = round(time.monotonic() - started, 2)
    raw = log.read_bytes()
    contents = raw.decode("utf-8", errors="replace")
    junit_receipt = _junit_receipt(junit)
    if timed_out:
        status = "TIMEOUT"
    elif rc is not None and rc < 0:
        status = "NATIVE_SIGNAL"
    elif rc in (133, 3221225477, 3221226505, 3221225725):
        status = "ABNORMAL_EXIT"
    elif rc == 0 and junit_receipt["complete"]:
        status = "PASS" if junit_receipt["counts"]["skipped"] == 0 else "PASS_WITH_SKIPS"
    else:
        status = "FAIL_OR_INCOMPLETE"
    receipt = {
        "schema": "v2-f03-f04-native-pytest/1",
        "status": status,
        "source_sha": _git_sha(),
        "label": label,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "selections": selections,
        "elapsed_seconds": duration,
        "timeout_seconds": seconds,
        "timed_out": timed_out,
        "returncode": rc,
        "returncode_unsigned_32": None if rc is None else rc & 0xFFFFFFFF,
        "log_sha256": hashlib.sha256(raw).hexdigest(),
        "junit": junit_receipt,
        "last_started_tests": _LAST_TEST.findall(contents)[-8:],
    }
    path = output / f"{label}.receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
    # Skips must not be misreported as native acceptance, but they are
    # legitimate for collection-only and platform-guarded tests.
    return 0 if status in {"PASS", "PASS_WITH_SKIPS"} else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=360)
    parser.add_argument("pytest_selections", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,48}", args.label):
        parser.error("unsafe label")
    if not 30 <= args.timeout_seconds <= 900:
        parser.error("timeout must be 30..900 seconds")
    selections = args.pytest_selections
    if selections and selections[0] == "--":
        selections = selections[1:]
    if not selections:
        parser.error("pass a test path or --collect-only")
    return run(args.label, args.output, args.timeout_seconds, selections)


if __name__ == "__main__":
    raise SystemExit(main())
