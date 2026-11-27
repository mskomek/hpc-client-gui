"""Crash reporting is neutral in headless runs and owned by wx in V2."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


def _run(script, tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.contract
@pytest.mark.subprocess
def test_headless_exception_hook_persists_without_gui_imports(tmp_path):
    _run("""
import importlib.abc
import sys
from pathlib import Path

attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'wx', 'PySide6', 'PyQt5', 'PyQt6', 'shiboken6'}:
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())

from hpc_gui.core import crash_reporter, logging_setup
root = Path(sys.argv[1])
crash_reporter._crash_flag_path = lambda: root / 'crash_flag.json'
presented = []
logging_setup.install_excepthook(lambda: presented.append(crash_reporter.read_crash_flag()))
try:
    raise RuntimeError('headless synthetic crash')
except RuntimeError:
    sys.excepthook(*sys.exc_info())
assert len(presented) == 1
assert 'headless synthetic crash' in presented[0]['summary']
assert crash_reporter.read_crash_flag() == presented[0]
assert not attempts, attempts
""", tmp_path)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.regression
def test_wx_previous_and_live_crash_diagnostics(tmp_path):
    _run("""
import sys
import time
from pathlib import Path

import wx
from hpc_gui.core import crash_reporter
from hpc_gui.core import logging_setup
from hpc_gui.core.i18n import load_language, t
from hpc_gui import wx_crash_reporting

root = Path(sys.argv[1])
crash_reporter._crash_flag_path = lambda: root / 'crash_flag.json'
logging_setup.log_path = lambda: root / 'app.log'
load_language('en')
crash_reporter.write_crash_flag(RuntimeError, RuntimeError('previous synthetic crash'))
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
app.SetTopWindow(frame)
frame.Show()

def pump_until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('crash window not observed')

def crash_windows():
    return [w for w in wx.GetTopLevelWindows()
            if w is not frame and hasattr(w, '_wx_send_logs_controls')]

report_previous = wx_crash_reporting.install_wx_crash_reporting(app)
report_previous(frame)
pump_until(lambda: len(crash_windows()) == 1)
dialog = crash_windows()[0]
assert dialog.GetTitle() == t('crash.dialog_title_crash')
assert 'previous synthetic crash' in dialog._wx_send_logs_controls['header'].GetLabel()
assert crash_reporter.read_crash_flag() is None
dialog.Close()
pump_until(lambda: not crash_windows())

try:
    raise RuntimeError('live synthetic crash')
except RuntimeError:
    sys.excepthook(*sys.exc_info())
    sys.excepthook(*sys.exc_info())
pump_until(lambda: len(crash_windows()) == 1)
dialog = crash_windows()[0]
assert 'live synthetic crash' in dialog._wx_send_logs_controls['header'].GetLabel()
assert 'live synthetic crash' in crash_reporter.read_crash_flag()['summary']
assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'}
               for m in sys.modules)
dialog.Close()
pump_until(lambda: not crash_windows())
frame.Destroy()
app.ProcessPendingEvents()
""", tmp_path)
