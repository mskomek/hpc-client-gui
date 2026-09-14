"""Cluster-profile schema capability contract.

One canonical mapping answers "which application release first accepts a
given cluster-profile schema?" for release tooling, registry validation, and
cross-repository contract tests. Historical entries are release facts and
must never be rewritten to widen or narrow an already published capability.
"""

from __future__ import annotations

from typing import Any

from hpc_gui.plugins.compatibility import (
    minimum_admitted_version,
    parse_version,
)

# First released application version that validates each schema version.
#   schema 1 -> v1.4.0 (first plugin-registry capable release)
#   schema 2 -> v1.5.5 (structured provider profiles / storage metadata)
#   schema 3 -> 1.5.9  (job_outputs / file_filters)
#   schema 4 -> 1.5.9  (declarative adapter/parser contracts)
MIN_APP_VERSION_FOR_SCHEMA: dict[int, str] = {
    1: "1.4.0",
    2: "1.5.5",
    3: "1.5.9",
    4: "1.5.9",
}

SUPPORTED_CLUSTER_PROFILE_SCHEMAS: tuple[int, ...] = tuple(
    sorted(MIN_APP_VERSION_FOR_SCHEMA)
)

# First application release with the plugin registry/installer at all. A
# schema-1 plugin that declares an older floor is vacuously harmless: no
# earlier release can discover, download, or install it. Floors below this
# baseline are therefore not treated as false compatibility claims.
PLUGIN_INFRASTRUCTURE_VERSION = "1.4.0"


def minimum_app_version_for_schema(schema_version: Any) -> str | None:
    """First application release that supports ``schema_version``, if known."""
    try:
        key = int(schema_version)
    except (TypeError, ValueError):
        return None
    return MIN_APP_VERSION_FOR_SCHEMA.get(key)


def supported_schemas_label() -> str:
    return ", ".join(str(version) for version in SUPPORTED_CLUSTER_PROFILE_SCHEMAS)


def app_supports_schema(app_version: str, schema_version: Any) -> bool:
    """Answer "does application version X support plugin schema Y?"."""
    minimum_app = minimum_app_version_for_schema(schema_version)
    current = parse_version(app_version)
    minimum = parse_version(minimum_app) if minimum_app else None
    if current is None or minimum is None:
        return False
    return current >= minimum


def schema_floor_error(schema_version: Any, requires_app: str) -> str | None:
    """Return a problem string when ``requires_app`` claims too-old releases.

    A plugin payload may declare an application floor at or above the first
    release that actually implements its schema; a lower floor would make the
    registry advertise an install that must fail validation.
    """
    minimum_app = minimum_app_version_for_schema(schema_version)
    if minimum_app is None:
        return None
    minimum = parse_version(minimum_app)
    baseline = parse_version(PLUGIN_INFRASTRUCTURE_VERSION)
    if minimum is None or baseline is None or minimum <= baseline:
        # No released application predating the plugin infrastructure can be
        # affected by the claim.
        return None
    floor = minimum_admitted_version(requires_app)
    if floor is None:
        return None
    if floor < minimum:
        return (
            f"cluster-profile schema {int(schema_version)} first requires app "
            f"{minimum_app}, but requires_app {requires_app!r} would also admit "
            f"older releases"
        )
    return None


def unsupported_schema_message(
    schema_version: Any,
    *,
    app_version: str,
    supported_schemas: tuple[int, ...] = SUPPORTED_CLUSTER_PROFILE_SCHEMAS,
) -> str:
    """Actionable error text for a payload the running release cannot parse."""
    supported = ", ".join(str(version) for version in supported_schemas)
    return (
        f"This plugin uses cluster-profile schema {schema_version}, but "
        f"HPC Client GUI {app_version} supports schemas {supported}. "
        "Install a newer application release or use an older compatible "
        "plugin version."
    )


def cluster_profile_floor_errors(cluster_profiles: Any, requires_app: str) -> list[str]:
    """Floor violations for built profiles or raw profile mappings."""
    problems: list[str] = []
    for profile in cluster_profiles or ():
        if isinstance(profile, dict):
            schema_version = profile.get("schema_version")
        else:
            schema_version = getattr(profile, "schema_version", None)
        error = schema_floor_error(schema_version, requires_app)
        if error:
            problems.append(error)
    return problems
