from __future__ import annotations

import re

from typing import Any

from hpc_gui.plugins._validator_contracts import ALLOWED_ADAPTER_IDS, ALLOWED_PARSER_IDS, CLUSTER_PROFILE_REQUIRED_KEYS, KNOWN_COMMAND_PLACEHOLDERS, KNOWN_SCHEDULERS, V2_PROFILE_SECTIONS, V3_PROFILE_SECTIONS, V4_PROFILE_SECTIONS, _PLACEHOLDER_RE, _TRUSTED_SLURM_COMMANDS, _TRUSTED_SLURM_COMMAND_VARIANTS, _is_nonempty_str, _validate_storage_and_quota_sections
from hpc_gui.plugins.schema_compat import SUPPORTED_CLUSTER_PROFILE_SCHEMAS, supported_schemas_label

def validate_cluster_profile_dict(profile: Any) -> list[str]:
    """Validate a raw cluster-profile mapping; returns problems."""
    if not isinstance(profile, dict):
        return ["cluster profile must be a JSON object"]
    errors: list[str] = []
    for key in CLUSTER_PROFILE_REQUIRED_KEYS:
        if key not in profile:
            errors.append(f"cluster profile is missing required key '{key}'")
    if errors:
        return errors
    if profile["schema_version"] not in SUPPORTED_CLUSTER_PROFILE_SCHEMAS:
        errors.append(
            "cluster profile schema_version must be one of: "
            + supported_schemas_label()
        )
    if not _is_nonempty_str(profile["profile_id"]):
        errors.append("cluster profile 'profile_id' must be a non-empty string")
    elif not re.fullmatch(r"^[a-z][a-z0-9_-]*$", profile["profile_id"]) or len(profile["profile_id"]) > 64:
        errors.append("cluster profile 'profile_id' must match ^[a-z][a-z0-9_-]*$ and be at most 64 characters")
    if not _is_nonempty_str(profile["name"]):
        errors.append("cluster profile 'name' must be a non-empty string")
    elif len(profile["name"]) > 80:
        errors.append("cluster profile 'name' must be at most 80 characters")
    if profile["scheduler"] not in KNOWN_SCHEDULERS:
        errors.append(f"unsupported scheduler: {profile['scheduler']!r}")

    if profile["schema_version"] == 1:
        # v1 predates structured sections but tolerates them when present, so
        # enforce the shared shape instead of letting a malformed section
        # reach the loader.
        _validate_storage_and_quota_sections(profile, errors)

    if profile["schema_version"] == 2:
        unknown = set(profile) - set(CLUSTER_PROFILE_REQUIRED_KEYS) - V2_PROFILE_SECTIONS
        errors.extend(f"cluster profile has unknown key '{key}'" for key in sorted(unknown))
        for section_key in V2_PROFILE_SECTIONS - {"description", "paths", "commands", "storage", "quota_sources"}:
            section = profile.get(section_key)
            if section is not None and not isinstance(section, dict):
                errors.append(f"cluster profile '{section_key}' must be an object")
        _validate_storage_and_quota_sections(profile, errors)

    if profile["schema_version"] == 3:
        unknown = set(profile) - set(CLUSTER_PROFILE_REQUIRED_KEYS) - V3_PROFILE_SECTIONS
        errors.extend(f"cluster profile has unknown key '{key}'" for key in sorted(unknown))
        for section_key in V3_PROFILE_SECTIONS - {"description", "paths", "commands", "storage", "quota_sources", "file_filters"}:
            section = profile.get(section_key)
            if section is not None and not isinstance(section, dict):
                errors.append(f"cluster profile '{section_key}' must be an object")
        _validate_storage_and_quota_sections(profile, errors)
        _safe_id = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
        _reserved_filter_ids = frozenset({"all", "folders", "iso", "archives", "slurm", "shell", "other"})

        def _validate_labels(value, location):
            if not isinstance(value, dict):
                errors.append(f"{location} labels must be an object")
                return
            unknown_labels = set(value) - {"en", "tr"}
            if unknown_labels:
                errors.append(f"{location} labels has unknown properties {sorted(unknown_labels)}")
            if not _is_nonempty_str(value.get("en")):
                errors.append(f"{location} labels.en is required")
            for lang in ("en", "tr"):
                if lang in value and (not _is_nonempty_str(value[lang]) or len(value[lang]) > 128):
                    errors.append(f"{location} labels.{lang} must be a non-empty string of at most 128 characters")

        job_outputs = profile.get("job_outputs")
        if job_outputs is not None:
            if not isinstance(job_outputs, dict):
                errors.append("cluster profile 'job_outputs' must be an object")
            else:
                unknown = set(job_outputs) - {"strategy", "streams"}
                errors.extend(f"job_outputs has unknown property '{key}'" for key in sorted(unknown))
                if job_outputs.get("strategy") not in {None, "explicit", "legacy"}:
                    errors.append("job_outputs.strategy is invalid")
                streams = job_outputs.get("streams")
                if not isinstance(streams, list):
                    errors.append("cluster profile 'job_outputs.streams' must be a list")
                elif len(streams) > 50:
                    errors.append("cluster profile 'job_outputs.streams' exceeds 50 entries")
                else:
                    seen_stream_ids: set[str] = set()
                    for idx, stream in enumerate(streams):
                        location = f"job_outputs.streams[{idx}]"
                        if not isinstance(stream, dict):
                            errors.append(f"{location} must be an object")
                            continue
                        allowed = {"id", "role", "labels", "resolver", "relative_path", "order"}
                        errors.extend(f"{location} has unknown property '{key}'" for key in sorted(set(stream) - allowed))
                        sid = stream.get("id")
                        if not _is_nonempty_str(sid) or not _safe_id.fullmatch(str(sid)):
                            errors.append(f"{location}.id must match {_safe_id.pattern}")
                        elif sid in seen_stream_ids:
                            errors.append(f"{location} duplicate id {sid!r}")
                        seen_stream_ids.add(str(sid))
                        if stream.get("role") not in {"stdout", "stderr", "custom"}:
                            errors.append(f"{location}.role is invalid")
                        if stream.get("resolver") not in {"slurm.stdout", "slurm.stderr", "workdir.relative"}:
                            errors.append(f"{location}.resolver is invalid")
                        _validate_labels(stream.get("labels"), location)
                        order = stream.get("order")
                        if not isinstance(order, int) or isinstance(order, bool) or not 0 <= order <= 100000:
                            errors.append(f"{location}.order must be a bounded integer")
                        relative = stream.get("relative_path")
                        if stream.get("resolver") == "workdir.relative":
                            if not _is_nonempty_str(relative) or len(relative) > 512 or relative.startswith("/") or "\\" in relative or any(part in {"", ".", ".."} for part in relative.split("/")):
                                errors.append(f"{location}.relative_path must be a safe relative path")
                        elif "relative_path" in stream:
                            errors.append(f"{location}.relative_path is only valid for workdir.relative")

        file_filters = profile.get("file_filters")
        if file_filters is not None:
            if not isinstance(file_filters, list):
                errors.append("cluster profile 'file_filters' must be a list")
            elif len(file_filters) > 50:
                errors.append("cluster profile 'file_filters' exceeds 50 entries")
            else:
                seen_filter_ids: set[str] = set()
                for idx, ff in enumerate(file_filters):
                    location = f"file_filters[{idx}]"
                    if not isinstance(ff, dict):
                        errors.append(f"{location} must be an object")
                        continue
                    allowed = {"id", "labels", "globs", "suffixes", "order"}
                    errors.extend(f"{location} has unknown property '{key}'" for key in sorted(set(ff) - allowed))
                    fid = ff.get("id")
                    if not _is_nonempty_str(fid) or not _safe_id.fullmatch(str(fid)):
                        errors.append(f"{location}.id must match {_safe_id.pattern}")
                    elif fid in _reserved_filter_ids:
                        errors.append(f"{location}.id {fid!r} is reserved")
                    elif fid in seen_filter_ids:
                        errors.append(f"{location} duplicate id {fid!r}")
                    seen_filter_ids.add(str(fid))
                    _validate_labels(ff.get("labels"), location)
                    rule_count = 0
                    for key in ("globs", "suffixes"):
                        values = ff.get(key)
                        if values is not None and (not isinstance(values, list) or len(values) > 32):
                            errors.append(f"{location}.{key} must be a bounded list")
                        elif isinstance(values, list):
                            rule_count += len(values)
                            for value in values:
                                if not _is_nonempty_str(value) or len(value) > 128:
                                    errors.append(f"{location}.{key} contains an invalid rule")
                    if rule_count == 0:
                        errors.append(f"{location} needs at least one glob or suffix")
                    order = ff.get("order")
                    if not isinstance(order, int) or isinstance(order, bool) or not 0 <= order <= 100000:
                        errors.append(f"{location}.order must be a bounded integer")

    if profile["schema_version"] == 4:
        unknown = set(profile) - set(CLUSTER_PROFILE_REQUIRED_KEYS) - V4_PROFILE_SECTIONS
        errors.extend(f"cluster profile has unknown key '{key}'" for key in sorted(unknown))
        _validate_storage_and_quota_sections(profile, errors)
        # Validate v4 provider contract sections
        for section_key in ("job_details", "accounting", "cluster_status"):
            section = profile.get(section_key)
            if section is None:
                continue
            if not isinstance(section, dict):
                errors.append(f"cluster profile '{section_key}' must be an object")
                continue
            adapter_id = section.get("adapter")
            parser_id = section.get("parser")
            if adapter_id is not None and not isinstance(adapter_id, str):
                errors.append(f"cluster profile '{section_key}.adapter' must be a string")
            elif adapter_id is not None and adapter_id not in ALLOWED_ADAPTER_IDS:
                errors.append(f"cluster profile '{section_key}.adapter' references unknown adapter '{adapter_id}'")
            if parser_id is not None and not isinstance(parser_id, str):
                errors.append(f"cluster profile '{section_key}.parser' must be a string")
            elif parser_id is not None and parser_id not in ALLOWED_PARSER_IDS:
                errors.append(f"cluster profile '{section_key}.parser' references unknown parser '{parser_id}'")
            # Reject executable code fields
            for forbidden in ("source", "import_path", "eval", "exec", "callback", "shell"):
                if forbidden in section:
                    errors.append(f"cluster profile '{section_key}' must not contain executable field '{forbidden}'")

    for section_key in ("paths", "commands"):
        section = profile.get(section_key)
        if section is None:
            continue
        if not isinstance(section, dict):
            errors.append(f"cluster profile '{section_key}' must be a JSON object")
            continue
        for value in section.values():
            if not isinstance(value, str):
                errors.append(f"cluster profile '{section_key}' values must be strings")
                break

    commands = profile.get("commands")
    if isinstance(commands, dict):
        for key, value in commands.items():
            if not isinstance(value, str):
                continue
            variants = _TRUSTED_SLURM_COMMAND_VARIANTS.get(key, ())
            if key not in _TRUSTED_SLURM_COMMANDS or (
                value != _TRUSTED_SLURM_COMMANDS[key] and value not in variants
            ):
                errors.append(f"cluster profile command '{key}' is not an application-owned Slurm operation")
                continue
            for placeholder in _PLACEHOLDER_RE.findall(value):
                if placeholder not in KNOWN_COMMAND_PLACEHOLDERS:
                    errors.append(
                        f"cluster profile command '{key}' uses unknown placeholder "
                        f"{{{placeholder}}}"
                    )
    return errors
