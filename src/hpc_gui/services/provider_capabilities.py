"""Framework-neutral provider capability presentation model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from hpc_gui.services.cluster_self_test import NOT_CONFIGURED, NOT_TESTED

DECLARED = "DECLARED"
NOT_DECLARED = "NOT_DECLARED"

_CAPABILITIES = ("auth", "scheduler", "storage", "quota", "project", "account", "optional")


@dataclass(frozen=True)
class ProviderCapability:
    id: str
    declared: str
    observed: str
    detail: str = ""


@dataclass(frozen=True)
class ProviderCapabilityView:
    provider: str
    capabilities: tuple[ProviderCapability, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get(provider: Any, key: str, default: Any = None) -> Any:
    if isinstance(provider, Mapping):
        return provider.get(key, default)
    return getattr(provider, key, default)


def build_provider_capability_view(
    provider: Any = None,
    observed: Mapping[str, str] | None = None,
    *,
    project: str = "",
    account: str = "",
) -> ProviderCapabilityView:
    """Build declared-vs-observed data without provider-name conditionals."""
    observed = observed or {}
    access = _get(provider, "access", {}) or {}
    requirements = _get(provider, "requirements", {}) or {}
    declared = {
        "auth": bool(isinstance(access, Mapping) and access.get("auth_methods")),
        "scheduler": bool(_get(provider, "scheduler", "") or _get(provider, "commands", {})),
        "storage": bool(_get(provider, "storage", ())),
        "quota": bool(_get(provider, "quota_sources", ())),
        "project": isinstance(requirements, Mapping) and "project" in requirements,
        "account": isinstance(requirements, Mapping) and "account" in requirements,
        "optional": bool(_get(provider, "optional_capabilities", ())),
    }
    details = {
        "auth": "provider authentication metadata",
        "scheduler": "provider scheduler metadata",
        "storage": "provider-defined storage areas",
        "quota": "provider quota sources",
        "project": "project requirement",
        "account": "account requirement",
        "optional": "provider optional capabilities",
    }
    values = {"project": project, "account": account}
    items = []
    for key in _CAPABILITIES:
        actual = observed.get(key, NOT_TESTED if provider is not None else NOT_CONFIGURED)
        if key in values and declared[key] and not values[key]:
            actual = NOT_CONFIGURED
        items.append(ProviderCapability(key, DECLARED if declared[key] else NOT_DECLARED, actual, details[key]))
    name = str(_get(provider, "name", "") or _get(provider, "profile_id", "") or "Generic Slurm")
    return ProviderCapabilityView(name, tuple(items))


def observed_from_self_test(result: Any) -> dict[str, str]:
    """Extract known observed statuses from a self-test result."""
    values: dict[str, str] = {}
    for section in getattr(result, "sections", ()):
        for item in section.items:
            key = "auth" if item.id == "ssh" else item.id
            if key in _CAPABILITIES or item.id in {"squeue", "storage", "quota"}:
                if item.id in {"squeue", "storage", "quota"}:
                    key = {"squeue": "scheduler", "storage": "storage", "quota": "quota"}[item.id]
                values[key] = item.status
    return values
