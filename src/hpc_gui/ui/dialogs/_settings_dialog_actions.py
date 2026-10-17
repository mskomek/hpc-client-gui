from __future__ import annotations
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)
from hpc_gui.config.storage import (
    clear_file_association,
    set_file_association,
    update_settings,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_speed_test import run_transfer_speed_test
from hpc_gui.ui.async_call import AsyncCall
from hpc_gui.config.system_profile import (
    format_remote_path,
    normalize_system_settings,
    hpc_default_remote_paths,
)

def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class _SettingsDialogActions:
    def _reset_terminal_graphics(self) -> None:
            self.cb_terminal_graphics_mode.setCurrentIndex(
                max(0, self.cb_terminal_graphics_mode.findData("auto"))
            )
            self._terminal_graphics_auto_compatibility = False
            update_settings({
                "terminal_graphics_mode": "auto",
                "terminal_graphics_auto_compatibility": False,
            })
            self.lbl_terminal_graphics_remembered.setText(t("settings.terminal_graphics_not_remembered"))

    def _run_transfer_speed_test(self) -> None:
            session = self._session
            files = session.get("files") if session else None
            if not session or not session.get("connected") or not files:
                QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
                return
            cfg = session.get("cfg")
            system = normalize_system_settings(getattr(cfg, "system_settings", None))
            remote_dir = format_remote_path(system["scratch_dir"], getattr(cfg, "username", "user"))
            self.btn_transfer_speed_test.setEnabled(False)
            worker = AsyncCall(("speed-test", id(self)), lambda: run_transfer_speed_test(files, remote_dir=remote_dir, size_mib=int(self.cb_transfer_speed_test_size.currentData() or 8)))
            self._speed_test_worker = worker
            def finished(_token, result) -> None:
                self._speed_test_worker = None
                self.btn_transfer_speed_test.setEnabled(True)
                QMessageBox.information(self, _tr("settings.transfer_speed_test", "Remote transfer speed test"), _tr("settings.transfer_speed_test_result", "Size: {size} MiB\\nUpload: {upload} MiB/s\\nDownload: {download} MiB/s").format(size=f"{result['size_mib']:.0f}", upload=f"{result['upload_mib_s']:.2f}", download=f"{result['download_mib_s']:.2f}"))
            def failed(_token, error) -> None:
                self._speed_test_worker = None
                self.btn_transfer_speed_test.setEnabled(True)
                QMessageBox.warning(self, _tr("common.error", "Error"), str(error))
            worker.signals.finished.connect(finished)
            worker.signals.failed.connect(failed)
            QThreadPool.globalInstance().start(worker)

    def _clear_remote_directory_cache_clicked(self) -> None:
            if self._clear_remote_directory_cache is not None:
                self._clear_remote_directory_cache()

    def _reset_ftp_defaults(self) -> None:
            defaults = hpc_default_remote_paths()
            self.ftp_scratch_dir.setText(defaults["scratch_dir"])
            self.ftp_home_dir.setText(defaults["home_dir"])

    def _refresh_file_association_list(self) -> None:
            self.file_associations_list.clear()
            for extension, program in sorted(self._file_associations.items()):
                self.file_associations_list.addItem(f"{extension} -> {program}")
            empty = not self._file_associations
            self.btn_change_file_association.setEnabled(not empty)
            self.btn_clear_file_association.setEnabled(not empty)

    def _selected_file_association_extension(self) -> str:
            item = self.file_associations_list.currentItem()
            if item is None:
                return ""
            return item.text().split(" -> ", 1)[0].strip()

    def _change_selected_file_association(self) -> None:
            extension = self._selected_file_association_extension()
            if not extension:
                QMessageBox.information(
                    self,
                    t("common.info"),
                    t("settings.file_association_none_selected"),
                )
                return
            program, _ = QFileDialog.getOpenFileName(
                self,
                t("files.open_with_select_program"),
                self._file_associations.get(extension, ""),
                t("files.open_with_program_filter"),
            )
            if not program:
                return
            self._file_associations = set_file_association(extension, program)
            self._refresh_file_association_list()

    def _clear_selected_file_association(self) -> None:
            extension = self._selected_file_association_extension()
            if not extension:
                QMessageBox.information(
                    self,
                    t("common.info"),
                    t("settings.file_association_none_selected"),
                )
                return
            self._file_associations = clear_file_association(extension)
            self._refresh_file_association_list()
