"""Packaging regression checks: wheel assets and runtime dependency metadata.

The full wheel build is marked ``packaging`` so ordinary test runs stay fast;
CI runs it explicitly via ``pytest -m packaging``.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WHEEL_PATTERNS = (
    "hpc_gui/assets/flags/gb.svg",
    "hpc_gui/assets/flags/tr.svg",
    "hpc_gui/assets/icons/help.svg",
    "hpc_gui/assets/terminal/index.html",
    "hpc_gui/assets/terminal/xterm.js",
    "hpc_gui/assets/terminal/addon-fit.js",
    "hpc_gui/assets/terminal/bridge.js",
    "hpc_gui/assets/terminal/xterm.css",
    "hpc_gui/i18n/en.json",
    "hpc_gui/i18n/tr.json",
)


def _pyproject_text() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_pyproject_declares_packaging_runtime_dependency() -> None:
    text = _pyproject_text()
    match = re.search(r"^dependencies = \[(.*?)^\]", text, re.S | re.M)
    assert match, "runtime dependency list not found"
    assert any(
        dep.strip().startswith('"packaging>=')
        for dep in match.group(1).split("\n")
    ), "packaging must be declared as a runtime dependency"
    # The typo'd asset glob must be gone.
    assert "**/*.seg" not in text


def test_requirements_txt_declares_packaging() -> None:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert any(line.strip() == "packaging>=23" for line in lines)


def test_registry_client_uses_pep440_version_support() -> None:
    # Import in a fresh interpreter without pytest-provided sys.path help to
    # approximate production import behaviour.
    import subprocess

    code = (
        "import sys; sys.path.insert(0, 'src');"
        "from hpc_gui.plugins.registry_client import find_registry_entry;"
        "from hpc_gui.ui.dialogs import plugin_manager_dialog;"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


@pytest.mark.packaging
def test_built_wheel_contains_required_assets(tmp_path: Path) -> None:
    import subprocess

    dist_dir = tmp_path / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    wheels = list(dist_dir.glob("*.whl"))
    assert wheels, "no wheel produced"
    names = zipfile.ZipFile(wheels[0]).namelist()

    for required in REQUIRED_WHEEL_PATTERNS:
        assert required in names, f"missing from wheel: {required}"

    # Documentation embedded in the application ships in the wheel.
    assert any(name.startswith("hpc_gui/docs/HELP_en.md") for name in names)
    assert any(name.startswith("hpc_gui/docs/PLUGINS_en.md") for name in names)

    # No stray typo'd extensions.
    assert not any(name.endswith(".seg") for name in names)

    # Runtime dependency metadata is present in the built distribution.
    metadata_name = next(
        name for name in names if name.endswith("METADATA")
    )
    metadata = zipfile.ZipFile(wheels[0]).read(metadata_name).decode("utf-8")
    assert re.search(
        r"^Requires-Dist: packaging\s*(\(>=23\)|>=23)\s*$", metadata, re.M
    ), [line for line in metadata.splitlines() if line.startswith("Requires-Dist")]
