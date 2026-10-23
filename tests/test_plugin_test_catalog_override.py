"""Test-only local plugin catalog: activation switches and offline install/update."""

from __future__ import annotations

import logging
import socket
import urllib.request

import pytest

from plugin_test_catalog_fixture import (
    DEFAULT_FILES,
    PLUGIN_ID,
    enable_test_catalog,
    write_catalog,
)
from hpc_gui.plugins import test_catalog
from hpc_gui.plugins.installer import install_plugin_from_registry
from hpc_gui.plugins.registry_client import (
    OFFICIAL_REGISTRY_URL,
    default_fetcher,
    fetch_registry_with_cache,
)
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import packages_dir, read_active_versions
from hpc_gui.plugins.test_catalog import (
    TEST_CATALOG_ENV,
    TEST_MODE_ENV,
    active_catalog_root,
    configured_catalog_setting,
    mark_test_catalog_title,
)

V1 = {"data/readme.json": b'{"revision": 1}\n'}
V2 = {"data/readme.json": b'{"revision": 2}\n'}


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test if any socket, DNS lookup or urllib request is attempted."""

    def forbidden(*args, **kwargs):
        raise AssertionError("network access attempted in test catalog mode")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


def _clear(monkeypatch) -> None:
    monkeypatch.delenv(TEST_MODE_ENV, raising=False)
    monkeypatch.delenv(TEST_CATALOG_ENV, raising=False)


def test_disabled_by_default_and_network_path_untouched(monkeypatch, tmp_path):
    _clear(monkeypatch)
    write_catalog(tmp_path, {"0.1.0": V1})
    attempted: list[str] = []

    def fake_urlopen(request, timeout=None):
        attempted.append(request.full_url)
        raise OSError("offline sentinel")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert configured_catalog_setting() is None
    assert active_catalog_root() is None
    with pytest.raises(OSError, match="offline sentinel"):
        default_fetcher(OFFICIAL_REGISTRY_URL, 1024)
    assert attempted == [OFFICIAL_REGISTRY_URL]


@pytest.mark.parametrize(
    ("mode", "catalog", "expected_active"),
    [
        (None, "set", False),
        ("0", "set", False),
        ("1", None, False),
        ("1", "blank", False),
        ("1", "set", True),
    ],
)
def test_both_switches_are_required(monkeypatch, tmp_path, mode, catalog, expected_active):
    _clear(monkeypatch)
    if mode is not None:
        monkeypatch.setenv(TEST_MODE_ENV, mode)
    if catalog == "set":
        monkeypatch.setenv(TEST_CATALOG_ENV, tmp_path.as_uri())
    elif catalog == "blank":
        monkeypatch.setenv(TEST_CATALOG_ENV, "   ")
    assert (configured_catalog_setting() is not None) is expected_active
    assert (active_catalog_root() is not None) is expected_active


def test_title_badge_only_while_configured(monkeypatch, tmp_path):
    _clear(monkeypatch)
    assert mark_test_catalog_title("Plugin Manager", "TEST CATALOG") == "Plugin Manager"
    enable_test_catalog(monkeypatch, tmp_path)
    assert mark_test_catalog_title("Plugin Manager", "TEST CATALOG") == "Plugin Manager \u2014 TEST CATALOG"


def test_active_override_logs_warning(monkeypatch, tmp_path, caplog):
    _clear(monkeypatch)
    enable_test_catalog(monkeypatch, tmp_path)
    with caplog.at_level(logging.WARNING, logger=test_catalog.__name__):
        root = active_catalog_root()
    assert root == tmp_path.resolve()
    assert any("PLUGIN TEST CATALOG ACTIVE" in record.getMessage() for record in caplog.records)


def test_install_then_update_through_real_installer_offline(monkeypatch, tmp_path, no_network, caplog):
    _clear(monkeypatch)
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    registry = write_catalog(catalog, {"0.1.0": V1, "0.1.1": V2})
    enable_test_catalog(monkeypatch, catalog)
    plugin_root = tmp_path / "plugin-root"

    with caplog.at_level(logging.WARNING):
        fetched = fetch_registry_with_cache(root=plugin_root)
    assert {entry["version"] for entry in fetched.registry["plugins"]} == {"0.1.0", "0.1.1"}
    assert any("PLUGIN TEST CATALOG ACTIVE" in record.getMessage() for record in caplog.records)

    entries = {entry["version"]: entry for entry in registry["plugins"]}
    first = install_plugin_from_registry(entries["0.1.0"], root=plugin_root)
    assert first.activated
    assert read_active_versions(plugin_root)[PLUGIN_ID] == "0.1.0"

    update = install_plugin_from_registry(entries["0.1.1"], root=plugin_root)
    assert update.activated
    assert read_active_versions(plugin_root)[PLUGIN_ID] == "0.1.1"
    installed_dir = packages_dir(plugin_root) / PLUGIN_ID / "0.1.1" / "data" / "readme.json"
    assert installed_dir.read_bytes() == V2["data/readme.json"]
    assert set(read_installed_state(plugin_root)[PLUGIN_ID]["versions"]) == {"0.1.0", "0.1.1"}


def test_default_payload_fixture_installs(monkeypatch, tmp_path, no_network):
    _clear(monkeypatch)
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    registry = write_catalog(catalog, {"0.1.0": DEFAULT_FILES})
    enable_test_catalog(monkeypatch, catalog)
    result = install_plugin_from_registry(registry["plugins"][0], root=tmp_path / "root")
    assert result.installed.manifest.version == "0.1.0"
