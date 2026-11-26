"""Verify the native self-test result, copy and rerun without real connections."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_result_renders_observations_and_copies_safe_text(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import wx
import traceback
from unittest.mock import patch
from hpc_gui.core.i18n import load_language
from hpc_gui.services.cluster_self_test import ClusterSelfTestResult, SelfTestSection, SelfTestItem
from hpc_gui.wx_cluster_self_test_result import create_self_test_result_dialog, RUN_AGAIN_ID

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
parent = wx.Frame(None)
parent.Show()
result = ClusterSelfTestResult("PASS", (
    SelfTestSection("Connection", (SelfTestItem("ssh", "PASS", "authenticated"),)),
    SelfTestSection("Scheduler", (SelfTestItem("squeue", "PASS", "available"),)),
))
dialog = create_self_test_result_dialog(parent, result, provider={
    "name": "Mock provider", "scheduler": "slurm", "access": {"auth_methods": ["key"]},
})
controls = dialog._wx_self_test_controls
assert "PASS" in controls["summary"].GetLabel()
value = controls["content"].GetValue()
assert "Declared by provider: Mock provider" in value
assert "auth: DECLARED / PASS" in value
assert "scheduler: DECLARED / PASS" in value
assert "[Connection]" in value and "ssh: PASS" in value
assert not controls["content"].IsEditable()

copied = []
class Clipboard:
    def Open(self): return True
    def SetData(self, data): copied.append(data.GetText())
    def Close(self): pass

def click(button):
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    evt.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(evt)

errors = []
def act():
    try:
        click(controls["copy"])
        click(controls["again"])
    except Exception:
        errors.append(traceback.format_exc())
        dialog.EndModal(wx.ID_CANCEL)

with patch.object(wx, "TheClipboard", Clipboard()):
    wx.CallLater(50, act)
    assert dialog.ShowModal() == RUN_AGAIN_ID, errors
assert len(copied) == 1 and "ssh: PASS" in copied[0] and "status: PASS" in copied[0]
assert "password" not in copied[0]
dialog.Destroy()
parent.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
