"""wx host for plugin menu actions – never touches Qt."""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)


class WxPluginMenuHost:
    """wx implementation – routes only where a real wx path exists."""

    def __init__(self, editor_page=None, *, parent=None, lifecycle=None):
        self._editor = editor_page
        self._parent = parent
        self._lifecycle = lifecycle

    def run_editor_lint(self, plugin_id: str) -> bool:
        scoped = getattr(self._editor, "run_lint_for_plugin", None)
        if not callable(scoped):
            return False
        try:
            return bool(scoped(plugin_id))
        except Exception as exc:
            logger.warning("wx run_editor_lint failed: %s", exc, exc_info=exc)
            return False

    def open_plugin_templates(self, plugin_id: str) -> bool:
        # Try to use wx editor's plugin-scoped template flow if it exists
        ed = self._editor
        if ed is None:
            return False
        # Check if plugin actually has templates
        try:
            from hpc_gui.plugins.job_templates import load_job_templates

            templates = load_job_templates(plugin_id=plugin_id)
            if not templates:
                return False
        except Exception:
            return False
        # Try wx editor's filtered entry point if available
        scoped = getattr(ed, "new_from_template_for_plugin", None)
        if callable(scoped):
            try:
                return bool(scoped(plugin_id))
            except Exception as exc:
                logger.warning("wx open_plugin_templates failed: %s", exc, exc_info=exc)
                return False
        # No real wx path – disable safely
        logger.info("wx open_plugin_templates has no real path for %s", plugin_id)
        return False

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool
        from hpc_gui.plugins.linter_tools import load_tool_for_plugin
        from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation

        if not is_approved_trusted_tool(plugin.manifest):
            return False
        if getattr(self._lifecycle, "shutdown_started", False):
            return False
        try:
            from hpc_gui.wx_ansys_view import show_ansys_lint

            tool = load_tool_for_plugin(plugin)
            show_ansys_lint(self._parent or self._editor, AnsysToolPresentation(tool),
                            lifecycle=self._lifecycle)
            return True
        except Exception as exc:
            logger.warning("wx open_trusted_tool failed: %s", exc, exc_info=exc)
            return False
