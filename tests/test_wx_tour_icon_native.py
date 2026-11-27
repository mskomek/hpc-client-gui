"""Verify the native tour, navigation, and bundled product bitmap."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_tour_and_product_icon(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import wx
from hpc_gui.config.storage import get_ui_pref_bool
from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_product_icon import apply_product_icon, product_icon_path
from hpc_gui.wx_quick_tour import show_quick_tour
from hpc_gui.wx_shell_dispatch import _dispatch

load_language('en')
app = wx.App(False)
frame = wx.Frame(None)
book = wx.Notebook(frame)
pages = {}
for key in ('APP-CONNECT','NAV-DIRECTORIES','NAV-EDITOR','NAV-LOGS'):
    page = wx.Panel(book)
    book.AddPage(page, key)
    pages[key] = {'page': page}
frame._wx_shell_controls = {'notebook': book, 'pages': pages}
frame.Show()
assert product_icon_path().is_file()
assert apply_product_icon(frame)
assert frame.GetIcon().IsOk()
_dispatch('APP-QUICK-TOUR', frame)
dialog = frame._wx_quick_tour
assert dialog and dialog.IsShown()
assert show_quick_tour(frame) is dialog
controls = dialog._wx_tour_controls

def click(key):
    btn = controls[key]
    assert btn.IsEnabled()
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
    event.SetEventObject(btn)
    btn.GetEventHandler().ProcessEvent(event)
    app.ProcessPendingEvents()

assert book.GetSelection() == 1
assert controls['count'].GetLabel() == '1/4'
assert not controls['previous'].IsEnabled()
assert controls['title'].GetLabel() == t('tour.s2_title')
click('next')
assert book.GetSelection() == 1
assert controls['count'].GetLabel() == '2/4'
click('next')
assert book.GetSelection() == 2
click('previous')
assert book.GetSelection() == 1
click('next')
click('next')
assert book.GetSelection() == 3
assert controls['next'].GetLabel() == t('tour.finish')
controls['opt_out'].SetValue(True)
click('next')
assert frame._wx_quick_tour is None
assert not get_ui_pref_bool('show_tour', True)
assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    env["HPC_GUI_CONFIG_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
