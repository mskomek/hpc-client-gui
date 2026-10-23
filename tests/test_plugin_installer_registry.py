"""Plugin installer tests: Registry parsing, caching, and version resolution."""

from __future__ import annotations

import pytest

from plugin_installer_test_support import (
    FILE_MAX_BYTES,
    MANIFEST_MAX_BYTES,
    OFFICIAL_REGISTRY_URL,
    Path,
    REGISTRY_MAX_BYTES,
    RegistryError,
    VALID_REGISTRY,
    fetch_registry_with_cache,
    find_registry_entry,
    fluent_registry,
    json,
    make_fetcher,
    make_fluent_entry,
    make_plugin_files,
    make_registry_entry,
    parse_registry,
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


@pytest.mark.integration
def test_network_fetch_then_cache_fallback(tmp_path: Path):
    payload = json.dumps(VALID_REGISTRY).encode()
    fetcher = make_fetcher({OFFICIAL_REGISTRY_URL: payload})

    first = fetch_registry_with_cache(root=tmp_path, fetcher=fetcher)
    assert first.source == "network"

    # Network now fails; cache must serve the last known good registry.
    def broken_fetch(url: str, max_bytes: int) -> bytes:
        raise OSError("network down")

    second = fetch_registry_with_cache(root=tmp_path, fetcher=broken_fetch)
    assert second.source == "cache"
    assert second.registry["schema_version"] == 1

    # No cache anywhere and network down must raise, not crash silently.
    with pytest.raises(RegistryError):
        fetch_registry_with_cache(root=tmp_path / "empty", fetcher=broken_fetch)


@pytest.mark.integration
def test_corrupt_cache_is_not_trusted(tmp_path: Path):
    (Path(tmp_path) / "cache").mkdir(parents=True)
    (Path(tmp_path) / "cache" / "registry.json").write_text("{corrupt", encoding="utf-8")

    def broken_fetch(url: str, max_bytes: int) -> bytes:
        raise OSError("network down")

    with pytest.raises(RegistryError):
        fetch_registry_with_cache(root=tmp_path, fetcher=broken_fetch)


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
def test_incompatible_newer_version_is_skipped():
    registry = fluent_registry(
        make_fluent_entry("0.1.0", ">=1.4.0"),
        make_fluent_entry("0.2.0", ">=1.5.0"),
    )
    found = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version="1.4.0"
    )
    assert found["version"] == "0.1.0"

    # The newest overall is still resolvable explicitly.
    explicit = find_registry_entry(registry, "org.hpcclient.fluent", version="0.2.0")
    assert explicit["version"] == "0.2.0"


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
