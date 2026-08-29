from pathlib import Path

from scripts.sync_version import sync_version


def test_sync_version_updates_all_runtime_declarations(tmp_path: Path):
    files = {
        "pyproject.toml": 'version = "1.0.0"\n',
        "src/hpc_gui/__init__.py": "__version__ = '1.0.0'\n",
        "src/hpc_gui/cli/main.py": 'CLI_VERSION = "1.0.0"\n',
        "build/windows/version_info.txt": "filevers=(1, 0, 0, 0)\nprodvers=(1, 0, 0, 0)\nStringStruct('FileVersion', '1.0.0')\nStringStruct('ProductVersion', '1.0.0')\n",
        "build/macos/hpc-client-gui.spec": 'os.environ.get("APP_VERSION", "1.0.0")\n',
        "docs/wiki/Release-History.md": "current version is **1.0.0**\n",
        "docs/wiki/Release-History-TR.md": "Geçerli sürüm **1.0.0**\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    sync_version(tmp_path, "2.3.4")
    assert 'version = "2.3.4"' in (tmp_path / "pyproject.toml").read_text()
    assert "__version__ = '2.3.4'" in (tmp_path / "src/hpc_gui/__init__.py").read_text()
    assert "CLI_VERSION = \"2.3.4\"" in (tmp_path / "src/hpc_gui/cli/main.py").read_text()
    assert "filevers=(2, 3, 4, 0)" in (tmp_path / "build/windows/version_info.txt").read_text()
