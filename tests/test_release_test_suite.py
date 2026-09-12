import unittest

from scripts.release_test_suite import build_commands


class ReleaseTestSuiteTests(unittest.TestCase):
    def test_coverage_commands_are_flat_argument_lists(self):
        commands = build_commands(coverage=True)

        self.assertTrue(all(isinstance(argument, str) for command in commands for argument in command))
        self.assertIn("--cov=hpc_gui", commands[-2])
        self.assertIn("--cov-append", commands[-1])
        self.assertNotIn("--cov-fail-under=65", commands[-2])
        self.assertIn("--cov-fail-under=65", commands[-1])

    def test_toolkit_boundary_suite_isolated_without_skipping_it(self):
        commands = build_commands(coverage=False)
        self.assertTrue(
            any("tests/test_editor_flow.py" in command for command in commands)
        )
        self.assertTrue(any("--ignore" in command for command in commands))
        self.assertTrue(
            any("tests/test_wx_terminal_webview.py" in command for command in commands)
        )
        editor_command = next(
            command for command in commands if command[-1] == "tests/test_editor_flow.py"
        )
        self.assertNotIn("--ignore", editor_command)


if __name__ == "__main__":
    unittest.main()
