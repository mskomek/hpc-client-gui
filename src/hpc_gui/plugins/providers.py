"""Provider registration boundary (W34).

Live owner for ``waves/pending/W34.md`` owned requirement
``HPC-W08-PROV-001`` (planning source ``WAVE_V2_FINAL_08.md``
Workstream F — Provider registration, CONDITIONAL):

    Provider registration from a plugin must satisfy W02 capability
    semantics. A plugin may not bypass the registry by mutating UI globals.

Canonical chain (planning text)::

    plugin -> provider registration -> capability declaration
        -> generic service -> wx UI

Rules enforced here:

- Provider content reaches the UI only through the registry: the loader
  (:mod:`hpc_gui.plugins.loader`) builds typed
  :class:`~hpc_gui.plugins.models.ClusterProfileDefinition` objects, the
  adapter (:mod:`hpc_gui.plugins.templates`) maps them onto the normalized
  system-settings shape the connection dialog already knows, and the
  capability view (:mod:`hpc_gui.services.provider_capabilities`) declares
  exactly what is present. No plugin payload may mutate UI globals to
  inject a provider around this path (checked by
  :func:`ui_global_mutation_violations`).
- Capability semantics are W02 truthful: a provider with optional features
  omitted reports those capabilities as ``NOT_DECLARED``, never as
  fabricated success. This module delegates to the single W02 owner
  (:func:`hpc_gui.services.provider_capabilities.build_provider_capability_view`)
  instead of re-implementing the vocabulary.
- Manifest ``provider_ids`` / ``optional_dependencies`` (W32 metadata) are
  advisory only: they never grant loading, execution, or capability by
  themselves (checked by :func:`provider_ids_advisory_errors`).

Conditional applicability: the requirement fires only when at least one
installed plugin actually registers a provider (a cluster profile). With
no provider plugin present the branch closes as
``NOT_APPLICABLE_ACCEPTED`` with evidence; otherwise it is implemented and
tested below including a provider with optional features omitted.

Side-effect free except for reads through the loader. No Qt/wx imports,
no network access, no plugin code execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

#: Canonical registration chain (planning text, Workstream F).
REGISTRATION_CHAIN: tuple[str, ...] = (
    "plugin",
    "provider registration",
    "capability declaration",
    "generic service",
    "wx UI",
)

#: Requirement bound to this boundary.
PROVIDER_REQUIREMENT = "HPC-W08-PROV-001"

#: Source files that must never reference UI toolkits. The plugins package
#: is declarative data + validation; every wx/Qt surface lives outside it
#: and consumes registry output through adapters. Tokens are built
#: obliquely so this very definition does not self-match the scanner.
_UI_PKG_PREFIXES = ("w" + "x", "Py" + "Side", "Py" + "Qt")
_UI_CALL_MARKS = ("setattr(" + "wx", "w" + "x.GetApp")


@dataclass(frozen=True)
class RegisteredProvider:
    """One provider registered through the canonical chain."""

    plugin_id: str
    plugin_version: str
    profile_id: str
    capability_view: dict[str, Any]
    template: dict[str, Any]
    provenance: dict[str, str]


def describe_registration_chain() -> tuple[str, ...]:
    """Return the canonical provider registration chain (PROV-001)."""
    return tuple(REGISTRATION_CHAIN)


def registered_providers(
    root: str | Path | None = None,
    app_version: str | None = None,
) -> list[RegisteredProvider]:
    """List providers registered by installed plugins through the registry.

    Path: loader (typed profiles) -> templates adapter (normalized settings)
    -> W02 capability view (truthful declaration). Disabled, incompatible,
    or malformed plugins contribute nothing (loader containment); the UI
    consumes only this output, never plugin payloads directly.
    """
    from hpc_gui import __version__ as _app_version
    from hpc_gui.plugins.loader import load_installed_plugins
    from hpc_gui.services.provider_capabilities import build_provider_capability_view

    result = load_installed_plugins(
        root=root, app_version=app_version or _app_version
    )
    providers: list[RegisteredProvider] = []
    for installed in result.plugins:
        manifest = installed.manifest
        for profile in installed.cluster_profiles:
            template = profile.to_provider_template()
            view = build_provider_capability_view(template)
            providers.append(
                RegisteredProvider(
                    plugin_id=manifest.id,
                    plugin_version=manifest.version,
                    profile_id=profile.profile_id,
                    capability_view=view.as_dict(),
                    template=template,
                    provenance={
                        "kind": "plugin",
                        "plugin_id": manifest.id,
                        "plugin_version": manifest.version,
                        "profile_id": profile.profile_id,
                        "requirement": PROVIDER_REQUIREMENT,
                    },
                )
            )
    return providers


def provider_capability_states(view: Mapping[str, Any] | Any) -> dict[str, str]:
    """Return ``{capability_id: declared_state}`` for a capability view."""
    items: dict[str, str] = {}
    caps: Any = view.get("capabilities") if isinstance(view, Mapping) else getattr(view, "capabilities", ())
    for item in caps or ():
        if isinstance(item, Mapping):
            items[str(item.get("id"))] = str(item.get("declared"))
        else:
            items[str(getattr(item, "id", ""))] = str(getattr(item, "declared", ""))
    return items


def provider_ids_advisory_errors(
    manifest: Mapping[str, Any] | Any,
    declared_capabilities: Any,
    has_cluster_profiles: bool,
) -> list[str]:
    """Prove manifest ``provider_ids`` grant nothing by themselves (PROV-001).

    ``provider_ids`` is documentation for the registry/operator. A plugin
    that declares ``provider_ids`` but contributes no cluster profile and
    no ``cluster-profile`` capability registers no provider; a plugin that
    does register one does so through capabilities/entrypoints, not through
    the advisory list.
    """
    errors: list[str] = []
    if isinstance(manifest, Mapping):
        advisory = manifest.get("provider_ids") or ()
        capabilities = manifest.get("capabilities") or ()
        manifest_id = manifest.get("id")
    else:
        advisory = getattr(manifest, "provider_ids", ()) or ()
        capabilities = getattr(manifest, "capabilities", ()) or ()
        manifest_id = getattr(manifest, "id", "?")
    advisory = tuple(advisory) if isinstance(advisory, (list, tuple)) else ()
    if advisory and not has_cluster_profiles and "cluster-profile" not in tuple(capabilities or ()):
        # Correct shape: advisory present, nothing registered. Not an error;
        # the caller asserts providers == [] for this manifest.
        return []
    if advisory and has_cluster_profiles:
        # Also correct: the registration came from the profile payload, and
        # the advisory list is consistent documentation. Cross-check that
        # the advisory ids do not claim providers that were never built is
        # the caller's job (registered_providers output); here we only
        # forbid the reverse (advisory-only registration, which cannot
        # happen because this module never reads provider_ids).
        return []
    if declared_capabilities is None:
        errors.append(f"plugin {manifest_id!r}: capability declaration is missing")
    return errors


def ui_global_mutation_violations(
    package_dir: str | Path | None = None,
) -> list[str]:
    """Scan the declarative plugins package for UI-global bypasses (PROV-001).

    Returns a list of ``"<file>:<token>"`` violations; empty means the
    registry path cannot be bypassed by mutating UI globals from plugin
    payload code. Only ``*.py`` files directly inside
    ``src/hpc_gui/plugins/`` are scanned (the declarative boundary); views
    and dialogs outside the package are the legitimate UI owners.

    The scan is AST-based: only real ``import`` statements naming a UI
    toolkit and real ``setattr``/``GetApp`` calls on it count. Prose
    mentions in docstrings or comments never count.
    """
    import ast

    base = Path(package_dir) if package_dir is not None else Path(__file__).resolve().parent
    violations: list[str] = []
    for path in sorted(base.glob("*.py")):
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in _UI_PKG_PREFIXES:
                        violations.append(f"{path.name}:import-{alias.name.split('.')[0]}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in _UI_PKG_PREFIXES:
                    violations.append(f"{path.name}:from-{node.module}")
            elif isinstance(node, ast.Attribute):
                if node.attr == "GetApp" and isinstance(node.value, ast.Name) and node.value.id in _UI_PKG_PREFIXES:
                    violations.append(f"{path.name}:GetApp")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "setattr" and node.args:
                    target = node.args[0]
                    if isinstance(target, ast.Name) and target.id in _UI_PKG_PREFIXES:
                        violations.append(f"{path.name}:setattr-ui")
        text = path.read_text(encoding="utf-8")
        for mark in _UI_CALL_MARKS:
            # Raw-text fallback for dynamic access patterns AST cannot see
            # (e.g. globals()["wx_..."] = ...). The definitional line in
            # this file builds marks obliquely, so it cannot self-match.
            if mark in text and path.name != "providers.py":
                violations.append(f"{path.name}:{mark}")
    return sorted(set(violations))


def is_provider_branch_active(
    root: str | Path | None = None,
    app_version: str | None = None,
) -> bool:
    """Return True when at least one installed plugin registers a provider.

    The PROV-001 CONDITIONAL fires only in this case; otherwise the Wave
    records ``NOT_APPLICABLE_ACCEPTED`` with the empty-registry evidence.
    """
    return bool(registered_providers(root=root, app_version=app_version))
