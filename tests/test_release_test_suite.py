from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.release_test_suite import (
    ISOLATED_NATIVE_GUI_FILES,
    ISOLATED_TEST_NODES,
    ISOLATED_WIRE_FILES,
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
        broad = next(command for command in commands if "--ignore" in command)
        self.assertIn("--deselect", broad)
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
