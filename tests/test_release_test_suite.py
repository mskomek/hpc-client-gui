from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.release_test_suite import (
    ISOLATED_FILES,
    ISOLATED_NATIVE_GUI_FILES,
    ISOLATED_TEST_NODES,
    EVIDENCE_GATED_TESTS,
    PREFLIGHT_COMMANDS,
    build_commands,
    main,
)
from scripts.native_gui_test_files import discover_native_gui_test_files


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
        required_boundaries = {
            "tests/test_wx_jobs_behavior.py",
            "tests/test_wx_jobs_files_outputs.py",
            "tests/test_wx_terminal_webview_lifecycle.py",
            "tests/test_remote_accordion.py",
            "tests/test_startup_changelog.py",
            "tests/test_transfer_performance_scenarios.py",
        }
        self.assertTrue(required_boundaries.issubset(ISOLATED_NATIVE_GUI_FILES))
        discovered = set(discover_native_gui_test_files(Path(__file__).parent))
        self.assertTrue(discovered.issubset(ISOLATED_NATIVE_GUI_FILES))
        self.assertEqual(len(ISOLATED_NATIVE_GUI_FILES), len(set(ISOLATED_NATIVE_GUI_FILES)))
        broad = next(command for command in commands if "--ignore" in command)
        self.assertIn("--deselect", broad)
        for path, prerequisite in EVIDENCE_GATED_TESTS.items():
            if not (Path(__file__).resolve().parents[1] / prerequisite).is_file():
                self.assertIn(path, broad)
        for nodeid in ISOLATED_TEST_NODES:
            self.assertIn(nodeid, broad)
        for path in ISOLATED_FILES:
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
        self.assertNotIn("--ignore", commands[-1])
        self.assertIn(commands[-1][-1], ISOLATED_FILES)

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


@pytest.mark.unit
@pytest.mark.semantic
def test_native_gui_discovery_handles_pytest_aliases(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_gui.py").write_text(
        "import pytest as pt\n@pt.mark.gui\ndef test_window(): pass\n",
        encoding="utf-8",
    )
    (tests_dir / "test_qt.py").write_text(
        "from pytest import mark as checks\n@checks.qt\ndef test_widget(): pass\n",
        encoding="utf-8",
    )
    (tests_dir / "test_plain.py").write_text(
        "def test_plain(): pass\n", encoding="utf-8"
    )

    assert discover_native_gui_test_files(tests_dir) == (
        "tests/test_gui.py",
        "tests/test_qt.py",
    )


if __name__ == "__main__":
    unittest.main()
