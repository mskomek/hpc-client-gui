"""W44 — ARCH-QT-WX / ARCH-PACKAGE pins (evidence reconciliation wave).

Owned requirements:
- HPC-W10-TODO-ARCH-QT-WX-001: no new Qt-only service logic while wx is target.
- HPC-W10-TODO-ARCH-QT-WX-002: wx runtime must not import Qt UI modules
  (``hpc_gui.ui.*``); shared values live in framework-neutral modules.
- HPC-W10-TODO-ARCH-PACKAGE-001: PyInstaller hidden imports re-audited;
  Qt/WebEngine stack ships intentionally (dual-runtime until the W56
  runtime-cutover decision), not from stale imports.

These tests pin the W44 correction; they do not weaken any other suite.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.regression]

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SERVICES = SRC / "hpc_gui" / "services"

EXPECTED_PLUGIN_REQUEST_URL = (
    "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
    "?template=plugin-request.yml"
)

_UI_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+hpc_gui\.ui\b", re.MULTILINE)
_QT_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(?:PySide6|PyQt[56])\b", re.MULTILINE)

NEUTRAL_MODULES = [
    SERVICES / "remote_entry_format.py",
    SERVICES / "plugin_request.py",
]

WX_CONSUMERS = [
    SRC / "hpc_gui" / "wx_local_files.py",
    SRC / "hpc_gui" / "wx_remote_files_view.py",
    SRC / "hpc_gui" / "wx_shell.py",
]


def test_w44_neutral_modules_are_qt_free_and_ui_free():
    """ARCH-QT-WX-001/002: new shared modules import neither Qt nor hpc_gui.ui."""
    for path in NEUTRAL_MODULES:
        assert path.is_file(), f"missing neutral module {path}"
        src = path.read_text(encoding="utf-8")
        assert _QT_IMPORT_RE.search(src) is None, f"{path.name} imports Qt"
        assert _UI_IMPORT_RE.search(src) is None, f"{path.name} imports hpc_gui.ui"


def test_w44_wx_runtime_has_no_hpc_gui_ui_imports():
    """ARCH-QT-WX-002: wx consumers must not import hpc_gui.ui.* for shared behavior."""
    offenders = []
    for path in WX_CONSUMERS:
        src = path.read_text(encoding="utf-8")
        if _UI_IMPORT_RE.search(src):
            offenders.append(path.name)
    assert not offenders, f"wx modules still import hpc_gui.ui.*: {offenders}"


def test_w44_plugin_request_url_single_sourced():
    """ARCH-QT-WX-002: plugin-request URL lives in the neutral module."""
    from hpc_gui.services.plugin_request import (
        PLUGIN_REQUEST_URL,
        is_allowed_plugin_request_url,
    )

    assert PLUGIN_REQUEST_URL == EXPECTED_PLUGIN_REQUEST_URL
    assert is_allowed_plugin_request_url(EXPECTED_PLUGIN_REQUEST_URL) is True
    assert is_allowed_plugin_request_url("https://evil.example.com/x") is False
    # The Qt dialog must re-export the neutral constant, not define its own copy.
    dialog_src = (
        SRC / "hpc_gui" / "ui" / "dialogs" / "plugin_manager_dialog.py"
    ).read_text(encoding="utf-8")
    assert "from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL" in dialog_src
    assert "PLUGIN_REQUEST_URL = (" not in dialog_src


def test_w44_entry_format_parity_with_qt_surface():
    """ARCH-QT-WX-002: Qt-surface shim re-exports the neutral implementation."""
    from hpc_gui.services import remote_entry_format as neutral
    from hpc_gui.ui.models import remote_entry_helpers as shim

    for name in ("fmt_size", "fmt_mtime", "file_type", "category", "natural_sort_key"):
        assert getattr(shim, name) is getattr(neutral, name), f"{name} diverged"
    assert neutral.fmt_size(1536) == "1.5 KB"
    assert neutral.natural_sort_key("file10") > neutral.natural_sort_key("file2")


def test_w44_wx_imports_without_qt_ui_or_pyside():
    """ARCH-QT-WX-002 runtime proof: wx consumers load with no hpc_gui.ui/PySide6."""
    code = (
        "import sys; "
        "sys.path.insert(0, 'src'); "
        "import hpc_gui.wx_local_files as w1, hpc_gui.wx_remote_files_view as w2; "
        "from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL as u; "
        "ui = sorted(m for m in sys.modules if m == 'hpc_gui.ui' or m.startswith('hpc_gui.ui.')); "
        "qt = sorted(m for m in sys.modules if m == 'PySide6' or m.startswith('PySide6.')); "
        "print('UI_MODULES:', ui); print('QT_MODULES:', qt); print('URL:', u); "
        "assert not ui, ui; assert not qt, qt"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, f"wx ui-free import failed:\n{proc.stdout}\n{proc.stderr}"
    assert f"URL: {EXPECTED_PLUGIN_REQUEST_URL}" in proc.stdout


def test_w44_package_hidden_imports_are_intentional():
    """ARCH-PACKAGE-001: Qt/WebEngine hidden imports ship by dual-runtime decision."""
    spec = ROOT / "build" / "windows" / "hpc-client-gui.spec"
    assert spec.is_file(), "windows PyInstaller spec missing"
    text = spec.read_text(encoding="utf-8")
    for mod in (
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ):
        assert mod in text, f"spec lost required dual-runtime import {mod}"
    # The spec must carry the W44 audit marker documenting intentional
    # dual-runtime packaging until the W56 runtime-cutover decision.
    assert "ARCH-PACKAGE-001" in text, "spec lacks W44 hidden-import audit marker"
