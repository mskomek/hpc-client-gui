"""wx plugin manager model backed by the existing secure plugin services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.plugins.state import activate_version, remove_plugin, set_plugin_disabled
from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool


@dataclass(frozen=True)
class PluginCard:
    plugin_id: str
    name: str
    version: str
    installed: bool = False
    enabled: bool = True
    compatible: bool = True


class WxPluginManagerModel:
    def __init__(self, *, root=None, install: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self.root = root
        self.install = install
        self.cards: tuple[PluginCard, ...] = ()
        self.registry_source = "offline"

    def set_registry(self, entries: list[dict[str, Any]], source: str = "cache") -> None:
        self.registry_source = source if source in {"network", "cache", "offline"} else "offline"
        self.cards = tuple(
            PluginCard(str(item.get("id", "")), str(item.get("name", item.get("id", ""))), str(item.get("version", "")), bool(item.get("installed")), bool(item.get("enabled", True)), bool(item.get("compatible", True)))
            for item in entries if item.get("id")
        )

    def install_or_update(self, entry: dict[str, Any]) -> Any:
        return self.install(dict(entry)) if self.install and entry.get("id") else None

    def rollback(self, plugin_id: str, version: str) -> None:
        activate_version(plugin_id, version, root=self.root)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        set_plugin_disabled(plugin_id, not enabled, root=self.root)

    def remove(self, plugin_id: str) -> list[str]:
        return remove_plugin(plugin_id, root=self.root)

    def open_trusted_tool(self, manifest: dict[str, Any], opener: Callable[[dict[str, Any]], Any]) -> Any:
        if not is_approved_trusted_tool(manifest):
            raise PermissionError("trusted tool is not approved")
        return opener(dict(manifest))


__all__ = ["PluginCard", "WxPluginManagerModel"]
