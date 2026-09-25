"""wx plugin manager model backed by the existing secure plugin services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from hpc_gui import __version__
from hpc_gui.plugins.compatibility import entry_is_app_compatible
from hpc_gui.plugins.state import activate_version, remove_plugin, set_plugin_disabled


def _parse_version(value: object):
    try:
        from packaging.version import InvalidVersion, Version

        return Version(str(value or ""))
    except Exception:
        return None


def _is_newer(candidate: str, current: str) -> bool:
    try:
        from packaging.version import InvalidVersion, Version

        return Version(str(candidate)) > Version(str(current))
    except Exception:
        return False


@dataclass(frozen=True)
class PluginCard:
    plugin_id: str
    name: str
    version: str
    installed: bool = False
    enabled: bool = True
    compatible: bool = True
    description: str = ""
    capabilities: tuple[str, ...] = ()
    update_available: bool = False
    active_version: str | None = None


def _search_text_for_card(card: PluginCard) -> str:
    parts = [card.plugin_id, card.name, card.version, card.description, *card.capabilities]
    return " ".join(str(p or "") for p in parts).lower()


def _group_latest_registry_entries(
    entries: list[dict[str, Any]], app_version: str
) -> list[tuple[dict[str, Any], list[str]]]:
    """Group registry entries by plugin id, latest-compatible wins.

    Reuses the Qt dialog grouping rule so wx and Qt offer the same catalogue:
    the latest app-compatible version is primary; when no version is
    compatible the highest version is shown as an incompatible card.
    Registry order never decides which version is latest.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        groups.setdefault(str(entry.get("id", "")), []).append(entry)
    grouped: list[tuple[dict[str, Any], list[str]]] = []
    for entries_in_group in groups.values():
        parsed: list[tuple[Any | None, dict[str, Any]]] = [
            (_parse_version(e.get("version")), e) for e in entries_in_group
        ]
        with_versions = [item for item in parsed if item[0] is not None]
        pool = (
            [item for item in with_versions if entry_is_app_compatible(item[1], app_version)]
            or with_versions
            or parsed
        )

        def _sort_key(item: tuple[Any | None, dict[str, Any]]):
            version, _entry = item
            if version is None:
                return (0, str(_entry.get("version") or ""))
            try:
                return (1, version)
            except Exception:
                return (0, str(_entry.get("version") or ""))

        best_version, best = max(pool, key=_sort_key)
        others = sorted(
            {
                str(e.get("version"))
                for _, e in parsed
                if e is not best and e.get("version") != best.get("version")
            },
        )
        # Sort others newest-first where parseable.
        def _other_key(value: str):
            parsed_value = _parse_version(value)
            if parsed_value is None:
                return (0, value)
            return (1, parsed_value)

        others_sorted = sorted(others, key=_other_key, reverse=True)
        grouped.append((best, others_sorted))
    grouped.sort(key=lambda item: str(item[0].get("name") or item[0].get("id") or ""))
    return grouped


