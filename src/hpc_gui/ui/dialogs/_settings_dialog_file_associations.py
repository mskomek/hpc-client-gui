from __future__ import annotations


from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)

from hpc_gui.config.storage import (
    set_file_association,
)
from hpc_gui.core.i18n import t


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class _SettingsDialogFileAssociationsMixin:
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
