"""Exercise actual wx array controls and editor document mutation."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_slurm_array_edit_cancel_and_single_mode(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import traceback
import faulthandler
import wx
faulthandler.enable()
faulthandler.dump_traceback_later(15, repeat=True)
from hpc_gui.core.i18n import load_language
from hpc_gui.services.slurm_arrays import get_array
from hpc_gui.wx_editor_view import show_editor

print("native editor: initialize", flush=True)
load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
original = '#!/bin/bash\\n#SBATCH --array=1-2\\n#SBATCH --comment=keep\\necho test\\n'
print("native editor: construct", flush=True)
host = show_editor(path="/remote/job.slurm", content=original, is_local=False)
print("native editor: constructed", flush=True)
app.ProcessPendingEvents()
model = host._wx_editor_model
editor = host._wx_editor_controls["editor"]
button = host._wx_editor_header["array"]
errors = []

def click(control):
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, control.GetId())
    event.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(event)

def run(action):
    print("array:", action, flush=True)
    def answer():
        dialog = next((w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_array_controls") and w.IsModal()), None)
        if dialog is None:
            wx.CallLater(20, answer)
            return
        try:
            controls = dialog._wx_array_controls
            if action == "cancel":
                assert controls["directive"].GetValue() == "#SBATCH --array=1-2"
                controls["directive"].SetValue("invalid")
                assert not controls["ok"].IsEnabled()
                dialog.EndModal(wx.ID_CANCEL)
            elif action == "array":
                controls["directive"].SetValue("#SBATCH --array=0-100:2%10")
                assert controls["ok"].IsEnabled()
                click(controls["ok"])
            else:
                controls["single"].SetValue(True)
                evt = wx.CommandEvent(wx.EVT_RADIOBUTTON.typeId, controls["single"].GetId())
                evt.SetEventObject(controls["single"])
                controls["single"].GetEventHandler().ProcessEvent(evt)
                assert not controls["directive"].IsEnabled()
                click(controls["ok"])
        except Exception:
            errors.append(traceback.format_exc())
            dialog.EndModal(wx.ID_CANCEL)
    wx.CallLater(30, answer)
    click(button)
    assert not errors, errors

assert button.IsEnabled()
run("cancel")
assert editor.GetValue() == original and not model.controller.active.dirty
run("array")
assert get_array(model.controller.active.content).render() == "0-100:2%10"
assert model.controller.active.dirty and "#SBATCH --comment=keep" in editor.GetValue()
run("single")
assert get_array(model.controller.active.content) is None
assert "echo test" in editor.GetValue()
print("native editor: destroy", flush=True)
host.Destroy()
app.ProcessPendingEvents()
faulthandler.cancel_dump_traceback_later()
print("native editor: completed", flush=True)
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script], cwd=root, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
