"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpc_gui.plugins.downloader import (
    DownloadError,
    download_exact_file,
    payload_url,
    validate_payload_rel_path,
)
from hpc_gui.plugins.registry_client import (
    FILE_MAX_BYTES,
    MANIFEST_MAX_BYTES,
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    REGISTRY_MAX_BYTES,
    RegistryError,
    fetch_registry_with_cache,
    find_registry_entry,
    parse_registry,
)
from support.plugin_installer_fixtures import (VALID_REGISTRY, fluent_registry, make_fetcher, make_fluent_entry, make_plugin_files, make_registry_entry, sha256_bytes)


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


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "../escape.json",
        "a/../../b.json",
        "/absolute.json",
        "C:\\evil.json",
        "%2e%2e%2fescape.json",
        "file\0.txt",
        "a//b.json",
    ],
)
@pytest.mark.contract
def test_unsafe_payload_paths_rejected(bad):
    with pytest.raises(DownloadError):
        validate_payload_rel_path(bad)


@pytest.mark.contract
def test_payload_url_requires_official_https_base():
    url = payload_url("plugins/truba/1.0.0/cluster-profile.json")
    assert url.startswith("https://raw.githubusercontent.com/")
    with pytest.raises(DownloadError):
        payload_url("x.json", raw_base="http://insecure.example/")


@pytest.mark.unit
def test_download_exact_file_verifies_hash_and_size(tmp_path: Path):
    payload = b'{"hello": "world"}'
    fetcher = make_fetcher(
        {OFFICIAL_RAW_BASE + "data/file.json": payload}
    )
    destination = download_exact_file(
        rel_path="data/file.json",
        destination_dir=tmp_path,
        expected_sha256=sha256_bytes(payload),
        expected_size=len(payload),
        fetcher=fetcher,
    )
    assert destination.read_bytes() == payload
    assert not list(tmp_path.rglob("*.part"))

    with pytest.raises(DownloadError, match="SHA-256"):
        download_exact_file(
            rel_path="data/file.json",
            destination_dir=tmp_path / "bad-hash",
            expected_sha256="0" * 64,
            fetcher=fetcher,
        )

    with pytest.raises(DownloadError, match="unexpected size"):
        download_exact_file(
            rel_path="data/file.json",
            destination_dir=tmp_path / "bad-size",
            expected_sha256=sha256_bytes(payload),
            expected_size=len(payload) + 5,
            fetcher=fetcher,
        )


@pytest.mark.unit
def test_download_missing_file_raises(tmp_path: Path):
    with pytest.raises(DownloadError):
        download_exact_file(
            rel_path="missing.json",
            destination_dir=tmp_path,
            expected_sha256="0" * 64,
            fetcher=make_fetcher({}),
        )
