"""Optional cross-repo integration test for Plugin API v2 linter tools.

Runs only when ``HPC_GUI_CONTRACT_REPO`` points at a checkout of
hpc-client-gui-plugins containing the bundled ANSYS linter engine.
Copies nothing into the source tree: a temporary installed-plugin layout
is built under pytest's tmp_path.
"""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import sys
from pathlib import Path

import pytest

from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
from hpc_gui.plugins.loader import _build_manifest, load_installed_plugins
from hpc_gui.plugins.models import InstalledPlugin
from hpc_gui.plugins.models import PluginFile, PluginManifest
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE, OFFICIAL_REGISTRY_URL

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


@pytest.fixture
def local_fetcher():
    repo = Path(REPO)

    def fetch(url: str, max_bytes: int) -> bytes:
        if url == OFFICIAL_REGISTRY_URL:
            payload = (repo / "registry.json").read_bytes()
        else:
            assert url.startswith(OFFICIAL_RAW_BASE)
            payload = (repo / url[len(OFFICIAL_RAW_BASE):]).read_bytes()
        assert len(payload) <= max_bytes
        return payload

    return fetch


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


def test_real_ansys_installer_round_trip(local_fetcher, qapp, tmp_path: Path):
    """Install the real registry package, then exercise its real engine."""
    from hpc_gui.plugins.installer import install_plugin_from_registry
    from hpc_gui.plugins.registry_client import parse_registry

    repo = Path(REPO)
    registry = parse_registry((repo / "registry.json").read_bytes())
    entry = next(item for item in registry["plugins"] if item["id"] == "org.hpcclient.ansyslint")
    result = install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.5.8", fetcher=local_fetcher
    )
    assert result.activated
    loaded = load_installed_plugins(root=tmp_path, app_version="1.5.8")
    assert not loaded.problems
    installed_tool = next(item for item in loaded.plugins if item.manifest.id == entry["id"])
    tool = load_tool_for_plugin(installed_tool)
    assert tool.version == entry["version"] == "0.1.0"
    from PySide6.QtWidgets import QWidget

    assert isinstance(tool.page_factory(parent=None), QWidget)
    journal = tmp_path / "headless.jou"
    journal.write_text("/file/set-tui-version 25.2\n/display/set/picture\n", encoding="utf-8")
    result = __import__("importlib").import_module(tool.module_name).lint_paths([journal])
    codes = {diagnostic.code for file_result in result.files for diagnostic in file_result.diagnostics}
    assert "FLUENT_GUI_IN_HEADLESS" in codes


def _fake_ansys_tool(tmp_path: Path, version: str, marker: str, *, broken=False):
    package = tmp_path / version / "engine" / "ansys_lint"
    package.mkdir(parents=True)
    init = "raise RuntimeError('broken')\n" if broken else (
        "from .api import MARKER\n"
        "def create_plugin():\n"
        "    return {'title': MARKER, 'page_factory': lambda parent=None: None}\n"
    )
    api = f"MARKER = {marker!r}\n"
    (package / "__init__.py").write_text(init, encoding="utf-8")
    (package / "api.py").write_text(api, encoding="utf-8")
    files = tuple(
        PluginFile(path=path, sha256=hashlib.sha256(data.encode()).hexdigest(), size=len(data), role="linter-engine")
        for path, data in (("engine/ansys_lint/__init__.py", init), ("engine/ansys_lint/api.py", api))
    )
    manifest = PluginManifest(
        schema_version=1, plugin_api=2, id="org.hpcclient.ansyslint",
        name="ANSYS", version=version, publisher="HPC Client GUI", license="MIT",
        description="test", requires_app=">=1.5.0", capabilities=("linter-tool",),
        entrypoints={"linter_engine": "engine/ansys_lint/__init__.py"}, files=files,
    )
    return InstalledPlugin(manifest=manifest, directory=tmp_path / version, linter_engine={"module": "engine/ansys_lint/__init__.py"})


def test_trusted_tool_versions_isolate_submodules_and_restore_bytecode_flag(tmp_path: Path):
    first = _fake_ansys_tool(tmp_path, "0.1.0", "VERSION_A")
    second = _fake_ansys_tool(tmp_path, "0.2.0", "VERSION_B")
    before = sys.dont_write_bytecode
    tool_a = load_tool_for_plugin(first)
    tool_b = load_tool_for_plugin(second)
    assert tool_a.module_name != tool_b.module_name
    assert __import__(f"{tool_a.module_name}.api", fromlist=["MARKER"]).MARKER == "VERSION_A"
    assert __import__(f"{tool_b.module_name}.api", fromlist=["MARKER"]).MARKER == "VERSION_B"
    assert sys.dont_write_bytecode is before

    broken = _fake_ansys_tool(tmp_path, "0.3.0", "VERSION_C", broken=True)
    with pytest.raises(ToolLoadError):
        load_tool_for_plugin(broken)
    assert sys.dont_write_bytecode is before
