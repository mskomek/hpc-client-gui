"""Plugin installer tests: Atomic plugin installation and integrity behavior."""

from __future__ import annotations

import pytest

from plugin_installer_test_support import (
    InstallError,
    OFFICIAL_RAW_BASE,
    Path,
    STAGING_DIR_NAME,
    _assert_no_staging_or_part_leftovers,
    compute_local_sha256,
    full_install_responses,
    install_plugin_from_registry,
    json,
    load_installed_plugins,
    make_fetcher,
    make_registry_entry,
    packages_dir,
    plugins_root,
    read_active_versions,
    read_installed_state,
    sha256_bytes,
)



@pytest.mark.integration
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


@pytest.mark.integration
def test_only_declared_files_are_downloaded(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()

    def counting_fetch(url: str, max_bytes: int) -> bytes:
        assert url in responses, f"unexpected download of {url}"
        return responses[url]

    entry = make_registry_entry(manifest, manifest_bytes)
    install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=counting_fetch
    )


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.contract
def test_incompatible_app_rejected_before_download(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses(requires_app=">=99.0.0")

    def refusing_fetch(url: str, max_bytes: int) -> bytes:
        raise AssertionError(f"must not download {url}")

    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.3.0", fetcher=refusing_fetch
        )


@pytest.mark.contract
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


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.integration
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
