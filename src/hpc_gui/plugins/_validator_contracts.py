from __future__ import annotations

import re
from typing import Any



MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "plugin_api",
    "id",
    "name",
    "version",
    "publisher",
    "license",
    "description",
    "requires_app",
    "capabilities",
    "entrypoints",
    "files",
)

MANIFEST_OPTIONAL_KEYS = frozenset({"ui_contributions", "provider_ids", "optional_dependencies"})

PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

CLUSTER_PROFILE_REQUIRED_KEYS = ("schema_version", "profile_id", "name", "scheduler")

V2_PROFILE_SECTIONS = frozenset(
    {"description", "metadata", "paths", "commands", "site", "access", "requirements", "scheduler_hints", "software", "storage", "quota_sources"}
)

V3_PROFILE_SECTIONS = V2_PROFILE_SECTIONS | {"job_outputs", "file_filters"}

V4_PROFILE_SECTIONS = V3_PROFILE_SECTIONS | {"job_details", "accounting", "cluster_status"}

KNOWN_SCHEDULERS = frozenset({"slurm"})

ALLOWED_ADAPTER_IDS = frozenset({
    "slurm.scontrol.job",
    "slurm.sacct.job",
    "truba.lssrv",
})

ALLOWED_PARSER_IDS = frozenset({
    "slurm.scontrol.v1",
    "slurm.sacct.pipe.v1",
    "truba.lssrv.v1",
    "generic.delimited_table.v1",
})

_TRUSTED_SLURM_COMMANDS = {
    "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
    "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
    "scancel_command": "scancel {job_id_q}",
    "sacct_command": "sacct -n -P -u {user} --format=JobIDRaw,JobName,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
    "sacct_job_command": "sacct -n -P -j {job_id_q} --format=JobIDRaw,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
    "scontrol_command": "scontrol show job {job_id_q}",
    "status_command": "lssrv",
    "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
    "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
}

_TRUSTED_SLURM_COMMAND_VARIANTS = {
    "sacct_command": frozenset({
        "sacct -u {user} --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES",
    }),
}

ALLOWED_PAYLOAD_SUFFIXES = frozenset({".json", ".md", ".txt", ".tpl"})

V2_LINTER_ENGINE_ROLE = "linter-engine"

V2_LINTER_DATA_ROLE = "linter-data"

V2_LINTER_ENTRYPOINT_KEY = "linter_engine"

TRUSTED_DECLARATIVE_ENGINES = frozenset({"declarative-rules-v1"})

KNOWN_COMMAND_PLACEHOLDERS = frozenset(
    {
        "user",
        "job_id",
        "job_id_q",
        "script_dir",
        "script_dir_q",
        "script_name",
        "script_name_q",
    }
)

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

REGISTRY_ENTRY_REQUIRED_KEYS = (
    "id",
    "name",
    "version",
    "plugin_api",
    "type",
    "description",
    "publisher",
    "requires_app",
    "manifest_path",
    "manifest_sha256",
    "official",
)

REGISTRY_PLUGIN_TYPES = frozenset(
    {
        "cluster-profile",
        "lint-rules",
        "job-template",
        "application-tools",
        "linter-tool",
    }
)

DISCOVERABLE_PLUGIN_API_VERSIONS = frozenset({1, 2})

def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _validate_storage_and_quota_sections(profile: Any, errors: list[str]) -> None:
    """Enforce the storage/quota_sources list-of-objects shape.

    v2/v3 historically enforced this while v1/v4 skipped it, so a malformed
    section passed validation and later crashed the loader (which assumes a
    list of mappings). Every schema version that can carry these sections
    must enforce the same shape: fail closed at validation, never at startup.
    """
    for section_key in ("storage", "quota_sources"):
        section = profile.get(section_key)
        if section is None:
            continue
        if not isinstance(section, list):
            errors.append(f"cluster profile '{section_key}' must be a list")
            continue
        for index, item in enumerate(section):
            if not isinstance(item, dict):
                errors.append(f"cluster profile '{section_key}[{index}]' must be an object")
                continue
            if not _is_nonempty_str(item.get("id")):
                errors.append(f"cluster profile '{section_key}[{index}]' needs a non-empty id")

def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
