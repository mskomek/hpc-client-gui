"""Subprocess acceptance of native editor lint and grouped file results."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_lint_snapshot_navigation_and_file_results(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import faulthandler
import traceback
from types import SimpleNamespace as NS
from unittest.mock import patch
import wx
from hpc_gui.core.i18n import load_language
from hpc_gui.lint.models import Diagnostic, Severity
from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost
from hpc_gui.wx_editor_view import show_editor
from hpc_gui.wx_lint_results import create_lint_results, show_lint_results

faulthandler.enable()
faulthandler.dump_traceback_later(15, repeat=True)
load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
host = show_editor(path="/remote/job.jou", content="first\nsecond\nthird\n", is_local=False)
app.ProcessPendingEvents()
errors = []
calls = []
diag = Diagnostic("RULE", Severity.WARNING, "finding", line=2, column=1,
                  explanation="reason", suggested_fix="fix it", documentation_url="https://example.test/doc",
                  plugin_id="org.test")
def click(control, binder=wx.EVT_BUTTON):
    evt = wx.CommandEvent(binder.typeId, control.GetId())
    evt.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(evt)

def collect(self, path, text, plugin_id=None):
    calls.append((path, text, plugin_id))
    return [], [diag]

def answer():
    dialog = next((w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_lint_controls") and w.IsModal()), None)
    if dialog is None:
        wx.CallLater(20, answer)
        return
    try:
        c = dialog._wx_lint_controls
        assert "RULE" in c["listing"].GetString(0)
        assert "fix it" in c["detail"].GetValue()
        assert c["docs"].IsEnabled()
        click(c["listing"], wx.EVT_LISTBOX_DCLICK)
    except Exception:
        errors.append(traceback.format_exc())
        dialog.EndModal(wx.ID_CANCEL)

with patch("hpc_gui.services.editor_lint.EditorLintPipeline.collect", collect):
    wx.CallLater(30, answer)
    assert WxPluginMenuHost(host).run_editor_lint("org.test")
    deadline = __import__("time").monotonic() + 8
    while host._wx_editor_state.get("lint_running") and __import__("time").monotonic() < deadline:
        wx.Yield()
        __import__("time").sleep(.01)
assert not errors, errors
assert not host._wx_editor_state["lint_running"]
assert calls == [("/remote/job.jou", "first\nsecond\nthird\n", "org.test")]
editor = host._wx_editor_controls["editor"]
assert editor.GetStringSelection() == "second"
assert not host._wx_editor_model.controller.active.dirty

# Exercise the native accelerator's command event. Physical key injection
# needs an interactive desktop and is not claimed by this subprocess.
with patch("hpc_gui.services.editor_lint.EditorLintPipeline.collect", collect):
    panel, command_id = host._wx_lint_accelerator
    assert panel.GetAcceleratorTable().IsOk()
    assert host._wx_editor_header["lint"].IsEnabled()
    wx.CallLater(30, answer)
    event = wx.CommandEvent(wx.EVT_MENU.typeId, int(command_id))
    event.SetEventObject(panel)
    assert panel.GetEventHandler().ProcessEvent(event)
    assert host._wx_editor_state["lint_running"]
    deadline = __import__("time").monotonic() + 8
    while host._wx_editor_state.get("lint_running") and __import__("time").monotonic() < deadline:
        wx.Yield()
        __import__("time").sleep(.01)
assert not errors, errors
assert calls == [("/remote/job.jou", "first\nsecond\nthird\n", "org.test"),
                 ("/remote/job.jou", "first\nsecond\nthird\n", None)], calls
d = NS(code="C1", severity=NS(value="warning"), line=2, column=3, message="finding",
       explanation="reason", suggested_fix="fix it", source_url="https://example.test/doc", is_heuristic=True)
f = NS(file_path="job.jou", detection=NS(product="fluent", detected_version="25.2"),
       summary={"warning":1}, diagnostics=[d], sorted_diagnostics=lambda:[d])
run = NS(files=[f])
dialog = create_lint_results(host, "Lint", run)
try:
    controls = dialog._wx_lint_result_controls
    assert "fix" not in controls
    assert not controls["suggestion"].IsEnabled()
    controls["listing"].SetSelection(1)
    click(controls["listing"], wx.EVT_LISTBOX)
    assert controls["owners"][1] is d and "reason" in controls["detail"].GetValue()
    opened = []
    with patch.object(wx, "LaunchDefaultBrowser", lambda url: opened.append(url)):
        click(controls["documentation"])
    assert opened == [d.source_url]
    assert controls["suggestion"].IsEnabled()
finally:
    dialog.Destroy()
fired = []
def fix():
    modal = next((w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_lint_result_controls") and w.IsModal()), None)
    if modal is None:
        wx.CallLater(20, fix)
        return
    click(modal._wx_lint_result_controls["fix"])
wx.CallLater(30, fix)
show_lint_results(host, "Lint", run, open_in_tool=lambda: fired.append(True))
assert fired == [True]
host.Destroy()
app.ProcessPendingEvents()
faulthandler.cancel_dump_traceback_later()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
