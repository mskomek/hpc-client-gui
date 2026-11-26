"""Native approved tool routing and sorted result identity, in a fresh process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_approved_native_ansys_tool_rows(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import faulthandler
import sys
import wx
from types import SimpleNamespace as NS
from unittest.mock import patch
from hpc_gui.core.i18n import load_language
from hpc_gui.plugins.linter_tools import LinterTool
from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost

faulthandler.enable()
load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
parent = wx.Frame(None)
parent.Show()

def finding(code, severity, url):
    return NS(code=code, severity=NS(value=severity), line=2, column=1,
              message=code, explanation="explain " + code,
              suggested_fix="fix " + code, source_url=url, is_heuristic=False)

warning = finding("WARNING", "warning", "https://docs.ansys.com/warning")
error = finding("ERROR", "error", "https://docs.ansys.com/error")
module_name = "_native_ansys_test"
sys.modules[module_name] = NS(SUPPORTED_SUFFIXES={".jou"},
                              lint_text=lambda text, file_name="": NS(diagnostics=[warning, error]))

def forbidden_page(**kwargs):
    raise AssertionError("legacy page factory called")

tool = LinterTool("org.hpcclient.ansyslint", "1", "ANSYS", "", forbidden_page, module_name)
manifest = NS(id=tool.plugin_id, publisher="HPC Client GUI", plugin_api=2,
              capabilities=["linter-tool"], entrypoints={"linter_engine":"engine/ansys_lint/__init__.py"})
plugin = NS(manifest=manifest)
with patch("hpc_gui.plugins.linter_tools.load_tool_for_plugin", return_value=tool):
    assert WxPluginMenuHost(parent=parent).open_trusted_tool(plugin)

frame = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_ansys_model"))
model = frame._wx_ansys_model
results = model.lint_files([("z.jou", "text"), ("a.jou", "text")])
assert len(results) == 2 and all(r.state.status == "completed" for r in results)
frame._wx_ansys_render(results)
ctrl = frame._wx_ansys_controls
listing = ctrl["results"]
assert listing.GetItemCount() == 4
assert listing.GetItemText(0, 0) == "a.jou"
assert listing.GetItemText(0, 3) == "ERROR"
evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, listing.GetId())
evt.SetIndex(0)
evt.SetEventObject(listing)
listing.GetEventHandler().ProcessEvent(evt)
assert "explain ERROR" in ctrl["detail"].GetValue()
assert "fix ERROR" in ctrl["detail"].GetValue()
opened = []
def click(btn):
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
    evt.SetEventObject(btn)
    btn.GetEventHandler().ProcessEvent(evt)
with patch.object(wx, "LaunchDefaultBrowser", lambda url: opened.append(url)):
    click(ctrl["open_doc"])
assert opened == [error.source_url]
click(ctrl["clear"])
assert listing.GetItemCount() == 0
assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
frame.Close()
parent.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
