"""Test-only local plugin catalog: refused locations, traversal, mixed catalogs, tampering."""

from __future__ import annotations

import hashlib
import json
import socket
import urllib.request

import pytest

from plugin_test_catalog_fixture import (
    PLUGIN_ID,
    SLUG,
    enable_test_catalog,
    make_dir_link,
    write_catalog,
)
from hpc_gui.plugins.downloader import DownloadError
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    RegistryError,
    default_fetcher,
    fetch_registry_with_cache,
)
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import packages_dir, read_active_versions
from hpc_gui.plugins.test_catalog import (
    TEST_CATALOG_ENV,
    TEST_MODE_ENV,
    CatalogRefusedError,
    read_catalog_url,
    resolve_catalog_root,
)

V1 = {"data/readme.json": b'{"revision": 1}\n'}
V2 = {"data/readme.json": b'{"revision": 2}\n'}
REGISTRY_URL = OFFICIAL_RAW_BASE + "registry.json"


@pytest.fixture
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network access attempted in test catalog mode")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


@pytest.fixture
def catalog(monkeypatch, tmp_path):
    monkeypatch.delenv(TEST_CATALOG_ENV, raising=False)
    root = tmp_path / "catalog"
    root.mkdir()
    return root


def _plugin_root(tmp_path):
    return tmp_path / "plugin-root"


@pytest.mark.parametrize(
    "setting",
    [
        "http://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/",
        "https://example.com/catalog",
        "file://server/share/catalog",
        "file://localhost/tmp/catalog",
        "file:////server/share/catalog",
        "file:relative/catalog",
        "file:///C:/x/../y",
        "file:///C:/x?query=1",
        "\\\\server\\share\\catalog",
        "//server/share/catalog",
        "\\\\?\\C:\\catalog",
        "relative/catalog",
        "C:relative-catalog",
        "..\\catalog",
        "missing-dir-that-does-not-exist-anywhere",
    ],
)
def test_refused_catalog_locations(setting, monkeypatch, no_network):
    with pytest.raises(CatalogRefusedError):
        resolve_catalog_root(setting)
    monkeypatch.setenv(TEST_MODE_ENV, "1")
    monkeypatch.setenv(TEST_CATALOG_ENV, setting)
    with pytest.raises(RegistryError, match="test catalog refused"):
        default_fetcher(REGISTRY_URL, 1024)


def test_absolute_directory_with_dotdot_segment_is_refused(tmp_path):
    with pytest.raises(CatalogRefusedError, match=r"\.\."):
        resolve_catalog_root(str(tmp_path / ".." / tmp_path.name))


@pytest.mark.parametrize(
    "relative",
    [
        "../registry.json",
        "plugins/../../registry.json",
        "/registry.json",
        "C:/Windows/win.ini",
        "plugins\\x.json",
        "https://evil.example/x.json",
        "%2e%2e/registry.json",
        "data//x.json",
    ],
)
def test_traversal_and_foreign_urls_are_refused(catalog, relative):
    write_catalog(catalog, {"0.1.0": V1})
    with pytest.raises(CatalogRefusedError):
        read_catalog_url(catalog.resolve(), OFFICIAL_RAW_BASE + relative, OFFICIAL_RAW_BASE, 1024)


def test_url_outside_official_base_is_refused(catalog):
    with pytest.raises(CatalogRefusedError, match="outside"):
        read_catalog_url(catalog.resolve(), "https://evil.example/registry.json", OFFICIAL_RAW_BASE, 1024)


def test_directory_link_escaping_catalog_root_is_refused(catalog, tmp_path, no_network):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.json").write_bytes(b"{}")
    make_dir_link(catalog / "escape", outside)
    with pytest.raises(CatalogRefusedError, match="escapes"):
        read_catalog_url(catalog.resolve(), OFFICIAL_RAW_BASE + "escape/secret.json", OFFICIAL_RAW_BASE, 1024)


def test_file_link_escaping_catalog_root_is_refused(catalog, tmp_path, no_network):
    outside = tmp_path / "outside-secret.json"
    outside.write_bytes(b"{}")
    try:
        (catalog / "leak.json").symlink_to(outside)
    except OSError:
        pytest.skip("file symlinks need developer mode or privilege on this host")
    with pytest.raises(CatalogRefusedError, match="escapes"):
        read_catalog_url(catalog.resolve(), OFFICIAL_RAW_BASE + "leak.json", OFFICIAL_RAW_BASE, 1024)


