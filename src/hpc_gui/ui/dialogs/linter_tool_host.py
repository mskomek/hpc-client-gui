"""Host a Plugin API v2 linter-tool page inside a modal window.

Shared by the Plugin Manager ("Open tool") and the file-panel "send to
plugin" flows. Every interaction with plugin-supplied code stays inside
this module so a broken engine can never take a file panel down.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from hpc_gui.core.i18n import t

logger = logging.getLogger(__name__)


def host_tool_page(parent, tool, *, initial_paths=None, title=None) -> bool:
    """Show ``tool``'s page modally, optionally pre-loaded with files.

    Returns True when the page was created and shown; False when the
    engine failed and the user was already warned.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(
        title or f"{tool.title} — {tool.plugin_id}@{tool.version}"
    )
    dialog.resize(980, 680)
    layout = QVBoxLayout(dialog)
    try:
        page = tool.page_factory(
            parent=dialog, initial_paths=list(initial_paths or [])
        )
    except Exception as exc:
        logger.warning(
            "Linter tool page creation failed for %s", tool.plugin_id, exc_info=exc
        )
        QMessageBox.warning(parent, t("plugins.tool_open_failed"), str(exc))
        return False
    layout.addWidget(page)
    dialog.exec()
    return True
