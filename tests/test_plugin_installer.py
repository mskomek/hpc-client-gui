"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.downloader import (
    DownloadError,
    compute_local_sha256,
    download_exact_file,
    payload_url,
    validate_payload_rel_path,
)
from hpc_gui.plugins.installer import STAGING_DIR_NAME, InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
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
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import packages_dir, plugins_root, read_active_versions


VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": {
        "owner": "mskomek",
        "name": "hpc-client-gui-plugins",
        "raw_base": OFFICIAL_RAW_BASE,
    },
    "plugins": [],
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_plugin_files(
    *,
    plugin_id: str = "org.hpcclient.truba",
    version: str = "1.0.0",
    requires_app: str = ">=1.3.0",
) -> tuple[dict, bytes, bytes]:
    """Build a self-consistent manifest + cluster profile pair."""
    profile = {
        "schema_version": 1,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        "commands": {"status_command": "lssrv"},
    }
    profile_bytes = json.dumps(profile).encode("utf-8")
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": plugin_id,
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
                "sha256": sha256_bytes(profile_bytes),
                "size": len(profile_bytes),
                "role": "cluster-profile",
            }
        ],
    }
    manifest_bytes = json.dumps(manifest).encode("utf-8")
    return manifest, manifest_bytes, profile_bytes


def make_registry_entry(manifest: dict, manifest_bytes: bytes) -> dict:
    return {
        "id": manifest["id"],
        "name": manifest["name"],
        "version": manifest["version"],
        "plugin_api": 1,
        "type": "cluster-profile",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": manifest["requires_app"],
        "manifest_path": f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}/manifest.json",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "official": True,
    }


def make_fetcher(responses: dict[str, bytes]):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url not in responses:
            raise OSError(f"no response registered for {url}")
        payload = responses[url]
        if len(payload) > max_bytes:
            raise OSError(f"response exceeds {max_bytes} bytes")
        return payload

    return fetch


# ---------------------------------------------------------------------------
# Registry client
# ---------------------------------------------------------------------------


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
def test_parse_registry_rejects_invalid_payloads(mutation):
    bad = json.loads(json.dumps(VALID_REGISTRY))
    bad.update(mutation)
    with pytest.raises(RegistryError):
        parse_registry(json.dumps(bad).encode())


def test_registry_size_limit_constant():
    assert REGISTRY_MAX_BYTES == 1024 * 1024
    assert MANIFEST_MAX_BYTES == 256 * 1024
    assert FILE_MAX_BYTES == 5 * 1024 * 1024


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


def test_corrupt_cache_is_not_trusted(tmp_path: Path):
    (Path(tmp_path) / "cache").mkdir(parents=True)
    (Path(tmp_path) / "cache" / "registry.json").write_text("{corrupt", encoding="utf-8")

    def broken_fetch(url: str, max_bytes: int) -> bytes:
        raise OSError("network down")

    with pytest.raises(RegistryError):
        fetch_registry_with_cache(root=tmp_path, fetcher=broken_fetch)


def test_find_registry_entry_latest_and_specific():
    manifest, manifest_bytes, _ = make_plugin_files()
    entry_v1 = make_registry_entry(manifest, manifest_bytes)
    registry = {**VALID_REGISTRY, "plugins": [entry_v1]}
    found = find_registry_entry(registry, "org.hpcclient.truba")
    assert found["version"] == "1.0.0"
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.missing")


# ---------------------------------------------------------------------------
# Latest-version resolution (registry order must never decide "latest")
# ---------------------------------------------------------------------------


def make_fluent_entry(version: str, requires_app: str = ">=1.4.0") -> dict:
    return {
        "id": "org.hpcclient.fluent",
        "name": "Fluent Tools",
        "version": version,
        "plugin_api": 1,
        "type": "lint-rules",
        "description": "Fluent tools.",
        "publisher": "HPC Client GUI",
        "requires_app": requires_app,
        "manifest_path": f"plugins/fluent/{version}/manifest.json",
        "manifest_sha256": sha256_bytes(version.encode()),
        "official": True,
    }


def fluent_registry(*entries) -> dict:
    return {**VALID_REGISTRY, "plugins": list(entries)}


def test_latest_resolution_ascending_order():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"


