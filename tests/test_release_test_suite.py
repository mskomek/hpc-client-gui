from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import tempfile
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
    @pytest.mark.regression
    def test_pytest_commands_report_failure_and_skip_reasons(self):
        commands = build_commands(coverage=False)
        pytest_commands = [command for command in commands if "pytest" in command]
        self.assertTrue(pytest_commands)
        self.assertTrue(all("-rfs" in command for command in pytest_commands))

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
                "tests/test_corrective_jobs_details_i18n_and_regression.py",
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
        self.assertIn("tests/test_ftp_widget_activity_queue_controls.py", ISOLATED_WIRE_FILES)
        self.assertEqual(
            ISOLATED_WIRE_FILES[1:20],
            (
                "tests/test_ftp_widget_activity_queue_controls.py",
                "tests/test_ftp_widget_activity_rows_history.py",
                "tests/test_ftp_widget_backend_concurrency.py",
                "tests/test_ftp_widget_connection_profiles.py",
                "tests/test_ftp_widget_directory_tabs_cache_lifecycle.py",
                "tests/test_ftp_widget_directory_tabs_cache_lifecycle_2.py",
                "tests/test_ftp_widget_file_drop.py",
                "tests/test_ftp_widget_job_output_following.py",
                "tests/test_ftp_widget_local_file_operations.py",
                "tests/test_ftp_widget_permissions_and_path_navigation.py",
                "tests/test_ftp_widget_remote_file_operations.py",
                "tests/test_ftp_widget_script_submission.py",
                "tests/test_ftp_widget_settings_profiles.py",
                "tests/test_ftp_widget_transfer_backend_policy.py",
                "tests/test_ftp_widget_transfer_backend_policy_2.py",
                "tests/test_ftp_widget_transfer_dialog_planning.py",
                "tests/test_ftp_widget_transfer_dialog_planning_2.py",
                "tests/test_ftp_widget_transfer_preflight_pipeline.py",
                "tests/test_ftp_widget_transfer_preflight_pipeline_2.py",
            ),
        )
        self.assertIn(
            "tests/test_corrective_jobs_details_i18n_and_regression.py",
            ISOLATED_NATIVE_GUI_FILES,
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
    @pytest.mark.regression
    def test_acceptance_commands_include_evidence_gated_tests(self):
        commands = build_commands(coverage=False, scope="acceptance")
        broad = next(command for command in commands if "--ignore" in command)
        for path in EVIDENCE_GATED_TESTS:
            self.assertNotIn(path, broad)

    @pytest.mark.unit
    @pytest.mark.regression
    def test_portable_commands_ignore_evidence_gated_tests_even_when_present(self):
        commands = build_commands(coverage=False, scope="portable")
        broad = next(command for command in commands if "--ignore" in command)
        for path in EVIDENCE_GATED_TESTS:
            self.assertIn(path, broad)

    @pytest.mark.unit
    @pytest.mark.regression
    def test_acceptance_builds_candidate_wheel_before_tests(self):
        with (
            patch("scripts.release_test_suite._evidence_failures", return_value=()),
            patch("scripts.release_test_suite.subprocess.run") as run,
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            run.return_value = SimpleNamespace(returncode=0)
            result = main(["--scope", "acceptance"])

        self.assertEqual(result, 0)
        first_call = run.call_args_list[0]
        self.assertEqual(first_call.args[0][1:4], ("-m", "build", "--wheel"))

    @pytest.mark.unit
    @pytest.mark.regression
    def test_acceptance_fails_before_running_tests_when_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with (
                patch("scripts.release_test_suite.REPO_ROOT", root),
                patch(
                    "scripts.release_test_suite.EVIDENCE_GATED_TESTS",
                    {"tests/test_w04_support_freeze.py": "freeze.md"},
                ),
                patch("scripts.release_test_suite.EVIDENCE_EXPECTED_SHA256", {"freeze.md": "a" * 64}),
                patch("scripts.release_test_suite.subprocess.run") as run,
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                result = main(["--scope", "acceptance"])

        self.assertEqual(result, 2)
        run.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.regression
    def test_acceptance_fails_before_running_tests_when_evidence_hash_is_wrong(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "freeze.md").write_text("tampered", encoding="utf-8")
            with (
                patch("scripts.release_test_suite.REPO_ROOT", root),
                patch(
                    "scripts.release_test_suite.EVIDENCE_GATED_TESTS",
                    {"tests/test_w04_support_freeze.py": "freeze.md"},
                ),
                patch("scripts.release_test_suite.EVIDENCE_EXPECTED_SHA256", {"freeze.md": "a" * 64}),
                patch("scripts.release_test_suite.subprocess.run") as run,
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                result = main(["--scope", "acceptance"])

        self.assertEqual(result, 2)
        run.assert_not_called()

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
