from __future__ import annotations

import re
from pathlib import Path

from hpc_gui import __version__
from hpc_gui.cli.main import CLI_VERSION


ROOT = Path(__file__).parents[1]


def _project_version(path: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"$', path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, path
    return match.group(1)


def test_repository_version_views_match() -> None:
    assert _project_version(ROOT / "pyproject.toml") == __version__
    assert CLI_VERSION == __version__
    changelog = (ROOT / "src/hpc_gui/docs/CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## v{__version__}" in changelog
    version_info = (ROOT / "build/windows/version_info.txt").read_text(encoding="utf-8")
    assert f"'{__version__}'" in version_info
    tuple_version = ", ".join([*__version__.split("."), "0"])
    assert f"({tuple_version})" in version_info