def test_latest_resolution_reversed_order():
    registry = fluent_registry(make_fluent_entry("0.2.0"), make_fluent_entry("0.1.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"


def test_latest_resolution_with_app_version_guarantee():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version="1.4.0"
    )
    assert found["version"] == "0.2.0"


def test_explicit_version_selection():
    registry = fluent_registry(make_fluent_entry("0.1.0"), make_fluent_entry("0.2.0"))
    found = find_registry_entry(registry, "org.hpcclient.fluent", version="0.1.0")
    assert found["version"] == "0.1.0"
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent", version="9.9.9")


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


def test_no_compatible_version_raises():
    registry = fluent_registry(make_fluent_entry("0.2.0", ">=99.0.0"))
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent", app_version="1.4.0")


def test_prerelease_does_not_shadow_stable_release():
    registry = fluent_registry(
        make_fluent_entry("0.2.0"), make_fluent_entry("0.3.0rc1")
    )
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0"


def test_post_release_sorts_after_release():
    registry = fluent_registry(
        make_fluent_entry("0.2.0"), make_fluent_entry("0.2.0.post1")
    )
    found = find_registry_entry(registry, "org.hpcclient.fluent")
    assert found["version"] == "0.2.0.post1"


def test_duplicate_id_version_records_rejected():
    registry = fluent_registry(
        make_fluent_entry("0.1.0"), make_fluent_entry("0.1.0")
    )
    with pytest.raises(RegistryError, match="Duplicate"):
        find_registry_entry(registry, "org.hpcclient.fluent")


@pytest.mark.parametrize("bad", ["not-a-version", "", "1.0.0.0.0-final.broken"])
def test_invalid_versions_fail_validation(bad):
    registry = fluent_registry(make_fluent_entry(bad))
    with pytest.raises(RegistryError):
        find_registry_entry(registry, "org.hpcclient.fluent")


# ---------------------------------------------------------------------------
# Downloader path/URL security
# ---------------------------------------------------------------------------


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
def test_unsafe_payload_paths_rejected(bad):
    with pytest.raises(DownloadError):
        validate_payload_rel_path(bad)


def test_payload_url_requires_official_https_base():
    url = payload_url("plugins/truba/1.0.0/cluster-profile.json")
    assert url.startswith("https://raw.githubusercontent.com/")
    with pytest.raises(DownloadError):
        payload_url("x.json", raw_base="http://insecure.example/")


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


def test_download_missing_file_raises(tmp_path: Path):
    with pytest.raises(DownloadError):
        download_exact_file(
            rel_path="missing.json",
            destination_dir=tmp_path,
            expected_sha256="0" * 64,
            fetcher=make_fetcher({}),
        )


# ---------------------------------------------------------------------------
# Installer end-to-end (injected fetchers only)
# ---------------------------------------------------------------------------


def full_install_responses(**overrides) -> dict[str, bytes]:
    manifest, manifest_bytes, profile_bytes = make_plugin_files(**overrides)
    base = f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}"
    return {
        OFFICIAL_RAW_BASE + base + "/manifest.json": manifest_bytes,
        OFFICIAL_RAW_BASE + base + "/cluster-profile.json": profile_bytes,
    }, manifest, manifest_bytes


def test_valid_install_end_to_end(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)

    result = install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
    )
    assert result.activated is True
    version_dir = packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0"
    assert (version_dir / "manifest.json").is_file()
    assert (version_dir / "cluster-profile.json").is_file()
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    installed = read_installed_state(tmp_path)
    assert installed["org.hpcclient.truba"]["versions"] == ["1.0.0"]

    # The loader can pick the freshly installed plugin up.
    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert [p.manifest.id for p in loaded.plugins] == ["org.hpcclient.truba"]
    assert loaded.plugins[0].cluster_profiles[0].profile_id == "truba"


def test_only_declared_files_are_downloaded(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()

    def counting_fetch(url: str, max_bytes: int) -> bytes:
        assert url in responses, f"unexpected download of {url}"
        return responses[url]

    entry = make_registry_entry(manifest, manifest_bytes)
    install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=counting_fetch
    )


def test_bad_manifest_hash_aborts_install(tmp_path: Path):
    responses, manifest, _ = full_install_responses()
    entry = make_registry_entry(manifest, b"{}" * 10)
    entry["manifest_sha256"] = sha256_bytes(b"different")

    with pytest.raises(InstallError, match="SHA-256 mismatch"):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
        )
    assert not (packages_dir(tmp_path)).exists()
    assert read_active_versions(tmp_path) == {}


def test_bad_file_hash_aborts_and_cleans_staging(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    base = f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}"
    responses[OFFICIAL_RAW_BASE + base + "/cluster-profile.json"] += b"tamper"

    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError, match="SHA-256 mismatch|unexpected size"):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
        )
    staging_root = Path(plugins_root(tmp_path)) / STAGING_DIR_NAME
    assert not staging_root.exists() or not any(staging_root.iterdir())
    assert read_active_versions(tmp_path) == {}


