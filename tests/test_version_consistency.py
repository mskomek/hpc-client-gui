from __future__ import annotations

import re
from pathlib import Path

from truba_gui import __version__
from truba_gui.cli.main import CLI_VERSION


ROOT = Path(__file__).parents[1]


def _project_version(path: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"$', path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, path
    return match.group(1)


def test_repository_version_views_match() -> None:
    assert _project_version(ROOT / "pyproject.toml") == __version__
    assert CLI_VERSION == __version__
    changelog = (ROOT / "src/truba_gui/docs/CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## v{__version__}" in changelog
