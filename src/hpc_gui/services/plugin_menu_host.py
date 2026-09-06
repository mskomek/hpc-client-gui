"""Host adapter for plugin menu actions – framework-neutral.

The shared dispatch layer validates the allowlist/capability and then
delegates to a host-owned implementation.  Qt and wx provide concrete
hosts; the shared layer never imports PySide6/wx.
"""

from __future__ import annotations

from typing import Protocol

from hpc_gui.plugins.models import InstalledPlugin


class PluginMenuHost(Protocol):
    """Framework-specific host that actually performs the action."""

    def run_editor_lint(self, plugin_id: str) -> bool:
        """Run the editor lint pipeline for the given plugin."""
        ...

    def open_plugin_templates(self, plugin_id: str) -> bool:
        """Open the New-from-Template flow filtered to the plugin."""
        ...

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        """Open the approved trusted tool for the plugin."""
        ...
