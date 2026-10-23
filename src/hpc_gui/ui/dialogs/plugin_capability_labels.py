"""Translated labels for plugin capability identifiers (Plugin Manager)."""

from __future__ import annotations

from hpc_gui.core.i18n import t

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