def test_missing_file_aborts_install(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    base = f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}"
    del responses[OFFICIAL_RAW_BASE + base + "/cluster-profile.json"]

    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
        )
    assert read_active_versions(tmp_path) == {}


def test_incompatible_app_rejected_before_download(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses(requires_app=">=99.0.0")

    def refusing_fetch(url: str, max_bytes: int) -> bytes:
        raise AssertionError(f"must not download {url}")

    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.3.0", fetcher=refusing_fetch
        )


def test_unsupported_plugin_api_rejected(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    manifest_dict = json.loads(responses[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/manifest.json"])
    manifest_dict["plugin_api"] = 99
    tampered = json.dumps(manifest_dict).encode()
    base = "plugins/truba/1.0.0"
    responses[OFFICIAL_RAW_BASE + base + "/manifest.json"] = tampered

    entry = make_registry_entry(manifest, tampered)
    with pytest.raises(InstallError, match="Unsupported plugin API|plugin_api must be one of"):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
        )


def test_second_install_of_same_version_is_idempotent(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    fetcher = make_fetcher(responses)

    first = install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher
    )
    second = install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher
    )
    assert first.installed.manifest.id == second.installed.manifest.id
    assert read_installed_state(tmp_path)["org.hpcclient.truba"]["versions"] == ["1.0.0"]
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}


def test_interrupted_install_keeps_previous_state(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    fetcher = make_fetcher(responses)

    # First, a good 1.0.0 install.
    install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher)

    # Then a broken 1.1.0 install attempt.
    responses_110, manifest_110, manifest_bytes_110 = full_install_responses(version="1.1.0")
    base_110 = "plugins/truba/1.1.0"
    del responses_110[OFFICIAL_RAW_BASE + base_110 + "/cluster-profile.json"]
    entry_110 = make_registry_entry(manifest_110, manifest_bytes_110)

    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry_110, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses_110)
        )

    # The previous active version and its files are untouched.
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    assert (packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0" / "manifest.json").is_file()


def _assert_no_staging_or_part_leftovers(tmp_path: Path) -> None:
    base = Path(plugins_root(tmp_path))
    staging = base / STAGING_DIR_NAME
    assert not staging.exists() or not any(staging.iterdir())
    assert not list(base.rglob("*.part"))
    assert not list(base.rglob("*.tmp"))


# ---------------------------------------------------------------------------
# Immutable-version and failure-injection behaviour
# ---------------------------------------------------------------------------


def test_conflicting_same_version_payload_is_rejected(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
    )

    # A different payload published under the same immutable version.
    conflicting, conflicting_bytes, _ = full_install_responses(
        plugin_id="org.hpcclient.truba", version="1.0.0"
    )
    tampered_profile = json.loads(conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/cluster-profile.json"])
    tampered_profile["description"] = "A completely different payload."
    new_profile_bytes = json.dumps(tampered_profile).encode("utf-8")
    conflicting_manifest = json.loads(conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/manifest.json"])
    conflicting_manifest["files"][0]["sha256"] = sha256_bytes(new_profile_bytes)
    conflicting_manifest["files"][0]["size"] = len(new_profile_bytes)
    conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/cluster-profile.json"] = new_profile_bytes
    new_manifest_bytes = json.dumps(conflicting_manifest).encode("utf-8")
    conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/manifest.json"] = new_manifest_bytes
    conflicting_entry = make_registry_entry(conflicting_manifest, new_manifest_bytes)

    with pytest.raises(InstallError, match="immutable|conflict"):
        install_plugin_from_registry(
            conflicting_entry,
            root=tmp_path,
            app_version="1.4.0",
            fetcher=make_fetcher(conflicting),
        )

    # The previously active version is intact and still active.
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    kept = json.loads(
        (packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0" / "cluster-profile.json").read_text("utf-8")
    )
    assert "description" not in kept or kept.get("description") != "A completely different payload."
    _assert_no_staging_or_part_leftovers(tmp_path)


def test_corrupted_existing_version_is_not_overwritten(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    fetcher = make_fetcher(responses)
    install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher)

    version_file = packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0" / "cluster-profile.json"
    version_file.write_text('{"corrupted": true}', encoding="utf-8")

    with pytest.raises(InstallError, match="immutable|conflict"):
        install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher)

    assert version_file.read_text(encoding="utf-8") == '{"corrupted": true}'
    _assert_no_staging_or_part_leftovers(tmp_path)


def test_idempotent_reinstall_leaves_directory_untouched(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    fetcher = make_fetcher(responses)
    install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher)

    version_dir = packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0"
    before = {
        p.relative_to(version_dir).as_posix(): (p.stat().st_size, compute_local_sha256(p))
        for p in sorted(version_dir.rglob("*"))
        if p.is_file()
    }
    install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.0", fetcher=fetcher)

    after = {
        p.relative_to(version_dir).as_posix(): (p.stat().st_size, compute_local_sha256(p))
        for p in sorted(version_dir.rglob("*"))
        if p.is_file()
    }
    assert after == before
    assert set(after) == {"manifest.json", "cluster-profile.json"}
    assert read_installed_state(tmp_path)["org.hpcclient.truba"]["versions"] == ["1.0.0"]
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    _assert_no_staging_or_part_leftovers(tmp_path)


def test_update_from_older_to_newer_version(tmp_path: Path):
    responses_old, manifest_old, bytes_old = full_install_responses(version="0.1.0")
    entry_old = make_registry_entry(manifest_old, bytes_old)
    responses_new, manifest_new, bytes_new = full_install_responses(version="0.2.0")
    entry_new = make_registry_entry(manifest_new, bytes_new)

    install_plugin_from_registry(
        entry_old, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses_old)
    )
    result = install_plugin_from_registry(
        entry_new, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses_new)
    )
    assert result.activated
    assert read_active_versions(tmp_path)["org.hpcclient.truba"] == "0.2.0"
    # 0.1.0 stays on disk for rollback.
    assert (
        packages_dir(tmp_path) / "org.hpcclient.truba" / "0.1.0" / "manifest.json"
    ).is_file()
    assert sorted(read_installed_state(tmp_path)["org.hpcclient.truba"]["versions"]) == [
        "0.1.0",
        "0.2.0",
    ]


def test_failed_update_preserves_previous_version(tmp_path: Path):
    responses_old, manifest_old, bytes_old = full_install_responses(version="0.1.0")
    entry_old = make_registry_entry(manifest_old, bytes_old)
    install_plugin_from_registry(
        entry_old, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses_old)
    )

    responses_new, manifest_new, bytes_new = full_install_responses(version="0.2.0")
    del responses_new[OFFICIAL_RAW_BASE + "plugins/truba/0.2.0/cluster-profile.json"]
    entry_new = make_registry_entry(manifest_new, bytes_new)
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry_new, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses_new)
        )

    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "0.1.0"}
    assert (
        packages_dir(tmp_path) / "org.hpcclient.truba" / "0.1.0" / "manifest.json"
    ).is_file()
    assert not (packages_dir(tmp_path) / "org.hpcclient.truba" / "0.2.0").exists()
    _assert_no_staging_or_part_leftovers(tmp_path)


