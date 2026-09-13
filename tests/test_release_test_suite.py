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
        corrective_module = "tests/test_corrective_jobs_details.py"
        self.assertEqual(ISOLATED_TEST_NODES, (webview_node,))
        self.assertEqual(ISOLATED_GUI_FILES, (corrective_module,))
        self.assertIn("--deselect", commands[3])
        self.assertIn(webview_node, commands[3])
        self.assertEqual(commands[4][-1], webview_node)
        self.assertNotIn("--deselect", commands[4])
        self.assertIn("--ignore", commands[3])
        self.assertIn(corrective_module, commands[3])
        self.assertEqual(commands[5][-1], corrective_module)
        self.assertNotIn("--deselect", commands[5])
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
