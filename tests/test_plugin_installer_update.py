"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
)
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import packages_dir, read_active_versions
from support.plugin_installer_fixtures import (_assert_no_staging_or_part_leftovers, full_install_responses, make_fetcher, make_registry_entry)


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
