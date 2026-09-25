"""Plugin settings ownership (W34).

Live owner for ``waves/pending/W34.md`` owned requirements
``HPC-W08-PROV-002`` .. ``HPC-W08-PROV-007`` (planning source
``WAVE_V2_FINAL_08.md`` Workstream G — Settings ownership):

- PROV-002: settings are namespaced per plugin.
- PROV-003: settings survive the expected restart (atomic file persistence).
- PROV-004: plugin settings never overwrite core keys.
- PROV-005: types/defaults are validated fail-closed.
- PROV-006: absent/disabled/removed plugins are tolerated (defaults, no crash).
- PROV-007: secrets never leak in export/logs (dropped + redacted).

Storage layout (disposable-root safe, no real user config touched unless
the caller passes the production root explicitly)::

    <plugins_root>/settings/<plugin_id>.json

Every value file carries ``{"schema_version": 1, "plugin_id": ..., "settings": {...}}``.
Writes are atomic (tmp + replace). Reads are fail-closed to defaults:
missing file, corrupt JSON, wrong shape, or unknown plugin all return the
spec defaults instead of raising.

This module has no Qt/wx imports, no network access, and never executes
plugin code. It is the single place that states the Workstream G contract
so tests, diagnostics and UI text cannot drift apart.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

SETTINGS_SCHEMA_VERSION = 1
SETTINGS_DIR_NAME = "settings"

_NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")

#: Key fragments that mark a setting as secret. Secret values are stored
#: locally (the plugin needs them at runtime) but are dropped from every
#: export and redacted in every log rendering (PROV-007).
SECRET_KEY_RE = re.compile(
    r"(password|passwd|passphrase|token|api[-_]?key|session[-_]?token|secret|private[-_]?key)",
    re.IGNORECASE,
)

_STATIC_CORE_KEYS = frozenset(
    {
        "name",
        "scratch_dir",
        "home_dir",
        "squeue_command",
        "sbatch_command",
        "scancel_command",
        "sacct_command",
        "sacct_job_command",
        "scontrol_command",
        "status_command",
        "active_job_ids_command",
        "job_state_command",
        "system_templates",
        "provider_template",
    }
)


def core_protected_keys() -> frozenset[str]:
    """Return the core settings keys a plugin must never overwrite (PROV-004)."""
    try:
        from hpc_gui.config.system_profile import GENERIC_SLURM_DEFAULTS

        return frozenset(GENERIC_SLURM_DEFAULTS) | _STATIC_CORE_KEYS
    except Exception:
        return _STATIC_CORE_KEYS


def is_secret_key(key: str) -> bool:
    """Return True when a setting key must be treated as a secret (PROV-007)."""
    return bool(SECRET_KEY_RE.search(str(key or "")))


def namespaced_key(plugin_id: str, key: str) -> str:
    """Return the shared-dict namespaced form ``plugins.<id>.<key>`` (PROV-002)."""
    return f"plugins.{plugin_id}.{key}"


def parse_namespaced_key(full_key: str) -> tuple[str, str] | None:
    """Split ``plugins.<id>.<key>``; return None when not namespaced.

    Plugin ids are dotted (``org.hpcclient.truba``) while short keys are
    dot-free by convention, so the split is on the last dot: everything
    between the ``plugins.`` prefix and the final segment is the plugin
    id, the final segment is the key.
    """
    if not isinstance(full_key, str) or not full_key.startswith("plugins."):
        return None
    rest = full_key[len("plugins."):]
    plugin_id, sep, key = rest.rpartition(".")
    if not sep or not plugin_id or not key:
        return None
    return plugin_id, key


def settings_dir(root: str | Path | None = None) -> Path:
    """Return the per-root plugin settings directory (PROV-003)."""
    from hpc_gui.plugins.storage import plugins_root

    return Path(plugins_root(root)) / SETTINGS_DIR_NAME


def settings_path(root: str | Path | None, plugin_id: str) -> Path:
    """Return the settings file for one plugin; rejects unsafe ids."""
    if not isinstance(plugin_id, str) or not plugin_id or "/" in plugin_id or "\\" in plugin_id or ".." in plugin_id:
        raise ValueError(f"unsafe plugin id: {plugin_id!r}")
    return settings_dir(root) / f"{plugin_id}.json"


def validate_setting_key(plugin_id: str, key: Any) -> list[str]:
    """Validate one short setting key (PROV-002/PROV-004).

    Short keys live inside the per-plugin file; they must be safe,
    non-empty, bounded, and must not collide with a core key. The shared
    dict only ever carries the :func:`namespaced_key` form.
    """
    errors: list[str] = []
    if not isinstance(key, str) or not key.strip():
        errors.append(f"plugin {plugin_id!r} setting key must be a non-empty string")
        return errors
    if len(key) > 128 or not _KEY_RE.fullmatch(key):
        errors.append(f"plugin {plugin_id!r} setting key {key!r} is unsafe or too long")
        return errors
    if key in core_protected_keys():
        errors.append(f"plugin {plugin_id!r} setting key {key!r} overwrites a core key")
        return errors
    if key.startswith("plugins.") or ".." in key or "/" in key or "\\" in key:
        errors.append(f"plugin {plugin_id!r} setting key {key!r} must be a short key")
        return errors
    return errors


def _spec_default(spec: Mapping[str, Any] | None, key: str) -> Any:
    if isinstance(spec, Mapping):
        entry = spec.get(key)
        if isinstance(entry, Mapping) and "default" in entry:
            return entry["default"]
    return None


def spec_defaults(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the declared defaults for a settings spec (PROV-005)."""
    defaults: dict[str, Any] = {}
    if isinstance(spec, Mapping):
        for key, entry in spec.items():
            if isinstance(entry, Mapping) and "default" in entry:
                defaults[key] = entry["default"]
    return defaults


