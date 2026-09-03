import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.services.file_context_actions import context_selection, visible_actions
from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from hpc_gui.wx_local_files import show_local_files


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _pump(app, predicate):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()
from mock_hpc_files import MockRemoteFilesBackend


def test_file_context_target_stress_has_no_wrong_targets():
    wrong = 0
    for index in range(200):
        path = f"/work/item-{index}"
        clicked = context_selection(path, False, ("/work/other",), (False,))
        if clicked.effective_paths != (path,):
            wrong += 1
    assert wrong == 0


def test_remote_mutation_stress_has_no_lost_operations():
    backend = MockRemoteFilesBackend()
    for index in range(100):
        source = f"/work/item-{index}"
        backend.entries[source] = False
        backend.rename(source, f"/work/renamed-{index}")
        backend.move(f"/work/renamed-{index}", f"/work/moved-{index}")
    assert len([call for call in backend.calls if call[0] == "rename"]) == 100
    assert len([call for call in backend.calls if call[0] == "move"]) == 100
    assert len([name for name in backend.entries if name.startswith("/work/moved-")]) == 100


def test_context_policy_stays_stable_under_rapid_selection():
    for index in range(200):
        selection = context_selection(f"/work/{index}", False, (f"/work/{index}",), (False,))
        assert "edit" in visible_actions(selection, remote=True)


def test_wx_remote_context_target_stress_uses_real_events(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/dir-a": True, "/work/dir-b": True})
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 4)
    wrong_targets = 0
    captured = []

    def capture(menu):
        captured.append({item.GetItemLabelText() for item in menu.GetMenuItems()})

    listing.PopupMenu = capture
    for index in range(200):
        mode = index % 4
        if mode == 0:
            clicked = index % listing.GetItemCount()
            for item_index in range(listing.GetItemCount()):
                listing.Select(item_index, False)
            listing.Select(clicked)
            rect = listing.GetItemRect(clicked)
            position = listing.ClientToScreen(rect.GetPosition() + wx.Point(5, max(1, rect.height // 2)))
        elif mode == 1:
            for item_index in range(listing.GetItemCount()):
                listing.Select(item_index, False)
            listing.Select(0)
            listing.Select(1)
            rect = listing.GetItemRect(1)
            position = listing.ClientToScreen(rect.GetPosition() + wx.Point(5, max(1, rect.height // 2)))
        elif mode == 2:
            rect = listing.GetItemRect(listing.GetItemCount() - 1)
            position = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 5))
        else:
            for item_index in range(listing.GetItemCount()):
                listing.Select(item_index, False)
            listing.Select(0)
            position = wx.DefaultPosition
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(position)
        before = len(captured)
        listing.ProcessEvent(event)
        if len(captured) != before + 1:
            wrong_targets += 1
        if mode == 2 and ("Edit" in captured[-1] or "Rename" in captured[-1]):
            wrong_targets += 1
        if mode == 3 and "Edit" not in captured[-1]:
            wrong_targets += 1
    assert wrong_targets == 0, captured[-4:]
    assert len(captured) == 200


def test_wx_local_mutation_stress_uses_real_actions(wx_app, tmp_path: Path, monkeypatch):
    show_local_files(path=tmp_path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    listing = frame._wx_local_controls["listing"]
    rename_target = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return rename_target["name"]

        def Destroy(self):
            pass

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    for index in range(100):
        original = tmp_path / f"stress-{index}.txt"
        renamed = tmp_path / f"renamed-{index}.txt"
        original.write_text("x", encoding="utf-8")
        frame._wx_local_run_action("refresh")
        row = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == original.name)
        for item_index in range(listing.GetItemCount()):
            listing.Select(item_index, False)
        listing.Select(row)
        rename_target["name"] = renamed.name
        frame._wx_local_run_action("rename")
        _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
        assert renamed.exists() and not original.exists()
        for item_index in range(listing.GetItemCount()):
            listing.Select(item_index, False)
        row = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == renamed.name)
        listing.Select(row)
        frame._wx_local_run_action("delete")
        _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
        assert not renamed.exists()


def test_wx_remote_mutation_stress_uses_real_actions(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1 and not frame._wx_remote_state["busy"])
    rename_target = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return rename_target["name"]

        def Destroy(self):
            pass

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: Dialog())
    for index in range(100):
        source = f"/work/remote-{index}.txt"
        target = f"/work/renamed-{index}.txt"
        backend.entries[source] = False
        frame._wx_remote_run_action("refresh", ())
        _pump(wx_app, lambda: any(listing.GetItemText(row) == f"remote-{index}.txt" for row in range(listing.GetItemCount())))
        row = next(row for row in range(listing.GetItemCount()) if listing.GetItemText(row) == f"remote-{index}.txt")
        for item_index in range(listing.GetItemCount()):
            listing.Select(item_index, False)
        listing.Select(row)
        rename_target["name"] = f"renamed-{index}.txt"
        frame._wx_remote_run_action("rename", (source,), "/work")
        _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
        assert target in backend.entries and source not in backend.entries
