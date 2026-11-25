"""Native cancel/retry regression through the production wx transfer panel."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.regression
@pytest.mark.parametrize("with_pending", [False, True])
def test_native_cancel_retry_releases_rows_and_retracks_session(with_pending):
    script = """
import sys
import threading
import time
import wx
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_file_transfer import _start_file_transfers
from hpc_gui.wx_transfer_workspace import build_transfers_panel

app = wx.App(False)
frame = wx.Frame(None)
panel = build_transfers_panel(frame)
first_entered = threading.Event()
first_release = threading.Event()
retry_entered = threading.Event()
retry_release = threading.Event()
calls = []

class Backend:
    supports_parallel_transfers = False
    def exists(self, path):
        return False
    def upload(self, source, destination, progress_cb=None):
        calls.append(source)
        if source == 'first':
            if calls.count('first') == 1:
                first_entered.set()
                assert first_release.wait(5)
            else:
                retry_entered.set()
                assert retry_release.wait(5)
        progress_cb(1, 1)

def pump_until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('native condition timed out')

def click(control):
    assert control.IsEnabled()
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))

items = [TransferItem('upload', 'first', '/first')]
if sys.argv[1] == 'True':
    items.append(TransferItem('upload', 'second', '/second'))
state = {'session': {'files': Backend(), 'profile': {}},
         'embedded_transfers_panel': panel}
controller = _start_file_transfers(state, None, items)
engine = controller.engine
controls = panel._wx_transfer_controls
rows = panel._wx_transfer_state
try:
    pump_until(lambda: first_entered.is_set() and id(items[0]) in rows['queue_map'])
    click(controls['cancel'])
    first_release.set()
    pump_until(lambda: engine.wait(0) and controls['retry_failed'].IsEnabled()
               and controller not in state['transfer_sessions'])
    assert engine.failed == [(items[0], 'cancelled')]
    assert not engine.completed
    assert id(items[0]) not in rows['queue_map']
    assert id(items[0]) in rows['failed_map']
    click(controls['retry_failed'])
    pump_until(lambda: retry_entered.is_set() and id(items[0]) in rows['queue_map'])
    assert controller in state['transfer_sessions']
    assert id(items[0]) not in rows['failed_map']
    retry_release.set()
    pump_until(lambda: engine.wait(0) and not rows['queue_map']
               and len(rows['completed_map']) == len(items)
               and controller not in state['transfer_sessions'])
    assert not engine.failed
    assert engine.completed == items
    assert calls == ['first', 'first'] + (['second'] if len(items) == 2 else [])
    assert not any(m.split('.')[0] in {'PySide6', 'PyQt5', 'PyQt6', 'shiboken6'}
                   for m in sys.modules)
finally:
    first_release.set()
    retry_release.set()
    controller.cancel()
    engine.wait(5)
    panel._wx_transfer_close(None)
    frame.Destroy()
    app.ProcessPendingEvents()
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, str(with_pending)],
        cwd=root, env=env, capture_output=True, text=True, timeout=35,
    )
    assert result.returncode == 0, result.stdout + result.stderr
