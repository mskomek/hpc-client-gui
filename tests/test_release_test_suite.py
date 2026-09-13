import unittest

import pytest

from scripts.release_test_suite import build_commands


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
        for path in (
            "tests/test_editor_flow.py",
            "tests/test_corrective_jobs_details.py",
            "tests/test_wx_terminal_webview.py",
        ):
            self.assertIn(path, broad)
            isolated = [
                command for command in commands
                if path in command and "--ignore" not in command
            ]
            self.assertEqual(len(isolated), 1)
            self.assertNotIn("--ignore", isolated[0])


if __name__ == "__main__":
    unittest.main()
