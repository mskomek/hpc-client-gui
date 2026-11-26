"""Native modal preflight and worker-conflict cancellation in an isolated process."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_preflight_and_conflict_lifecycle(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import time
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
import wx
from hpc_gui.core.i18n import load_language
from hpc_gui.config.storage import get_upload_preflight_confirmation_enabled, set_upload_preflight_confirmation_enabled
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_conflict_policy import ConflictFileInfo
from hpc_gui.wx_shell_upload import prepare_upload
from hpc_gui.wx_conflict_bridge import request_conflict_decision

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
parent = wx.Frame(None)
parent.Show()
source = Path(sys.argv[1]) / "case"
source.mkdir()
(source / "empty").mkdir()
for i in range(250):
    (source / f"file-{i:03}.txt").write_text("x")
files = SimpleNamespace(supports_parallel_transfers=False)
session = {"files": files, "profile": {"transfer_parallelism": 4}}
state = {"session": session, "generation": 1}
lifecycle = SimpleNamespace(shutdown_started=False)
started = []

def pump(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("native lifecycle timed out")

def run_preflight(action):
    inspected = []
    def answer():
        dialogs = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_upload_preflight_controls")]
        if not dialogs:
            wx.CallLater(20, answer)
            return
        dialog = dialogs[0]
        controls = dialog._wx_upload_preflight_controls
        assert not started
        assert controls["listing"].GetItemCount() == 201
        assert "250 files" in controls["summary"].GetLabel()
        assert "2 folder" in controls["summary"].GetLabel()
        assert "1 transfers" in controls["summary"].GetLabel()
        assert "Remaining: 52" in controls["listing"].GetItemText(200)
        controls["dont_ask"].SetValue(True)
        inspected.append(True)
        if action == "stale":
            state["generation"] += 1
        dialog.EndModal(wx.ID_CANCEL if action == "cancel" else wx.ID_OK)
    wx.CallLater(30, answer)
    prepare_upload(state, lifecycle, parent, session, files, [source], "/remote",
                   lambda *args, **kwargs: started.append(args[2]), generation=state["generation"])
    assert inspected

run_preflight("cancel")
assert not started and get_upload_preflight_confirmation_enabled()
run_preflight("stale")
assert not started and get_upload_preflight_confirmation_enabled()
run_preflight("accept")
assert len(started[0]) == 252
assert not get_upload_preflight_confirmation_enabled()
prepare_upload(state, lifecycle, parent, session, files, [source], "/remote",
               lambda *args, **kwargs: started.append(args[2]), generation=state["generation"])
assert len(started) == 2
set_upload_preflight_confirmation_enabled(True)

live = {"value": True}
decisions = []
item = TransferItem("upload", str(source / "file-000.txt"), "/remote/a")
metadata = (ConflictFileInfo(item.src, 123, 1700000000), ConflictFileInfo(item.dst, 456, None))
worker = Thread(target=lambda: decisions.append(
    request_conflict_decision(parent, files, item, lambda: live["value"], metadata)), daemon=True)
def invalidate():
    dialogs = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_conflict_metadata_controls")]
    if not dialogs:
        wx.CallLater(20, invalidate)
        return
    controls = dialogs[0]._wx_conflict_metadata_controls
    assert controls["source"]["path"].GetValue() == item.src
    assert "123 B" in controls["source"]["details"].GetLabel()
    assert "456 B" in controls["target"]["details"].GetLabel()
    live["value"] = False
wx.CallLater(30, invalidate)
worker.start()
pump(lambda: bool(decisions))
assert decisions == ["cancel"]
pump(lambda: not any(hasattr(w, "_wx_conflict_metadata_controls") for w in wx.GetTopLevelWindows()))
assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
parent.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path / "config"))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], cwd=root, env=env,
        capture_output=True, text=True, timeout=35,
    )
    assert result.returncode == 0, result.stdout + result.stderr
