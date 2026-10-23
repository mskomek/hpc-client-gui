"""Collection of valid Plugins-menu contributions from installed plugins."""

from __future__ import annotations

import logging

from hpc_gui.plugins.ui_contributions_model import PluginMenuContribution
from hpc_gui.plugins.ui_contributions_parser import _parse_plugins_menu

logger = logging.getLogger(__name__)


def collect_plugin_menu_contributions(installed_plugins) -> list[PluginMenuContribution]:
    """Collect valid contributions from installed plugins, deterministic ordering."""
    contributions: list[PluginMenuContribution] = []
    for plugin in sorted(installed_plugins, key=lambda p: p.manifest.id):
        try:
            raw_manifest = getattr(plugin.manifest, "ui_contributions", None)
            if raw_manifest is None:
                # Try to get from manifest if it was stored as dict in PluginManifest
                # The loader will have already parsed, but we also fallback to reading the
                # plugin directory's manifest.json if needed (defensive)
                continue
            # raw_manifest is expected to be dict with plugins_menu inside
            # But PluginManifest stores ui_contributions as mapping if present
            # We need to parse it: expect raw is the ui_contributions dict
            if isinstance(raw_manifest, dict) and "plugins_menu" in raw_manifest:
                # raw_manifest is the ui_contributions dict; parse its plugins_menu
                contrib, errs = _parse_plugins_menu(raw_manifest.get("plugins_menu"), plugin.manifest.id, plugin.manifest.version)
                if errs:
                    logger.warning("Skipping plugin %s contribution: %s", plugin.manifest.id, "; ".join(errs))
                    continue
                if contrib:
                    contributions.append(contrib)
            elif isinstance(raw_manifest, dict):
                # This could already be parsed contribution? Another path
                pass
            else:
                logger.warning("plugin %s ui_contributions unexpected type %r", plugin.manifest.id, type(raw_manifest))
        except Exception as exc:
            logger.warning("Failed to collect contribution for plugin %s: %s", getattr(plugin.manifest, "id", "?"), exc, exc_info=exc)
            continue
    # Alternative path: if PluginManifest.ui_contributions holds raw dict, above works.
    # Also handle case where InstalledPlugin has direct attribute contribution
    # Check for attribute plugin_contribution or similar
    # For now, also look for extra field stored on InstalledPlugin
    for plugin in installed_plugins:
        # Check if plugin has an already parsed attribute (future extension)
        alt = getattr(plugin, "plugin_menu_contribution", None)
        if isinstance(alt, PluginMenuContribution):
            if alt not in contributions:
                # dedup by plugin_id; sorting
                contributions = [c for c in contributions if c.plugin_id != alt.plugin_id]
                contributions.append(alt)
    contributions.sort(key=lambda c: (c.label.casefold(), c.plugin_id.casefold()))
    return contributions
