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

from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
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
from hpc_gui.plugins.state import activate_version

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


def test_every_plugin_id_resolves_on_current_app(registry: dict):
    ids = sorted({entry["id"] for entry in registry["plugins"]})
    assert ids, "official registry must not be empty"
    for plugin_id in ids:
        entry = find_registry_entry(registry, plugin_id, app_version=CONTRACT_APP_VERSION)
        assert is_app_compatible(str(entry["requires_app"]), CONTRACT_APP_VERSION), (
            f"{plugin_id} resolved to {entry['version']} which excludes "
            f"{CONTRACT_APP_VERSION}"
        )


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


def _install(local_fetcher, tmp_path: Path, entry: dict, app_version: str = CONTRACT_APP_VERSION):
    return install_plugin_from_registry(
        entry,
        root=tmp_path,
        app_version=app_version,
        fetcher=local_fetcher,
    )


def test_truba_latest_resolves_and_profile_loads(registry, local_fetcher, tmp_path: Path):
    entry = find_registry_entry(
        registry, "org.hpcclient.truba", app_version=CONTRACT_APP_VERSION
    )
    assert entry["version"] == "1.5.0"  # first schema-4 capable release
    result = _install(local_fetcher, tmp_path, entry)
    assert result.activated

    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    truba = [p for p in loaded.plugins if p.manifest.id == "org.hpcclient.truba"]
    assert len(truba) == 1
    profiles = truba[0].cluster_profiles
    assert len(profiles) == 1
    assert profiles[0].profile_id == "truba"
    assert profiles[0].scheduler == "slurm"
    assert profiles[0].schema_version == 4


def test_released_1_5_8_gets_latest_compatible_truba(registry, local_fetcher, tmp_path: Path):
    """v1.5.8 supports schemas 1-2 only; TRUBA 1.3.0 is the fallback."""
    entry = find_registry_entry(
        registry, "org.hpcclient.truba", app_version=RELEASED_APP_VERSION
    )
    assert entry["version"] == "1.3.0"
    result = install_plugin_from_registry(
        entry,
        root=tmp_path,
        app_version=CONTRACT_APP_VERSION,
        fetcher=local_fetcher,
    )
    assert result.activated
    assert result.installed.cluster_profiles[0].schema_version == 2


def test_truba_1_4_0_rejected_on_released_1_5_8(registry, local_fetcher, tmp_path: Path):
    entry = find_registry_entry(
        registry,
        "org.hpcclient.truba",
        version="1.4.0",
        app_version=CONTRACT_APP_VERSION,
    )
    with pytest.raises(InstallError, match="requires app >=1.5.9"):
        install_plugin_from_registry(
            entry,
            root=tmp_path,
            app_version=RELEASED_APP_VERSION,
            fetcher=local_fetcher,
        )


def test_truba_1_4_0_installs_on_schema3_capable_release(
    registry, local_fetcher, tmp_path: Path
):
    entry = find_registry_entry(
        registry,
        "org.hpcclient.truba",
        version="1.4.0",
        app_version=CONTRACT_APP_VERSION,
    )
    result = _install(local_fetcher, tmp_path, entry)
    assert result.activated
    assert result.installed.cluster_profiles[0].schema_version == 3
    assert result.installed.cluster_profiles[0].job_outputs is not None


def test_truba_v2_plugin_installs_and_retains_structured_sections(
    registry, local_fetcher, tmp_path: Path
):
    entry = find_registry_entry(
        registry,
        "org.hpcclient.truba",
        version="1.1.0",
        app_version=CONTRACT_APP_VERSION,
    )
    result = install_plugin_from_registry(
        entry, root=tmp_path, app_version=CONTRACT_APP_VERSION, fetcher=local_fetcher
    )
    assert result.activated

    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    profile = loaded.plugins[0].cluster_profiles[0]
    assert profile.schema_version == 2
    assert {item["id"] for item in profile.storage} == {"home", "scratch"}
    assert profile.quota_sources[0]["enabled"] is False


