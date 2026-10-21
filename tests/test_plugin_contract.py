"""Cross-repository Plugin API v1 contract test.

Runs against a real checkout of the official plugin registry
(https://github.com/mskomek/hpc-client-gui-plugins). Set
``HPC_GUI_CONTRACT_REPO`` to the checkout path to enable it; CI checks the
repository out into a sibling directory. All downloads are served from the
local checkout through an injected fetcher, so no network access and no
GitHub token are needed at test time.
"""

from __future__ import annotations

pytest_plugins = ('support.test_plugin_contract_shared',)
from support.test_plugin_contract_shared import (
    CONTRACT_APP_VERSION,
    InstallError,
    MIN_APP_VERSION_FOR_SCHEMA,
    OLDEST_SUPPORTED_APP_VERSION,
    Path,
    RELEASED_APP_VERSION,
    REPO,
    _install,
    app_supports_schema,
    effective_requires_app,
    find_registry_entry,
    importlib,
    install_plugin_from_registry,
    is_app_compatible,
    json,
    load_installed_plugins,
    pytest,
    schema_floor_error,
    sys,
    validate_compatibility_override,
    validate_registry_dict,
)

pytestmark = pytest.mark.skipif(
    not REPO or not Path(REPO).is_dir(),
    reason="HPC_GUI_CONTRACT_REPO does not point to an official plugins checkout",
)

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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
def test_registry_compatibility_claim_cannot_bypass_schema_rejection(
    registry, local_fetcher, tmp_path: Path
):
    """Registry metadata never widens what the installer will accept.

    A registry entry that claims (or is corrected by a registry-level
    compatibility override to claim) an older floor still cannot make a
    schema-3 payload installable on a release that validates schemas 1-2.
    The installer's schema capability check is the final authority and
    fails closed.
    """
    entry = dict(
        find_registry_entry(
            registry,
            "org.hpcclient.truba",
            version="1.4.0",
            app_version=CONTRACT_APP_VERSION,
        )
    )
    entry["requires_app"] = f">={RELEASED_APP_VERSION}"
    with pytest.raises(InstallError, match="requires app >=1.5.9"):
        install_plugin_from_registry(
            entry,
            root=tmp_path,
            app_version=RELEASED_APP_VERSION,
            fetcher=local_fetcher,
        )
    # The capability matrix agrees independently of any registry claim: the
    # released 1.5.8 line never validates a schema-3 payload.
    assert not app_supports_schema(RELEASED_APP_VERSION, 3)
    assert app_supports_schema(CONTRACT_APP_VERSION, 3)

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.contract
def test_current_app_line_resolves_every_published_plugin(registry: dict):
    """Nothing published may be unreachable by the current application line."""
    for plugin_id in sorted({entry["id"] for entry in registry["plugins"]}):
        entry = find_registry_entry(
            registry, plugin_id, app_version=CONTRACT_APP_VERSION
        )
        assert is_app_compatible(str(entry["requires_app"]), CONTRACT_APP_VERSION)

@pytest.mark.contract
def test_oldest_supported_app_line_still_resolves_a_version(registry: dict):
    """Plugins that already shipped for the oldest served line keep one.

    Plugins first published for a later release (the community cluster
    providers declare ``>=1.5.8``) legitimately have no version for an older
    line; that is a publication date, not a compatibility regression.
    """
    for plugin_id in ("org.hpcclient.truba", "org.hpcclient.fluent"):
        entry = find_registry_entry(
            registry, plugin_id, app_version=OLDEST_SUPPORTED_APP_VERSION
        )
        assert is_app_compatible(
            str(entry["requires_app"]), OLDEST_SUPPORTED_APP_VERSION
        )
