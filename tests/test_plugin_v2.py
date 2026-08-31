"""Legacy executable-plugin security boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
from hpc_gui.plugins.validator import validate_manifest_dict


def _manifest(code: bytes) -> dict:
    return {
        "schema_version": 1, "plugin_api": 2, "id": "org.hpcclient.legacy",
        "name": "Legacy", "version": "1.0.0", "publisher": "test", "license": "MIT",
        "description": "legacy executable plugin", "requires_app": ">=1.0.0",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/__init__.py"},
        "files": [{
            "path": "engine/__init__.py", "sha256": hashlib.sha256(code).hexdigest(),
            "size": len(code), "role": "linter-engine",
        }],
    }


def test_unapproved_python_tool_is_rejected_by_trusted_policy():
    problems = validate_manifest_dict(_manifest(b"raise RuntimeError('must not run')"))
    assert any("unapproved trusted tool" in problem for problem in problems)


def test_legacy_plugin_cannot_execute_marker_payload(tmp_path: Path):
    marker = tmp_path / "marker"
    installed = type("Installed", (), {
        "manifest": type("Manifest", (), {"id": "org.hpcclient.legacy", "version": "1.0.0"})(),
        "directory": tmp_path,
        "linter_engine": {"module": "engine/__init__.py"},
    })()
    with pytest.raises(ToolLoadError, match="disabled|declarative"):
        load_tool_for_plugin(installed)
    assert not marker.exists()


def test_installer_rejects_legacy_executable_package(tmp_path: Path):
    manifest = _manifest(b"pass\n")
    payload = json.dumps(manifest).encode()
    entry = {
        "id": manifest["id"], "version": manifest["version"],
        "manifest_path": "plugins/legacy/1.0.0/manifest.json",
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
    }

    with pytest.raises(InstallError, match="Invalid manifest"):
        install_plugin_from_registry(
            entry, root=tmp_path / "plugins", app_version="1.5.7",
            fetcher=lambda _url, _max_bytes: payload,
        )
