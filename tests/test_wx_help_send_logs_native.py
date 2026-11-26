"""Native lifecycle and actual menu-view behavior for Help and Send Logs."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_help_and_send_logs_native(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import time
from pathlib import Path
from unittest.mock import patch

import wx
from hpc_gui.core.i18n import load_language, set_language, t
from hpc_gui.wx_help import show_help
from hpc_gui.wx_send_logs_view import show_send_logs

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
parent = wx.Frame(None)
parent.Show()

def pump(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("native operation timed out")

def click(button):
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)

assert show_help(parent) == wx.ID_OK
help_frame = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_help_controls"))
controls = help_frame._wx_help_controls
assert controls["sidebar"].GetCount() > 2
controls["search"].SetValue("Ctrl+Z")
pump(lambda: controls["results"].GetCount() > 0)
set_language("tr")
pump(lambda: help_frame.GetTitle() == t("help.help_title"))
assert controls["close"].GetLabel() == t("common.close")
set_language("en")
help_frame.Destroy()
pump(lambda: not any(hasattr(w, "_wx_help_controls") for w in wx.GetTopLevelWindows()))
set_language("tr")
app.ProcessPendingEvents()
load_language("en")

directory = Path(sys.argv[1])
log = directory / "app.log"
log.write_text("first line\\npassword=synthetic-secret\\nlast line\\n", encoding="utf-8")
exported = []
messages = []
class Folder:
    def ShowModal(self):
        return wx.ID_OK
    def GetPath(self):
        return str(directory)
    def Destroy(self):
        pass

def export(dest):
    exported.append(dest)
    return directory / "diagnostics.zip"

with patch.object(wx, "DirDialog", lambda *args: Folder()), patch.object(
    wx, "MessageBox", lambda *args: messages.append(args) or wx.OK
):
    assert show_send_logs(parent, log_path=log, crash_context=True,
                          crash_summary="synthetic crash", bundle=export) == wx.ID_OK
    logs = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_send_logs_controls"))
    controls = logs._wx_send_logs_controls
    pump(lambda: "last line" in controls["log_view"].GetValue())
    assert "first line" in controls["log_view"].GetValue()
    assert "synthetic-secret" not in controls["log_view"].GetValue()
    assert not controls["log_view"].IsEditable()
    assert "synthetic crash" in controls["header"].GetLabel()
    click(controls["export"])
    pump(lambda: bool(messages))
    assert exported == [str(directory)]
    assert "diagnostics.zip" in messages[0][0]
    set_language("tr")
    logs.Destroy()
    pump(lambda: not any(hasattr(w, "_wx_send_logs_controls") for w in wx.GetTopLevelWindows()))
    set_language("en")
    app.ProcessPendingEvents()
assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
parent.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
