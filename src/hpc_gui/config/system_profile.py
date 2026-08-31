from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from hpc_gui.config.storage import load_settings, update_settings


GENERIC_SLURM_DEFAULTS: dict[str, str] = {
    "name": "Generic Slurm",
    "scratch_dir": "",
    "home_dir": "",
    "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
    "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
    "scancel_command": "scancel {job_id_q}",
    "sacct_command": (
        "sacct -u {user} "
        "--format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES"
    ),
    "scontrol_command": "scontrol show job {job_id_q}",
    "status_command": "",
    "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
    "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
}

SYSTEM_SETTING_COMMAND_KEYS: tuple[str, ...] = tuple(
    key
    for key in GENERIC_SLURM_DEFAULTS
    if key.endswith("_command")
)

SYSTEM_TEMPLATE_SETTINGS_KEY = "system_templates"
_PROVIDER_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_PROVIDER_PLACEHOLDERS = {"user", "user_first", "project", "account"}


@dataclass(frozen=True)
class ProviderContext:
    user: str = ""
    project: str = ""
    account: str = ""

    @property
    def user_first(self) -> str:
        return self.user[:1]


@dataclass(frozen=True)
class ResolvedProviderPath:
    state: str
    path: str
    missing: tuple[str, ...] = ()


def resolve_provider_path(template: str, context: ProviderContext) -> ResolvedProviderPath:
    """Resolve only application-owned provider placeholders."""
    if not isinstance(template, str):
        return ResolvedProviderPath("invalid-template", "")
    names = _PROVIDER_PLACEHOLDER_RE.findall(template)
    unknown = tuple(dict.fromkeys(name for name in names if name not in _PROVIDER_PLACEHOLDERS))
    if unknown:
        return ResolvedProviderPath("invalid-template", template)
    values = {"user": context.user, "user_first": context.user_first,
              "project": context.project, "account": context.account}
    missing = tuple(dict.fromkeys(name for name in names if not values[name]))
    if missing:
        return ResolvedProviderPath("missing-context", template, missing)
    return ResolvedProviderPath("resolved", _PROVIDER_PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template))


def hpc_default_remote_paths() -> dict[str, str]:
    return {
        "scratch_dir": GENERIC_SLURM_DEFAULTS["scratch_dir"],
        "home_dir": GENERIC_SLURM_DEFAULTS["home_dir"],
    }


def builtin_system_template_groups() -> dict[str, list[dict[str, str]]]:
    return {
        "Generic Slurm": [dict(GENERIC_SLURM_DEFAULTS)],
    }


def plugin_system_template_groups(
    installed_plugins: Iterable[Any] | None,
) -> dict[str, list[dict[str, str]]]:
    """Convert installed declarative plugins into system-template groups.

    Accepts any iterable of objects exposing ``manifest.name`` and a
    ``cluster_profiles`` sequence of ``ClusterProfileDefinition``-like
    objects. Pure function; no Qt and no I/O.
    """
    groups: dict[str, list[dict[str, str]]] = {}
    for installed in installed_plugins or []:
        manifest = getattr(installed, "manifest", None)
        profiles = getattr(installed, "cluster_profiles", ()) or ()
        group_name = getattr(manifest, "name", "") or "Plugins"
        for profile in profiles:
            converter = getattr(profile, "to_system_settings", None)
            settings = converter() if callable(converter) else None
            if isinstance(settings, dict) and settings:
                groups.setdefault(group_name, []).append(settings)
    return groups


def normalize_system_settings(value: Any) -> dict[str, Any]:
    settings = dict(GENERIC_SLURM_DEFAULTS)
    if isinstance(value, dict):
        for key in settings:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                settings[key] = candidate.strip()
        if isinstance(value.get("provider_template"), dict):
            settings["provider_template"] = dict(value["provider_template"])
    return settings


def load_user_system_templates() -> list[dict[str, Any]]:
    templates = load_settings().get(SYSTEM_TEMPLATE_SETTINGS_KEY, [])
    if not isinstance(templates, list):
        return []
    result: list[dict[str, Any]] = []
    for item in templates:
        if not isinstance(item, dict):
            continue
        normalized = normalize_system_settings(item)
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        normalized["name"] = name
        result.append(normalized)
    return result


def save_user_system_template(name: str, settings: Any) -> dict[str, str]:
    template = normalize_system_settings(settings)
    template["name"] = str(name or "").strip()
    if not template["name"]:
        raise ValueError("system template name is required")

    templates = load_user_system_templates()
    index = next(
        (
            idx
            for idx, existing in enumerate(templates)
            if existing.get("name", "").casefold() == template["name"].casefold()
        ),
        None,
    )
    if index is None:
        templates.append(template)
    else:
        templates[index] = template
    update_settings({SYSTEM_TEMPLATE_SETTINGS_KEY: templates})
    return template


def format_remote_path(template: str, username: str) -> str:
    result = resolve_provider_path(template, ProviderContext(user=username))
    return result.path
