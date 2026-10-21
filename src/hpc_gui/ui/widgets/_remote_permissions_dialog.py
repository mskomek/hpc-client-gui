"""Remote permissions-dialog leaf for the file-manager remote panel.

Owns ``_parse_chmod_mode`` and ``_PermissionsDialog`` (octal/special-bit
checkbox sync, GUI thread only). The permission *apply* flow
(``RemoteDirPanel.change_permissions``) stays in the facade next to the other
transfer-adjacent flows because it reads the item-data mode role owned by the
tree-view leaf; it constructs this dialog through the normal facade→leaf edge.

Imports Qt and lower-level core/config only — never the local panel, FTP
widget, controllers, dialogs of other flows, or another branch's private
implementation.
"""

from __future__ import annotations

import re
import stat as pystat
from typing import Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.i18n import t, tr as _tr


def _parse_chmod_mode(value: str) -> Optional[int]:
    text = (value or "").strip()
    if text.startswith("0"):
        text = text[1:]
    if not re.fullmatch(r"[0-7]{3,4}", text):
        return None
    return int(text, 8)


class _PermissionsDialog(QDialog):
    _GROUPS = (
        ("dirs.permissions_owner", "Owner"),
        ("dirs.permissions_group", "Group"),
        ("dirs.permissions_others", "Others"),
    )
    _PERMISSIONS = (
        ("dirs.permissions_read", "Read", 0o4),
        ("dirs.permissions_write", "Write", 0o2),
        ("dirs.permissions_execute", "Execute", 0o1),
    )
    _SPECIAL_PERMISSIONS = (
        ("dirs.permissions_setuid", "Set-user-ID", 0o4000),
        ("dirs.permissions_setgid", "Set group-ID", 0o2000),
        ("dirs.permissions_sticky", "Sticky bit", 0o1000),
    )

    def __init__(self, parent: QWidget, initial_mode: Optional[int], target_name: str = "") -> None:
        super().__init__(parent)
        self._syncing = False
        self._boxes: Dict[Tuple[int, int], QCheckBox] = {}
        self._special_boxes: Dict[int, QCheckBox] = {}
        self.setWindowTitle(_tr("dirs.permissions_change_title", "Change file attributes"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        intro = QLabel(
            _tr(
                "dirs.permissions_intro",
                'Please select the new attributes for the selected item "{name}".',
            ).format(name=target_name or _tr("dirs.permissions_selected_items", "selected items"))
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for group_index, (group_key, group_fallback) in enumerate(self._GROUPS):
            box_group = QGroupBox(
                _tr("dirs.permissions_group_title", "{group} permissions").format(
                    group=_tr(group_key, group_fallback)
                )
            )
            row = QHBoxLayout(box_group)
            for permission_index, (key, fallback, _bit) in enumerate(self._PERMISSIONS):
                box = QCheckBox()
                box.setText(_tr(key, fallback))
                box.stateChanged.connect(self._update_code_from_checks)
                row.addWidget(box)
                self._boxes[(permission_index, group_index)] = box
            row.addStretch(1)
            layout.addWidget(box_group)

        special_group = QGroupBox(_tr("dirs.permissions_special_title", "Public permissions"))
        special_row = QHBoxLayout(special_group)
        for key, fallback, bit in self._SPECIAL_PERMISSIONS:
            box = QCheckBox(_tr(key, fallback))
            box.stateChanged.connect(self._update_code_from_checks)
            special_row.addWidget(box)
            self._special_boxes[bit] = box
        special_row.addStretch(1)
        layout.addWidget(special_group)

        code_row = QHBoxLayout()
        code_row.addWidget(QLabel(_tr("dirs.permissions_chmod_label", "Chmod:")))
        self.mode_edit = QLineEdit()
        self.mode_edit.setMaxLength(5)
        self.mode_edit.setPlaceholderText("00755")
        self.mode_edit.textEdited.connect(self._update_checks_from_code)
        code_row.addWidget(self.mode_edit)
        layout.addLayout(code_row)

        help_label = QLabel(
            _tr(
                "dirs.permissions_help",
                "You can enter a textual mode change (chmod), or the new mode bits in octal.",
            )
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.recurse_check = QCheckBox(_tr("dirs.permissions_recurse", "Recurse into subdirectories"))
        self.recurse_check.setEnabled(False)
        layout.addWidget(self.recurse_check)
        self.recurse_all_radio = QRadioButton(
            _tr("dirs.permissions_recurse_all", "Apply to all files and directories")
        )
        self.recurse_files_radio = QRadioButton(
            _tr("dirs.permissions_recurse_files", "Apply to files only")
        )
        self.recurse_dirs_radio = QRadioButton(
            _tr("dirs.permissions_recurse_dirs", "Apply to directories only")
        )
        self.recurse_all_radio.setChecked(True)
        for radio in (self.recurse_all_radio, self.recurse_files_radio, self.recurse_dirs_radio):
            radio.setEnabled(False)
            layout.addWidget(radio)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._set_checks_from_mode(0o644 if initial_mode is None else pystat.S_IMODE(initial_mode))
        self._update_code_from_checks()

    def _mode_from_checks(self) -> int:
        mode = 0
        for group_index in range(3):
            digit = 0
            for permission_index, (_key, _fallback, bit) in enumerate(self._PERMISSIONS):
                if self._boxes[(permission_index, group_index)].isChecked():
                    digit |= bit
            mode = (mode << 3) | digit
        for bit, box in self._special_boxes.items():
            if box.isChecked():
                mode |= bit
        return mode

    def _set_checks_from_mode(self, mode: int) -> None:
        self._syncing = True
        try:
            plain_mode = mode & 0o7777
            for bit, box in self._special_boxes.items():
                box.setChecked(bool(plain_mode & bit))
            for group_index in range(3):
                shift = (2 - group_index) * 3
                digit = (plain_mode >> shift) & 0o7
                for permission_index, (_key, _fallback, bit) in enumerate(self._PERMISSIONS):
                    self._boxes[(permission_index, group_index)].setChecked(bool(digit & bit))
        finally:
            self._syncing = False

    def _update_code_from_checks(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            self.mode_edit.setText(f"0{self._mode_from_checks():04o}")
        finally:
            self._syncing = False

    def _update_checks_from_code(self, value: str) -> None:
        if self._syncing:
            return
        mode = _parse_chmod_mode(value)
        if mode is None:
            return
        self._set_checks_from_mode(mode)

    def selected_mode(self) -> Optional[int]:
        return _parse_chmod_mode(self.mode_edit.text())

    def accept(self) -> None:
        if self.selected_mode() is None:
            QMessageBox.warning(
                self,
                t("common.error"),
                _tr("dirs.permissions_invalid", "Enter a valid octal mode such as 755 or 0644."),
            )
            return
        super().accept()


__all__ = [
    "_PermissionsDialog",
    "_parse_chmod_mode",
]
