from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtWidgets import QMessageBox, QMainWindow

from hpc_gui.config.storage import SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT, SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED, SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT, SBATCH_FOLLOW_MODE_NONE, SBATCH_FOLLOW_MODE_OUTPUTS_TAB, get_follow_window_open_minimized_enabled

from hpc_gui.core.i18n import t

from hpc_gui.core.ui_errors import show_exception

from hpc_gui.core.history import append_event

from hpc_gui.services.slurm_script_parser import parse_job_paths, parse_job_name

from ._jobs_output_follower_views import _FollowerWindow, _OutputFollowerWidget, _SingleFileFollowerWidget



class _JobsOutputsFollowersMixin:
        def load_one_file(self, remote_path: str):
            """
            Çift tık: Eğer slurm script ise parse edip output/error'a bağlan.
            Değilse varsayılan olarak Çıktı-1'de aç ve izle.
            """
            if not remote_path:
                return
            lower = remote_path.lower()
            if lower.endswith((".slurm", ".sbatch")):
                self._activate_slurm_script(remote_path)
            else:
                self.open_in_output_slot(0, remote_path)
        def _output_target_choices(self) -> list[tuple[str, str]]:
            return [
                (target_id, self._follow_target_labels[target_id])
                for target_id in self._follow_target_order
                if target_id in self._follow_targets
                and target_id in self._follow_target_labels
            ]
        def _register_output_target(
            self,
            kind: str,
            follower: _OutputFollowerWidget,
        ) -> tuple[str, str]:
            if kind == "window":
                number = self._next_follow_window_number
                self._next_follow_window_number += 1
                label = t("jobs_outputs.follow_window_label").format(number=number)
            else:
                number = self._next_follow_tab_number
                self._next_follow_tab_number += 1
                label = t("jobs_outputs.follow_tab_label").format(number=number)
            target_id = f"{kind}:{number}"
            self._follow_targets[target_id] = follower
            self._follow_target_labels[target_id] = label
            self._follow_target_order.append(target_id)
            return target_id, label
        def _unregister_output_target(self, target_id: str) -> None:
            self._follow_targets.pop(target_id, None)
            self._follow_target_labels.pop(target_id, None)
            if target_id in self._follow_target_order:
                self._follow_target_order.remove(target_id)
        def _close_follow_tab(self, index: int) -> None:
            if index < 3:
                return
            follower = self.section_tabs.widget(index)
            if not isinstance(follower, _OutputFollowerWidget):
                return
            target_id = self._follow_tab_target_ids.pop(follower, "")
            if target_id:
                self._unregister_output_target(target_id)
            if follower in self._follow_tabs:
                self._follow_tabs.remove(follower)
            follower.shutdown()
            self.section_tabs.removeTab(index)
            follower.deleteLater()
        def open_in_existing_follower(
            self,
            target_id: str,
            slot: int,
            remote_path: str,
        ) -> None:
            follower = self._follow_targets.get(target_id)
            if follower is None:
                return
            follower.open_in_output_slot(slot, remote_path)
        def _make_output_follower(
            self,
            slot: int,
            remote_path: str,
        ) -> _OutputFollowerWidget:
            follower = _OutputFollowerWidget()
            follower.set_session(self.session)
            follower.open_in_output_slot(slot, remote_path)
            return follower
        def _make_output_pair_follower(
            self,
            output_path: str,
            error_path: str,
        ) -> _OutputFollowerWidget:
            follower = _OutputFollowerWidget()
            follower.set_session(self.session)
            if output_path:
                follower.open_in_output_slot(0, output_path)
            if error_path:
                follower.open_in_output_slot(1, error_path)
            return follower
        def _show_new_follow_window(self, window: QMainWindow) -> None:
            window.show()
            if get_follow_window_open_minimized_enabled():
                window.showMinimized()
        def _show_follower_window(
            self,
            follower: _OutputFollowerWidget,
            *,
            title: str = "",
        ) -> QMainWindow:
            target_id, label = self._register_output_target("window", follower)
            window = _FollowerWindow(None, Qt.WindowType.Window)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.setWindowTitle(title or label)
            window.setCentralWidget(follower)
            window.resize(900, 650)
            self._follow_windows.append(window)
            window_token = id(window)

            def cleanup(*_args) -> None:
                self._unregister_output_target(target_id)
                # The destroyed signal can run while the C++ QMainWindow is
                # already being torn down.  Do not compare/access that wrapper;
                # id() is a Python-only stable token captured before destruction.
                self._follow_windows[:] = [
                    candidate
                    for candidate in self._follow_windows
                    if id(candidate) != window_token
                ]

            window.destroyed.connect(cleanup)
            self._show_new_follow_window(window)
            return window
        def open_in_output_window(self, slot: int, remote_path: str) -> None:
            if slot not in (0, 1) or not remote_path:
                return
            self._show_follower_window(self._make_output_follower(slot, remote_path))
        def open_file_follow_window(self, remote_path: str) -> QMainWindow | None:
            if not remote_path:
                return
            follower = _SingleFileFollowerWidget(remote_path)
            follower.set_session(self.session)
            filename = remote_path.rstrip("/").rsplit("/", 1)[-1] or remote_path
            window = _FollowerWindow(None, Qt.WindowType.Window)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.setWindowTitle(
                t("jobs_outputs.single_follow_window_title").format(name=filename)
            )
            window.setCentralWidget(follower)
            window.resize(900, 650)
            self._single_file_follow_windows.append(window)
            window_token = id(window)

            def cleanup(*_args) -> None:
                self._single_file_follow_windows[:] = [
                    candidate
                    for candidate in self._single_file_follow_windows
                    if id(candidate) != window_token
                ]

            window.destroyed.connect(cleanup)
            self._show_new_follow_window(window)
            return window
        def open_output_pair_window(
            self,
            output_path: str,
            error_path: str,
        ) -> None:
            if not output_path and not error_path:
                return
            output_name = output_path.rstrip("/").rsplit("/", 1)[-1] if output_path else "-"
            error_name = error_path.rstrip("/").rsplit("/", 1)[-1] if error_path else "-"
            follower = self._make_output_pair_follower(output_path, error_path)
            # This is the automatic combined sbatch window, not the explicit
            # Output 1/Output 2 window action.  Its visible panels describe the
            # file roles directly rather than exposing reusable slot terminology.
            follower.out_box.setTitle(t("jobs_outputs.output"))
            follower.err_box.setTitle(t("common.error"))
            self._show_follower_window(
                follower,
                title=t("jobs_outputs.combined_follow_window_title").format(
                    output=output_name,
                    error=error_name,
                ),
            )
        def _append_follower_tab(
            self,
            follower: _OutputFollowerWidget,
        ) -> int:
            target_id, label = self._register_output_target("tab", follower)
            self._follow_tabs.append(follower)
            self._follow_tab_target_ids[follower] = target_id
            index = self.section_tabs.addTab(follower, label)
            self.section_tabs.setCurrentIndex(index)
            return index
        def open_in_output_tab(self, slot: int, remote_path: str) -> None:
            if slot not in (0, 1) or not remote_path:
                return
            self._append_follower_tab(self._make_output_follower(slot, remote_path))
        def open_output_pair_tab(
            self,
            output_path: str,
            error_path: str,
        ) -> None:
            if not output_path and not error_path:
                return
            self._append_follower_tab(
                self._make_output_pair_follower(output_path, error_path)
            )
        def open_in_output_slot(
            self,
            slot: int,
            remote_path: str,
            *,
            switch_to_outputs: bool = True,
        ):
            """
            Sağ tuş menüsü: seçili dosyayı Output-1 (slot=0) veya Output-2 (slot=1) izle.
            """
            self._tail_suspended = False
            self._reset_live_tail_idle_state()
            if slot == 0:
                self.active_out = remote_path
                self.path_out.setText(remote_path)
                self._last_sig[0] = None
                self.txt_out.setPlainText("")
            else:
                self.active_err = remote_path
                self.path_err.setText(remote_path)
                self._last_sig[1] = None
                self.txt_err.setPlainText("")
            if switch_to_outputs:
                self.section_tabs.setCurrentWidget(self.outputs_tab)
            self._sync_polling(immediate=True)
            append_event({"type": "open_watch", "slot": slot+1, "path": remote_path})
        def _follow_path_from_field(self, slot: int) -> None:
            field = self.path_out if slot == 0 else self.path_err
            remote_path = field.text().strip()
            if not remote_path:
                field.setText(self.active_out if slot == 0 else self.active_err)
                return
            self.open_in_output_slot(slot, remote_path)
        def _activate_slurm_script(
            self,
            script_path: str,
            *,
            switch_to_outputs: bool = True,
            follow_mode: str = SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
        ):
            if not self.session or not self.session.get("files"):
                QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
                return
            files = self.session["files"]
            try:
                script_text = files.read_text(script_path)
            except Exception as e:
                show_exception(self, title=t("common.error"), user_message=f"Script açılamadı: {e}", exc=e, area="JOBS")
                return

            self.active_script = script_path
            self.lbl_script.setText(t("jobs_outputs.active_script").format(path=script_path))

            job_name = parse_job_name(script_text)
            jobid = self.cancel_id.text().strip() or None
            paths = parse_job_paths(script_text, script_path, jobid, job_name)
            out_path, err_path = paths.stdout, paths.stderr
            self._tracking.set_output_metadata(
                stdout_path=out_path, stderr_path=err_path,
                script_path=script_path, workdir=paths.workdir,
            )
            self._show_workdir(paths.workdir)

            if follow_mode == SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED:
                self.open_output_pair_window(out_path, err_path)
            elif follow_mode == SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT:
                if out_path:
                    self.open_file_follow_window(out_path)
                if err_path:
                    self.open_file_follow_window(err_path)
            elif follow_mode == SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT:
                self.open_output_pair_tab(out_path, err_path)
            elif follow_mode == SBATCH_FOLLOW_MODE_OUTPUTS_TAB:
                if out_path:
                    self.open_in_output_slot(
                        0,
                        out_path,
                        switch_to_outputs=switch_to_outputs,
                    )
                if err_path:
                    self.open_in_output_slot(
                        1,
                        err_path,
                        switch_to_outputs=switch_to_outputs,
                    )
                if switch_to_outputs:
                    self.section_tabs.setCurrentWidget(self.outputs_tab)
                self._poll_live()
            elif follow_mode != SBATCH_FOLLOW_MODE_NONE:
                # A corrupt persisted value is harmless: retain the familiar view.
                if out_path:
                    self.open_in_output_slot(0, out_path, switch_to_outputs=switch_to_outputs)
                if err_path:
                    self.open_in_output_slot(1, err_path, switch_to_outputs=switch_to_outputs)
            append_event({"type": "activate_slurm", "script": script_path, "out": out_path, "err": err_path})
