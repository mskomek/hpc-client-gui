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

from hpc_gui import __version__ as _APP_VERSION
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.trusted_api3 import (
    API3_LINTER_ID,
    API3_STUDIO_ID,
    api3_error_for_dir,
)

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

# Exact owning plugin identity per OpenFOAM host action (fail closed, no
# fallback). Dotted IDs are the API 3 release identities; short IDs are the
# legacy API 1/2 package identities which stay inert (pending) until a real
# API 3 path is proven. Any other id is rejected and never falls back to
# another plugin.
_OPENFOAM_ACTION_IDS: dict[str, tuple[str, ...]] = {
    "openfoam.open_studio": (API3_STUDIO_ID, "openfoam-case-studio"),
    "openfoam.new_case": (API3_STUDIO_ID, "openfoam-case-studio"),
    "openfoam.create_job_draft": (API3_STUDIO_ID, "openfoam-case-studio"),
    "openfoam.validate": (API3_LINTER_ID, "openfoam-linter"),
}

# Identities that may carry an API 3 executable/declarative path. Legacy
# short IDs never reach the API 3 on-disk gate; they stay pending.
_OPENFOAM_API3_IDS = frozenset({API3_LINTER_ID, API3_STUDIO_ID})

# OpenFOAM subset of the allowlist (W65 r10 inert registration; r14 live
# gate below reuses the same set).
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


def _openfoam_gate(action: str, plugin, host=None) -> tuple[bool, str]:
    """Fail-closed gate for one OpenFOAM host action.

    Verifies exact owning plugin id, required capability, app
    compatibility, API 3 static+on-disk integrity via
    ``api3_error_for_dir``, and a real callable framework callback when a
    host is supplied. Disabled/incompatible/corrupt/wrong-version/
    wrong-plugin and missing framework block visibly and never fall back
    to another plugin/callback. Legacy short identities stay pending
    (menu disabled, no execution) to preserve r10-r13 inert behavior.
    """
    manifest = getattr(plugin, "manifest", None)
    if manifest is None or getattr(manifest, "id", None) is None:
        return False, "plugin is not installed or missing manifest"
    required = ACTION_CAPABILITIES.get(action, ())
    if required:
        caps = set(getattr(manifest, "capabilities", None) or ())
        if not any(cap in caps for cap in required):
            return False, (
                f"plugin {manifest.id} lacks required capability "
                f"for {action!r}: needs {required}"
            )
    allowed_ids = _OPENFOAM_ACTION_IDS.get(action, ())
    if manifest.id not in allowed_ids:
        return False, (
            f"plugin {manifest.id!r} is not the owning plugin "
            f"for {action!r}"
        )
    # The old short IDs are deliberately inert while their API 2 payloads
    # remain untrusted. Return the explicit pending state before touching
    # activation storage; these historical InstalledPlugin test/upgrade
    # objects need not point at a current package directory.
    if manifest.id not in _OPENFOAM_API3_IDS:
        return False, OPENFOAM_PENDING_REASON
    try:
        if not is_app_compatible(
            getattr(manifest, "requires_app", ""), _APP_VERSION
        ):
            return False, (
                f"plugin {manifest.id}@{getattr(manifest, 'version', '?')} "
                f"is incompatible with app {_APP_VERSION} "
                f"(requires {getattr(manifest, 'requires_app', '')})"
            )
    except Exception:
        return False, "plugin compatibility evidence unavailable (fail closed)"
    # InstalledPlugin objects can remain in an open menu after a disable,
    # deactivation, or uninstall. Recheck live storage state at invocation,
    # and bind the object to the exact canonical <root>/packages/id/version
    # directory before any callback or executable loader is reached.
    from pathlib import Path

    from hpc_gui.plugins.storage import (
        plugin_package_dir,
        plugins_root,
        read_active_versions,
        read_disabled_ids,
    )

    try:
        root = Path(getattr(plugin, "plugin_root", None) or plugins_root()).resolve(strict=True)
        expected = plugin_package_dir(manifest.id, manifest.version, root).resolve(strict=True)
        actual = Path(plugin.directory).resolve(strict=True)
        if actual != expected:
            return False, "plugin package directory does not match its installed identity"
        if read_active_versions(root).get(manifest.id) != manifest.version:
            return False, "plugin version is not the currently active version"
        if manifest.id in read_disabled_ids(root):
            return False, "plugin is disabled"
    except (OSError, RuntimeError, ValueError) as exc:
        return False, f"plugin activation state unavailable (fail closed): {exc}"
    if manifest.id in _OPENFOAM_API3_IDS and getattr(manifest, "plugin_api", None) == 3:
        try:
            problem = api3_error_for_dir(manifest, plugin.directory)
        except Exception as exc:
            return False, f"openfoam integrity evidence unavailable: {exc}"
        if problem:
            return False, problem
    else:
        return False, OPENFOAM_PENDING_REASON
    if host is not None:
        method = _OPENFOAM_HOST_METHODS.get(action, "")
        handler = getattr(host, method, None) if method else None
        if not callable(handler):
            return False, (
                f"host callback {method!r} unavailable for {action!r} "
                f"(fail closed; no fallback)"
            )
    return True, ""


def is_openfoam_dispatch_ready(plugin=None) -> bool:
    """Return True only when an OpenFOAM host execution path is proven.

    Dynamic fail-closed gate (r14): exact owning identity, capability,
    app compatibility, API 3 static+on-disk integrity via
    ``api3_error_for_dir``, and (for dispatch) a real callable framework
    callback. Legacy short identities and empty production pins stay
    disabled. Never sets the code-owned ``OPENFOAM_DISPATCH_READY`` flag.
    """
    if plugin is None or getattr(plugin, "manifest", None) is None:
        return False
    for action in OPENFOAM_ACTIONS:
        if _OPENFOAM_ACTION_IDS.get(action) and plugin.manifest.id in _OPENFOAM_ACTION_IDS[action]:
            allowed, _ = _openfoam_gate(action, plugin, host=None)
            if allowed:
                return True
    return False


def is_allowed_action(action: str) -> bool:
    return action in ALLOWED_ACTIONS


def can_execute_action(action: str, plugin: InstalledPlugin) -> tuple[bool, str]:
    """Return (allowed, reason). Validates allowlist, capability guard, plugin integrity."""
    if action not in ALLOWED_ACTIONS:
        return False, f"unknown action {action!r}"
    if plugin is None or getattr(plugin, "manifest", None) is None:
        return False, "plugin is not installed or missing manifest"
    if action in OPENFOAM_ACTIONS:
        return _openfoam_gate(action, plugin, host=None)
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
        logger.warning("Blocked plugin menu action %r for plugin %s: %s", action, getattr(getattr(plugin, "manifest", None), "id", "?"), reason)
        return False

    # OpenFOAM live path (r14): fail closed, never fall back to another
    # plugin/callback. can_execute_action already verified identity,
    # capability, app compatibility and API 3 integrity; re-verify the
    # host callback here for the supplied host instance.
    if action in OPENFOAM_ACTIONS:
        gate_ok, gate_reason = _openfoam_gate(action, plugin, host=host)
        if not gate_ok:
            logger.warning(
                "Blocked plugin menu action %r for plugin %s: %s",
                action, plugin.manifest.id, gate_reason,
            )
            return False
        if host is None:
            logger.warning(
                "Blocked plugin menu action %r for plugin %s: %s",
                action, plugin.manifest.id,
                "host callback unavailable (fail closed; no fallback)",
            )
            return False
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

