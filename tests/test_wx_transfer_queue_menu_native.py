"""Exercise native wx menu bindings against the production transfer workspace."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_transfer_menu_commands():
    root = Path(__file__).resolve().parents[1]
    script = """
import threading
import time
import sys
import wx
from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_file_transfer import _start_file_transfers
from hpc_gui.wx_transfer_workspace import build_transfers_panel
from hpc_gui._wx_transfer_common import find_row
from hpc_gui._wx_transfer_queue_menu import build_transfer_menu

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
        if source in ('bad1', 'bad2') and calls.count(source) == 1:
            raise OSError('synthetic')
        progress_cb(1, 1)

def pump(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('native menu condition timed out')

items = [TransferItem('upload', name, '/'+name, cached_size=size)
         for name, size in zip(('first', 'bad1', 'bad2', 'remove', 'last'), (128, 0, None, 4096, 777))]
state = {'session': {'files': Backend(), 'profile': {}}, 'embedded_transfers_panel': panel}
controller = _start_file_transfers(state, None, items)
engine = controller.engine
view = panel._wx_transfer_state
controls = panel._wx_transfer_controls

def select(kind, item):
    listing = controls[kind]
    row = listing.GetFirstSelected()
    while row != -1:
        listing.Select(row, False)
        row = listing.GetFirstSelected()
    row = find_row(view, listing, id(item))
    assert row >= 0
    listing.Select(row)

def command(menu, key, enabled=True):
    entry = next(i for i in menu.GetMenuItems() if i.GetItemLabelText() == t(key))
    assert entry.IsEnabled() == enabled, key
    if enabled:
        event = wx.CommandEvent(wx.EVT_MENU.typeId, entry.GetId())
        event.SetEventObject(menu)
        assert menu.ProcessEvent(event), key
    return entry

def menu_action(kind, key):
    menu = build_transfer_menu(wx, panel, view, controls, kind)
    try:
        command(menu, key)
    finally:
        menu.Destroy()

try:
    pump(lambda: entered.is_set() and len(view['queue_map']) == 5)
    for item, expected in zip(items, ('128', '0', '', '4096', '777')):
        assert controls['queue'].GetItemText(find_row(view, controls['queue'], id(item)), 3) == expected
    select('queue', items[0])
    menu = build_transfer_menu(wx, panel, view, controls, 'queue')
    try:
        command(menu, 'transfer.remove_selected', False)
    finally:
        menu.Destroy()
    select('queue', items[4])
    menu = build_transfer_menu(wx, panel, view, controls, 'queue')
    try:
        sub = next(i.GetSubMenu() for i in menu.GetMenuItems() if i.IsSubMenu())
        command(sub, 'transfer.priority_highest')
    finally:
        menu.Destroy()
    pump(lambda: engine.pending[0] is items[4]
         and controls['queue'].GetItemText(find_row(view, controls['queue'], id(items[4])), 5)
             == t('transfer.priority_highest'))
    assert find_row(view, controls['queue'], id(items[4])) == 1
    select('queue', items[3])
    menu_action('queue', 'transfer.remove_selected')
    pump(lambda: id(items[3]) not in view['queue_map'])
    release.set()
    pump(lambda: engine.wait(0) and len(view['failed_map']) == 2
         and len(view['completed_map']) == 2)
    assert calls == ['first', 'last', 'bad1', 'bad2']
    for kind, item, expected in (('completed', items[0], '128'), ('failed', items[1], '0')):
        assert controls[kind].GetItemText(find_row(view, controls[kind], id(item)), 3) == expected
    select('failed', items[2])
    menu_action('failed', 'transfer.retry_selected')
    pump(lambda: engine.wait(0) and len(view['failed_map']) == 1
         and len(view['completed_map']) == 3)
    assert calls[-1] == 'bad2'
    assert [it for it, _ in engine.failed] == [items[1]]
    select('failed', items[1])
    menu_action('failed', 'transfer.remove_selected')
    pump(lambda: not view['failed_map'])
    assert not engine.failed
    select('completed', items[4])
    menu_action('completed', 'transfer.remove_selected')
    pump(lambda: len(view['completed_map']) == 2)
    assert items[4] not in engine.completed
    menu_action('completed', 'transfer.clear_completed')
    pump(lambda: not view['completed_map'])
    assert not engine.completed
    assert calls == ['first', 'last', 'bad1', 'bad2', 'bad2']
    # Retired toolkit tab-selection contract: each queue update must leave
    # the user's currently selected tab alone, including background errors.
    notebook = controls['notebook']
    assert notebook.GetPageCount() == 3
    for index in range(3):
        notebook.SetSelection(index)
        failed_item = TransferItem('upload', 'failure', '/failure')
        completed_item = TransferItem('upload', 'success', '/success')
        panel._wx_transfer_queue('queued', failed_item)
        pump(lambda: id(failed_item) in view['queue_map'])
        assert notebook.GetSelection() == index
        panel._wx_transfer_queue('failed', failed_item)
        pump(lambda: id(failed_item) in view['failed_map'])
        assert notebook.GetSelection() == index
        panel._wx_transfer_queue('queued', completed_item)
        pump(lambda: id(completed_item) in view['queue_map'])
        assert notebook.GetSelection() == index
        panel._wx_transfer_queue('completed', completed_item)
        pump(lambda: id(completed_item) in view['completed_map'])
        assert notebook.GetSelection() == index
        assert [notebook.GetPageText(i) for i in range(3)] == [
            f"{t('transfer.queue_tab')} (0)",
            f"{t('transfer.failed_tab')} (1)",
            f"{t('transfer.completed_tab')} (1)",
        ]
        panel._wx_transfer_queue('forgotten_failed', failed_item)
        panel._wx_transfer_queue('forgotten_completed', completed_item)
        pump(lambda: not view['failed_map'] and not view['completed_map'])
    assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
finally:
    release.set()
    controller.cancel()
    engine.wait(5)
    panel._wx_transfer_close(None)
    frame.Destroy()
    app.ProcessPendingEvents()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
