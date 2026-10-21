from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import scripts.ci as ci
from scripts.release_test_suite import (
    ISOLATED_FILES,
    ISOLATED_FILESYSTEM_FILES,
    ISOLATED_NATIVE_GUI_FILES,
    ISOLATED_NODE_SELECTORS,
    ISOLATED_TEST_NODES,
    EVIDENCE_GATED_TESTS,
    PREFLIGHT_COMMANDS,
    _discover_ftp_widget_splits,
    _evidence_failures,
    _test_environment,
    build_commands,
    main,
)
from scripts.native_gui_test_files import discover_native_gui_test_files


class ReleaseTestSuiteTests(unittest.TestCase):
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_pytest_commands_report_skip_reasons(self):
        pytest_commands = [
            command for command in build_commands(coverage=False) if "pytest" in command
        ]
        self.assertTrue(pytest_commands)
        self.assertTrue(all("-rfs" in command for command in pytest_commands))

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_ftp_widget_test_splits_keep_the_wire_process_boundary(self):
        expected = (
            "tests/test_ftp_widget_activity_queue_controls.py",
            "tests/test_ftp_widget_transfer_preflight.py",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            split_dir = temp_root / "tests"
            split_dir.mkdir()
            for relative in expected:
                (temp_root / relative).touch()
            actual = _discover_ftp_widget_splits(split_dir)
        self.assertEqual(actual, expected)

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_portable_scope_omits_evidence_suites_and_acceptance_includes_them(self):
        portable_commands = build_commands(coverage=False, scope="portable")
        acceptance_commands = build_commands(coverage=False, scope="acceptance")
        portable_broad = next(
            command for command in portable_commands if "tests" in command and "--ignore" in command
        )
        acceptance_broad = next(
            command for command in acceptance_commands if "tests" in command and "--ignore" in command
        )
        for path in EVIDENCE_GATED_TESTS:
            self.assertIn(path, portable_broad)
            isolated = [
                command
                for command in acceptance_commands[len(PREFLIGHT_COMMANDS) + 1 :]
                if command[-1] == path
            ]
            exists = (Path(__file__).resolve().parents[1] / path).is_file()
            if path in ISOLATED_FILES and exists:
                self.assertEqual(len(isolated), 1)
                self.assertIn(path, acceptance_broad)
            else:
                self.assertEqual(isolated, [])
                self.assertNotIn(path, acceptance_broad)

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_evidence_hash_validation_uses_raw_file_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "freeze.md"
            evidence.write_bytes(b"evidence\r\n")
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            with (
                patch("scripts.release_test_suite.REPO_ROOT", root),
                patch("scripts.release_test_suite.EVIDENCE_GATED_TESTS", {"test.py": "freeze.md"}),
                patch("scripts.release_test_suite.EVIDENCE_EXPECTED_SHA256", {"freeze.md": digest}),
            ):
                self.assertEqual(_evidence_failures(), ())
                evidence.write_bytes(b"changed")
                self.assertIn("SHA-256 mismatch", _evidence_failures()[0])

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_pinned_v2_evidence_file_matches_its_expected_hash(self):
        self.assertEqual(_evidence_failures(), ())

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_acceptance_builds_wheel_before_preflight_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("scripts.release_test_suite.REPO_ROOT", Path(temp_dir)),
                patch("scripts.release_test_suite._evidence_failures", return_value=()),
                patch("scripts.release_test_suite.build_commands", return_value=[]),
                patch("scripts.release_test_suite.subprocess.run") as run,
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                run.return_value = SimpleNamespace(returncode=0)
                result = main(["--scope", "acceptance"])
        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0][1:4], ("-m", "build", "--wheel"))

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_acceptance_blocks_before_subprocesses_when_evidence_is_missing(self):
        with (
            patch("scripts.release_test_suite._evidence_failures", return_value=("missing: freeze.md",)),
            patch("scripts.release_test_suite.subprocess.run") as run,
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main(["--scope", "acceptance"])
        self.assertEqual(result, 2)
        run.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_ci_uses_portable_scope_for_gui_and_acceptance_for_release(self):
        with patch("scripts.ci._run", return_value=0) as run:
            ci.gui()
            gui_command = run.call_args_list[0].args[1]
            self.assertEqual(gui_command[2:4], ["--scope", "portable"])
            ci.release()
            release_command = run.call_args_list[-1].args[1]
            self.assertEqual(release_command[2:4], ["--scope", "acceptance"])

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
            "tests/test_jobs_history_mock_wire.py",
            "tests/test_wx_dispatch_error_gov.py",
            "tests/test_jobs_auto_refresh_toggle.py",
            "tests/test_wx_connection_progress.py",
            "tests/test_wx_shell_layout.py",
            "tests/test_wx_terminal_webview_lifecycle.py",
            "tests/test_remote_accordion.py",
            "tests/test_startup_changelog.py",
            "tests/test_transfer_performance_scenarios.py",
        }
        self.assertTrue(required_boundaries.issubset(ISOLATED_NATIVE_GUI_FILES))
        self.assertIn("tests/test_updater_helper.py", ISOLATED_FILESYSTEM_FILES)
        discovered = set(discover_native_gui_test_files(Path(__file__).parent))
        self.assertTrue(discovered.issubset(ISOLATED_NATIVE_GUI_FILES))
        self.assertEqual(len(ISOLATED_NATIVE_GUI_FILES), len(set(ISOLATED_NATIVE_GUI_FILES)))
        broad = next(command for command in commands if "--ignore" in command)
        runnable_files = {
            path for path in ISOLATED_FILES
            if (Path(__file__).resolve().parents[1] / path).is_file()
        }
        if ISOLATED_NODE_SELECTORS:
            self.assertIn("--deselect", broad)
        else:
            self.assertNotIn("--deselect", broad)
        for path, prerequisite in EVIDENCE_GATED_TESTS.items():
            self.assertIn(path, broad)
            isolated_commands = commands[len(PREFLIGHT_COMMANDS) + 1 :]
            self.assertFalse(any(command[-1] == path for command in isolated_commands))
        for nodeid in ISOLATED_TEST_NODES:
            test_file = nodeid.split("::", 1)[0]
            if test_file in runnable_files:
                self.assertIn(test_file, broad)
                self.assertNotIn(nodeid, broad)
            elif test_file in ISOLATED_FILES:
                self.assertNotIn(test_file, broad)
                self.assertNotIn(nodeid, broad)
            else:
                self.assertIn(nodeid, broad)
        for path in ISOLATED_FILES:
            if path not in runnable_files:
                self.assertNotIn(path, broad)
                continue
            self.assertIn(path, broad)
            if path in EVIDENCE_GATED_TESTS:
                continue
            isolated = [
                command for command in commands
                if path in command and "--ignore" not in command
            ]
            self.assertEqual(len(isolated), 1)
            self.assertNotIn("--deselect", isolated[0])
            self.assertEqual(isolated[0][-1], path)
        for index, nodeid in enumerate(
            ISOLATED_NODE_SELECTORS, start=len(PREFLIGHT_COMMANDS) + 1
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
            patch.dict("os.environ", {"HPC_GUI_CONFIG_ROOT": ""}),
            patch("scripts.release_test_suite.subprocess.run", run),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main([])

        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, len(commands))
        environments = [call.kwargs["env"] for call in run.call_args_list]
        config_roots = {environment["HOME"] for environment in environments}
        self.assertEqual(len(config_roots), 1)
        config_root = Path(config_roots.pop())
        self.assertEqual(config_root.parent, Path(__file__).resolve().parents[1] / ".tmp")
        self.assertFalse(config_root.exists())
        self.assertTrue(all("HPC_GUI_CONFIG_ROOT" not in environment for environment in environments))

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_test_environment_redirects_per_user_state(self):
        with (
            patch.dict("os.environ", {"HPC_GUI_CONFIG_ROOT": "caller-config"}),
            patch("scripts.release_test_suite._TEST_CONFIG_ROOT", "isolated-config"),
        ):
            environment = _test_environment()
            self.assertEqual(environment["HOME"], "isolated-config")
            self.assertEqual(environment["USERPROFILE"], "isolated-config")
            self.assertNotIn("HPC_GUI_CONFIG_ROOT", environment)
            self.assertTrue(environment.get("PYTHONUSERBASE"))


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
    (tests_dir / "test_native_wx_import.py").write_text(
        "import wx\ndef test_window(): pass\n", encoding="utf-8"
    )
    (tests_dir / "test_optional_wx_import.py").write_text(
        'import pytest\nwx = pytest.importorskip("wx")\ndef test_optional_window(): pass\n',
        encoding="utf-8",
    )
    (tests_dir / "test_helper_wx_import.py").write_text(
        "from gui_test_support import wx\ndef test_helper_window(): pass\n",
        encoding="utf-8",
    )
    (tests_dir / "test_manual_verification.py").write_text(
        "import wx\ndef run_verification(): pass\n", encoding="utf-8"
    )

    assert discover_native_gui_test_files(tests_dir) == (
        "tests/test_gui.py",
        "tests/test_helper_wx_import.py",
        "tests/test_native_wx_import.py",
        "tests/test_optional_wx_import.py",
        "tests/test_qt.py",
    )


if __name__ == "__main__":
    unittest.main()
