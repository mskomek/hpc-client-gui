"""Run the shared release preflight test suite.

The manual release workflow and local release gate use this same test
definition, so a release cannot be published when its required suite is red.

The suite mirrors the CI gates:

    * source compilation;
    * i18n drift gate;
    * headless smoke test;
    * the normal non-packaging pytest suite (``-m "not packaging"``).

Usage:
    python scripts/release_test_suite.py [--coverage]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Keep these checks aligned with the local release gate in scripts/ci.py.
PREFLIGHT_COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "compileall", "-q", str(REPO_ROOT / "src" / "hpc_gui")),
    (sys.executable, str(REPO_ROOT / "scripts" / "check_i18n.py")),
    (sys.executable, str(REPO_ROOT / "scripts" / "smoke_test.py")),
)

PYTEST_BASE = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "--tb=short",
    "-rf",
    "-m",
    "not packaging",
    "tests",
)

# Wire-heavy suites spawn real socket/paramiko worker threads that outlive
# their test module inside one interpreter. The Qt editor flow also shares a
# process with wx tests, which can trigger a native toolkit teardown failure.
# Running these files in dedicated pytest processes keeps those boundaries
# isolated. Every gate below still applies to every file: nothing is skipped
# or weakened.
ISOLATED_WIRE_FILES = (
    "tests/test_ftp_widget.py",
    "tests/test_download_cancel_wire.py",
    "tests/test_editor_flow.py",
    "tests/test_remote_directory_listing.py",
)
# When combined in one process, these wx modules create and tear down a real
# wx.App before the Qt Jobs-scroll widget; the sequence terminates Windows
# with 0xC000041D despite no live wx windows or worker threads. The WebView2
# module passes alone but heap-corrupts (0xC0000374) after mixed-GUI tests,
# and the wx Jobs cluster terminated the broad process near 90% with exit
# 0xFFFFFFFF. Destroying or garbage-collecting one of several wx.App objects
# in a single process invalidates the global app, so the Jobs behavior and
# layout owner nodes fail with PyNoAppError only in broad order. Keep every
# proven native boundary process-scoped; every node below still runs in a
# dedicated pytest process instead of being skipped.
ISOLATED_NATIVE_GUI_FILES = (
    "tests/test_corrective_jobs_details.py",
    "tests/test_wx_terminal_webview.py",
    "tests/test_wx_jobs_behavior.py",
    "tests/test_wx_layout_resize.py",
    "tests/test_wx_jobs_files_outputs.py",
    "tests/test_wx_jobs_final_fix.py",
    "tests/test_wx_jobs_stress.py",
)
ISOLATED_TEST_NODES = (
    "tests/test_wx_file_actions_stress.py::test_wx_remote_context_target_stress_uses_real_events",
    "tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths",
)
ISOLATED_FILES = ISOLATED_WIRE_FILES + ISOLATED_NATIVE_GUI_FILES


COVERAGE_FAIL_UNDER = 65

COVERAGE_ARGS = (
    "--cov=hpc_gui",
    "--cov-report=term",
    "--cov-report=json:coverage.json",
    "--cov-report=xml:coverage.xml",
)

COVERAGE_APPEND_ARGS = (
    "--cov=hpc_gui",
    "--cov-append",
    "--cov-report=term",
    "--cov-report=json:coverage.json",
    "--cov-report=xml:coverage.xml",
)


def _test_environment() -> dict[str, str]:
    """Keep Qt tests headless without changing the caller's environment."""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    return environment


def build_commands(*, coverage: bool) -> list[tuple[str, ...]]:
    commands = list(PREFLIGHT_COMMANDS)
    ignores = tuple(
        argument
        for path in ISOLATED_FILES
        for argument in ("--ignore", path)
    )
    deselects = tuple(
        argument
        for nodeid in ISOLATED_TEST_NODES
        for argument in ("--deselect", nodeid)
    )
    commands.append(
        PYTEST_BASE + ignores + deselects + (COVERAGE_ARGS if coverage else ())
    )
    isolated_selectors = (
        *ISOLATED_TEST_NODES,
        *ISOLATED_NATIVE_GUI_FILES,
        *ISOLATED_WIRE_FILES,
    )
    for index, selector in enumerate(isolated_selectors):
        coverage_args = COVERAGE_APPEND_ARGS if coverage else ()
        if coverage and index == len(isolated_selectors) - 1:
            coverage_args += (f"--cov-fail-under={COVERAGE_FAIL_UNDER}",)
        commands.append(PYTEST_BASE[:-1] + (selector,) + coverage_args)
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="add the CI coverage gate flags to the pytest invocation",
    )
    args = parser.parse_args(argv)

    failed_test_partition = 0
    for index, command in enumerate(build_commands(coverage=args.coverage)):
        printable = " ".join(str(part) for part in command)
        print(f"[release-test-suite] {printable}", flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT, env=_test_environment())
        if result.returncode:
            print(
                f"[release-test-suite] FAILED with exit code {result.returncode}: {printable}",
                file=sys.stderr,
            )
            if index < len(PREFLIGHT_COMMANDS):
                return result.returncode
            if not failed_test_partition:
                failed_test_partition = result.returncode
    if failed_test_partition:
        return failed_test_partition
    print("[release-test-suite] all release preflight gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
