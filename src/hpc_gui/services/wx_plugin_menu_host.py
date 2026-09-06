"""wx host for plugin menu actions – never touches Qt."""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)


class WxPluginMenuHost:
    """wx implementation – routes only where a real wx path exists."""

    def __init__(self, editor_page=None):
        self._editor = editor_page

    def run_editor_lint(self, plugin_id: str) -> bool:
        # No verified wx lint pipeline – explicitly unsupported
        logger.info("wx run_editor_lint not supported for %s", plugin_id)
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
                scoped(plugin_id)
                return True
            except Exception as exc:
                logger.warning("wx open_plugin_templates failed: %s", exc, exc_info=exc)
                return False
        # No real wx path – disable safely
        logger.info("wx open_plugin_templates has no real path for %s", plugin_id)
        return False

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        # wx has no Qt dialog – explicitly unsupported, do not fabricate
        logger.info("wx open_trusted_tool not supported for %s", plugin.manifest.id)
        return False
