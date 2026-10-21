"""Remote metadata leaf for the file-manager remote panel.

Owns ``RemoteMetadataMixin``: per-entry file metadata concerns — the comparison
column rendering (statuses supplied externally by the FTP comparison
controller) and the permission apply flow (`files.chmod` with the permissions
dialog). The dialog itself lives in ``_remote_permissions_dialog``; listing
refresh and error surfacing live in their own leaves/facade and are reached
via ``self``.

Imports Qt and lower-level core/services only — never the local panel, FTP
widget, controllers, or another branch's private implementation. Sibling
imports (``_FILE_MODE_ROLE`` from ``_remote_tree_view``, ``_PermissionsDialog``
from ``_remote_permissions_dialog``) follow the recorded one-directional
branch pattern: neither sibling imports this leaf, no cycle.
"""

from __future__ import annotations

import stat as pystat
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QTreeWidget, QTreeWidgetItem

from hpc_gui.core.i18n import t, tr as _tr
from hpc_gui.services.directory_comparison import CompareStatus
from hpc_gui.ui.widgets._remote_permissions_dialog import _PermissionsDialog
from hpc_gui.ui.widgets._remote_tree_view import _FILE_MODE_ROLE, _SORT_NAME_ROLE


class RemoteMetadataMixin:
    """Comparison display + permission apply (mixed into ``RemoteDirPanel``)."""

    session: object
    views: dict
    tabs: object
    _comparison_statuses: object

    def set_comparison_visible(self, visible: bool) -> None:
        for view in list(getattr(self, "views", {}).values()):
            try:
                if visible:
                    view.showColumn(4)
                else:
                    view.hideColumn(4)
            except RuntimeError:
                continue
        if not visible:
            self.clear_comparison_statuses()

    def clear_comparison_statuses(self) -> None:
        self._comparison_statuses = None
        for view in list(getattr(self, "views", {}).values()):
            try:
                for index in range(view.topLevelItemCount()):
                    item = view.topLevelItem(index)
                    item.setText(4, "")
                    item.setToolTip(4, "")
            except RuntimeError:
                continue

    def _comparison_status_labels(self) -> dict[CompareStatus, str]:
        return {
            CompareStatus.SAME: t("ftp.cmp_same"),
            CompareStatus.LOCAL_ONLY: t("ftp.cmp_local_only"),
            CompareStatus.REMOTE_ONLY: t("ftp.cmp_remote_only"),
            CompareStatus.TYPE_MISMATCH: t("ftp.cmp_type_differs"),
            CompareStatus.SIZE_DIFFERENT: t("ftp.cmp_size_different"),
            CompareStatus.LOCAL_NEWER: t("ftp.cmp_local_newer"),
            CompareStatus.REMOTE_NEWER: t("ftp.cmp_remote_newer"),
        }

    def _render_comparison_statuses(self) -> None:
        statuses = self._comparison_statuses or {}
        labels = self._comparison_status_labels()
        for view in list(self.views.values()):
            try:
                items = [view.topLevelItem(i) for i in range(view.topLevelItemCount())]
            except RuntimeError:
                continue
            for item in items:
                if bool(item.data(0, Qt.ItemDataRole.UserRole + 2)):
                    continue
                name = str(item.data(0, _SORT_NAME_ROLE) or "")
                status = statuses.get(name)
                if status is None:
                    item.setText(4, "")
                    item.setToolTip(4, "")
                    continue
                label = labels.get(status, str(status.value))
                item.setText(4, "=" if status is CompareStatus.SAME else label)
                item.setToolTip(4, label)

    def apply_comparison_statuses(
        self, statuses: dict[str, CompareStatus]
    ) -> None:
        self._comparison_statuses = dict(statuses)
        self._render_comparison_statuses()

    def change_permissions(
        self,
        paths: Optional[List[str]] = None,
        selected_items: Optional[List[QTreeWidgetItem]] = None,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        if paths is None:
            current = self.tabs.currentWidget()  # type: ignore[union-attr]
            view = current if isinstance(current, QTreeWidget) else self.views["all"]
            paths = self._selected_paths_from_view(view)  # type: ignore[attr-defined]
            selected_items = view.selectedItems()
        paths = [path for path in (paths or []) if path]
        if not paths:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))  # type: ignore[arg-type]
            return False

        initial_mode: Optional[int] = None
        target_name = ""
        if len(paths) == 1 and selected_items:
            try:
                mode = int(selected_items[0].data(0, _FILE_MODE_ROLE) or 0)
            except Exception:
                mode = 0
            if mode:
                initial_mode = pystat.S_IMODE(mode)
            target_name = selected_items[0].text(0)

        dialog = _PermissionsDialog(self, initial_mode, target_name)  # type: ignore[arg-type]
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        mode = dialog.selected_mode()
        if mode is None:
            QMessageBox.warning(
                self,  # type: ignore[arg-type]
                t("common.error"),
                _tr("dirs.permissions_invalid", "Enter a valid octal mode such as 755 or 0644."),
            )
            return False

        files = self.session["files"]
        try:
            for path in paths:
                files.chmod(path, mode)
        except Exception as exc:
            self._show_op_error(  # type: ignore[attr-defined]
                _tr("dirs.permissions_failed", "Permission update failed: {err}").format(err=exc)
            )
            return False

        self._refresh_from_ui(force=True)  # type: ignore[attr-defined]
        return True


__all__ = [
    "RemoteMetadataMixin",
]
