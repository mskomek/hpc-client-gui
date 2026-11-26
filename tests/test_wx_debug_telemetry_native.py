"""Real wx event routing for source-only structural telemetry."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_wx_telemetry_is_structural_and_nonblocking():
    root = Path(__file__).resolve().parents[1]
    script = """
import logging
import sys
import time
import wx
from hpc_gui.core.debug_telemetry import TelemetryRecorder
from hpc_gui.wx_debug_telemetry import install_wx_debug_telemetry

records = []
class Capture(logging.Handler):
    def emit(self, record):
        records.append(record.getMessage())
logger = logging.getLogger('test.wx.telemetry')
logger.setLevel(logging.INFO)
logger.addHandler(Capture())
app = wx.App(False)
frame = wx.Frame(None)
book = wx.Notebook(frame)
first, second = wx.Panel(book), wx.Panel(book)
book.AddPage(first, 'PRIVATE-TAB-LABEL')
book.AddPage(second, 'SECOND-PRIVATE-TAB')
button = wx.Button(first, label='PRIVATE-BUTTON-LABEL')
field = wx.TextCtrl(first, value='PRIVATE-INPUT', style=wx.TE_PASSWORD)
seen = []
button.Bind(wx.EVT_BUTTON, lambda event: (seen.append('button'), event.Skip()))
frame.Show()
recorder = TelemetryRecorder(logger=logger)
assert install_wx_debug_telemetry(frame, book, recorder=recorder) is recorder
event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
event.SetEventObject(button)
button.GetEventHandler().ProcessEvent(event)
book.SetSelection(1)
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    if any('ui.tab ready' in x for x in records):
        break
    time.sleep(.01)
assert seen == ['button']
assert any('ui.action clicked control=Button' in x for x in records), records
assert any('ui.tab changed scope=main from=0 to=1' in x for x in records), records
assert any('ui.tab ready scope=main tab=1' in x for x in records), records
assert not any('PRIVATE' in x for x in records), records
assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
sys.frozen = True
assert install_wx_debug_telemetry(frame, book, recorder=recorder) is None
del sys.frozen
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
