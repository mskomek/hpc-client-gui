"""Registry-level ``compatibility_override`` on the application side.

The plugin registry can correct a compatibility decision without touching an
immutable published package's bytes. The application is a separate trust
boundary: it validates the field itself and resolves through it, so a
registry that understands the override and an application that ignores it
cannot drift apart.

These tests drive the *production* resolver (``find_registry_entry``,
``parse_registry``, ``validate_registry_dict``, the installer), never a
standalone helper on its own.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.compatibility import (
    effective_requires_app,
    entry_is_app_compatible,
    validate_compatibility_override,
)
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    RegistryError,
    fetch_registry_with_cache,
    find_registry_entry,
    parse_registry,
)
from hpc_gui.plugins.validator import validate_registry_dict

PLUGIN_ID = "org.hpcclient.truba"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_and_profile(version: str, requires_app: str, schema_version: int = 1):
    profile = {
        "schema_version": schema_version,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        "commands": {"status_command": "lssrv"},
    }
    profile_bytes = json.dumps(profile, indent=2).encode()
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": PLUGIN_ID,
        "name": "TRUBA",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "TRUBA cluster profile.",
        "requires_app": requires_app,
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [
            {
                "path": "cluster-profile.json",
                "sha256": _sha256(profile_bytes),
                "size": len(profile_bytes),
                "role": "cluster-profile",
            }
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    return manifest, manifest_bytes, profile_bytes


def _entry(version: str, requires_app: str, override: dict | None = None, **extra):
    manifest, manifest_bytes, _ = _manifest_and_profile(
        version, requires_app, **extra
    )
    entry = {
        "id": PLUGIN_ID,
        "name": "TRUBA",
        "version": version,
        "plugin_api": 1,
        "type": "cluster-profile",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": requires_app,
        "manifest_path": f"plugins/truba/{version}/manifest.json",
        "manifest_sha256": _sha256(manifest_bytes),
        "official": True,
    }
    if override is not None:
        entry["compatibility_override"] = override
    return entry


def _registry(*entries: dict) -> dict:
    return {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {
            "owner": "mskomek",
            "name": "hpc-client-gui-plugins",
            "raw_base": OFFICIAL_RAW_BASE,
        },
        "plugins": list(entries),
    }


def _fetcher(responses: dict[str, bytes]):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url not in responses:
            raise OSError(f"no response registered for {url}")
        payload = responses[url]
        if len(payload) > max_bytes:
            raise OSError(f"response exceeds {max_bytes} bytes")
        return payload

    return fetch


NARROWING = {
    "requires_app": ">=1.6.0",
    "reason": "1.5.9 mis-parses this payload; corrected after publication.",
    "recorded": "2026-09-15",
}


# --- A. no override: behaviour is byte-for-byte what it was ----------------


@pytest.mark.contract
def test_registry_without_override_resolves_exactly_as_before():
    registry = _registry(_entry("1.3.0", ">=1.5.5"), _entry("1.4.0", ">=1.5.9"))
    assert validate_registry_dict(registry) == []
    assert parse_registry(json.dumps(registry).encode())["plugin_api"] == 1

    assert find_registry_entry(registry, PLUGIN_ID, app_version="1.5.8")["version"] == "1.3.0"
    assert find_registry_entry(registry, PLUGIN_ID, app_version="1.5.9")["version"] == "1.4.0"
    assert effective_requires_app(registry["plugins"][1]) == ">=1.5.9"


@pytest.mark.contract
def test_absent_override_is_not_an_error_for_any_entry():
    registry = _registry(_entry("1.0.0", ">=1.4.0"))
    assert "compatibility_override" not in registry["plugins"][0]
    assert validate_compatibility_override(registry["plugins"][0]) == []
    assert validate_registry_dict(registry) == []


# --- B. a narrowing override changes real resolution ----------------------


@pytest.mark.contract
def test_narrowing_override_drives_the_production_resolver():
    registry = _registry(
        _entry("1.3.0", ">=1.5.5"),
        _entry("1.4.0", ">=1.5.9", override=NARROWING),
    )
    assert validate_registry_dict(registry) == []

    # 1.5.9 satisfies the published floor but not the corrected one, so the
    # resolver must fall back to 1.3.0 instead of offering 1.4.0.
    assert find_registry_entry(registry, PLUGIN_ID, app_version="1.5.9")["version"] == "1.3.0"
    # 1.6.0 satisfies the override and gets the newer version.
    assert find_registry_entry(registry, PLUGIN_ID, app_version="1.6.0")["version"] == "1.4.0"


@pytest.mark.contract
def test_narrowing_override_can_leave_nothing_compatible():
    registry = _registry(_entry("1.4.0", ">=1.5.9", override=NARROWING))
    with pytest.raises(RegistryError, match="compatible with app 1.5.9"):
        find_registry_entry(registry, PLUGIN_ID, app_version="1.5.9")


@pytest.mark.unit
def test_entry_level_check_agrees_with_the_resolver():
    entry = _entry("1.4.0", ">=1.5.9", override=NARROWING)
    assert entry_is_app_compatible(entry, "1.5.9") is False
    assert entry_is_app_compatible(entry, "1.6.0") is True


# --- C. an override may never widen ---------------------------------------


@pytest.mark.contract
def test_widening_override_is_rejected_by_application_registry_validation():
    widening = {"requires_app": ">=1.5.8", "reason": "widen", "recorded": "2026-09-15"}
    registry = _registry(_entry("1.4.0", ">=1.5.9", override=widening))

    problems = validate_registry_dict(registry)
    assert any("may only narrow compatibility" in problem for problem in problems), problems
    with pytest.raises(RegistryError):
        parse_registry(json.dumps(registry).encode())


@pytest.mark.contract
def test_widening_an_upper_bound_is_also_rejected():
    registry = _registry(
        _entry(
            "1.4.0",
            ">=1.5.9,<1.6.0",
            override={
                "requires_app": ">=1.5.9,<2.0.0",
                "reason": "widen the ceiling",
            },
        )
    )
    problems = validate_registry_dict(registry)
    assert any("may only narrow compatibility" in problem for problem in problems), problems


@pytest.mark.contract
@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ("not-an-object", "must be a JSON object"),
        ({"reason": "no range"}, "requires_app must be a non-empty string"),
        ({"requires_app": ">=1.6.0"}, "reason must be a non-empty string"),
        ({"requires_app": ">=1.6.0", "reason": "  "}, "reason must be a non-empty string"),
        (
            {"requires_app": "not a range", "reason": "bad"},
            "compatibility_override.unsupported requires_app clause",
        ),
        (
            {"requires_app": ">=1.6.0", "reason": "r", "recorded": "15/09/2026"},
            "recorded must be an ISO date",
        ),
        (
            {"requires_app": ">=1.6.0", "reason": "r", "surprise": 1},
            "unsupported key(s): surprise",
        ),
    ],
)
def test_malformed_override_fails_registry_validation(override, expected):
    registry = _registry(_entry("1.4.0", ">=1.5.9", override=override))
    problems = validate_registry_dict(registry)
    assert any(expected in problem for problem in problems), problems


@pytest.mark.unit
def test_malformed_override_fails_closed_in_resolution():
    """A malformed override never silently falls back to the wider range."""
    entry = _entry("1.4.0", ">=1.5.9", override={"requires_app": ">=1.6.0"})
    assert effective_requires_app(entry) is None
    assert entry_is_app_compatible(entry, "1.9.0") is False


# --- D. the installer stays the authority ---------------------------------


@pytest.mark.integration
def test_override_cannot_widen_what_the_manifest_permits(tmp_path: Path):
    """Even a registry claim the app accepted cannot beat the manifest."""
    manifest, manifest_bytes, profile_bytes = _manifest_and_profile("1.4.0", ">=1.5.9")
    entry = _entry("1.4.0", ">=1.5.9")
    # Simulate a registry that lies about the floor after validation.
    entry["requires_app"] = ">=1.5.8"
    responses = {
        OFFICIAL_RAW_BASE + "plugins/truba/1.4.0/manifest.json": manifest_bytes,
        OFFICIAL_RAW_BASE + "plugins/truba/1.4.0/cluster-profile.json": profile_bytes,
    }
    entry["manifest_sha256"] = _sha256(manifest_bytes)

    with pytest.raises(InstallError, match="requires app >=1.5.9"):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.5.8", fetcher=_fetcher(responses)
        )
    assert manifest["requires_app"] == ">=1.5.9"


@pytest.mark.integration
def test_unsupported_schema_stays_fail_closed_under_an_override(tmp_path: Path):
    """Schema capability is independent of any registry metadata."""
    from hpc_gui.plugins.schema_compat import app_supports_schema

    manifest, manifest_bytes, profile_bytes = _manifest_and_profile(
        "1.4.0", ">=1.5.9", schema_version=3
    )
    entry = _entry("1.4.0", ">=1.5.9", schema_version=3)
    entry["manifest_sha256"] = _sha256(manifest_bytes)
    entry["compatibility_override"] = NARROWING
    responses = {
        OFFICIAL_RAW_BASE + "plugins/truba/1.4.0/manifest.json": manifest_bytes,
        OFFICIAL_RAW_BASE + "plugins/truba/1.4.0/cluster-profile.json": profile_bytes,
    }

    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.5.8", fetcher=_fetcher(responses)
        )
    assert app_supports_schema("1.5.8", 3) is False


# --- G. the cached registry path keeps the same semantics ------------------


@pytest.mark.integration
def test_override_survives_the_cached_registry_path(tmp_path: Path):
    registry = _registry(
        _entry("1.3.0", ">=1.5.5"),
        _entry("1.4.0", ">=1.5.9", override=NARROWING),
    )
    payload = json.dumps(registry).encode()

    fresh = fetch_registry_with_cache(
        root=tmp_path, fetcher=_fetcher({OFFICIAL_REGISTRY_URL: payload})
    )
    assert fresh.source == "network"

    def offline(url: str, limit: int) -> bytes:
        raise OSError("offline")

    cached = fetch_registry_with_cache(root=tmp_path, fetcher=offline)
    assert cached.source == "cache"
    entry = find_registry_entry(cached.registry, PLUGIN_ID, app_version="1.5.9")
    assert entry["version"] == "1.3.0"
    assert (
        find_registry_entry(cached.registry, PLUGIN_ID, app_version="1.6.0")["version"]
        == "1.4.0"
    )


@pytest.mark.integration
def test_cache_rejects_a_widening_override(tmp_path: Path):
    """A poisoned cache file cannot smuggle a widening override in."""
    from hpc_gui.plugins.registry_client import read_cached_registry
    from hpc_gui.plugins.storage import plugins_root

    good = _registry(_entry("1.3.0", ">=1.5.5"))
    cache = Path(plugins_root(tmp_path)) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / "registry.json"

    # The fixture path itself is right: a clean cache file round-trips.
    cache_file.write_bytes(json.dumps(good).encode())
    assert read_cached_registry(tmp_path) is not None

    poisoned = _registry(
        _entry(
            "1.4.0",
            ">=1.5.9",
            override={"requires_app": ">=1.0.0", "reason": "poison"},
        )
    )
    cache_file.write_bytes(json.dumps(poisoned).encode())
    assert read_cached_registry(tmp_path) is None
