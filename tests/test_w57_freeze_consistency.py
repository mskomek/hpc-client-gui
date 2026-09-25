"""W57 freeze-consistency regression tests.

Purpose IDs: REQ-FREEZE-035 (support matrix and release-facing docs match the
candidate), REQ-FREEZE-042 (final support matrix evidence), REQ-FREEZE-011
(documentation consistency).

Taxonomy: contract + regression (source/static; hermetic, no network, no GUI).

Real code exercised: the release-facing wiki docs, ``pyproject.toml``,
``src/hpc_gui/runtime.py`` (import only, no GUI launch).

Mocked boundary: none.

Why no mocking is legitimate: assertions read committed source text directly.

What this test does NOT prove: packaged artifact bytes (exe SHA-256, bundle
content), the freeze declaration artifact, and real-cluster behavior. Those
are proven by the W57 wave report packaged-regression, freeze declaration,
and LOCAL_REAL replay evidence against the frozen candidate, not by this
file.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.regression]

ROOT = Path(__file__).resolve().parents[1]

MATRIX_EN = ROOT / "docs/wiki/Compatibility-and-Support-Matrix.md"
MATRIX_TR = ROOT / "docs/wiki/Compatibility-and-Support-Matrix-TR.md"
INSTALL_LINUX_EN = ROOT / "docs/wiki/Installation-Linux.md"
INSTALL_LINUX_TR = ROOT / "docs/wiki/Installation-Linux-TR.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _pyproject_version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def test_matrix_versions_match_pyproject_version() -> None:
    """Matrix-declared release version equals the packaged project version."""
    version = _pyproject_version()
    assert f"Current version: **{version}**" in _read(MATRIX_EN)
    assert f"Ge\xe7erli s\xfcr\xfcm: **{version}**" in _read(MATRIX_TR)


def test_install_docs_reference_current_version_only() -> None:
    """Install docs name the current release artifacts, not older ones."""
    version = _pyproject_version()
    for path in (INSTALL_LINUX_EN, INSTALL_LINUX_TR):
        text = _read(path)
        assert version in text
        assert "1.2.6" not in text


def test_matrix_does_not_advertise_qt_runtime() -> None:
    """Support matrix must not present Qt as the shipped production runtime."""
    text_en = _read(MATRIX_EN)
    assert "| Qt runtime |" not in text_en
    assert "Provided by PySide6" not in text_en
    assert "wxPython" in text_en
    text_tr = _read(MATRIX_TR)
    assert "| Qt \xe7al\u0131\u015fma zaman\u0131 |" not in text_tr
    assert "PySide6 sa\u011flar" not in text_tr
    assert "wxPython" in text_tr


def test_install_linux_does_not_require_qt_platform_libs() -> None:
    """Linux install docs must not prescribe Qt platform libraries."""
    text_en = _read(INSTALL_LINUX_EN)
    assert "is a Qt (PySide6) desktop program" not in text_en
    assert "sudo apt install libegl1" not in text_en
    assert "wxPython (wxWidgets)" in text_en
    text_tr = _read(INSTALL_LINUX_TR)
    assert "bir Qt (PySide6) masa\xfcst\xfc program\u0131d\u0131r" not in text_tr
    assert "sudo apt install libegl1" not in text_tr
    assert "wxPython (wxWidgets)" in text_tr


def test_production_runtime_default_is_wx() -> None:
    """Frozen-candidate invariant: the shipped default runtime stays wx."""
    runtime_source = _read(ROOT / "src/hpc_gui/runtime.py")
    assert 'DEFAULT_GUI_RUNTIME = "wx"' in runtime_source
