"""Qt host for plugin menu actions – owns the Qt UI."""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)


class QtPluginMenuHost:
    """Qt implementation of PluginMenuHost."""

    def __init__(self, editor_widget=None, host_window=None):
        self._editor = editor_widget
        self._window = host_window

    def run_editor_lint(self, plugin_id: str) -> bool:
        editor = self._editor
        if editor is None:
            logger.warning("run_editor_lint requires editor_widget")
            return False
        # Prefer plugin-scoped lint
        scoped = getattr(editor, "run_lint_for_plugin", None)
        if callable(scoped):
            try:
                scoped(plugin_id)
                return True
            except Exception:
                pass
        try:
            editor.run_lint()  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            logger.warning("run_editor_lint failed: %s", exc, exc_info=exc)
            return False

    def open_plugin_templates(self, plugin_id: str) -> bool:
        editor = self._editor
        if editor is None:
            logger.warning("open_plugin_templates requires editor_widget")
            return False
        scoped = getattr(editor, "new_from_template_for_plugin", None)
        if callable(scoped):
            try:
                scoped(plugin_id)
                return True
            except Exception as exc:
                logger.warning("open_plugin_templates failed: %s", exc, exc_info=exc)
                return False
        logger.warning("open_plugin_templates: editor missing new_from_template_for_plugin")
        return False

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
        from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool

        if not is_approved_trusted_tool(plugin.manifest):
            logger.warning("plugin %s is not an approved trusted tool", plugin.manifest.id)
            return False
        try:
            tool = load_tool_for_plugin(plugin)
        except ToolLoadError as exc:
            logger.warning("Cannot load trusted tool %s: %s", plugin.manifest.id, exc)
            return False
        except Exception as exc:
            logger.warning("Unexpected error loading trusted tool %s: %s", plugin.manifest.id, exc, exc_info=exc)
            return False

        # Qt UI construction lives here, not in the shared service
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout

            parent = self._window
            dialog = QDialog(parent)
            dialog.setWindowTitle(f"{tool.title} — {plugin.manifest.id}@{tool.version}")
            dialog.resize(980, 680)
            layout = QVBoxLayout(dialog)
            page = tool.page_factory(parent=dialog)
            layout.addWidget(page)
            dialog.exec()
            return True
        except Exception as exc:
            logger.warning("Opening trusted tool %s failed: %s", plugin.manifest.id, exc, exc_info=exc)
            return False