def test_oldest_supported_app_line_still_resolves_a_version(registry: dict):
    for plugin_id in sorted({entry["id"] for entry in registry["plugins"]}):
        entry = find_registry_entry(
            registry, plugin_id, app_version=OLDEST_SUPPORTED_APP_VERSION
        )
        assert is_app_compatible(
            str(entry["requires_app"]), OLDEST_SUPPORTED_APP_VERSION
        )


def test_fluent_latest_compatible_and_loads(registry, local_fetcher, tmp_path: Path):
    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    assert entry["version"] == "0.3.0"
    # Explicit selection still resolves exactly.
    old = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.1.0", app_version=CONTRACT_APP_VERSION
    )
    assert old["version"] == "0.1.0"

    result = _install(local_fetcher, tmp_path, entry)
    assert result.installed.manifest.version == "0.3.0"
    capabilities = set(result.installed.manifest.capabilities)
    assert {"lint-rules", "job-template"} <= capabilities


def test_fluent_lint_rules_run(registry, local_fetcher, tmp_path: Path):
    from hpc_gui.lint.engine import lint_text
    from hpc_gui.lint.rulepack import load_lint_packs

    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    _install(local_fetcher, tmp_path, entry)

    packs = load_lint_packs(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    fluent_packs = [
        pack for pack in packs if pack.plugin_id == "org.hpcclient.fluent"
    ]
    assert fluent_packs, "Fluent lint pack must load"

    journal_without_tui = "/solve/iterate 100\n"
    diagnostics = []
    for pack in fluent_packs:
        diagnostics.extend(
            lint_text(journal_without_tui, file_name="run.jou", rule_pack=pack)
        )
    rule_ids = {diagnostic.rule_id for diagnostic in diagnostics}
    assert any(rule_id.startswith("FLUENT") for rule_id in rule_ids), sorted(rule_ids)


def test_fluent_slurm_template_is_plain_substitution(
    registry, local_fetcher, tmp_path: Path
):
    from hpc_gui.plugins.job_templates import load_job_templates, render_template

    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    result_version = _install(local_fetcher, tmp_path, entry).installed.manifest.version

    templates = load_job_templates(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    assert templates, "Fluent job template must load"
    template = next(t for t in templates if t.id == "fluent-slurm-basic")

    values = {
        "partition": "long",
        "cpus": 16,
        "time_limit": "04:00:00",
        "fluent_version": "v252",
        "journal_file": "case.jou",
        "journal_base": "fluent_run",
    }
    rendered = render_template(template, values)

    # Plain substitution proof: manual replacement over the exact installed
    # template bytes must produce identical output. No shell/format
    # evaluation happens during rendering.
    body = (
        tmp_path
        / "packages"
        / "org.hpcclient.fluent"
        / result_version
        / "templates"
        / "fluent_job.slurm.tpl"
    ).read_text(encoding="utf-8")
    expected = body
    for key, value in values.items():
        expected = expected.replace("{{" + key + "}}", str(value))
    assert rendered == expected
    assert "{{" not in rendered

    # Template content never executes anything by itself: no command is run
    # during rendering; this assertion documents the invariant explicitly.
    assert "#!/bin/bash" in rendered


def test_fluent_update_then_rollback_preserves_versions(
    registry, local_fetcher, tmp_path: Path
):
    old = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.1.0", app_version=CONTRACT_APP_VERSION
    )
    new = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.2.0", app_version=CONTRACT_APP_VERSION
    )

    _install(local_fetcher, tmp_path, old)
    packages = tmp_path / "packages" / "org.hpcclient.fluent"
    assert (packages / "0.1.0").is_dir()

    _install(local_fetcher, tmp_path, new)
    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    active_fluent = [
        p.manifest.version for p in loaded.plugins if p.manifest.id == "org.hpcclient.fluent"
    ]
    assert active_fluent == ["0.2.0"]
    assert (packages / "0.1.0").is_dir()  # kept for rollback

    activate_version("org.hpcclient.fluent", "0.1.0", root=tmp_path)
    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    active_fluent = [
        p.manifest.version for p in loaded.plugins if p.manifest.id == "org.hpcclient.fluent"
    ]
    assert active_fluent == ["0.1.0"]


def test_contract_metadata_documented(plugins_repo: Path):
    readme = (plugins_repo / "README.md").read_text(encoding="utf-8")
    assert "Available plugins" in readme
