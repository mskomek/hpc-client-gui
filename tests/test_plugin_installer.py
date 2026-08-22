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
    manifest_dict["plugin_api"] = 2
    tampered = json.dumps(manifest_dict).encode()
    base = "plugins/truba/1.0.0"
    responses[OFFICIAL_RAW_BASE + base + "/manifest.json"] = tampered

    entry = make_registry_entry(manifest, tampered)
    with pytest.raises(InstallError, match="Unsupported plugin API|plugin_api must be 1"):
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
