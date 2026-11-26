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
import faulthandler
import traceback
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch
import wx
from hpc_gui.core.i18n import load_language, t
from hpc_gui.config.storage import get_upload_preflight_confirmation_enabled, set_upload_preflight_confirmation_enabled
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_conflict_policy import ConflictFileInfo
from hpc_gui.wx_shell_upload import prepare_upload
from hpc_gui.wx_upload_preflight import create_upload_preflight
from hpc_gui.wx_conflict_bridge import request_conflict_decision

faulthandler.dump_traceback_later(15, repeat=True)
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
errors = []
def capture_error(*args, **kwargs):
    errors.append(str(args))
    print("unexpected message box", args, flush=True)
    return wx.ID_OK
wx.MessageBox = capture_error

# Exact three-row native dialog parity, without starting a worker.
small_plan = [
    TransferItem("mkdir_remote", "", "/remote/folder"),
    TransferItem("upload", str(source / "file-000.txt"), "/remote/folder/a.txt"),
    TransferItem("upload", str(source / "file-001.txt"), "/remote/folder/b.txt"),
]
small = create_upload_preflight(parent, small_plan, 2)
try:
    c = small._wx_upload_preflight_controls
    assert c["listing"].GetItemCount() == 3
    for value in ("2 files", "1 folder", "3 total steps", "2 transfers"):
        assert value in c["summary"].GetLabel()
    assert c["listing"].GetItemText(1, 1) == small_plan[1].src
    assert c["listing"].GetItemText(1, 2) == small_plan[1].dst
    assert c["start"].GetLabel() == "Start transfer"
    assert c["dont_ask"].GetLabel() == "Don't ask again"
    assert not c["dont_ask"].GetValue()
finally:
    small.Destroy()
    app.ProcessPendingEvents()

def pump(predicate, timeout=5):
    if predicate():
        return
    loop = wx.GUIEventLoop()
    deadline = time.monotonic() + timeout
    timer = None

    def poll():
        nonlocal timer
        # The conflict dialog owns a nested modal loop until its cancellation
        # timer runs. Never Exit the suspended outer GUIEventLoop.
        if wx.EventLoopBase.GetActive() is not loop:
            timer = wx.CallLater(20, poll)
            return
        if predicate():
            loop.ScheduleExit(0)
        elif time.monotonic() >= deadline:
            loop.ScheduleExit(1)
        else:
            timer = wx.CallLater(20, poll)

    with wx.EventLoopActivator(loop):
        timer = wx.CallLater(20, poll)
        code = loop.Run()
    if timer is not None:
        timer.Stop()
    assert code == 0 and predicate(), "native lifecycle timed out"


def run_preflight(action):
    print("preflight", action, flush=True)
    inspected = []
    deadline = time.monotonic() + 5

    def answer():
        dialogs = [w for w in wx.GetTopLevelWindows()
                   if hasattr(w, "_wx_upload_preflight_controls") and w.IsModal()]
        if not dialogs:
            if time.monotonic() < deadline:
                wx.CallLater(20, answer)
            else:
                errors.append("preflight dialog not observed")
            return
        dialog = dialogs[0]
        code = wx.ID_CANCEL
        try:
            controls = dialog._wx_upload_preflight_controls
            assert not started
            assert controls["listing"].GetItemCount() == 201
            assert "250 files" in controls["summary"].GetLabel()
            assert "252 total steps" in controls["summary"].GetLabel()
            assert controls["listing"].GetItemText(2, 1) == str(source / "file-000.txt")
            assert controls["listing"].GetItemText(2, 2) == "/remote/case/file-000.txt"
            assert not controls["dont_ask"].GetValue()
            assert "2 folder" in controls["summary"].GetLabel()
            assert "1 transfers" in controls["summary"].GetLabel()
            assert "Remaining: 52" in controls["listing"].GetItemText(200)
            controls["dont_ask"].SetValue(True)
            inspected.append(True)
            if action == "stale":
                state["generation"] += 1
            code = wx.ID_CANCEL if action == "cancel" else wx.ID_OK
        except Exception:
            errors.append(traceback.format_exc())
        finally:
            dialog.EndModal(code)
    wx.CallLater(30, answer)
    completed = []
    def prepare():
        try:
            prepare_upload(state, lifecycle, parent, session, files, [source], "/remote",
                           lambda *args, **kwargs: started.append(args[2]), generation=state["generation"])
        finally:
            completed.append(True)
    # Exercise the same posted GUI call and active event loop as production.
    worker = Thread(target=prepare, daemon=True)
    worker.start()
    pump(lambda: bool(inspected or errors))
    pump(lambda: not any(hasattr(w, "_wx_upload_preflight_controls") and w.IsModal()
                         for w in wx.GetTopLevelWindows()))
    assert completed and inspected and not errors, errors
    app.ProcessPendingEvents()


