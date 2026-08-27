"""Optional cross-repo integration test for Plugin API v2 linter tools.

Runs only when ``HPC_GUI_CONTRACT_REPO`` points at a checkout of
hpc-client-gui-plugins containing the bundled ANSYS linter engine.
Copies nothing into the source tree: a temporary installed-plugin layout
is built under pytest's tmp_path.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from hpc_gui.plugins.linter_tools import load_tool_for_plugin
from hpc_gui.plugins.loader import _build_manifest
from hpc_gui.plugins.models import InstalledPlugin

REPO = os.environ.get("HPC_GUI_CONTRACT_REPO", "")
pytestmark = pytest.mark.skipif(
    not REPO or not Path(REPO).is_dir(),
    reason="HPC_GUI_CONTRACT_REPO does not point to an official plugins checkout",
)


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def installed(tmp_path: Path) -> InstalledPlugin:
    engines = sorted(Path(REPO).glob("plugins/ansys-lint/*/engine"))
    if not engines:
        raise AssertionError(
            "HPC_GUI_CONTRACT_REPO is configured, but it carries no ansys-lint engine"
        )
    engine_src = engines[-1]
    manifest_path = engine_src.parent / "manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))

    package_dir = tmp_path / "packages" / raw["id"] / raw["version"]
    package_dir.mkdir(parents=True)
    shutil.copytree(engine_src, package_dir / "engine")
    manifest, error = _build_manifest(raw)
    assert error is None, error
    return InstalledPlugin(
        manifest=manifest,
        directory=package_dir,
        linter_engine={"module": raw["entrypoints"]["linter_engine"]},
    )


def test_real_ansys_lint_tool_loads_and_builds_page(installed, qapp):
    from PySide6.QtWidgets import QWidget

    tool = load_tool_for_plugin(installed)
    assert tool.title == "ANSYS Script & Journal Linter"
    assert tool.plugin_id == "org.hpcclient.ansyslint"
    page = tool.page_factory(parent=None)
    assert isinstance(page, QWidget)


def test_real_ansys_lint_engine_lints_offline(installed, qapp, tmp_path: Path):
    """The imported engine lints a journal through the host's module name."""
    journal = tmp_path / "job.jou"
    journal.write_text("/file/set-tui-version 25.2\n/display/set/picture\n", encoding="utf-8")
    tool = load_tool_for_plugin(installed)

    import importlib

    engine_module = importlib.import_module(tool.module_name)
    result = engine_module.lint_paths([journal])
    codes = {
        diag.code
        for file_result in result.files
        for diag in file_result.diagnostics
    }
    assert "FLUENT_GUI_IN_HEADLESS" in codes
