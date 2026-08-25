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
)

# Wire-heavy suites spawn real socket/paramiko worker threads that outlive
# their test module inside one interpreter. Running them in dedicated
# pytest processes keeps those daemon threads from colliding with later
# GUI/socket tests (observed as a native segfault mid-suite in CI). Every
# gate below still applies to every file: nothing is skipped or weakened.
ISOLATED_WIRE_FILES = (
    "tests/test_ftp_widget.py",
    "tests/test_download_cancel_wire.py",
)

COVERAGE_ARGS = (
    "--cov=hpc_gui",
    "--cov-report=term",
    "--cov-report=json:coverage.json",
    "--cov-report=xml:coverage.xml",
    "--cov-fail-under=65",
)

COVERAGE_APPEND_ARGS = (
    "--cov=hpc_gui",
    "--cov-append",
    "--cov-report=term",
    "--cov-report=json:coverage.json",
    "--cov-report=xml:coverage.xml",
    "--cov-fail-under=65",
)


def build_commands(*, coverage: bool) -> list[tuple[str, ...]]:
    commands = list(PREFLIGHT_COMMANDS)
    ignores = tuple(
        argument
        for path in ISOLATED_WIRE_FILES
        for argument in ("--ignore", path)
    )
    commands.append(
        PYTEST_BASE + ignores + ((COVERAGE_ARGS,) if coverage else ())
    )
    commands.append(
        PYTEST_BASE + ISOLATED_WIRE_FILES + ((COVERAGE_APPEND_ARGS,) if coverage else ())
    )
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
        result = subprocess.run(command, cwd=REPO_ROOT)
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
