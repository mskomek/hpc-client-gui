"""Remote transfer-UI leaf for the file-manager remote panel.

Owns ``RemoteTransferUiMixin``: transfer session wiring (mode/output-target/
activity-callback providers, dialog visibility) and the user-invoked transfer
entries (template upload menu, file upload, download). The heavy planning and
execution flows live in the transfer leaves and are reached via ``self``.

Imports Qt and lower-level core only — never the local panel, FTP widget,
controllers, or another branch's private implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox

from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_mode import BINARY, normalize_transfer_mode
from hpc_gui.ui.dialogs.transfer_dialog import TransferItem


class RemoteTransferUiMixin:
    """Transfer session wiring + user entries (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    views: dict
    tabs: object

    def set_transfer_mode_provider(
        self, provider: Optional[Callable[[str], str]]
    ) -> None:
        self._transfer_mode_provider = provider  # type: ignore[attr-defined]

    def set_output_target_provider(
        self,
        provider: Optional[Callable[[], List[Tuple[str, str]]]],
    ) -> None:
        self._output_target_provider = provider  # type: ignore[attr-defined]

    def set_transfer_activity_callback(
        self,
        callback: Optional[Callable[[str, List[TransferItem], str], None]],
    ) -> None:
        self._transfer_activity_callback = callback  # type: ignore[attr-defined]

    def set_local_target_refresh_callback(
        self,
        callback: Optional[Callable[[str], None]],
    ) -> None:
        """Set a callback used to refresh local transfer targets after success."""
        self._local_target_refresh_callback = callback  # type: ignore[attr-defined]

    def set_transfer_dialog_visible(self, visible: bool) -> None:
        self._show_transfer_dialog = bool(visible)  # type: ignore[attr-defined]

    def _requested_transfer_mode(self, path: str) -> str:
        if self._transfer_mode_provider is None:  # type: ignore[attr-defined]
            return BINARY
        try:
            return normalize_transfer_mode(self._transfer_mode_provider(path), BINARY)  # type: ignore[attr-defined]
        except Exception:
            return BINARY

    def _template_upload_path(self) -> Path:
        return Path(__file__).resolve().parents[4] / "templates" / "extract_iso.py"

    def show_template_upload_menu(self) -> None:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return

        menu = QMenu(self)
        act_extract_iso = menu.addAction(
            t("dirs.template_extract_iso")
        )
        chosen = menu.exec(self.btn_template_upload.mapToGlobal(self.btn_template_upload.rect().bottomLeft()))
        if chosen != act_extract_iso:
            return
        self.upload_template_file(self._template_upload_path())

    def upload_template_file(self, template_path: Path) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return False
        if not template_path.exists():
            QMessageBox.warning(
                self,
                t("common.error"),
                t("dirs.template_missing").format(path=str(template_path)),
            )
            return False
        return self._apply_local_upload_incremental(
            [str(template_path)],
            self.current_dir,
        )

    # ---------- upload / download ----------
    def upload_files(self):
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))  # type: ignore[arg-type]
            return
        paths, _ = QFileDialog.getOpenFileNames(self, t("dirs.upload"))  # type: ignore[arg-type]
        if not paths:
            return
        self._apply_local_upload_incremental(paths, self.current_dir)  # type: ignore[attr-defined]

    def download_selected(self):
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        tab = self.tabs.currentWidget()
        tab_key = "all"
        for k, v in self.views.items():
            if v is tab:
                tab_key = k
                break
        sel = self.selected_paths(tab_key)
        if not sel:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))
            return
        target_dir = QFileDialog.getExistingDirectory(
            self, t("dirs.download_selected")       )
        if not target_dir:
            return
        self._apply_remote_download_incremental(sel, target_dir)


__all__ = [
    "RemoteTransferUiMixin",
]
