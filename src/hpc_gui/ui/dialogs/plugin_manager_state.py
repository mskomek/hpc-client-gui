"""Pure plugin-manager state (Wave M01).

Qt-free ownership of the Plugin Manager dialog's business rules: capability
labels, PEP 440 version ordering, registry grouping, install summaries and
error mapping. The Qt dialog (``plugin_manager_dialog.py``) and its card
builders (``plugin_manager_cards.py``) call into this module; this module
never imports Qt or ``hpc_gui.ui`` so the dependency direction stays acyclic
and wx-neutral code can reuse the rules.
"""

from __future__ import annotations

from packaging.version import InvalidVersion, Version

from hpc_gui.core.i18n import t
from hpc_gui.plugins.compatibility import (
    effective_requires_app,
    entry_is_app_compatible,
)
from hpc_gui.plugins.registry_client import RegistryError

# Human-readable labels for Plugin API v1/v2 capability identifiers. Raw
# identifiers must never appear as primary UI text.
_CAPABILITY_LABEL_KEYS = {
    "cluster-profile": "plugins.capability_cluster_profile",
    "lint-rules": "plugins.capability_lint_rules",
    "job-template": "plugins.capability_job_templates",
    "application-tools": "plugins.capability_application_tools",
    "linter-tool": "plugins.capability_linter_tool",
}


def capability_label(capability: str) -> str:
    """Translated, user-facing label for a capability identifier."""
    key = _CAPABILITY_LABEL_KEYS.get(str(capability or "").strip())
    return t(key) if key else str(capability or "")


def entry_sort_key(entry: dict):
    return str(entry.get("name") or entry.get("id") or "")


def parse_version(value: object) -> Version | None:
    try:
        return Version(str(value or ""))
    except (InvalidVersion, TypeError):
        return None


def is_newer_version(candidate: str, current: str) -> bool:
    """PEP 440 comparison; unparseable versions never count as updates."""
    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return False


def is_installed(entry: dict, active: dict[str, str]) -> bool:
    return (
        entry.get("id") in active and active[entry["id"]] == entry.get("version")
    )


def entry_capabilities(entry: dict) -> list[str]:
    """Capabilities for display: the authoritative array when present,
    otherwise the legacy single ``type`` field."""
    capabilities = entry.get("capabilities")
    if isinstance(capabilities, list) and capabilities:
        return [str(item) for item in capabilities if str(item)]
    legacy = str(entry.get("type", "") or "")
    return [legacy] if legacy else []


def search_text_for(entry: dict) -> str:
    return " ".join(
        str(entry.get(key, "") or "")
        for key in ("name", "id", "description", "publisher", "type")
    )


def sorted_entries(registry: dict | None) -> list[dict]:
    if not registry:
        return []
    return sorted(
        [e for e in registry.get("plugins", []) if isinstance(e, dict)],
        key=entry_sort_key,
    )


def grouped_latest(
    registry: dict | None, app_version: str
) -> list[tuple[dict, list[str]]]:
    """Group registry entries by plugin id.

    Returns one ``(entry, other_versions)`` pair per plugin: the latest
    app-compatible version is the primary card; when no version is
    compatible, the highest version is shown as an incompatible card.
    Registry order never decides which version is latest. Older
    versions stay reachable through the details view.
    """
    groups: dict[str, list[dict]] = {}
    for entry in sorted_entries(registry):
        groups.setdefault(str(entry.get("id", "")), []).append(entry)
    grouped: list[tuple[dict, list[str]]] = []
    for entries in groups.values():
        parsed: list[tuple[Version | None, dict]] = [
            (parse_version(entry.get("version")), entry) for entry in entries
        ]
        with_versions = [item for item in parsed if item[0] is not None]
        pool = (
            [item for item in with_versions
             if entry_is_app_compatible(item[1], app_version)]
            or with_versions
            or parsed
        )
        best_version, best = max(
            pool,
            key=lambda item: item[0] if item[0] is not None else Version("0"),
        )
        others = sorted(
            (str(entry.get("version")) for _, entry in parsed
             if entry is not best and entry.get("version") != best.get("version")),
            key=lambda value: Version(value),
            reverse=True,
        )
        grouped.append((best, others))
    grouped.sort(key=lambda item: entry_sort_key(item[0]))
    return grouped


def updates_for(
    registry: dict | None, active: dict[str, str], app_version: str
) -> list[dict]:
    """Registry entries that are newer, compatible updates of active plugins."""
    updates = []
    for entry, _others in grouped_latest(registry, app_version):
        plugin_id = str(entry.get("id", ""))
        current = active.get(plugin_id)
        if not current or current == entry.get("version"):
            continue
        if not entry_is_app_compatible(entry, app_version):
            continue
        if is_newer_version(str(entry.get("version", "")), current):
            updates.append(entry)
    return updates


def sort_versions_desc(versions: list[str]) -> list[str]:
    return sorted(
        set(versions),
        key=lambda value: parse_version(value) or Version("0"),
        reverse=True,
    )


