"""Exercise the real updater helper modal in its own native wx process."""
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
@pytest.mark.parametrize("failure", [False, True])
def test_native_updater_helper_progress_ready_and_result(tmp_path, failure):
    config = tmp_path / "update.json"
    config.write_text(
        '{"strategy":"linux-appimage","package":"unused","target":"unused",'
        '"current_pid":1,"version":"2.0.0"}', encoding="utf-8"
    )
    script = """
import sys
import threading
from pathlib import Path

import wx
from hpc_gui.services import updater_helper as helper

config = Path(sys.argv[1])
failure = sys.argv[2] == 'True'
app = wx.App(False)
main_thread = threading.get_ident()
observed = threading.Event()
errors = []
messages = []
dialogs = []

def install(cfg, publish):
    assert threading.get_ident() != main_thread
    assert config.with_suffix('.ready').read_text(encoding='ascii') == 'ready'
    assert cfg.version == '2.0.0'
    publish(None, 'Waiting for application to close...')
    publish(40, 'Copying: example')
    assert observed.wait(5), 'native progress never rendered'
    if failure:
        raise RuntimeError('synthetic installer failure')
    publish(100, 'Update complete.')

def inspect():
    try:
        for dialog in wx.GetTopLevelWindows():
            if not isinstance(dialog, wx.Dialog) or not dialog.IsModal():
                continue
            children = [child for panel in dialog.GetChildren()
                        for child in panel.GetChildren()]
            gauges = [child for child in children if isinstance(child, wx.Gauge)]
            if not gauges or gauges[0].GetValue() != 40:
                continue
            assert any(isinstance(c, wx.StaticText) and c.GetLabel() == '40%'
                       for c in children)
            dialogs.append(dialog)
            dialog.Close()
            assert dialog.IsModal(), 'active installer was closed'
            observed.set()
            return
        wx.CallLater(30, inspect)
    except BaseException as exc:
        errors.append(str(exc))
        observed.set()

def message_box(message, caption, style, parent):
    assert threading.get_ident() == main_thread
    assert parent.IsModal()
    messages.append(message)
    return wx.ID_OK

helper.perform_update = install
wx.MessageBox = message_box
wx.CallLater(30, inspect)
result = helper.run_helper(config)
assert not errors, errors
assert observed.is_set() and dialogs, 'native dialog not observed'
assert result == int(failure), result
assert len(messages) == int(failure), messages
if failure:
    assert 'synthetic installer failure' in messages[0]
assert not any(m.split('.')[0] in {'PySide6', 'PyQt5', 'PyQt6', 'shiboken6'}
               for m in sys.modules)
app.ProcessPendingEvents()
assert not wx.GetTopLevelWindows()
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, str(config), str(failure)],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