def validate_plugin_settings(
    plugin_id: str,
    values: Any,
    spec: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate candidate settings against a declared spec (PROV-005).

    Returns ``(cleaned, errors)``. Fail-closed: any error means the caller
    must not persist the candidate. Rules:

    - ``values`` must be a mapping; unknown keys (not in ``spec``) are errors.
    - every key passes :func:`validate_setting_key` (namespace + core guard).
    - every value matches the declared ``type`` exactly (``bool`` is never
      accepted where ``int`` is declared and vice versa).
    - an optional ``validator`` callable may add further errors; exceptions
      inside it are treated as errors, never as acceptance.
    """
    errors: list[str] = []
    cleaned: dict[str, Any] = {}
    if not isinstance(values, Mapping):
        return {}, [f"plugin {plugin_id!r} settings must be an object"]
    spec = spec if isinstance(spec, Mapping) else {}
    for key, value in values.items():
        errors.extend(validate_setting_key(plugin_id, key))
        entry = spec.get(key)
        if not isinstance(entry, Mapping) or "type" not in entry:
            errors.append(f"plugin {plugin_id!r} setting {key!r} is not declared")
            continue
        expected = entry["type"]
        try:
            ok = isinstance(value, expected)
        except Exception:
            ok = False
        # bool/int strictness: isinstance(True, int) is True in Python, but
        # a plugin toggle must not silently pass as an integer setting.
        if expected is int and isinstance(value, bool):
            ok = False
        if expected is bool and not isinstance(value, bool):
            ok = False
        if not ok:
            name = getattr(expected, "__name__", repr(expected))
            errors.append(
                f"plugin {plugin_id!r} setting {key!r} must be {name} "
                f"(got {type(value).__name__})"
            )
            continue
        validator = entry.get("validator")
        if validator is not None:
            try:
                problem = validator(value)
            except Exception as exc:
                errors.append(f"plugin {plugin_id!r} setting {key!r} invalid: {exc}")
                continue
            if problem:
                errors.append(f"plugin {plugin_id!r} setting {key!r} invalid: {problem}")
                continue
        cleaned[key] = value
    return cleaned, errors


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def load_plugin_settings(
    root: str | Path | None,
    plugin_id: str,
    spec: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Load one plugin's settings; absent/corrupt input yields defaults (PROV-006).

    Removing or disabling a plugin must not crash settings loading because
    namespaced keys remain: a missing file, unreadable file, corrupt JSON,
    wrong schema, or values that no longer validate all fall back to the
    declared ``spec`` defaults (plus a warning diagnostic, never an
    exception for ordinary absence).
    """
    defaults = spec_defaults(spec)
    try:
        path = settings_path(root, plugin_id)
    except ValueError:
        logger.warning("Refusing to load settings for unsafe plugin id %r", plugin_id)
        return dict(defaults)
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return dict(defaults)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Plugin %r settings unreadable, using defaults: %s", plugin_id, exc)
        return dict(defaults)
    if not isinstance(payload, Mapping):
        logger.warning("Plugin %r settings has a bad shape, using defaults", plugin_id)
        return dict(defaults)
    stored = payload.get("settings")
    cleaned, errors = validate_plugin_settings(plugin_id, stored, spec)
    if errors:
        logger.warning(
            "Plugin %r settings invalid, using defaults for bad keys: %s",
            plugin_id,
            "; ".join(errors),
        )
    merged = dict(defaults)
    merged.update(cleaned)
    return merged


def save_plugin_settings(
    root: str | Path | None,
    plugin_id: str,
    values: Mapping[str, Any],
    spec: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate and atomically persist one plugin's settings (PROV-003/005).

    Fail-closed: when validation reports any error nothing is written and
    the errors are returned. On success the merged defaults+cleaned mapping
    is written and returned with an empty error list.
    """
    cleaned, errors = validate_plugin_settings(plugin_id, values, spec)
    if errors:
        return {}, errors
    merged = spec_defaults(spec)
    merged.update(cleaned)
    try:
        path = settings_path(root, plugin_id)
    except ValueError as exc:
        return {}, [str(exc)]
    try:
        _atomic_write_json(
            path,
            {
                "schema_version": SETTINGS_SCHEMA_VERSION,
                "plugin_id": plugin_id,
                "settings": merged,
            },
        )
    except OSError as exc:
        return {}, [f"cannot persist settings for {plugin_id!r}: {exc}"]
    return dict(merged), []


def load_all_plugin_settings(
    root: str | Path | None,
    specs: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Load every plugin spec's settings; absence never crashes (PROV-006)."""
    result: dict[str, dict[str, Any]] = {}
    for plugin_id, spec in (specs or {}).items():
        result[str(plugin_id)] = load_plugin_settings(root, str(plugin_id), spec)
    return result


def export_safe_settings(
    settings: Mapping[str, Any],
    spec: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return exportable settings with secrets dropped (PROV-007).

    Secret keys (declared ``secret: True`` or matching :data:`SECRET_KEY_RE`)
    are removed entirely — never redacted-in-place — so exported payloads
    and logs cannot leak them through length/format side channels.
    """
    safe: dict[str, Any] = {}
    spec = spec if isinstance(spec, Mapping) else {}
    for key, value in (settings or {}).items():
        entry = spec.get(key)
        declared_secret = bool(
            isinstance(entry, Mapping) and entry.get("secret") is True
        )
        if declared_secret or is_secret_key(str(key)):
            continue
        safe[key] = value
    return safe


def export_namespaced_safe_settings(
    plugin_id: str,
    settings: Mapping[str, Any],
    spec: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the ``plugins.<id>.<key>`` export view without secrets (PROV-002/007)."""
    safe = export_safe_settings(settings, spec)
    return {namespaced_key(plugin_id, key): value for key, value in safe.items()}


def redact_settings_for_log(
    plugin_id: str,
    settings: Mapping[str, Any],
    spec: Mapping[str, Any] | None = None,
) -> str:
    """Render settings for diagnostics with every secret redacted (PROV-007)."""
    parts: list[str] = []
    for key in sorted((settings or {})):
        entry = spec.get(key) if isinstance(spec, Mapping) else None
        declared_secret = bool(
            isinstance(entry, Mapping) and entry.get("secret") is True
        )
        if declared_secret or is_secret_key(str(key)):
            parts.append(f"{key}=<redacted>")
        else:
            parts.append(f"{key}={(settings or {})[key]!r}")
    return f"plugin {plugin_id!r} settings: " + (", ".join(parts) if parts else "<empty>")


def merge_into_shared(
    shared_core: Mapping[str, Any],
    plugin_id: str,
    settings: Mapping[str, Any],
    spec: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Merge namespaced plugin settings onto a copy of shared core settings.

    Core keys are never overwritten (PROV-004): the merge only adds
    ``plugins.<id>.<key>`` entries. If a namespaced key already exists with
    a different value the merge fails closed with ``ValueError`` instead of
    silently shadowing it.
    """
    merged = dict(shared_core or {})
    for key, value in export_namespaced_safe_settings(plugin_id, settings, spec).items():
        if key in merged and merged[key] != value:
            raise ValueError(f"namespaced key collision: {key!r}")
        merged[key] = value
    for core_key in core_protected_keys():
        if core_key in (settings or {}):
            raise ValueError(f"plugin {plugin_id!r} must not carry core key {core_key!r}")
    return merged
