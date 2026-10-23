"""Cross-repository Plugin API v1 contract test.

Runs against a real checkout of the official plugin registry
(https://github.com/mskomek/hpc-client-gui-plugins). Set
``HPC_GUI_CONTRACT_REPO`` to the checkout path to enable it; CI checks the
repository out into a sibling directory. All downloads are served from the
local checkout through an injected fetcher, so no network access and no
GitHub token are needed at test time.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from hpc_gui.plugins.compatibility import (
    effective_requires_app,
    is_app_compatible,
    validate_compatibility_override,
)
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    find_registry_entry,
    parse_registry,
)
from hpc_gui.plugins.schema_compat import (
    MIN_APP_VERSION_FOR_SCHEMA,
    schema_floor_error,
)
from hpc_gui.plugins.validator import validate_registry_dict

# Current application release line under test (first schema-3/4 capable).
CONTRACT_APP_VERSION = "1.5.9"
# Published release with cluster-profile schemas 1-2 only.
RELEASED_APP_VERSION = "1.5.8"
# Oldest registry-served application line.
OLDEST_SUPPORTED_APP_VERSION = "1.5.5"

REPO = os.environ.get("HPC_GUI_CONTRACT_REPO", "")
pytestmark = pytest.mark.skipif(
    not REPO or not Path(REPO).is_dir(),
    reason="HPC_GUI_CONTRACT_REPO does not point to an official plugins checkout",
)


@pytest.fixture(scope="module")
def plugins_repo() -> Path:
    return Path(REPO).resolve()


@pytest.fixture(scope="module")
def local_fetcher(plugins_repo: Path):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url == OFFICIAL_REGISTRY_URL:
            payload = (plugins_repo / "registry.json").read_bytes()
        elif url.startswith(OFFICIAL_RAW_BASE):
            payload = (plugins_repo / url[len(OFFICIAL_RAW_BASE):]).read_bytes()
        else:
            raise OSError(f"unexpected URL outside the official raw base: {url}")
        if len(payload) > max_bytes:
            raise OSError("response exceeds size limit")
        return payload

    return fetch


@pytest.fixture(scope="module")
def registry(plugins_repo: Path) -> dict:
    return parse_registry((plugins_repo / "registry.json").read_bytes())


@pytest.mark.contract
def test_real_registry_passes_repository_validator(plugins_repo: Path):
    scripts_dir = plugins_repo / "scripts"
    assert (scripts_dir / "validate_registry.py").is_file()
    sys.path.insert(0, str(scripts_dir))
    try:
        import validate_registry  # noqa: PLC0415

        errors, warnings = validate_registry.validate_repository(root=plugins_repo)
        assert not errors, f"registry validation failed: {errors}"
    finally:
        sys.path.remove(str(scripts_dir))


@pytest.mark.contract
def test_override_contract_agrees_across_both_repositories(plugins_repo: Path, registry: dict):
    """Both sides must compute the same effective compatibility range.

    The registry's own helper and the application's helper are separate
    implementations behind a trust boundary; a drift between them would let
    one repository honour a correction the other ignores.
    """
    scripts_dir = plugins_repo / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import schema_compatibility  # noqa: PLC0415

        for entry in registry["plugins"]:
            assert schema_compatibility.effective_requires_app(
                entry
            ) == effective_requires_app(entry)

        corrected = dict(registry["plugins"][0])
        corrected["compatibility_override"] = {
            "requires_app": ">=99.0.0",
            "reason": "contract check: narrowing correction",
            "recorded": "2026-09-15",
        }
        assert schema_compatibility.override_error(corrected) is None
        assert validate_compatibility_override(corrected) == []
        assert (
            schema_compatibility.effective_requires_app(corrected)
            == effective_requires_app(corrected)
            == ">=99.0.0"
        )

        widening = dict(registry["plugins"][0])
        widening["compatibility_override"] = {
            "requires_app": ">=0.1.0",
            "reason": "contract check: illegal widening",
        }
        assert schema_compatibility.override_error(widening) is not None
        assert validate_compatibility_override(widening) != []
        assert effective_requires_app(widening) is None
    finally:
        sys.path.remove(str(scripts_dir))


@pytest.mark.contract
def test_real_registry_resolution_honours_a_narrowing_override(registry: dict):
    """The production resolver, on the real registry, obeys an override."""
    baseline = find_registry_entry(
        registry, "org.hpcclient.truba", app_version=CONTRACT_APP_VERSION
    )
    patched = json.loads(json.dumps(registry))
    for entry in patched["plugins"]:
        if entry["id"] == "org.hpcclient.truba" and entry["version"] == baseline["version"]:
            entry["compatibility_override"] = {
                "requires_app": ">=99.0.0",
                "reason": "contract check: withdraw the newest version",
                "recorded": "2026-09-15",
            }
    assert validate_registry_dict(patched) == []
    resolved = find_registry_entry(
        patched, "org.hpcclient.truba", app_version=CONTRACT_APP_VERSION
    )
    assert resolved["version"] != baseline["version"]


@pytest.mark.contract
def test_plugin_repository_schema_matrix_matches_application(plugins_repo: Path):
    """Drift guard: the independently validatable plugin-side matrix must
    equal the application's canonical capability contract."""
    matrix_path = plugins_repo / "scripts" / "schema_compatibility.py"
    assert matrix_path.is_file()
    spec = importlib.util.spec_from_file_location("plugin_schema_compatibility", matrix_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.MIN_APP_VERSION_FOR_SCHEMA == MIN_APP_VERSION_FOR_SCHEMA


@pytest.mark.contract
def test_every_plugin_id_resolves_on_current_app(registry: dict):
    ids = sorted({entry["id"] for entry in registry["plugins"]})
    assert ids, "official registry must not be empty"
    for plugin_id in ids:
        entry = find_registry_entry(registry, plugin_id, app_version=CONTRACT_APP_VERSION)
        assert is_app_compatible(str(entry["requires_app"]), CONTRACT_APP_VERSION), (
            f"{plugin_id} resolved to {entry['version']} which excludes "
            f"{CONTRACT_APP_VERSION}"
        )


@pytest.mark.contract
def test_manifest_hashes_and_identities_match_registry(registry: dict, plugins_repo: Path):
    import hashlib

    for entry in registry["plugins"]:
        payload = (plugins_repo / entry["manifest_path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["manifest_sha256"], (
            entry["manifest_path"]
        )
        manifest = json.loads(payload)
        assert manifest["id"] == entry["id"]
        assert manifest["version"] == entry["version"]
        assert manifest["requires_app"] == entry["requires_app"]
        if manifest["plugin_api"] == 2:
            assert "linter-tool" in manifest["capabilities"]
            continue
        assert manifest["plugin_api"] == 1


@pytest.mark.contract
def test_published_payload_schema_floors_are_honest(registry: dict, plugins_repo: Path):
    """The exact regression gate: no published payload may claim an app
    release older than the first one implementing its schema."""
    problems = []
    for entry in registry["plugins"]:
        manifest_path = plugins_repo / entry["manifest_path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for file_entry in manifest.get("files", []):
            if file_entry.get("role") != "cluster-profile":
                continue
            profile_path = manifest_path.parent / file_entry["path"]
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            error = schema_floor_error(
                profile.get("schema_version"), str(manifest.get("requires_app", ""))
            )
            if error:
                problems.append(f"{entry['id']}@{entry['version']}: {error}")
    assert not problems, "\n".join(problems)
