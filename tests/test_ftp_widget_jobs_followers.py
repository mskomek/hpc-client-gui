"""Focused FTP widget tests for jobs followers behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import patch
import pytest
from PySide6.QtCore import QPoint, Qt
from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog
from hpc_gui.ui.main_window import MainWindow
from hpc_gui.ui.widgets.directories_widget import DirectoriesWidget
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel
from ftp_widget_test_support import FtpWidgetTestCase, _Files


class FtpWidgetJobsFollowersTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_main_window_routes_ftp_actions_to_existing_directories_handlers(self) -> None:
        opened = []
        submitted = []
        shell_batches = []

        def record_open(_self, path):
            opened.append(path)

        def record_submit(_self, path):
            submitted.append(path)

        def record_shell_run(_self, path):
            shell_runs.append(path)

        def record_shell_batch(_self, paths):
            shell_batches.append(paths)

        shell_runs = []

        with (
            patch("hpc_gui.ui.main_window.QTimer.singleShot"),
            patch.object(DirectoriesWidget, "on_open_file", record_open),
            patch.object(DirectoriesWidget, "submit_script", record_submit),
            patch.object(DirectoriesWidget, "run_shell_script", record_shell_run),
            patch.object(MainWindow, "run_shell_batch_in_terminal", record_shell_batch),
        ):
            window = MainWindow()
            try:
                window.ftp.panel_scratch.open_file.emit("/scratch/file.txt")
                window.ftp.panel_home.submit_requested.emit("/home/job.slurm")
                window.ftp.panel_home.run_shell_requested.emit("/home/run.sh")
                window.ftp.panel_scratch.batch_shell_requested.emit(
                    ["/scratch/Z.sh", "/scratch/a.sh"]
                )

                self.assertEqual(opened, ["/scratch/file.txt"])
                self.assertEqual(submitted, ["/home/job.slurm"])
                self.assertEqual(shell_runs, ["/home/run.sh"])
                self.assertEqual(shell_batches, [["/scratch/Z.sh", "/scratch/a.sh"]])
            finally:
                window.graceful_shutdown()
                window.deleteLater()

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_main_window_batch_shell_uses_login_terminal_order(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            with (
                patch.object(window.tabs, "setCurrentWidget") as select_tab,
                patch.object(window.login, "run_command_text") as run_command,
            ):
                window.run_shell_batch_in_terminal(["/remote/Z name.sh", "/remote/a.sh"])
            select_tab.assert_called_once_with(window.login)
            run_command.assert_called_once_with("bash '/remote/Z name.sh'\nbash /remote/a.sh")
        finally:
            window.graceful_shutdown()
            window.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_main_window_contains_top_level_ftp_tab(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            labels = [window.tabs.tabText(index) for index in range(window.tabs.count())]
            self.assertIn("Files", labels)
            self.assertIs(window.ftp, window.tabs.widget(labels.index("Files")))
        finally:
            window.graceful_shutdown()
            window.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_submission_follow_modes_route_to_the_requested_destination(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            for mode, shows_jobs_page in {
                "none": False,
                "outputs_tab": True,
                "new_tabs_split": True,
                "new_window_combined": False,
                "new_windows_split": False,
            }.items():
                window.tabs.setCurrentWidget(window.ftp)
                with (
                    patch.object(window.jobs_outputs, "focus_job") as focus,
                    patch(
                        "hpc_gui.ui.main_window.get_sbatch_follow_mode",
                        return_value=mode,
                    ),
                ):
                    window.on_script_submitted("123", "/remote/job.sbatch")
                self.assertIs(
                    window.tabs.currentWidget(),
                    window.jobs_outputs if shows_jobs_page else window.ftp,
                )
                focus.assert_called_once_with(
                    "123",
                    "/remote/job.sbatch",
                    switch_to_outputs=shows_jobs_page,
                    follow_mode=mode,
                )
        finally:
            window.graceful_shutdown()
            window.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_focus_job_none_still_refreshes_and_binds_script(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget

        jobs_widget = JobsOutputsWidget()
        try:
            jobs_widget.section_tabs.setCurrentWidget(jobs_widget.details_tab)
            with (
                patch.object(jobs_widget, "refresh_jobs") as refresh_jobs,
                patch.object(jobs_widget, "refresh_sacct") as refresh_sacct,
                patch.object(jobs_widget, "_activate_slurm_script") as activate,
            ):
                jobs_widget.focus_job(
                    "123",
                    "/remote/job.sbatch",
                    switch_to_outputs=False,
                    follow_mode="none",
                )
            refresh_jobs.assert_called_once()
            refresh_sacct.assert_called_once()
            activate.assert_called_once_with(
                "/remote/job.sbatch",
                switch_to_outputs=False,
                follow_mode="none",
            )
            self.assertIs(jobs_widget.section_tabs.currentWidget(), jobs_widget.details_tab)
        finally:
            jobs_widget.deleteLater()

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_sbatch_follow_modes_use_existing_follower_helpers(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget

        class ScriptFiles:
            def read_text(self, _path: str) -> str:
                return "#SBATCH --output=job.out\n#SBATCH --error=job.err\n"

        jobs_widget = JobsOutputsWidget()
        # _activate_slurm_script only needs the file backend; avoid a connected
        # session here because it would also start unrelated directory polling.
        jobs_widget.session = {"files": ScriptFiles()}
        try:
            with (
                patch.object(jobs_widget, "open_in_output_slot") as output_slot,
                patch.object(jobs_widget, "open_output_pair_tab") as pair_tab,
                patch.object(jobs_widget, "open_output_pair_window") as pair_window,
                patch.object(jobs_widget, "open_in_output_window") as output_window,
                patch.object(jobs_widget, "open_file_follow_window") as file_window,
                patch.object(jobs_widget, "_poll_live") as poll_live,
            ):
                for mode in (
                    "none",
                    "outputs_tab",
                    "new_tabs_split",
                    "new_window_combined",
                    "new_windows_split",
                ):
                    output_slot.reset_mock()
                    pair_tab.reset_mock()
                    pair_window.reset_mock()
                    output_window.reset_mock()
                    file_window.reset_mock()
                    poll_live.reset_mock()
                    jobs_widget._activate_slurm_script(
                        "/remote/job.sbatch",
                        switch_to_outputs=False,
                        follow_mode=mode,
                    )
                    if mode == "none":
                        output_slot.assert_not_called()
                        pair_tab.assert_not_called()
                        pair_window.assert_not_called()
                        output_window.assert_not_called()
                    elif mode == "outputs_tab":
                        self.assertEqual(output_slot.call_count, 2)
                        poll_live.assert_called_once()
                    elif mode == "new_tabs_split":
                        pair_tab.assert_called_once_with("/remote/job.out", "/remote/job.err")
                    elif mode == "new_window_combined":
                        pair_window.assert_called_once_with("/remote/job.out", "/remote/job.err")
                    else:
                        output_window.assert_not_called()
                        self.assertEqual(file_window.call_count, 2)
                        self.assertEqual(
                            [entry.args[0] for entry in file_window.call_args_list],
                            ["/remote/job.out", "/remote/job.err"],
                        )
        finally:
            jobs_widget.shutdown()
            jobs_widget.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_generic_new_window_follower_is_one_single_file_window(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import (
            JobsOutputsWidget,
            _SingleFileFollowerWidget,
        )

        jobs_widget = JobsOutputsWidget()
        try:
            window = jobs_widget.open_file_follow_window("/remote/run.log")
            self.assertIsNotNone(window)
            self.assertEqual(len(jobs_widget._single_file_follow_windows), 1)
            self.assertEqual(len(jobs_widget._follow_windows), 0)
            self.assertIsInstance(window.centralWidget(), _SingleFileFollowerWidget)
            self.assertIn("run.log", window.windowTitle())
            self.assertNotIn("Output 1", window.windowTitle())
            self.assertNotIn("Output 2", window.windowTitle())
            follower = window.centralWidget()
            self.assertFalse(follower.err_box.isVisible())
            self.assertEqual(follower.out_box.title(), "run.log")
            self.assertNotIn("Output 1", follower.out_box.title())
            self.assertNotIn("Output 2", follower.out_box.title())
        finally:
            jobs_widget.shutdown()
            jobs_widget.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_combined_sbatch_follower_uses_one_clear_output_error_window(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget

        class ScriptFiles:
            def read_text(self, _path: str) -> str:
                return "#SBATCH --output=job.out\n#SBATCH --error=job.err\n"

        jobs_widget = JobsOutputsWidget()
        jobs_widget.session = {"files": ScriptFiles()}
        try:
            jobs_widget._activate_slurm_script(
                "/remote/job.sbatch",
                follow_mode="new_window_combined",
            )
            self.assertEqual(len(jobs_widget._follow_windows), 1)
            self.assertEqual(len(jobs_widget._single_file_follow_windows), 0)
            window = jobs_widget._follow_windows[0]
            self.assertIn("Output: job.out", window.windowTitle())
            self.assertIn("Error: job.err", window.windowTitle())
            self.assertNotIn("Output 1", window.windowTitle())
            self.assertNotIn("Output 2", window.windowTitle())
            follower = window.centralWidget()
            self.assertEqual(follower.out_box.title(), "Output")
            self.assertEqual(follower.err_box.title(), "Error")
            self.assertNotIn("Output 1", follower.out_box.title())
            self.assertNotIn("Output 2", follower.err_box.title())
        finally:
            jobs_widget.shutdown()
            jobs_widget.deleteLater()

    @pytest.mark.contract
    @pytest.mark.regression
    def test_sbatch_follow_mode_settings_migrate_and_persist(self) -> None:
        from hpc_gui.config import storage

        with patch.object(
            storage,
            "load_settings",
            return_value={
                "focus_jobs_outputs_after_submission_enabled": False,
            },
        ):
            self.assertEqual(storage.get_sbatch_follow_mode(), "none")
        with patch.object(
            storage,
            "load_settings",
            return_value={
                "focus_jobs_outputs_after_submission_enabled": True,
            },
        ):
            self.assertEqual(storage.get_sbatch_follow_mode(), "outputs_tab")
        with patch.object(storage, "load_settings", return_value={}):
            self.assertEqual(storage.get_sbatch_follow_mode(), "outputs_tab")
        with patch.object(storage, "update_settings") as update:
            self.assertEqual(storage.set_sbatch_follow_mode("new_tabs_split"), "new_tabs_split")
            update.assert_called_once_with({"sbatch_follow_mode": "new_tabs_split"})

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_sbatch_follow_mode_settings_have_all_tooltips(self) -> None:
        with patch(
            "hpc_gui.ui.dialogs.settings_dialog.get_sbatch_follow_mode",
            return_value="outputs_tab",
        ):
            dialog = SettingsDialog()
        try:
            expected_modes = {
                "none",
                "outputs_tab",
                "new_tabs_split",
                "new_window_combined",
                "new_windows_split",
            }
            self.assertEqual(
                {
                    dialog.cb_sbatch_follow_mode.itemData(index)
                    for index in range(dialog.cb_sbatch_follow_mode.count())
                },
                expected_modes,
            )
            for index in range(dialog.cb_sbatch_follow_mode.count()):
                self.assertTrue(
                    dialog.cb_sbatch_follow_mode.itemData(
                        index, Qt.ItemDataRole.ToolTipRole
                    ).strip()
                )
            with patch("hpc_gui.ui.dialogs.settings_dialog.update_settings") as update:
                dialog.cb_sbatch_follow_mode.setCurrentIndex(
                    dialog.cb_sbatch_follow_mode.findData("new_windows_split")
                )
                dialog.btn_apply.click()
            self.assertEqual(
                update.call_args.args[0]["sbatch_follow_mode"],
                "new_windows_split",
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_context_menu_restores_sbatch_submit_action(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == "Submit with sbatch":
                        return action
                return None

        files = _Files()
        files.remote["/remote/job.slurm"] = b"#!/bin/bash\n#SBATCH -J demo\n"
        panel = RemoteDirPanel()
        submitted: list[str] = []
        try:
            panel.submit_requested.connect(submitted.append)
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "job.slurm":
                    item.setSelected(True)
                    break

            with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
                panel._on_context_menu(view, QPoint(0, 0))

            self.assertEqual(submitted, ["/remote/job.slurm"])
        finally:
            panel.deleteLater()