class WxPluginManagerModel:
    VALID_VIEWS = ("discover", "installed", "updates")

    def __init__(
        self,
        *,
        root=None,
        install: Callable[[dict[str, Any]], Any] | None = None,
        fetcher: Callable[[str, int], bytes] | None = None,
        app_version: str | None = None,
    ) -> None:
        self.root = root
        self.install = install
        self.fetcher = fetcher
        self.app_version = app_version or __version__
        self.cards: tuple[PluginCard, ...] = ()
        self.registry_source = "offline"
        self.registry_entries: dict[str, dict[str, Any]] = {}
        self.other_versions: dict[str, tuple[str, ...]] = {}

    def set_registry(self, entries: list[dict[str, Any]], source: str = "cache") -> None:
        self.registry_source = source if source in {"network", "cache", "offline"} else "offline"
        cards: list[PluginCard] = []
        for item in entries:
            if not item.get("id"):
                continue
            capabilities = item.get("capabilities")
            if not isinstance(capabilities, list):
                legacy = str(item.get("type") or "")
                capabilities = [legacy] if legacy else []
            cards.append(
                PluginCard(
                    str(item.get("id", "")),
                    str(item.get("name", item.get("id", ""))),
                    str(item.get("version", "")),
                    bool(item.get("installed")),
                    bool(item.get("enabled", True)),
                    bool(item.get("compatible", True)),
                    str(item.get("description", "") or ""),
                    tuple(str(c) for c in capabilities if str(c)),
                    bool(item.get("update_available", False)),
                    str(item.get("active_version") or item.get("version") or "") or None,
                )
            )
        self.cards = tuple(cards)
        # Keep raw entries for installer handoff (fail-closed install path).
        self.registry_entries = {
            str(item.get("id")): dict(item) for item in entries if item.get("id")
        }
        self.other_versions = {}

    def build_cards_from_registry(
        self,
        registry: dict[str, Any] | None,
        source: str,
        *,
        root=None,
        app_version: str | None = None,
    ) -> tuple[PluginCard, ...]:
        """Merge registry + installed + compat into truthful cards.

        Uses only production services: active versions, disabled ids, and the
        fail-closed ``entry_is_app_compatible`` gate. The configured
        production root is honoured (``root`` overrides only for tests).
        """
        from hpc_gui.plugins.storage import read_active_versions, read_disabled_ids

        effective_root = root if root is not None else self.root
        effective_app = app_version or self.app_version
        self.registry_source = source if source in {"network", "cache", "offline"} else "offline"
        entries: list[dict[str, Any]] = []
        if isinstance(registry, dict):
            raw = registry.get("plugins", [])
            if isinstance(raw, list):
                entries = [e for e in raw if isinstance(e, dict)]
        try:
            active = read_active_versions(effective_root)
        except Exception:
            active = {}
        try:
            disabled = read_disabled_ids(effective_root)
        except Exception:
            disabled = set()
        grouped = _group_latest_registry_entries(entries, effective_app)
        cards: list[PluginCard] = []
        raw_by_id: dict[str, dict[str, Any]] = {}
        others_by_id: dict[str, tuple[str, ...]] = {}
        for best, others in grouped:
            plugin_id = str(best.get("id", ""))
            version = str(best.get("version", ""))
            compatible = bool(entry_is_app_compatible(best, effective_app))
            active_version = active.get(plugin_id)
            installed_here = bool(
                plugin_id in active and active[plugin_id] == version
            )
            update_available = bool(
                compatible
                and active_version
                and not installed_here
                and _is_newer(version, active_version)
            )
            capabilities = best.get("capabilities")
            if not isinstance(capabilities, list) or not capabilities:
                legacy = str(best.get("type") or "")
                capabilities = [legacy] if legacy else []
            cards.append(
                PluginCard(
                    plugin_id=plugin_id,
                    name=str(best.get("name", plugin_id)),
                    version=version,
                    installed=bool(plugin_id in active),
                    enabled=plugin_id not in disabled,
                    compatible=compatible,
                    description=str(best.get("description", "") or ""),
                    capabilities=tuple(str(c) for c in capabilities if str(c)),
                    update_available=update_available,
                    active_version=active_version,
                )
            )
            raw_by_id[plugin_id] = dict(best)
            others_by_id[plugin_id] = tuple(others)
        # Installed plugins absent from the registry stay visible under
        # Manage Installed (never silently dropped).
        registry_ids = {c.plugin_id for c in cards}
        for plugin_id in sorted(active):
            if plugin_id in registry_ids:
                continue
            cards.append(
                PluginCard(
                    plugin_id=plugin_id,
                    name=plugin_id,
                    version=str(active.get(plugin_id) or ""),
                    installed=True,
                    enabled=plugin_id not in disabled,
                    compatible=True,
                    description="",
                    capabilities=(),
                    update_available=False,
                    active_version=str(active.get(plugin_id) or ""),
                )
            )
        cards.sort(key=lambda c: (c.name or c.plugin_id).lower())
        self.cards = tuple(cards)
        self.registry_entries = raw_by_id
        self.other_versions = others_by_id
        return self.cards

    def filtered_cards(self, view: str = "discover", needle: str = "") -> tuple[PluginCard, ...]:
        """Distinct Browse/Manage/Updates states plus a truthful search filter."""
        normalized = str(view or "discover").strip().lower()
        if normalized not in self.VALID_VIEWS:
            normalized = "discover"
        query = str(needle or "").strip().lower()
        selected: list[PluginCard] = []
        for card in self.cards:
            if normalized == "installed" and not card.installed:
                continue
            if normalized == "updates" and not (card.update_available and card.installed):
                continue
            if query and query not in _search_text_for_card(card):
                continue
            selected.append(card)
        return tuple(selected)

    def registry_entry_for(self, plugin_id: str) -> dict[str, Any] | None:
        entry = self.registry_entries.get(str(plugin_id))
        return dict(entry) if entry is not None else None

    def install_or_update(self, entry: dict[str, Any]) -> Any:
        # Fail-closed: no installer callback or no id means no backend action.
        if self.install is None:
            return None
        if not isinstance(entry, dict) or not entry.get("id"):
            return None
        return self.install(dict(entry))

    def default_installer(self, entry: dict[str, Any]) -> Any:
        """Production installer path (exact-file protocol, fail-closed)."""
        from hpc_gui.plugins.installer import install_plugin_from_registry

        if not isinstance(entry, dict) or not entry.get("id"):
            return None
        full = self.registry_entry_for(str(entry.get("id"))) or dict(entry)
        # The backend independently rejects incompatible/invalid plugins;
        # UI-side checks are never the sole enforcement.
        return install_plugin_from_registry(
            full,
            root=self.root,
            app_version=self.app_version,
            fetcher=self.fetcher,
        )

    def install_with_default_or_injected(self, entry: dict[str, Any]) -> Any:
        """Prefer the injected test callback; fall back to the real backend."""
        if self.install is not None:
            return self.install_or_update(entry)
        return self.default_installer(entry)

    def rollback(self, plugin_id: str, version: str) -> None:
        activate_version(plugin_id, version, root=self.root)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        set_plugin_disabled(plugin_id, not enabled, root=self.root)

    def remove(self, plugin_id: str) -> list[str]:
        return remove_plugin(plugin_id, root=self.root)

    def open_trusted_tool(self, manifest: dict[str, Any], opener: Callable[[dict[str, Any]], Any]) -> Any:
        from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool

        if not is_approved_trusted_tool(manifest):
            raise PermissionError("trusted tool is not approved")
        return opener(dict(manifest))


__all__ = ["PluginCard", "WxPluginManagerModel"]
