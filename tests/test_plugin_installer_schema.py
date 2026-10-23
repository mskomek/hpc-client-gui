"""Plugin installer tests: Cluster-profile schema compatibility behavior."""

from __future__ import annotations

import pytest

from plugin_installer_test_support import (
    InstallError,
    Path,
    _assert_no_staging_or_part_leftovers,
    full_install_responses,
    install_plugin_from_registry,
    load_installed_plugins,
    make_fetcher,
    make_registry_entry,
    packages_dir,
)



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
