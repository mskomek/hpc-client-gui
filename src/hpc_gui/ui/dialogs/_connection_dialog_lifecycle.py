from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
)


ProfileData = dict[str, Any]


class _ConnectionDialogLifecycleMixin:
    def _clamp_dialog_to_screen(self) -> None:
        screen = self.screen() or self.windowHandle().screen()
        if screen is None:
            return
        available = screen.availableGeometry().adjusted(16, 16, -16, -16)
        if self.height() > available.height():
            self.resize(self.width(), available.height())
        if self.width() > available.width():
            self.resize(available.width(), self.height())

    def _set_jump_children_enabled(self, enabled: bool) -> None:
        for widget in self._jump_child_widgets:
            widget.setEnabled(enabled)

    def showEvent(self, event) -> None:
        # Keep the dialog inside the screen from the start; the scroll area
        # absorbs any overflow instead of growing past the desktop.
        QDialog.showEvent(self, event)
        self._clamp_dialog_to_screen()

    def _set_advanced_visible(self, visible: bool) -> None:
        self.advanced_body.setVisible(visible)
        self.advanced_button.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )
        if visible:
            self._clamp_dialog_to_screen()

    def _open_plugin_manager(self) -> None:
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

            dialog = PluginManagerDialog(self)
            dialog.plugins_changed.connect(self._rebuild_system_template_menu)
            dialog.exec()
            self._rebuild_system_template_menu()
        except Exception:
            pass