def test_registry_with_foreign_raw_base_is_refused(monkeypatch, catalog, tmp_path, no_network):
    write_catalog(catalog, {"0.1.0": V1}, raw_base="https://evil.example/mirror/")
    enable_test_catalog(monkeypatch, catalog)
    with pytest.raises(RegistryError):
        fetch_registry_with_cache(root=_plugin_root(tmp_path))


@pytest.mark.parametrize(
    "foreign",
    ["https://evil.example/manifest.json", "\\\\server\\share\\manifest.json", "file:///C:/Windows/x.json"],
)
def test_mixed_registry_entry_pointing_elsewhere_is_refused(monkeypatch, catalog, tmp_path, no_network, foreign):
    registry = write_catalog(catalog, {"0.1.0": V1})
    registry["plugins"][0]["manifest_path"] = foreign
    (catalog / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    enable_test_catalog(monkeypatch, catalog)
    with pytest.raises(RegistryError):
        fetch_registry_with_cache(root=_plugin_root(tmp_path))


def test_manifest_path_outside_catalog_root_fails_closed(monkeypatch, catalog, tmp_path, no_network):
    registry = write_catalog(catalog, {"0.1.0": V1})
    (tmp_path / "outside").mkdir()
    entry = dict(registry["plugins"][0], manifest_path="../../../outside/manifest.json")
    enable_test_catalog(monkeypatch, catalog)
    root = _plugin_root(tmp_path)
    with pytest.raises((InstallError, RegistryError)):
        install_plugin_from_registry(entry, root=root)
    assert read_active_versions(root) == {}


def test_tampered_payload_leaves_installed_state_untouched(monkeypatch, catalog, tmp_path, no_network):
    registry = write_catalog(catalog, {"0.1.0": V1, "0.1.1": V2})
    entries = {entry["version"]: entry for entry in registry["plugins"]}
    enable_test_catalog(monkeypatch, catalog)
    root = _plugin_root(tmp_path)
    install_plugin_from_registry(entries["0.1.0"], root=root)
    before_state = read_installed_state(root)

    payload = catalog / "plugins" / SLUG / "0.1.1" / "data" / "readme.json"
    payload.write_bytes(b'{"revision": 9}\n')  # same size, different bytes
    with pytest.raises(InstallError, match="SHA-256 mismatch"):
        install_plugin_from_registry(entries["0.1.1"], root=root)

    assert read_active_versions(root)[PLUGIN_ID] == "0.1.0"
    assert read_installed_state(root) == before_state
    assert not (packages_dir(root) / PLUGIN_ID / "0.1.1").exists()
    staging = root / ".staging"
    assert not staging.exists() or not any(staging.iterdir())


def test_truncated_payload_is_refused_before_activation(monkeypatch, catalog, tmp_path, no_network):
    registry = write_catalog(catalog, {"0.1.0": V1, "0.1.1": V2})
    entries = {entry["version"]: entry for entry in registry["plugins"]}
    (catalog / "plugins" / SLUG / "0.1.1" / "data" / "readme.json").write_bytes(b"{}")
    enable_test_catalog(monkeypatch, catalog)
    root = _plugin_root(tmp_path)
    with pytest.raises((InstallError, DownloadError)):
        install_plugin_from_registry(entries["0.1.1"], root=root)
    assert read_active_versions(root) == {}


def test_tampered_manifest_is_refused(monkeypatch, catalog, tmp_path, no_network):
    registry = write_catalog(catalog, {"0.1.0": V1})
    manifest_path = catalog / "plugins" / SLUG / "0.1.0" / "manifest.json"
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    enable_test_catalog(monkeypatch, catalog)
    with pytest.raises(InstallError, match="Manifest SHA-256 mismatch"):
        install_plugin_from_registry(registry["plugins"][0], root=_plugin_root(tmp_path))


def test_zip_slip_style_payload_path_is_refused(monkeypatch, catalog, tmp_path, no_network):
    # The installer has no archive format; the equivalent is a manifest path that climbs out.
    registry = write_catalog(catalog, {"0.1.0": V1})
    manifest_path = catalog / "plugins" / SLUG / "0.1.0" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../../escape.json"
    body = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(body)
    registry["plugins"][0]["manifest_sha256"] = hashlib.sha256(body).hexdigest()
    enable_test_catalog(monkeypatch, catalog)
    root = _plugin_root(tmp_path)
    with pytest.raises((InstallError, DownloadError)):
        install_plugin_from_registry(registry["plugins"][0], root=root)
    assert not (root / "escape.json").exists()
    assert not (root.parent / "escape.json").exists()
    assert read_active_versions(root) == {}