def test_failure_before_activation_preserves_previous_active(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.installer as installer_module

    responses_old, manifest_old, bytes_old = full_install_responses(version="0.1.0")
    install_plugin_from_registry(
        make_registry_entry(manifest_old, bytes_old),
        root=tmp_path,
        app_version="1.4.0",
        fetcher=make_fetcher(responses_old),
    )

    responses_new, manifest_new, bytes_new = full_install_responses(version="0.2.0")
    entry_new = make_registry_entry(manifest_new, bytes_new)

    def exploding_record(*args, **kwargs):
        raise OSError("disk full while writing state")

    monkeypatch.setattr(installer_module, "record_installed_version", exploding_record)
    with pytest.raises(Exception):
        install_plugin_from_registry(
            entry_new,
            root=tmp_path,
            app_version="1.4.0",
            fetcher=make_fetcher(responses_new),
        )

    # Files were published but activation never happened; the previous
    # active pointer is untouched.
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "0.1.0"}
    _assert_no_staging_or_part_leftovers(tmp_path)


def test_post_activation_loader_failure_rolls_back(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.loader as loader_module

    responses_old, manifest_old, bytes_old = full_install_responses(version="0.1.0")
    install_plugin_from_registry(
        make_registry_entry(manifest_old, bytes_old),
        root=tmp_path,
        app_version="1.4.0",
        fetcher=make_fetcher(responses_old),
    )

    responses_new, manifest_new, bytes_new = full_install_responses(version="0.2.0")
    entry_new = make_registry_entry(manifest_new, bytes_new)

    real_load = loader_module.load_installed_plugins

    def failing_load(**kwargs):
        result = real_load(**kwargs)
        result.plugins = [p for p in result.plugins if p.manifest.version != "0.2.0"]
        return result

    monkeypatch.setattr(loader_module, "load_installed_plugins", failing_load)
    with pytest.raises(InstallError, match="previous version 0.1.0 remains active"):
        install_plugin_from_registry(
            entry_new,
            root=tmp_path,
            app_version="1.4.0",
            fetcher=make_fetcher(responses_new),
        )

    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "0.1.0"}
    _assert_no_staging_or_part_leftovers(tmp_path)
