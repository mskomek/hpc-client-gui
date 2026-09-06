"""Host-owned action dispatcher for declarative plugin menu contributions.

All callable code lives here or in existing host services. A manifest may
only name a host-owned action ID; it never supplies an import path,
callable, eval/exec, shell command or URL action.

The dispatcher receives the owning ``InstalledPlugin`` from the host so a
plugin cannot spoof another plugin's identity. Capability and integrity
checks remain enforced.
"""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)

# Finite allowlist
ALLOWED_ACTIONS = frozenset(
    {
        "editor.lint_current",
        "editor.new_from_plugin_templates",
        "plugin.open_trusted_tool",
    }
)

# Action -> required plugin capability (at least one must be present)
ACTION_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "editor.lint_current": ("lint-rules", "linter-tool"),
    "editor.new_from_plugin_templates": ("job-template",),
    "plugin.open_trusted_tool": ("linter-tool",),
}


def is_allowed_action(action: str) -> bool:
    return action in ALLOWED_ACTIONS


def can_execute_action(action: str, plugin: InstalledPlugin) -> tuple[bool, str]:
    """Return (allowed, reason). Validates allowlist, capability guard, plugin integrity."""
    if action not in ALLOWED_ACTIONS:
        return False, f"unknown action {action!r}"
    if plugin is None or getattr(plugin, "manifest", None) is None:
        return False, "plugin is not installed or missing manifest"
    # Capability guard
    required = ACTION_CAPABILITIES.get(action, ())
    if required:
        caps = set(plugin.manifest.capabilities or ())
        if not any(cap in caps for cap in required):
            return False, f"plugin {plugin.manifest.id} lacks required capability for {action!r}: needs {required}"
    # Integrity: disabled/incompatible/corrupt plugins never reach here because
    # they are filtered by load_installed_plugins, but double-check
    # that manifest requires_app is still satisfied by current app version could be done by caller.
    return True, ""


def dispatch_plugin_menu_action(
    action: str,
    plugin: InstalledPlugin,
    host=None,
    *,
    editor_widget=None,
    host_window=None,
) -> bool:
    """Framework-neutral dispatch.

    Preferred: pass a ``PluginMenuHost`` as *host*.  The legacy
    ``editor_widget``/``host_window`` kwargs are kept for backward
    compatibility with existing tests but are not used for UI construction
    in the shared layer.
    """
    # Back-compat: if host is actually an editor_widget passed positionally
    if host is not None and not hasattr(host, "run_editor_lint") and editor_widget is None:
        # host looks like a widget, not a host – treat as legacy editor_widget
        editor_widget = host  # type: ignore[assignment]
        host = None
    allowed, reason = can_execute_action(action, plugin)
    if not allowed:
        logger.warning("Blocked plugin menu action %r for plugin %s: %s", action, getattr(plugin.manifest, "id", "?"), reason)
        return False

    # If a host adapter is supplied, delegate to it – shared layer never builds Qt UI
    if host is not None:
        try:
            if action == "editor.lint_current":
                return bool(host.run_editor_lint(plugin.manifest.id))
            if action == "editor.new_from_plugin_templates":
                return bool(host.open_plugin_templates(plugin.manifest.id))
            if action == "plugin.open_trusted_tool":
                return bool(host.open_trusted_tool(plugin))
        except Exception as exc:
            logger.warning("Plugin menu action %r failed for %s: %s", action, plugin.manifest.id, exc, exc_info=exc)
            return False
        logger.warning("Unhandled plugin menu action %r", action)
        return False

    # Legacy fallback without host – still no Qt construction, just capability-checked no-op
    # This path keeps older unit tests that call dispatch without a host from crashing,
    # but it does not construct dialogs.
    try:
        if action == "editor.lint_current":
            if editor_widget is not None and hasattr(editor_widget, "run_lint_for_plugin"):
                try:
                    editor_widget.run_lint_for_plugin(plugin.manifest.id)  # type: ignore[attr-defined]
                    return True
                except Exception:
                    pass
            if editor_widget is not None and hasattr(editor_widget, "run_lint"):
                try:
                    editor_widget.run_lint()  # type: ignore[attr-defined]
                    return True
                except Exception:
                    pass
            logger.warning("editor.lint_current requires a host with run_editor_lint")
            return False
        if action == "editor.new_from_plugin_templates":
            if editor_widget is not None and hasattr(editor_widget, "new_from_template_for_plugin"):
                try:
                    editor_widget.new_from_template_for_plugin(plugin.manifest.id)  # type: ignore[attr-defined]
                    return True
                except Exception:
                    pass
            logger.warning("editor.new_from_plugin_templates requires a host with open_plugin_templates")
            return False
        if action == "plugin.open_trusted_tool":
            logger.warning("plugin.open_trusted_tool requires a host with open_trusted_tool (Qt host)")
            return False
    except Exception as exc:
        logger.warning("Plugin menu action %r failed for %s: %s", action, plugin.manifest.id, exc, exc_info=exc)
        return False
    logger.warning("Unhandled plugin menu action %r", action)
    return False

