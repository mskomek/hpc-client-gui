"""Run the shared release preflight test suite.

The release workflow and the CI ``gui`` job must never drift apart: a
release must not be publishable when the source revision's required test
suite is red. This module is the single definition of that suite; both
workflows invoke it instead of maintaining two separate test lists.

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
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Keep this list identical to the checks the CI gui job runs. When adding a
# new repository-wide gate, extend it here so releases inherit it.
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
)
ISOLATED_GUI_FILES = ("tests/test_corrective_jobs_details.py",)
# Keep the real WebView navigation behavior test but isolate its native state;
# Windows recorded process heap corruption when it ran after the broad GUI set.
ISOLATED_TEST_NODES = (
    "tests/test_wx_terminal_webview.py::test_wx_terminal_external_navigation_blocked",
)

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


def build_commands(*, coverage: bool) -> list[tuple[str, ...]]:
    commands = list(PREFLIGHT_COMMANDS)
    ignores = tuple(
        argument
        for path in (*ISOLATED_WIRE_FILES, *ISOLATED_GUI_FILES)
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
        *ISOLATED_GUI_FILES,
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
        result = subprocess.run(command, cwd=REPO_ROOT)
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