run_preflight("cancel")
assert not started and get_upload_preflight_confirmation_enabled()
run_preflight("stale")
assert not started and get_upload_preflight_confirmation_enabled()
run_preflight("accept")
assert len(started[0]) == 252
assert not get_upload_preflight_confirmation_enabled()
with patch("hpc_gui.wx_upload_preflight.create_upload_preflight", side_effect=AssertionError("disabled preflight created a dialog")):
    prepare_upload(state, lifecycle, parent, session, files, [source], "/remote",
                   lambda *args, **kwargs: started.append(args[2]), generation=state["generation"])
assert len(started) == 2 and not errors
set_upload_preflight_confirmation_enabled(True)

print("preflight complete; conflict start", flush=True)
live = {"value": True}
decisions = []
item = TransferItem("upload", str(source / "file-000.txt"), "/remote/a")
metadata = (ConflictFileInfo(item.src, 123, 1700000000), ConflictFileInfo(item.dst, 456, None))
worker = Thread(target=lambda: decisions.append(
    request_conflict_decision(parent, files, item, lambda: live["value"], metadata)), daemon=True)
deadline = time.monotonic() + 5
def invalidate():
    dialogs = [w for w in wx.GetTopLevelWindows()
               if hasattr(w, "_wx_conflict_metadata_controls") and w.IsModal()]
    if not dialogs:
        if time.monotonic() < deadline:
            wx.CallLater(20, invalidate)
        else:
            errors.append("conflict dialog not observed")
            live["value"] = False
        return
    try:
        controls = dialogs[0]._wx_conflict_metadata_controls
        assert controls["source"]["path"].GetValue() == item.src
        assert "123 B" in controls["source"]["details"].GetLabel()
        assert "456 B" in controls["target"]["details"].GetLabel()
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        live["value"] = False
wx.CallLater(30, invalidate)
worker.start()
pump(lambda: bool(decisions) and not any(
    hasattr(w, "_wx_conflict_metadata_controls") and w.IsModal()
    for w in wx.GetTopLevelWindows()))
assert decisions == ["cancel"] and not errors, errors
pump(lambda: not any(hasattr(w, "_wx_conflict_metadata_controls") for w in wx.GetTopLevelWindows()))

# Exercise actual native button bindings and all scope controls, not a
# replacement dialog or a synthetic controller decision.
files.resume_upload = lambda *args: None
live["value"] = True
for action in ("skip", "overwrite", "overwrite_if_newer", "overwrite_if_size_differs",
               "overwrite_if_size_differs_or_newer", "resume"):
    decisions.clear()
    deadline = time.monotonic() + 5

    def choose():
        dialogs = [w for w in wx.GetTopLevelWindows()
                   if hasattr(w, "_wx_conflict_controls") and w.IsModal()]
        if not dialogs:
            if time.monotonic() < deadline:
                wx.CallLater(20, choose)
            else:
                errors.append("native conflict choices not observed")
                live["value"] = False
            return
        dialog = dialogs[0]
        try:
            controls = dialog._wx_conflict_controls
            assert set(controls) == {
                "overwrite", "overwrite_if_newer", "overwrite_if_size_differs",
                "overwrite_if_size_differs_or_newer", "resume", "rename", "skip", "cancel",
            }
            assert all(control is not None for control in controls.values())
            assert dialog.GetTitle() == t("transfer.conflict_title")
            for control in (dialog._wx_conflict_apply_all, dialog._wx_conflict_always_use,
                            dialog._wx_conflict_downloads_only):
                assert not control.GetValue()
                control.SetValue(True)
            button = controls[action]
            assert button.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
        except Exception:
            errors.append(traceback.format_exc())
            if dialog.IsModal():
                dialog.EndModal(wx.ID_CANCEL)

    worker = Thread(target=lambda: decisions.append(
        request_conflict_decision(parent, files, item, lambda: live["value"], metadata)), daemon=True)
    wx.CallLater(30, choose)
    worker.start()
    pump(lambda: bool(decisions))
    assert not errors, errors
    assert decisions == [{"value": action, "apply_all": True,
                          "always_use": True, "downloads_only": True}]
    pump(lambda: not any(hasattr(w, "_wx_conflict_metadata_controls") for w in wx.GetTopLevelWindows()))

assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
parent.Destroy()
app.ProcessPendingEvents()
faulthandler.cancel_dump_traceback_later()
print("native preflight/conflict PASS", flush=True)
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path / "config"))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    try:
        result = subprocess.run(
            [sys.executable, "-u", "-c", script, str(tmp_path)], cwd=root, env=env,
            capture_output=True, text=True, timeout=35,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"native timeout: stdout={exc.stdout!r}; stderr={exc.stderr!r}")
    assert result.returncode == 0, result.stdout + result.stderr
