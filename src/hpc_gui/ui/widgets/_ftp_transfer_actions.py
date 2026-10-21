"""FTP transfer-actions leaf for the file-manager FTP widget.

Owns ``FtpTransferActionsMixin``: selection helpers and the user-invoked
upload/download/save-as/drop/clipboard entries, including the repeat
activation debounce. The heavy panel-side flows live in the remote/local
panels and are reached via ``self`` and panel references.

Imports Qt-core plus lower-level core/i18n only — never local-panel
internals, FTP internals of other leaves, controllers, or other branches.
The remote-panel class is imported only for the drop-guard registry lookup,
preserving the established ftp→panels direction.
"""

from __future__ import annotations

from time import monotonic

from PySide6.QtWidgets import QFileDialog, QMessageBox

from hpc_gui.core.i18n import t, tr as _tr
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel


class FtpTransferActionsMixin:
    """Upload/download action ownership (mixed into ``FtpWidget``)."""

    session: object
    _ACTIVATION_DEBOUNCE_SECONDS: float

    @staticmethod
    def _selected_remote_paths(panel: RemoteDirPanel) -> list[str]:
        current = panel.tabs.currentWidget()
        for key, view in panel.views.items():
            if view is current:
                return panel.selected_paths(key)
        return panel.selected_paths()

    def upload_selected(self) -> bool:
        paths = self.local_panel.selected_paths()
        panel = self.active_remote_panel()
        if not paths:
            QMessageBox.information(self, t("common.info"), t("ftp.no_local_selection"))
            return False
        if not self.session or not self.session.get("connected") or not panel.current_dir:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        try:
            return panel._apply_local_upload_incremental(paths, panel.current_dir)
        finally:
            self.apply_settings()

    def _upload_local_path(self, path: str) -> None:
        panel = self.active_remote_panel()
        if self._is_repeated_activation_transfer("upload", path, panel.current_dir):
            return
        self._upload_local_paths([path])

    def _upload_local_paths(self, paths: list[str]) -> None:
        panel = self.active_remote_panel()
        clean_paths = [path for path in paths if path]
        if not clean_paths or not self.session or not self.session.get("connected") or not panel.current_dir:
            return
        try:
            panel._apply_local_upload_incremental(clean_paths, panel.current_dir)
        finally:
            self.apply_settings()

    def download_selected(self) -> bool:
        panel = self.active_remote_panel()
        paths = self._selected_remote_paths(panel)
        if not paths:
            QMessageBox.information(self, t("common.info"), t("ftp.no_remote_selection"))
            return False
        if not self.session or not self.session.get("connected"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        return self._download_remote_paths(panel, paths)

    def _download_remote_paths(self, panel: RemoteDirPanel, paths: list[str]) -> bool:
        """Download remote selections directly into the local panel folder."""
        clean_paths = [str(path) for path in paths if path]
        target_dir = str(self.local_panel.current_dir or "")
        if not clean_paths or not target_dir:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        if not self.session or not self.session.get("connected"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        try:
            return bool(panel._apply_remote_download_incremental(clean_paths, target_dir))
        except Exception as exc:
            # A frozen release must not let a context-menu slot exception
            # terminate the GUI process.
            QMessageBox.critical(self, t("common.error"), str(exc))
            return False
        finally:
            self.apply_settings()

    def _save_remote_paths_as(self, panel: RemoteDirPanel, paths: list[str]) -> bool:
        if not self.session or not self.session.get("connected"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        target_dir = QFileDialog.getExistingDirectory(
            self,
            _tr("dirs.save_as", "Save remote files as"),
            self.local_panel.current_dir,
        )
        if not target_dir:
            return False
        return self._download_remote_paths_to(panel, paths, target_dir)

    def _download_remote_paths_to(
        self, panel: RemoteDirPanel, paths: list[str], target_dir: str
    ) -> bool:
        try:
            return bool(panel._apply_remote_download_incremental(
                [str(path) for path in paths if path], str(target_dir)
            ))
        except Exception as exc:
            QMessageBox.critical(self, t("common.error"), str(exc))
            return False
        finally:
            self.apply_settings()

    def _download_remote_path(self, path: str) -> None:
        panel = self.active_remote_panel()
        if not path or not self.session or not self.session.get("connected"):
            return
        if self._is_repeated_activation_transfer("download", path, self.local_panel.current_dir):
            return
        try:
            panel._apply_remote_download_incremental(
                [path],
                self.local_panel.current_dir,
            )
        finally:
            self.apply_settings()

    def _is_repeated_activation_transfer(
        self,
        op: str,
        src: str,
        dst_dir: str,
    ) -> bool:
        key = (op, str(src or ""), str(dst_dir or ""))
        now = monotonic()
        cutoff = now - self._ACTIVATION_DEBOUNCE_SECONDS
        self._recent_activation_transfers = {
            recent_key: timestamp
            for recent_key, timestamp in self._recent_activation_transfers.items()
            if timestamp >= cutoff
        }
        previous = self._recent_activation_transfers.get(key)
        self._recent_activation_transfers[key] = now
        return previous is not None and now - previous < self._ACTIVATION_DEBOUNCE_SECONDS

    def _download_dropped_paths(self, paths: list[str], source_panel_id: str) -> None:
        panel = RemoteDirPanel._instances.get(source_panel_id)
        if panel is None or panel not in (self.panel_scratch, self.panel_home):
            QMessageBox.warning(self, t("common.error"), t("ftp.invalid_drop"))
            return
        panel._apply_remote_download_incremental(
            paths,
            self.local_panel.current_dir,
        )

    def _download_remote_clipboard_paths(
        self,
        paths: list[str],
        target_dir: str,
    ) -> None:
        panel = self.active_remote_panel()
        clean_paths = [path for path in paths if path]
        if not clean_paths or not self.session or not self.session.get("connected"):
            return
        try:
            panel._apply_remote_download_incremental(clean_paths, target_dir)
        finally:
            self.apply_settings()

__all__ = [
    "FtpTransferActionsMixin",
]
