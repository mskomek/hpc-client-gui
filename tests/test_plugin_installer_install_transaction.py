"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations
from support.test_plugin_installer_shared import (
    InstallError,
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    Path,
    RegistryError,
    STAGING_DIR_NAME,
    VALID_REGISTRY,
    _assert_no_staging_or_part_leftovers,
    compute_local_sha256,
    fetch_registry_with_cache,
    find_registry_entry,
    fluent_registry,
    full_install_responses,
    install_plugin_from_registry,
    json,
    load_installed_plugins,
    make_fetcher,
    make_fluent_entry,
    make_registry_entry,
    packages_dir,
    plugins_root,
    pytest,
    read_active_versions,
    read_installed_state,
    sha256_bytes,
)

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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
def test_unsupported_future_schema_error_names_supported_schemas(tmp_path: Path):
    """Unknown future schemas stay rejected with an actionable message and the
    strict validation detail is preserved."""
    responses, manifest, manifest_bytes = full_install_responses(
        schema_version=999, requires_app=">=1.5.9"
    )
    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError) as excinfo:
        install_plugin_from_registry(
            entry,
            root=tmp_path,
            app_version="1.5.9",
            fetcher=make_fetcher(responses),
        )
    text = str(excinfo.value)
    assert "cluster-profile schema 999" in text
    assert "supports schemas 1, 2, 3, 4" in text
    assert "Install a newer application release" in text
    assert "must be one of" in text  # strict validation detail retained
