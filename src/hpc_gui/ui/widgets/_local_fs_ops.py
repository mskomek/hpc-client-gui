"""Local filesystem-operations leaf for the file-manager local panel.

Owns the ``LocalFsOpsMixin``: clipboard copy/cut/paste, drive listing,
navigation helpers, create/delete/rename, and open-with/explorer flows.
Imports services and Qt only — never remote panel, FTP, or controllers.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QTreeWidgetItem,
)

from hpc_gui.config.storage import get_file_association, set_file_association
from hpc_gui.core.i18n import t
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.local_files import list_windows_drives

logger = logging.getLogger(__name__)


class LocalFsOpsMixin:
    """Filesystem mutation and navigation helpers (mixed into ``LocalDirPanel``)."""

    current_dir: str
    _history: list[str]
    _tab_dirs: dict
    _local_clipboard: tuple[str, list[str]] | None
    tree: object
    tabs: object
    path: object

    # -- navigation ------------------------------------------------------
    def show_drives(self) -> None:
        self.tree.clear()  # type: ignore[union-attr]
        self.path.setText(t("ftp.drives"))  # type: ignore[union-attr]
        for entry in list_windows_drives():
            self._add_entry(entry.name, entry.path, True, 0, 0)  # type: ignore[attr-defined]
        self.tree.apply_sort()  # type: ignore[union-attr]

    def go_back(self) -> None:
        if self._history:
            self.set_dir(self._history.pop(), remember=False)  # type: ignore[attr-defined]

    def go_parent(self) -> None:
        parent = str(Path(self.current_dir).parent)
        if parent != self.current_dir:
            self.set_dir(parent)  # type: ignore[attr-defined]

    # -- selection -------------------------------------------------------
    def _selected_items(self) -> list[QTreeWidgetItem]:
        return [
            item
            for item in self.tree.selectedItems()  # type: ignore[union-attr]
            if item.data(0, Qt.ItemDataRole.UserRole)
            and not bool(item.data(0, Qt.ItemDataRole.UserRole + 2))
        ]

    def selected_paths(self) -> list[str]:
        return [
            str(item.data(0, Qt.ItemDataRole.UserRole))
            for item in self._selected_items()
        ]

    # -- clipboard -------------------------------------------------------
    def _set_system_file_clipboard(self, paths: list[str]) -> None:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        QApplication.clipboard().setMimeData(mime)

    def copy_selected(self) -> bool:
        paths = self.selected_paths()  # type: ignore[attr-defined]
        if not paths:
            return False
        self._local_clipboard = ("copy", paths)
        self._set_system_file_clipboard(paths)
        return True

    def cut_selected(self) -> bool:
        paths = self.selected_paths()  # type: ignore[attr-defined]
        if not paths:
            return False
        self._local_clipboard = ("move", paths)
        self._set_system_file_clipboard(paths)
        return True

    @staticmethod
    def _unique_destination(target: Path) -> Path:
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        for index in range(1, 1000):
            candidate = parent / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
        return parent / f"{stem} copy{suffix}"

    def paste_into_current_dir(self) -> bool:
        remote_clip = get_file_clipboard().get()
        if remote_clip and remote_clip.paths:
            self.remoteClipboardPasteRequested.emit(  # type: ignore[attr-defined]
                list(remote_clip.paths),
                self.current_dir,
            )
            return True

        if not self._local_clipboard:
            return False
        op, paths = self._local_clipboard
        target_dir = Path(self.current_dir)
        if not target_dir.is_dir():
            return False

        changed = False
        for source_text in paths:
            source = Path(source_text)
            if not source.exists():
                continue
            if source.parent == target_dir and op == "move":
                continue
            destination = self._unique_destination(target_dir / source.name)
            try:
                if op == "move":
                    shutil.move(str(source), str(destination))
                elif source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
            except OSError as exc:
                QMessageBox.warning(self, t("common.error"), str(exc))  # type: ignore[arg-type]
                return changed
            changed = True
        if changed:
            if op == "move":
                self._local_clipboard = None
            self.refresh()  # type: ignore[attr-defined]
        return changed

    # -- explorer / create / delete / rename / open-with -----------------
    def open_selected_in_file_explorer(self) -> bool:
        selected = self._selected_items()  # type: ignore[attr-defined]
        if len(selected) == 1:
            path = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
            target = path if path.is_dir() else path.parent
        else:
            target = Path(self.current_dir)
        if not target.exists():
            return False
        if os.name == "nt":
            subprocess.Popen(["explorer", str(target)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        return True

    def create_directory(self, *, enter: bool = False) -> bool:
        name, ok = QInputDialog.getText(
            self,  # type: ignore[arg-type]
            t("dirs.new_folder"),
            t("dirs.new_folder_label"),
        )
        if not ok or not name.strip():
            return False
        target = Path(self.current_dir, name.strip())
        try:
            target.mkdir()
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))  # type: ignore[arg-type]
            return False
        if enter:
            return self.set_dir(str(target))  # type: ignore[attr-defined]
        self.refresh()  # type: ignore[attr-defined]
        return True

    def delete_selected(self) -> bool:
        paths = [Path(path) for path in self.selected_paths()]  # type: ignore[attr-defined]
        if not paths:
            return False
        if QMessageBox.question(self, t("common.confirm"), t("dirs.delete_confirm")) != QMessageBox.StandardButton.Yes:  # type: ignore[arg-type]
            return False
        for path in paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except OSError as exc:
                QMessageBox.warning(self, t("common.error"), str(exc))  # type: ignore[arg-type]
                return False
        self.refresh()  # type: ignore[attr-defined]
        return True

    def rename_selected(self) -> bool:
        selected = self._selected_items()
        if len(selected) != 1:
            return False
        old = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
        new_name, ok = QInputDialog.getText(
            self,
            t("dirs.rename"),
            t("dirs.rename_label"),
            text=old.name,
        )
        if not ok or not new_name.strip():
            return False
        target = old.with_name(new_name.strip())
        try:
            old.rename(target)
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return False
        self.refresh()
        return True

    def open_selected_with_program(self) -> bool:
        selected = self._selected_items()  # type: ignore[attr-defined]
        if len(selected) != 1:
            return False
        target = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
        if not target.is_file():
            return False
        program = get_file_association(target.suffix)
        if not program or not Path(program).exists():
            program, _ = QFileDialog.getOpenFileName(
                self,  # type: ignore[arg-type]
                t("files.open_with_select_program"),
                "",
                t("files.open_with_program_filter"),
            )
            program = str(program or "").strip()
            if not program:
                return False
            if target.suffix:
                answer = QMessageBox.question(
                    self,  # type: ignore[arg-type]
                    t("files.open_with_save_title"),
                    t("files.open_with_save_prompt").format(
                        extension=target.suffix.lower()
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    set_file_association(target.suffix, program)
        try:
            subprocess.Popen([program, str(target)])
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))  # type: ignore[arg-type]
            return False
        return True


__all__ = ["LocalFsOpsMixin"]
