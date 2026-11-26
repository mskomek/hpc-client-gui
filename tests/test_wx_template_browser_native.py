"""Native plugin-scoped browser and unsaved editor tab acceptance."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_template_browser_validates_and_opens_new_tab(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import traceback
import faulthandler
import wx
faulthandler.enable()
faulthandler.dump_traceback_later(15, repeat=True)
from unittest.mock import patch
from hpc_gui.core.i18n import load_language
from hpc_gui.plugins.job_templates import JobTemplate, TemplateVariable
from hpc_gui.wx_editor_view import show_editor

print("native editor: initialize", flush=True)
load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
print("native editor: construct", flush=True)
host = show_editor(path="/remote/existing.slurm", content="ORIGINAL", is_local=False)
print("native editor: constructed", flush=True)
app.ProcessPendingEvents()
model = host._wx_editor_model
template = JobTemplate("a", "Template A", "slurm", "plugin.a", "1", "job.slurm",
    variables=(TemplateVariable("count", "integer", required=True, minimum=1, maximum=8, default=2),
               TemplateVariable("partition", "choice", choices=("arf", "hamsi"), default="arf"),
               TemplateVariable("enabled", "boolean", default=False)),
    content="count={{count}} partition={{partition}} enabled={{enabled}}")
other = JobTemplate("b", "Template B", "slurm", "plugin.b", "1", "b.slurm", content="other")
errors = []

def click(btn):
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
    event.SetEventObject(btn)
    btn.GetEventHandler().ProcessEvent(event)

def run(accept):
    print("template:", accept, flush=True)
    def answer():
        dialog = next((w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_template_controls") and w.IsModal()), None)
        if dialog is None:
            wx.CallLater(20, answer)
            return
        try:
            controls = dialog._wx_template_controls
            assert controls["listing"].GetCount() == 1
            assert "plugin.a" in controls["listing"].GetString(0)
            fields = controls["fields"]
            fields["count"][0].SetValue("0")
            click(controls["ok"])
            assert dialog.IsModal() and controls["error"].GetLabel()
            if not accept:
                dialog.EndModal(wx.ID_CANCEL)
                return
            fields["count"][0].SetValue("4")
            fields["partition"][0].SetStringSelection("hamsi")
            fields["enabled"][0].SetValue(True)
            click(controls["ok"])
        except Exception:
            errors.append(traceback.format_exc())
            dialog.EndModal(wx.ID_CANCEL)
    wx.CallLater(30, answer)
    with patch("hpc_gui.plugins.job_templates.load_job_templates", return_value=[template, other]):
        assert host.new_from_template_for_plugin("plugin.a") is accept
    assert not errors, errors

run(False)
assert len(model.controller.documents) == 1 and model.controller.active.content == "ORIGINAL"
run(True)
assert len(model.controller.documents) == 2
assert model.controller.documents[0].content == "ORIGINAL"
assert model.controller.active.path == "" and model.controller.active.dirty
assert "count=4 partition=hamsi" in model.controller.active.content
assert host._wx_editor_header["path"].GetValue() == ""
assert host._wx_editor_header["array"].IsEnabled()
run(True)
assert len(model.controller.documents) == 3
print("native editor: destroy", flush=True)
host.Destroy()
app.ProcessPendingEvents()
faulthandler.cancel_dump_traceback_later()
print("native editor: completed", flush=True)
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script], cwd=root, env=env,
                            capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
