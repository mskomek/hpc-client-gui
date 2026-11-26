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


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.regression
@pytest.mark.parametrize("action", ["pause_resume", "clear", "reset", "overlap"])
def test_native_queue_stop_clear_and_owner_isolation(action):
    script = """
import sys
import threading
import time
import wx
from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_file_transfer import _start_file_transfers
from hpc_gui.wx_shell_session_reset import reset_connection_views
from hpc_gui.wx_transfer_workspace import build_transfers_panel

app = wx.App(False)
frame = wx.Frame(None)
panel = build_transfers_panel(frame)
frame.Show()
entered, release = threading.Event(), threading.Event()
calls = []

class Backend:
    supports_parallel_transfers = False
    def exists(self, path):
        return False
    def upload(self, source, destination, progress_cb=None):
        calls.append(source)
        if source == 'first':
            entered.set()
            assert release.wait(5)
        progress_cb(1, 1)

def pump_until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('native queue condition timed out')

def click(key):
    control = controls[key]
    assert control.IsEnabled(), key
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, control.GetId())
    event.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(event)

action = sys.argv[1]
items = [TransferItem('upload', 'first', '/first'), TransferItem('upload', 'second', '/second')]
state = {'session': {'files': Backend(), 'profile': {}},
         'embedded_transfers_panel': panel}
controller = _start_file_transfers(state, None, items)
engine = controller.engine
controls = panel._wx_transfer_controls
rows = panel._wx_transfer_state
try:
    pump_until(lambda: entered.is_set() and controls['stop'].IsEnabled())
    assert controls['cancel'].IsEnabled()
    assert not controls['process_queue'].IsEnabled()
    assert controls['notebook'].GetPageText(0).endswith('(2)')
    if action == 'clear':
        click('clear_pending')
        pump_until(lambda: set(rows['queue_map']) == {id(items[0])})
        assert not engine.pending
        assert not controls['clear_pending'].IsEnabled()
        assert not controls['stop'].IsEnabled()
        assert controls['cancel'].IsEnabled()
    else:
        click('stop')
        assert not engine.cancel_requested
        assert not controls['stop'].IsEnabled()
        assert controls['cancel'].IsEnabled()
        assert not controls['process_queue'].IsEnabled()
    release.set()
    pump_until(lambda: engine.wait(0) and id(items[0]) in rows['completed_map']
               and controller not in state['transfer_sessions'])
    assert engine.completed == [items[0]]
    assert not engine.failed
    assert calls == ['first']
    assert not controls['cancel'].IsEnabled()
    if action == 'clear':
        assert not rows['queue_map']
        assert not controls['process_queue'].IsEnabled()
        assert controls['status'].GetLabel() == t('transfer.completed_tab')
    else:
        pump_until(lambda: controls['process_queue'].IsEnabled()
                   and controls['status'].GetLabel() == t('transfer.stopped_after_current'))
        assert engine.pending == [items[1]]
        assert set(rows['queue_map']) == {id(items[1])}
        if action == 'reset':
            # A late old-owner event must not repopulate the cleared panel.
            panel._wx_transfer_queue('queued', items[1], owner=controller)
            reset_connection_views(state)
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            assert rows['controller'] is None
            assert not engine.pending and not rows['queue_map'] and not rows['completed_map']
            assert not controls['process_queue'].IsEnabled()
            assert controls['status'].GetLabel() == t('transfer.no_active_transfer')
            assert controls['notebook'].GetPageText(0).endswith('(0)')
        else:
            if action == 'overlap':
                second_controller = _start_file_transfers(
                    state, None, [TransferItem('upload', 'third', '/third')])
                assert second_controller is not controller
                pump_until(lambda: second_controller.engine.wait(0))
                assert rows['controller'] is controller
                assert calls == ['first', 'third']
                assert controls['process_queue'].IsEnabled()
            click('process_queue')
            pump_until(lambda: engine.wait(0) and len(rows['completed_map']) == 2
                       and controller not in state['transfer_sessions'])
            assert not engine.failed and engine.completed == items
            assert calls == (['first', 'third', 'second'] if action == 'overlap' else ['first', 'second'])
            assert not rows['queue_map'] and not controls['process_queue'].IsEnabled()
            assert not controls['stop'].IsEnabled() and not controls['cancel'].IsEnabled()
finally:
    release.set()
    controller.cancel()
    engine.wait(5)
    panel._wx_transfer_close(None)
    for window in list(wx.GetTopLevelWindows()):
        if window is not frame:
            window.Destroy()
    frame.Destroy()
    app.ProcessPendingEvents()
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, action],
        cwd=root, env=env, capture_output=True, text=True, timeout=35,
    )
    assert result.returncode == 0, result.stdout + result.stderr
