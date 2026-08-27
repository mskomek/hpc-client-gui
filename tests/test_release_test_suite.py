import unittest

from scripts.release_test_suite import build_commands


class ReleaseTestSuiteTests(unittest.TestCase):
    def test_coverage_commands_are_flat_argument_lists(self):
        commands = build_commands(coverage=True)

        self.assertTrue(all(isinstance(argument, str) for command in commands for argument in command))
        self.assertIn("--cov=hpc_gui", commands[-2])
        self.assertIn("--cov-append", commands[-1])


if __name__ == "__main__":
    unittest.main()
