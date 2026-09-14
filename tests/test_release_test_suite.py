from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.release_test_suite import (
    ISOLATED_GUI_FILES,
    ISOLATED_TEST_NODES,
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
        self.assertIn("--cov=hpc_gui", commands[-2])
        self.assertIn("--cov-append", commands[-1])
        self.assertNotIn("--cov-fail-under=65", commands[-2])
        self.assertIn("--cov-fail-under=65", commands[-1])

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_toolkit_boundary_suite_isolated_without_skipping_it(self):
        commands = build_commands(coverage=False)
        webview_node = (
            "tests/test_wx_terminal_webview.py::"
            "test_wx_terminal_external_navigation_blocked"
        )
        remote_context_node = (
            "tests/test_wx_file_actions_stress.py::"
            "test_wx_remote_context_target_stress_uses_real_events"
        )
        shell_stress_node = (
            "tests/test_wx_shell_p0_stress.py::"
            "test_wx_shell_p0_stress_real_wx_paths"
        )
        corrective_module = "tests/test_corrective_jobs_details.py"
        jobs_modules = (
            "tests/test_wx_jobs_files_outputs.py",
            "tests/test_wx_jobs_final_fix.py",
            "tests/test_wx_jobs_stress.py",
        )
        isolated_nodes = (webview_node, remote_context_node, shell_stress_node)
        self.assertEqual(ISOLATED_TEST_NODES, isolated_nodes)
        self.assertEqual(ISOLATED_GUI_FILES, (corrective_module, *jobs_modules))
        self.assertIn("--deselect", commands[3])
        for index, nodeid in enumerate(isolated_nodes, start=4):
            self.assertIn(nodeid, commands[3])
            self.assertEqual(commands[index][-1], nodeid)
            self.assertNotIn("--deselect", commands[index])
        self.assertIn("--ignore", commands[3])
        self.assertIn(corrective_module, commands[3])
        self.assertEqual(commands[7][-1], corrective_module)
        self.assertNotIn("--deselect", commands[7])
        for index, module in enumerate(jobs_modules, start=8):
            self.assertIn(module, commands[3])
            self.assertEqual(commands[index][-1], module)
        self.assertIn("tests/test_editor_flow.py", commands[-1])
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
