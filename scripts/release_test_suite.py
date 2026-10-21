"""Run the shared release preflight test suite.

The manual release workflow and local release gate use this same test
definition, so a release cannot be published when its required suite is red.

The suite mirrors the CI gates:

    * source compilation;
    * i18n drift gate;
    * headless smoke test;
    * source/test contracts (excluding package and supplied-evidence gates).

Usage:
    python scripts/release_test_suite.py [--coverage]
"""

from __future__ import annotations

import argparse
import os
import site
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if __package__:
    from .native_gui_test_files import discover_native_gui_test_files
else:
    from native_gui_test_files import discover_native_gui_test_files

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
    "not packaging and not artifact_dependent",
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
# Bundle replacement is a Windows filesystem resource boundary. When it runs
# in the broad process after unrelated temp-directory stress, Windows can
# transiently deny the staged-directory rename; the same test passes alone.
ISOLATED_FILESYSTEM_FILES = ("tests/test_updater_helper.py",)
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
# Transfer cancellation pumps Qt events while its worker and process-queue
# state is shutting down; mixed GUI runs triggered a Windows native crash,
# while the module passes in its own process.
_KNOWN_NATIVE_GUI_FILES = (
    # W19 GUI fixtures pump wx.Yield() while neighboring mixed-GUI tests can
    # still own deferred WebView-backed native deletes. The combined process
    # hit a Windows access violation in that teardown; isolate the GUI files.
    "tests/test_w19_connection_gui.py",
    "tests/test_w19_connection_shell.py",
    "tests/test_w15_fresh_user_startup.py",
    "tests/test_wx_w55_shell_soak.py",
    "tests/test_wx_file_list_zebra.py",
    # Column-click tests dispatch native list-control events; mixed wx test
    # teardown corrupted this control's state on Windows.
    "tests/test_remote_dir_panel_sorting.py",
    # Qt offscreen rendering collides with wx native teardown in the combined
    # Windows process; run the synthetic benchmark in its own process.
    "tests/test_remote_directory_gui_benchmark.py",
    # Startup window resize tests instantiate wx frames; combining them with
    # prior SSH/WebView fixtures triggers Windows native teardown failures.
    "tests/test_startup_changelog.py",
    # Transfer dialog callbacks touch Qt widgets from executor threads; mixed
    # toolkit teardown crashed the combined process in this invariant test.
    "tests/test_transfer_key_release.py",
    # Concurrent transfer UI callbacks cross native GUI/worker boundaries;
    # the module is stable alone but crashes after mixed toolkit tests.
    "tests/test_transfer_performance_scenarios.py",
    # Transfer-activity selection dispatches GUI events and must not share the
    # interpreter's native event loop with earlier wx/Qt tests on Windows.
    "tests/test_transfer_tab_selection.py",
    "tests/test_corrective_jobs_details.py",
    "tests/test_jobs_outputs_scroll.py",
    "tests/test_local_dir_panel.py",
    "tests/test_lssrv_auto_refresh.py",
    "tests/test_wx_file_actions_stress.py",
    "tests/test_transfer_cancel_recovery.py",
    "tests/test_wx_terminal_webview_bridge.py",
    "tests/test_wx_terminal_webview_input.py",
    "tests/test_wx_terminal_webview_lifecycle.py",
    "tests/test_wx_terminal_webview_output.py",
    "tests/test_wx_terminal_webview_readback.py",
    "tests/test_wx_jobs_behavior.py",
    "tests/test_wx_layout_resize.py",
    "tests/test_wx_jobs_files_outputs.py",
    "tests/test_wx_jobs_final_fix.py",
    "tests/test_wx_jobs_stress.py",
    # The accordion fixture creates a wx App while mixed GUI tests may leave
    # deferred native windows pending teardown on Windows.
    "tests/test_remote_accordion.py",
    # Plugin manager refresh tests own native wx timers; mixed GUI execution
    # terminated Windows while one of those timers was being asserted.
    "tests/test_plugin_manager_ui.py",
    # The performance probe exercises the Qt event loop and can tear down
    # native GUI state owned by neighboring mixed-toolkit tests on Windows.
    "tests/test_performance_probe.py",
)
ISOLATED_NATIVE_GUI_FILES = tuple(dict.fromkeys((
    *_KNOWN_NATIVE_GUI_FILES,
    *discover_native_gui_test_files(REPO_ROOT / "tests"),
)))
ISOLATED_TEST_NODES = (
    "tests/test_wx_terminal_interaction.py::test_header_status_identity_dimensions",
    "tests/test_wx_file_actions_stress.py::test_wx_remote_context_target_stress_uses_real_events",
    "tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths",
)
ISOLATED_FILES = tuple(
    dict.fromkeys(
        (*ISOLATED_WIRE_FILES, *ISOLATED_FILESYSTEM_FILES, *ISOLATED_NATIVE_GUI_FILES)
    )
)
ISOLATED_NODE_SELECTORS = tuple(
    nodeid
    for nodeid in ISOLATED_TEST_NODES
    if nodeid.split("::", 1)[0] not in ISOLATED_FILES
)
EVIDENCE_GATED_TESTS = {
    "tests/test_w04_support_freeze.py": "artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md",
    "tests/test_w04_menu_actions.py": "artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md",
    "tests/test_w04_file_actions.py": "artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md",
    "tests/test_w04_about_packaging.py": "artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md",
}