def installed_card_rows(
    installed_plugins, active: dict[str, str], state_records: dict
) -> list[tuple[str, str, list[str], str | None, bool]]:
    """Rows for the installed tab: ``(name, plugin_id, versions,
    active_version, has_tool)`` with versions newest-first."""
    installed_by_id = {
        installed.manifest.id: installed for installed in installed_plugins
    }
    rows = []
    for installed in installed_plugins:
        versions = state_records.get(installed.manifest.id, {}).get(
            "versions", [installed.manifest.version]
        )
        rows.append((installed.manifest.name, installed.manifest.id, versions))
    for plugin_id, version in sorted(active.items()):
        if plugin_id not in installed_by_id:
            rows.append((plugin_id, plugin_id, [version]))

    cards: list[tuple[str, str, list[str], str | None, bool]] = []
    for name, plugin_id, versions in rows:
        versions = sort_versions_desc(
            list(versions) + ([active[plugin_id]] if plugin_id in active else [])
        )
        installed = installed_by_id.get(plugin_id)
        has_tool = bool(
            installed is not None
            and "linter-tool" in getattr(installed.manifest, "capabilities", ())
            and getattr(installed, "linter_engine", None)
        )
        cards.append(
            (name, plugin_id, versions, active.get(plugin_id), has_tool)
        )
    return cards


def capability_counts(installed) -> dict[str, int]:
    cluster = len(tuple(getattr(installed, "cluster_profiles", ()) or ()))
    lint_index = getattr(installed, "lint_index", None)
    lint = 1 if isinstance(lint_index, dict) and lint_index.get("rules") is not None else 0
    templates_index = getattr(installed, "job_templates_index", None)
    templates = 0
    if isinstance(templates_index, dict):
        raw_templates = templates_index.get("templates")
        if isinstance(raw_templates, list):
            templates = len(raw_templates)
    return {"cluster": cluster, "lint": lint, "templates": templates}


def install_summary_text(entry: dict, last_result) -> str:
    """Human-readable install/update summary from loader data.

    Counts come only from the freshly loaded installed plugin; when the
    detailed counts are unavailable a correct generic message is shown.
    """
    installed = getattr(last_result, "installed", None) if last_result else None
    manifest = getattr(installed, "manifest", None)
    name = (
        getattr(manifest, "name", None)
        or str(entry.get("name", ""))
        or t("plugins.action")
    )
    counts = capability_counts(installed)
    if not counts or not any(counts.values()):
        return t("plugins.install_generic").format(name=name)
    parts = [
        t("plugins.summary_cluster_profiles").format(count=counts["cluster"]),
        t("plugins.summary_job_templates").format(count=counts["templates"]),
        t("plugins.summary_lint_rule_packs").format(count=counts["lint"]),
    ]
    details = ", ".join(parts[:-1])
    if len(parts) > 1:
        details += f" {t('common.and')} " + parts[-1]
    else:
        details = parts[0]
    return t("plugins.install_summary").format(name=name, details=details)


def install_error_message(error: Exception | None) -> str:
    text = str(error or "")
    lowered = text.lower()
    if isinstance(error, RegistryError) or "registry" in lowered:
        return t("plugins.registry_unavailable")
    if "sha-256" in lowered or "sha256" in lowered or "size" in lowered:
        return t("plugins.verification_failed").format(name="")
    if "requires app" in lowered or "incompatible" in lowered:
        return t("plugins.incompatible")
    if "plugin api" in lowered or "plugin_api" in lowered:
        return t("plugins.unsupported_api")
    if "identity" in lowered or "invalid" in lowered:
        return t("plugins.invalid_plugin")
    return t("plugins.install_failed").format(name="")


def details_lines(
    entry: dict, installed_state_text: str, other_versions: list[str] | None = None
) -> list[str]:
    capabilities = entry_capabilities(entry)
    lines = [
        f"ID: {entry.get('id', '')}",
        f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
        f"{t('plugins.version')}: {entry.get('version', '')}",
        f"{t('plugins.license')}: {entry.get('license', '—')}",
        f"{t('plugins.requires_app_label')}: "
        f"{effective_requires_app(entry) or entry.get('requires_app', '')}",
        (
            f"{t('plugins.capabilities')}: "
            + ", ".join(capability_label(capability) for capability in capabilities)
        ),
        f"{t('plugins.source_label')}: {t('plugins.source_official_registry')}",
        f"{t('plugins.installed_state')}: {installed_state_text}",
    ]
    if other_versions:
        lines.append(
            f"{t('plugins.other_versions_catalog')}: {', '.join(other_versions)}"
        )
    lines += [
        "",
        str(entry.get("description", "")),
    ]
    if "cluster-profile" in set(capabilities):
        lines += ["", t("plugins.cluster_commands_warning")]
    if "linter-tool" in set(capabilities):
        lines += ["", t("plugins.trusted_tool_disclosure")]
    return lines
