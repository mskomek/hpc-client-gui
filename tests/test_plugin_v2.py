"""Plugin API v2 (linter-tool) unit tests.

Covers the additive validator rules, the loader's static entrypoint
handling, and the lazy/defensive engine import. No network, no Qt needed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.linter_tools import ToolLoadError, _TOOL_CACHE, load_tool_for_plugin
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import InstalledPlugin
from hpc_gui.plugins.validator import validate_manifest_dict


@pytest.fixture(autouse=True)
def _clear_tool_cache():
    _TOOL_CACHE.clear()
    yield
    _TOOL_CACHE.clear()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _v2_manifest(engine_py: bytes, *, plugin_api: int = 2) -> dict:
    engine_rel = "engine/tiny_lint/__init__.py"
    data_json = json.dumps({"schema_version": 1}).encode()
    files = [
        {
            "path": "README.md",
            "sha256": _sha(b"readme"),
            "size": len(b"readme"),
            "role": "documentation",
        },
        {
            "path": engine_rel,
            "sha256": _sha(engine_py),
            "size": len(engine_py),
            "role": "linter-engine",
        },
        {
            "path": "data/catalog.json",
            "sha256": _sha(data_json),
            "size": len(data_json),
            "role": "linter-data",
        },
    ]
    return {
        "schema_version": 1,
        "plugin_api": plugin_api,
        "id": "org.hpcclient.tinylint",
        "name": "Tiny Linter",
        "version": "0.1.0",
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "Test fixture plugin.",
        "requires_app": ">=1.5.0",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": engine_rel},
        "files": files,
    }


GOOD_ENGINE = b'''
def create_plugin():
    return {"id": "x", "title": "Tiny", "description": "", "page_factory": lambda parent=None: None}
'''

BAD_ENGINE = b"raise RuntimeError('broken engine')\n"


def test_v2_manifest_validates():
    problems = validate_manifest_dict(_v2_manifest(GOOD_ENGINE))
    assert not problems


def test_v1_manifest_with_python_rejected():
    manifest = _v2_manifest(GOOD_ENGINE, plugin_api=1)
    problems = validate_manifest_dict(manifest)
    assert any("plugin_api 2" in problem for problem in problems)


def test_v1_manifest_with_linter_entrypoint_rejected():
    manifest = _v2_manifest(GOOD_ENGINE, plugin_api=1)
    problems = validate_manifest_dict(manifest)
    # The .py payload alone already fails under api 1.
    assert any(".py" in problem for problem in problems)


def test_v2_python_with_wrong_role_rejected():
    manifest = _v2_manifest(GOOD_ENGINE)
    manifest["files"][1]["role"] = "documentation"
    problems = validate_manifest_dict(manifest)
    assert any("linter-engine" in problem for problem in problems)


def test_v2_entrypoint_must_match_declared_file():
    manifest = _v2_manifest(GOOD_ENGINE)
    manifest["entrypoints"]["linter_engine"] = "engine/other.py"
    problems = validate_manifest_dict(manifest)
    assert any("does not match any declared manifest file" in p for p in problems)


def _build_installed(tmp_path: Path, engine_bytes: bytes) -> InstalledPlugin:
    package_dir = tmp_path / "packages" / "org.hpcclient.tinylint" / "0.1.0"
    engine_dir = package_dir / "engine" / "tiny_lint"
    engine_dir.mkdir(parents=True)
    (package_dir / "README.md").write_bytes(b"readme")
    (engine_dir / "__init__.py").write_bytes(engine_bytes)
    (package_dir / "data").mkdir(exist_ok=True)
    (package_dir / "data" / "catalog.json").write_text('{"schema_version": 1}', encoding="utf-8")

    raw = _v2_manifest(engine_bytes)
    from hpc_gui.plugins.loader import _build_manifest

    manifest, error = _build_manifest(raw)
    assert error is None
    return InstalledPlugin(
        manifest=manifest,
        directory=package_dir,
        linter_engine={"module": "engine/tiny_lint/__init__.py"},
    )


def test_load_tool_success_and_cache(tmp_path: Path):
    installed = _build_installed(tmp_path, GOOD_ENGINE)
    tool = load_tool_for_plugin(installed)
    assert tool.title == "Tiny"
    assert callable(tool.page_factory)
    again = load_tool_for_plugin(installed)
    assert again is tool  # cached per (plugin id, version)


def test_load_tool_broken_engine_contained(tmp_path: Path):
    installed = _build_installed(tmp_path, BAD_ENGINE)
    with pytest.raises(ToolLoadError):
        load_tool_for_plugin(installed)


def test_load_tool_missing_descriptor(tmp_path: Path):
    engine = b"def other(): pass\n"
    installed = _build_installed(tmp_path, engine)
    with pytest.raises(ToolLoadError):
        load_tool_for_plugin(installed)


# ---------------------------------------------------------------------------
# Installer + loader roundtrip through a synthetic registry checkout.
# ---------------------------------------------------------------------------


def _fetcher_for(root: Path):
    base = "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/"

    def fetch(url: str, max_bytes: int) -> bytes:
        assert url.startswith(base)
        payload = (root / url[len(base):]).read_bytes()
        assert len(payload) <= max_bytes
        return payload

    return fetch


def test_install_and_loader_roundtrip(tmp_path: Path):
    repo = tmp_path / "repo"
    pkg = repo / "plugins" / "tinylint" / "0.1.0"
    engine_dir = pkg / "engine" / "tiny_lint"
    engine_dir.mkdir(parents=True)
    (pkg / "README.md").write_bytes(b"readme")
    (engine_dir / "__init__.py").write_bytes(GOOD_ENGINE)
    data_dir = pkg / "data"
    data_dir.mkdir()
    (data_dir / "catalog.json").write_text('{"schema_version": 1}', encoding="utf-8")

    raw_manifest = _v2_manifest(GOOD_ENGINE)
    # Registry paths must mirror plugins/<dir>/<version>/manifest.json layout.
    raw_manifest["entrypoints"] = {"linter_engine": "engine/tiny_lint/__init__.py"}
    manifest_path = pkg / "manifest.json"
    manifest_path.write_text(json.dumps(raw_manifest), encoding="utf-8")

    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {
            "owner": "mskomek",
            "name": "hpc-client-gui-plugins",
            "raw_base": "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/",
        },
        "plugins": [
            {
                "id": "org.hpcclient.tinylint",
                "name": "Tiny Linter",
                "version": "0.1.0",
                "plugin_api": 2,
                "type": "linter-tool",
                "description": "Test fixture plugin.",
                "publisher": "HPC Client GUI",
                "requires_app": ">=0.1",
                "manifest_path": "plugins/tinylint/0.1.0/manifest.json",
                "manifest_sha256": _sha(manifest_path.read_bytes()),
                "official": True,
                "capabilities": ["linter-tool"],
            }
        ],
    }
    (repo / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

    result = install_plugin_from_registry(
        registry["plugins"][0],
        root=tmp_path / "appdata",
        app_version="1.5.0",
        fetcher=_fetcher_for(repo),
    )
    assert result.activated
    assert "linter-tool" in result.installed.manifest.capabilities
    assert result.installed.linter_engine == {"module": "engine/tiny_lint/__init__.py"}

    loaded = load_installed_plugins(root=tmp_path / "appdata", app_version="1.5.0")
    matches = [p for p in loaded.plugins if p.manifest.id == "org.hpcclient.tinylint"]
    assert len(matches) == 1
    assert matches[0].linter_engine is not None

    tool = load_tool_for_plugin(matches[0])
    assert tool.title == "Tiny"


def test_installer_still_rejects_api_99(tmp_path: Path):
    repo = tmp_path / "repo99"
    pkg = repo / "plugins" / "future" / "9.9.9"
    pkg.mkdir(parents=True)
    raw_manifest = _v2_manifest(GOOD_ENGINE)
    raw_manifest["plugin_api"] = 99
    raw_manifest["version"] = "9.9.9"
    manifest_path = pkg / "manifest.json"
    manifest_path.write_text(json.dumps(raw_manifest), encoding="utf-8")

    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {
            "owner": "o",
            "name": "n",
            "raw_base": "https://raw.githubusercontent.com/o/n/main/",
        },
        "plugins": [
            {
                "id": "org.hpcclient.tinylint",
                "name": "Tiny Linter",
                "version": "9.9.9",
                "plugin_api": 99,
                "type": "linter-tool",
                "description": "d",
                "publisher": "p",
                "requires_app": ">=0.1",
                "manifest_path": "plugins/future/9.9.9/manifest.json",
                "manifest_sha256": _sha(manifest_path.read_bytes()),
                "official": True,
            }
        ],
    }
    (repo / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(InstallError):
        install_plugin_from_registry(
            registry["plugins"][0],
            root=tmp_path / "appdata99",
            app_version="1.5.0",
            fetcher=_fetcher_for(repo),
        )
