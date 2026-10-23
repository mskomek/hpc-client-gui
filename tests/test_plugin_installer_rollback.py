"""Plugin installer tests: Plugin update activation and rollback behavior."""

from __future__ import annotations

import pytest

from plugin_installer_test_support import (
    InstallError,
    OFFICIAL_RAW_BASE,
    Path,
    _assert_no_staging_or_part_leftovers,
    full_install_responses,
    install_plugin_from_registry,
    make_fetcher,
    make_registry_entry,
    packages_dir,
    read_active_versions,
    read_installed_state,
)



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
