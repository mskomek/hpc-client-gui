from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    QPoint,
    RemoteDirPanel,
    _Files,
    patch,
    pytest,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_focus_job_none_still_refreshes_and_binds_script(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget
        jobs_widget = JobsOutputsWidget()
        try:
            jobs_widget.section_tabs.setCurrentWidget(jobs_widget.details_tab)
            with patch.object(jobs_widget, "refresh_jobs") as refresh_jobs, patch.object(
                jobs_widget, "refresh_sacct"
            ) as refresh_sacct, patch.object(
                jobs_widget, "_activate_slurm_script"
            ) as activate:
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
                for mode in ("none", "outputs_tab", "new_tabs_split", "new_window_combined", "new_windows_split"):
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
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_jobs_files_context_menu_restores_output_follow_actions(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            instances: list["FakeMenu"] = []
            choose_text = "Follow in Output 2"

            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []
                FakeMenu.instances.append(self)

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == self.choose_text:
                        return action
                return None

        files = _Files()
        files.remote["/remote/out.log"] = b"out"
        panel = RemoteDirPanel()
        seen: list[tuple[int, str]] = []
        assigned: list[tuple[str, int, str]] = []
        try:
            panel.enable_output_menu = True
            panel.set_output_target_provider(
                lambda: [("window:1", "Follow window 1")]
            )
            panel.open_in_slot.connect(lambda slot, path: seen.append((slot, path)))
            panel.open_in_existing_follower.connect(
                lambda target, slot, path: assigned.append(
                    (target, slot, path)
                )
            )
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "out.log":
                    item.setSelected(True)
                    break

            with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
                panel._on_context_menu(view, QPoint(0, 0))
                FakeMenu.choose_text = "Assign to Follow window 1 Output 2"
                panel._on_context_menu(view, QPoint(0, 0))

            labels = [
                action.text
                for action in FakeMenu.instances[-1].actions
                if action is not None
            ]
            self.assertIn("Follow in Output 1", labels)
            self.assertIn("Follow in Output 2", labels)
            self.assertIn("Follow file in new window", labels)
            self.assertIn("Follow in Output 1 in new window", labels)
            self.assertIn("Follow in Output 2 in new window", labels)
            self.assertIn("Follow in Output 1 in new tab", labels)
            self.assertIn("Follow in Output 2 in new tab", labels)
            self.assertIn("Assign to Follow window 1 Output 1", labels)
            self.assertIn("Assign to Follow window 1 Output 2", labels)
            self.assertEqual(seen, [(1, "/remote/out.log")])
            self.assertEqual(
                assigned,
                [("window:1", 1, "/remote/out.log")],
            )
        finally:
            FakeMenu.choose_text = "Follow in Output 2"
            panel.deleteLater()
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
