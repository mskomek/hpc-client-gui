from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.core.i18n import load_language
from hpc_gui.wx_transfer_workspace import build_transfers_panel
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


@pytest.mark.gui
@pytest.mark.wx
def test_wx_transfer_events_preserve_user_selected_tab():
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    parent = wx.Frame(None)
    panel = build_transfers_panel(parent)
    notebook = panel._wx_transfer_controls["notebook"]
    item = TransferItem("upload", "local.txt", "/remote/local.txt")
    try:
        for index in range(notebook.GetPageCount()):
            notebook.SetSelection(index)
            panel._wx_transfer_queue("queued", item)
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            assert notebook.GetSelection() == index
            panel._wx_transfer_queue("failed", item)
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            assert notebook.GetSelection() == index
            panel._wx_transfer_queue("queued", item)
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            assert notebook.GetSelection() == index
            panel._wx_transfer_queue("completed", item)
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            assert notebook.GetSelection() == index
        assert [notebook.GetPageText(index) for index in range(3)] == [
            "Queue (0)",
            "Failed (0)",
            "Completed (1)",
        ]
    finally:
        parent.Destroy()
        for window in list(wx.GetTopLevelWindows()):
            if window:
                window.Destroy()
        for _ in range(3):
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
        app.Destroy()


@pytest.mark.gui
@pytest.mark.wx
def test_wx_failed_transfer_can_be_requeued_from_retry_button():
    app = wx.App.Get() or wx.App(False)
    parent = wx.Frame(None)
    panel = build_transfers_panel(parent)
    item = TransferItem("upload", "local.txt", "/remote/local.txt")
    calls = []

    def run_item(_item, _progress):
        calls.append("run")
        if len(calls) == 1:
            raise OSError("temporary failure")

    controller = TransferSessionController([item], run_item)
    panel._wx_transfer_set_controller(controller)
    controller.engine._on_queue = panel._wx_transfer_queue
    try:
        controller.start()
        assert controller.engine.wait(2)
        app.ProcessPendingEvents()
        retry = panel._wx_transfer_controls["retry_failed"]
        assert retry.IsEnabled()
        retry.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, retry.GetId()))
        assert controller.engine.wait(2)
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        assert calls == ["run", "run"]
        assert controller.engine.failed == []
        assert controller.engine.completed == [item]
        assert id(item) not in panel._wx_transfer_state["failed_map"]
        assert id(item) in panel._wx_transfer_state["completed_map"]
    finally:
        parent.Destroy()
        for window in list(wx.GetTopLevelWindows()):
            if window:
                window.Destroy()
        for _ in range(3):
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
        app.Destroy()


@pytest.mark.wx
def test_wx_transfer_parallelism_respects_backend_capability():
    class SerialFiles:
        supports_parallel_transfers = False

        def upload(self, _source, _destination):
            return None

    files = SerialFiles()
    state = {
        "session": {"files": files, "profile": {"transfer_parallelism": 5}},
    }
    controller = _start_file_transfers(
        state,
        None,
        [
            TransferItem("upload", "one.txt", "/one.txt"),
            TransferItem("upload", "two.txt", "/two.txt"),
        ],
        files_backend=files,
    )
    assert controller.engine.parallel_limit == 1
    assert controller.engine.wait(2)
