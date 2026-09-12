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
import os
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
    "tests/test_remote_directory_listing.py",
)


def _wx_test_files() -> tuple[str, ...]:
    """Keep wx and Qt native toolkit lifetimes in separate pytest processes."""
    files = []
    for path in sorted((REPO_ROOT / "tests").glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        if (
            ("import wx" in source or 'importorskip("wx")' in source)
            and ("def test_" in source or "unittest.TestCase" in source)
        ):
            files.append(path.relative_to(REPO_ROOT).as_posix())
    return tuple(files)

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
    wx_files = _wx_test_files()
    ignores = tuple(
        argument
        for path in (*ISOLATED_WIRE_FILES, *wx_files)
        for argument in ("--ignore", path)
    )
    commands.append(
        PYTEST_BASE + ignores + (COVERAGE_ARGS if coverage else ())
    )
    if wx_files:
        for path in wx_files:
            commands.append(
                PYTEST_BASE[:-1]
                + (path,)
                + (COVERAGE_APPEND_ARGS if coverage else ())
            )
    for index, path in enumerate(ISOLATED_WIRE_FILES):
        coverage_args = COVERAGE_APPEND_ARGS if coverage else ()
        if coverage and index == len(ISOLATED_WIRE_FILES) - 1:
            coverage_args += (f"--cov-fail-under={COVERAGE_FAIL_UNDER}",)
        commands.append(PYTEST_BASE[:-1] + (path,) + coverage_args)
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="add the CI coverage gate flags to the pytest invocation",
    )
    args = parser.parse_args(argv)

    for command in build_commands(coverage=args.coverage):
        printable = " ".join(str(part) for part in command)
        print(f"[release-test-suite] {printable}", flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT, env=_test_environment())
        if result.returncode:
            print(
                f"[release-test-suite] FAILED with exit code {result.returncode}: {printable}",
                file=sys.stderr,
            )
            return result.returncode
    print("[release-test-suite] all release preflight gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