COVERAGE_FAIL_UNDER = 65
_TEST_CONFIG_ROOT: str | None = None

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
    """Redirect per-user test state into a temporary home and keep Qt headless."""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    # APPDATA is redirected below to isolate the application's settings, but
    # Python also derives its user-site package directory from APPDATA on
    # Windows. Preserve the existing user base so installed test extras remain
    # importable in child pytest processes.
    user_base = site.getuserbase()
    if user_base and not environment.get("PYTHONUSERBASE"):
        environment["PYTHONUSERBASE"] = user_base
    if _TEST_CONFIG_ROOT:
        environment.pop("HPC_GUI_CONFIG_ROOT", None)
        environment["HOME"] = _TEST_CONFIG_ROOT
        environment["USERPROFILE"] = _TEST_CONFIG_ROOT
        environment["APPDATA"] = str(Path(_TEST_CONFIG_ROOT) / "AppData" / "Roaming")
        environment["LOCALAPPDATA"] = str(
            Path(_TEST_CONFIG_ROOT) / "AppData" / "Local"
        )
        environment["XDG_CONFIG_HOME"] = str(Path(_TEST_CONFIG_ROOT) / ".config")
        environment["XDG_DATA_HOME"] = str(Path(_TEST_CONFIG_ROOT) / ".local" / "share")
    return environment


def build_commands(*, coverage: bool) -> list[tuple[str, ...]]:
    commands = list(PREFLIGHT_COMMANDS)
    ignores = tuple(
        argument
        for path in ISOLATED_FILES
        for argument in ("--ignore", path)
    )
    blocked_paths = tuple(
        path
        for path, prerequisite in EVIDENCE_GATED_TESTS.items()
        if not (REPO_ROOT / prerequisite).is_file()
    )
    evidence_ignores = tuple(
        argument for path in blocked_paths for argument in ("--ignore", path)
    )
    deselects = tuple(
        argument
        for nodeid in ISOLATED_NODE_SELECTORS
        for argument in ("--deselect", nodeid)
    )
    commands.append(
        PYTEST_BASE + ignores + evidence_ignores + deselects + (COVERAGE_ARGS if coverage else ())
    )
    runnable_isolated_files = tuple(
        path for path in ISOLATED_FILES if path not in blocked_paths
    )
    isolated_selectors = (*ISOLATED_NODE_SELECTORS, *runnable_isolated_files)
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

    for test_path, prerequisite in EVIDENCE_GATED_TESTS.items():
        if not (REPO_ROOT / prerequisite).is_file():
            print(
                f"[release-test-suite] BLOCKED evidence prerequisite missing: {prerequisite} ({test_path})",
                flush=True,
            )

    global _TEST_CONFIG_ROOT
    temp_root = REPO_ROOT / ".tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    failed_test_partition = 0
    with tempfile.TemporaryDirectory(
        prefix="release-test-config-", dir=temp_root
    ) as isolated_config_root:
        _TEST_CONFIG_ROOT = isolated_config_root
        try:
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
        finally:
            _TEST_CONFIG_ROOT = None
    if failed_test_partition:
        return failed_test_partition
    print("[release-test-suite] all release preflight gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
