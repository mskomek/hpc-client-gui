"""Native splash startup stages and late callback shutdown."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_real_splash_checks_backends_and_cancels_late_callbacks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import time
import threading
import wx
from hpc_gui.core.i18n import load_language, t
from hpc_gui.services import app_updater
from hpc_gui import startup_checks
from hpc_gui.wx_splash import create_startup_splash
from hpc_gui.wx_startup_flow import start_startup_flow

app = wx.App(False)
app.SetExitOnFrameDelete(False)
app_updater.get_latest_release = lambda **kw: None
startup_checks.check_startup_helpers = lambda: {'SSH backend': True, 'SFTP backend': False}
completed = []
load_language('en')
splash = create_startup_splash(pure_splash=True)
splash.Show()
flow = start_startup_flow(app, splash, lambda: completed.append(True))

def pump_until(predicate, timeout=8):
    if predicate():
        return
    # The production startup is driven by native timer messages inside a
    # running event loop. ProcessPendingEvents/Yield alone do not reliably
    # dispatch those messages on Windows.
    loop = wx.GUIEventLoop()
    deadline = time.monotonic() + timeout
    timer = None
    def check():
        nonlocal timer
        app.ProcessPendingEvents()
        loop.ProcessIdle()
        if predicate():
            loop.Exit(0)
        elif time.monotonic() >= deadline:
            loop.Exit(1)
        else:
            timer = wx.CallLater(20, check)
    with wx.EventLoopActivator(loop):
        timer = wx.CallLater(20, check)
        loop.ProcessIdle()
        code = loop.Run()
    if timer is not None:
        timer.Stop()
    assert code == 0 and predicate(), 'native startup condition timed out'

pump_until(lambda: completed == [True])
assert splash._wx_splash_state['stages']['preferences'] == 'complete'
assert splash._wx_splash_state['stages']['helpers'] == 'failed'
log = splash._wx_splash_controls['log'].GetValue()
assert 'SSH backend: available' in log
assert 'SFTP backend: unavailable' in log
assert 'Checking SFTP helper...' not in log
assert splash._wx_splash_controls['brand_sub'].GetLabel() == t('splash.starting')
load_language('tr')
assert flow._cancelled and flow.timer is None
splash.Destroy()
pump_until(lambda: not splash)

entered, release, finished = threading.Event(), threading.Event(), threading.Event()
def blocked_release(**kw):
    entered.set()
    release.wait(5)
    finished.set()
    return None

app_updater.get_latest_release = blocked_release
second = create_startup_splash(pure_splash=True)
second.Show()
assert second._wx_splash_controls['brand_sub'].GetLabel() == t('splash.starting')
late = []
other = start_startup_flow(app, second, lambda: late.append(True))
try:
    pump_until(entered.is_set)
    second.Destroy()
    pump_until(lambda: other._cancelled and not second)
    release.set()
    pump_until(finished.is_set)
    for _ in range(20):
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        time.sleep(.01)
    assert not late
    assert other.update_check.status == 'skipped'
    assert other.timer is None
    assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
finally:
    release.set()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    env["HPC_GUI_CONFIG_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
