"""Installed API 3 Case Studio records load only their pinned byte closure."""
from __future__ import annotations

import json
from pathlib import Path

from hpc_gui import __version__ as APP_VERSION
from hpc_gui.plugins.application_tools import load_application_tool_for_plugin
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.storage import write_active_versions, write_disabled_ids

from tests.test_w65_r14_openfoam_dispatch import (
    API3_STUDIO_ID,
    API3_STUDIO_VERSION,
    STUDIO_ENGINE_REL,
    _pins_for,
    _studio_manifest,
    _write_package,
)


def test_loader_returns_usable_pinned_studio_record(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as trusted_api3

    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(
        trusted_api3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes)
    )
    package = _write_package(tmp_path, manifest, {})
    plugin_root = package.parents[2]
    write_active_versions({API3_STUDIO_ID: API3_STUDIO_VERSION}, root=plugin_root)
    write_disabled_ids(set(), root=plugin_root)

    loaded = load_installed_plugins(root=plugin_root, app_version=APP_VERSION)

    assert loaded.problems == []
    assert len(loaded.plugins) == 1
    installed = loaded.plugins[0]
    assert installed.application_tool == {"module": STUDIO_ENGINE_REL}
    tool = load_application_tool_for_plugin(installed)
    assert tool.plugin_id == API3_STUDIO_ID
    assert callable(tool.qt_page_factory) and callable(tool.wx_page_factory)
