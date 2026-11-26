"""Native wx key modifiers, visibility and privacy regressions."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_key_event_with_keyboard_modifiers_is_logged_without_error():
    root = Path(__file__).resolve().parents[1]
    script = """
import logging
import sys
import time
import wx
from unittest.mock import patch
from hpc_gui.core.debug_telemetry import TelemetryRecorder
from hpc_gui.wx_debug_telemetry import install_wx_debug_telemetry, observe_wx_window

records = []
class Capture(logging.Handler):
    def emit(self, record):
        records.append(record.getMessage())

logger = logging.getLogger('test.wx.lifecycle')
logger.setLevel(logging.INFO)
logger.addHandler(Capture())
app = wx.App(False)
frame = wx.Frame(None)
book = wx.Notebook(frame)
page = wx.Panel(book)
book.AddPage(page, 'PRIVATE-TAB')
button = wx.Button(page, label='PRIVATE-BUTTON')
field = wx.TextCtrl(page, value='PRIVATE-INPUT', style=wx.TE_PASSWORD)
recorder = TelemetryRecorder(logger=logger)
install_wx_debug_telemetry(frame, book, recorder=recorder)
frame.Show()
app.ProcessPendingEvents()

def key(target, code):
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.m_keyCode = code
    event.SetEventObject(target)
    with patch.object(wx.Window, 'FindFocus', return_value=target):
        frame.GetEventHandler().ProcessEvent(event)

key(button, wx.WXK_DELETE)
assert any('key=%s modifiers=0' % wx.WXK_DELETE in item for item in records), records
before = len(records)
key(field, wx.WXK_DELETE)
key(button, ord('A'))
assert len(records) == before, records

dialog = wx.Dialog(frame, title='PRIVATE-DIALOG')
assert observe_wx_window(dialog, recorder=recorder) is recorder
assert observe_wx_window(dialog, recorder=recorder) is recorder
dialog.Show()
deadline = time.monotonic() + 3
while time.monotonic() < deadline:
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    if any('ui.window ready' in item for item in records):
        break
    time.sleep(.01)
assert any('ui.window shown kind=Dialog' in item for item in records), records
assert any('ui.window ready kind=Dialog' in item for item in records), records
dialog.Hide()
app.ProcessPendingEvents()
assert sum('ui.window hidden kind=Dialog' in item for item in records) == 1, records
dialog.Destroy()
app.ProcessPendingEvents()
assert not any('PRIVATE' in item for item in records), records
assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
