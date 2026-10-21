"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations
from support.test_plugin_installer_shared import (
    FILE_MAX_BYTES,
    InstallError,
    MANIFEST_MAX_BYTES,
    Path,
    REGISTRY_MAX_BYTES,
    RegistryError,
    VALID_REGISTRY,
    _assert_no_staging_or_part_leftovers,
    find_registry_entry,
    fluent_registry,
    full_install_responses,
    install_plugin_from_registry,
    json,
    load_installed_plugins,
    make_fetcher,
    make_fluent_entry,
    make_plugin_files,
    make_registry_entry,
    packages_dir,
    parse_registry,
    pytest,
)

@pytest.mark.contract
def test_parse_registry_accepts_valid_payload():
    registry = parse_registry(json.dumps(VALID_REGISTRY).encode())
    assert registry["schema_version"] == 1

@pytest.mark.parametrize(
    "mutation",
    [
        {"schema_version": 2},
        {"plugin_api": 2},
        {"repository": {"raw_base": "http://insecure/"}},
        {"plugins": [{"id": "x"}]},
    ],
)
@pytest.mark.contract
def test_parse_registry_rejects_invalid_payloads(mutation):
    bad = json.loads(json.dumps(VALID_REGISTRY))
    bad.update(mutation)
    with pytest.raises(RegistryError):
        parse_registry(json.dumps(bad).encode())

@pytest.mark.contract
def test_registry_size_limit_constant():
    assert REGISTRY_MAX_BYTES == 1024 * 1024
    assert MANIFEST_MAX_BYTES == 256 * 1024
    assert FILE_MAX_BYTES == 5 * 1024 * 1024

@pytest.mark.unit
def test_find_registry_entry_latest_and_specific():
    manifest, manifest_bytes, _ = make_plugin_files()
    entry_v1 = make_registry_entry(manifest, manifest_bytes)
    registry = {**VALID_REGISTRY, "plugins": [entry_v1]}
    found = find_registry_entry(registry, "org.hpcclient.truba")
    assert found["version"] == "1.0.0"
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.missing")

@pytest.mark.unit
def test_latest_resolution_ascending_order():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"

@pytest.mark.unit
def test_latest_resolution_reversed_order():
    registry = fluent_registry(make_fluent_entry("0.2.0"), make_fluent_entry("0.1.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"

@pytest.mark.unit
def test_latest_resolution_with_app_version_guarantee():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version="1.4.0"
    )
    assert found["version"] == "0.2.0"

@pytest.mark.unit
def test_explicit_version_selection():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent", version="0.1.0")
    assert found["version"] == "0.1.0"
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent", version="9.9.9")

@pytest.mark.unit
def test_no_compatible_version_raises():
    registry = fluent_registry(make_fluent_entry("0.2.0", ">=99.0.0"))
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent", app_version="1.4.0")

@pytest.mark.unit
def test_prerelease_does_not_shadow_stable_release():
    registry = fluent_registry(
        make_fluent_entry("0.2.0"), make_fluent_entry("0.3.0rc1")
    )
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"

@pytest.mark.unit
def test_post_release_sorts_after_release():
    registry = fluent_registry(
        make_fluent_entry("0.2.0"), make_fluent_entry("0.2.0.post1")
    )
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0.post1"

@pytest.mark.unit
def test_duplicate_id_version_records_rejected():
    registry = fluent_registry(
        make_fluent_entry("0.1.0"), make_fluent_entry("0.1.0")
    )
    with pytest.raises(RegistryError, match="Duplicate"):
        find_registry_entry(registry, "org.hpcclient.fluent")

@pytest.mark.parametrize("bad", ["not-a-version", "", "1.0.0.0.0-final.broken"])
@pytest.mark.contract
def test_invalid_versions_fail_validation(bad):
    registry = fluent_registry(make_fluent_entry(bad))
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent")

@pytest.mark.integration
def test_schema3_floor_below_schema_capability_is_rejected(tmp_path: Path):
    """A schema-3 payload declaring >=1.5.8 (the released schema-1/2 app) is a
    false compatibility claim and must fail closed before activation."""
    responses, manifest, manifest_bytes = full_install_responses(
        schema_version=3, requires_app=">=1.5.8"
    )
    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError, match="first requires app 1.5.9"):
        install_plugin_from_registry(
            entry,
            root=tmp_path,
            app_version="1.5.9",
            fetcher=make_fetcher(responses),
        )
    assert not (packages_dir(tmp_path) / "org.hpcclient.truba").exists()
    _assert_no_staging_or_part_leftovers(tmp_path)

@pytest.mark.integration
def test_schema3_floor_capable_app_installs(tmp_path: Path):
    """The first schema-3 capable application installs the same payload when
    the declared floor is honest."""
    responses, manifest, manifest_bytes = full_install_responses(
        schema_version=3, requires_app=">=1.5.9"
    )
    entry = make_registry_entry(manifest, manifest_bytes)
    result = install_plugin_from_registry(
        entry,
        root=tmp_path,
        app_version="1.5.9",
        fetcher=make_fetcher(responses),
    )
    assert result.activated is True
    assert result.installed.cluster_profiles[0].schema_version == 3

    loaded = load_installed_plugins(root=tmp_path, app_version="1.5.9")
    assert [p.manifest.version for p in loaded.plugins] == ["1.0.0"]
