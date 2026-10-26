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
        # W65 r10: OpenFOAM studio/linter registration (HOST-002/G02).
        # Allowlisted so the r9 validator-clean manifest fragment resolves
        # to a known host action instead of "unknown action", but kept
        # inert by the readiness gate below until plugin/host readiness
        # is verified in a VM (no execution, no UI construction).
        "openfoam.open_studio",
        "openfoam.new_case",
        "openfoam.create_job_draft",
        "openfoam.validate",
    }
)

# OpenFOAM subset of the allowlist (W65 r10 inert registration).
OPENFOAM_ACTIONS = frozenset(
    {
        "openfoam.open_studio",
        "openfoam.new_case",
        "openfoam.create_job_draft",
        "openfoam.validate",
    }
)

# Code-owned readiness flag: False until an OpenFOAM package identity is
# installed AND a real (wx/Qt) host execution path is verified in a VM.
# Reactivation trigger: N package install (G47) + VM-proven host path.
OPENFOAM_DISPATCH_READY = False

OPENFOAM_PENDING_REASON = (
    "openfoam host binding pending readiness "
    "(menu stays disabled; no execution)"
)

# Host method names for the future live path (r10 stubs return False).
_OPENFOAM_HOST_METHODS = {
    "openfoam.open_studio": "run_openfoam_studio",
    "openfoam.new_case": "new_openfoam_case",
    "openfoam.create_job_draft": "create_openfoam_job_draft",
    "openfoam.validate": "validate_with_openfoam_linter",
}

# Action -> required plugin capability (at least one must be present)
ACTION_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "editor.lint_current": ("lint-rules", "linter-tool"),
    "editor.new_from_plugin_templates": ("job-template",),
    "plugin.open_trusted_tool": ("linter-tool",),
    # W65 r10: studio actions need the generic application-tools surface;
    # validate reuses the same lint surfaces as the existing lint action.
    "openfoam.open_studio": ("application-tools",),
    "openfoam.new_case": ("application-tools",),
    "openfoam.create_job_draft": ("application-tools",),
    "openfoam.validate": ("lint-rules", "linter-tool"),
}


def is_openfoam_dispatch_ready(plugin=None) -> bool:
    """Return True only when an OpenFOAM host execution path is proven.

    R10 always returns False (code-owned flag above): the registration
    path (allowlist + capability) is live, but dispatch stays inert so
    menu items render disabled and nothing executes. Reactivation needs
    an installed OpenFOAM package identity plus a VM-verified host path.
    """
    return bool(OPENFOAM_DISPATCH_READY)


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
    # W65 r10 readiness gate: OpenFOAM actions are registered but inert
    # until a host execution path is proven. Items stay disabled; the
    # reason distinguishes "pending" from "unknown action".
    if action in OPENFOAM_ACTIONS and not is_openfoam_dispatch_ready(plugin):
        return False, OPENFOAM_PENDING_REASON
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

    # W65 r10: OpenFOAM actions stay inert even when a host is supplied.
    # No UI is constructed and no plugin code runs; the readiness gate
    # above already blocks, this is defense in depth for direct callers.
    if action in OPENFOAM_ACTIONS:
        if not is_openfoam_dispatch_ready(plugin):
            logger.warning("Blocked plugin menu action %r for plugin %s: %s", action, plugin.manifest.id, OPENFOAM_PENDING_REASON)
            return False
        if host is not None:
            try:
                handler = getattr(host, _OPENFOAM_HOST_METHODS[action], None)
                if callable(handler):
                    return bool(handler(plugin))
            except Exception as exc:
                logger.warning("Plugin menu action %r failed for %s: %s", action, plugin.manifest.id, exc, exc_info=exc)
                return False
        logger.warning("Unhandled plugin menu action %r", action)
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

