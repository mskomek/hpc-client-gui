from __future__ import annotations

from typing import Any, Iterable

from hpc_gui.config.storage import load_settings, update_settings


GENERIC_SLURM_DEFAULTS: dict[str, Any] = {
    "name": "Generic Slurm",
    "scratch_dir": "",
    "home_dir": "",
    "quota_tracking_enabled": False,
    "home_quota_limit": "",
    "home_inode_limit": "",
    "scratch_quota_limit": "",
    "scratch_inode_limit": "",
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
QUOTA_LIMIT_KEYS = (
    "home_quota_limit",
    "home_inode_limit",
    "scratch_quota_limit",
    "scratch_inode_limit",
)


def hpc_default_remote_paths() -> dict[str, str]:
    return {
        "scratch_dir": GENERIC_SLURM_DEFAULTS["scratch_dir"],
        "home_dir": GENERIC_SLURM_DEFAULTS["home_dir"],
    }


def quota_tracking_enabled(value: Any) -> bool:
    """Return whether manual quota tracking has usable configured limits."""
    settings = normalize_system_settings(value)
    return bool(settings["quota_tracking_enabled"]) and any(
        settings[key].strip() for key in QUOTA_LIMIT_KEYS
    )


def builtin_system_template_groups() -> dict[str, list[dict[str, Any]]]:
    return {
        "Generic Slurm": [dict(GENERIC_SLURM_DEFAULTS)],
    }


def plugin_system_template_groups(
    installed_plugins: Iterable[Any] | None,
) -> dict[str, list[dict[str, Any]]]:
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
            if key == "quota_tracking_enabled" and isinstance(candidate, bool):
                settings[key] = candidate
            elif isinstance(candidate, str) and candidate.strip():
                settings[key] = candidate.strip()
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


def save_user_system_template(name: str, settings: Any) -> dict[str, Any]:
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
    try:
        return template.format(user=username)
    except (KeyError, ValueError):
        return template
