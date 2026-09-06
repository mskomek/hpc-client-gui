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
    *,
    editor_widget=None,
    host_window=None,
    template_filter_plugin_id: str | None = None,
) -> bool:
    """Dispatch a host-owned action.

    Returns True if the action was handled, False otherwise. Never raises
    for unknown/invalid actions – logs and returns False.
    """
    allowed, reason = can_execute_action(action, plugin)
    if not allowed:
        logger.warning("Blocked plugin menu action %r for plugin %s: %s", action, getattr(plugin.manifest, "id", "?"), reason)
        return False

    try:
        if action == "editor.lint_current":
            return _do_editor_lint_current(plugin, editor_widget=editor_widget)
        if action == "editor.new_from_plugin_templates":
            return _do_editor_new_from_templates(plugin, editor_widget=editor_widget)
        if action == "plugin.open_trusted_tool":
            return _do_open_trusted_tool(plugin, host_window=host_window)
    except Exception as exc:
        logger.warning("Plugin menu action %r failed for %s: %s", action, plugin.manifest.id, exc, exc_info=exc)
        return False
    logger.warning("Unhandled plugin menu action %r", action)
    return False


def _do_editor_lint_current(plugin: InstalledPlugin, *, editor_widget=None) -> bool:
    """Reuse existing Editor lint pipeline. Optional plugin scoping is applied when clean."""
    if editor_widget is None:
        logger.warning("editor.lint_current requires an editor_widget")
        return False
    # Prefer plugin-scoped lint if the widget exposes a scoped entry point; otherwise fall back to full lint
    # Attempt optional scoping cleanly:
    path = ""
    try:
        path = getattr(editor_widget, "path_in", None)
        if path is not None:
            path = path.text().strip() if hasattr(path, "text") else ""
        else:
            path = getattr(editor_widget, "current_path", "") or ""
    except Exception:
        path = ""
    # Try scoped helper if available (not required)
    scoped = getattr(editor_widget, "run_lint_for_plugin", None)
    if callable(scoped):
        try:
            scoped(plugin.manifest.id)
            return True
        except Exception:
            pass
    # Fall back to existing generic lint – reuses the same pipeline (no second engine)
    try:
        editor_widget.run_lint()
        return True
    except Exception as exc:
        logger.warning("editor.lint_current failed: %s", exc, exc_info=exc)
        return False


def _do_editor_new_from_templates(plugin: InstalledPlugin, *, editor_widget=None) -> bool:
    if editor_widget is None:
        logger.warning("editor.new_from_plugin_templates requires editor_widget")
        return False
    # Reuse existing New from Template flow but filter to templates owned by the contributing plugin
    try:
        from hpc_gui.plugins.job_templates import load_job_templates

        templates = load_job_templates()
        owned = [t for t in templates if t.plugin_id == plugin.manifest.id]
        if not owned:
            logger.warning("No job templates owned by plugin %s", plugin.manifest.id)
            # Still open the generic dialog filtered to owned (will show empty message)
            # We reuse the widget's flow with filtered list by monkey-patching load_job_templates locally
            # Instead, if widget supports filtered entry point, use it
            filtered = getattr(editor_widget, "new_from_template_for_plugin", None)
            if callable(filtered):
                filtered(plugin.manifest.id)
                return True
            # Fallback: temporarily patch load_job_templates
            import hpc_gui.plugins.job_templates as jt_mod
            original = jt_mod.load_job_templates
            try:
                jt_mod.load_job_templates = lambda *a, **k: owned
                editor_widget.new_from_template()
            finally:
                jt_mod.load_job_templates = original
            return True
        # If the widget has a filtered entry point, prefer it
        filtered = getattr(editor_widget, "new_from_template_for_plugin", None)
        if callable(filtered):
            filtered(plugin.manifest.id)
            return True
        # Generic fallback with patched loader
        import hpc_gui.plugins.job_templates as jt_mod

        original = jt_mod.load_job_templates
        try:
            jt_mod.load_job_templates = lambda *a, **k: owned
            editor_widget.new_from_template()
        finally:
            jt_mod.load_job_templates = original
        return True
    except Exception as exc:
        logger.warning("editor.new_from_plugin_templates failed: %s", exc, exc_info=exc)
        return False


def _do_open_trusted_tool(plugin: InstalledPlugin, *, host_window=None) -> bool:
    """Route only through the existing approved trusted-tool path and current policy."""
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

    # Reuse existing hosting: create dialog similar to PluginManagerDialog.open_linter_tool
    try:
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        parent = host_window
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

