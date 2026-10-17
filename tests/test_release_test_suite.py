from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.release_test_suite import (
    ISOLATED_NATIVE_GUI_FILES,
    ISOLATED_TEST_NODES,
    ISOLATED_WIRE_FILES,
    EVIDENCE_GATED_TESTS,
    PREFLIGHT_COMMANDS,
    build_commands,
    main,
)


class ReleaseTestSuiteTests(unittest.TestCase):
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_coverage_commands_are_flat_argument_lists(self):
        commands = build_commands(coverage=True)

        self.assertTrue(all(isinstance(argument, str) for command in commands for argument in command))
        pytest_commands = [command for command in commands if "-m" in command and "pytest" in command]
        self.assertTrue(all("--cov=hpc_gui" in command for command in pytest_commands))
        self.assertTrue(all("--cov-append" in command for command in pytest_commands[1:]))
        self.assertTrue(all("--cov-fail-under=65" not in command for command in pytest_commands[:-1]))
        self.assertIn("--cov-fail-under=65", commands[-1])

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_native_toolkit_boundary_suites_are_isolated_without_skipping_them(self):
        commands = build_commands(coverage=False)
        self.assertEqual(
            ISOLATED_NATIVE_GUI_FILES,
            (
                "tests/test_w19_connection_gui.py",
                "tests/test_w19_connection_shell.py",
                "tests/test_w15_fresh_user_startup.py",
                "tests/test_wx_w55_shell_soak.py",
                "tests/test_wx_file_list_zebra.py",
                "tests/test_corrective_jobs_details.py",
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
            ),
        )
        broad = next(command for command in commands if "--ignore" in command)
        self.assertIn("--deselect", broad)
        for path, prerequisite in EVIDENCE_GATED_TESTS.items():
            if not (Path(__file__).resolve().parents[1] / prerequisite).is_file():
                self.assertIn(path, broad)
        for nodeid in ISOLATED_TEST_NODES:
            self.assertIn(nodeid, broad)
        for path in (*ISOLATED_WIRE_FILES, *ISOLATED_NATIVE_GUI_FILES):
            self.assertIn(path, broad)
            isolated = [
                command for command in commands
                if path in command and "--ignore" not in command
            ]
            self.assertEqual(len(isolated), 1)
            self.assertNotIn("--deselect", isolated[0])
            self.assertEqual(isolated[0][-1], path)
        for index, nodeid in enumerate(
            ISOLATED_TEST_NODES, start=len(PREFLIGHT_COMMANDS) + 1
        ):
            self.assertEqual(commands[index][-1], nodeid)
            self.assertNotIn("--deselect", commands[index])
        self.assertIn(ISOLATED_WIRE_FILES[-1], commands[-1])
        self.assertNotIn("--ignore", commands[-1])

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_runner_finishes_other_pytest_partitions_after_failure(self):
        commands = build_commands(coverage=False)
        statuses = [0] * len(commands)
        statuses[len(PREFLIGHT_COMMANDS)] = 1
        run = Mock(
            side_effect=(SimpleNamespace(returncode=status) for status in statuses)
        )

        with (
            patch("scripts.release_test_suite.subprocess.run", run),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main([])

        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, len(commands))


if __name__ == "__main__":
    unittest.main()
