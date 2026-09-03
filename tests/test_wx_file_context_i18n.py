import time

import pytest
from pathlib import Path

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from hpc_gui.wx_local_files import show_local_files
from mock_hpc_files import MockRemoteFilesBackend


def _pump(app, predicate):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App(False)
    yield app
    load_language("en")
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_remote_context_menu_reopens_with_turkish_labels(wx_app):
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() > 0)
    listing.Select(0)
    labels = []
    listing.PopupMenu = lambda menu: labels.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    rect = listing.GetItemRect(0)
    position = listing.ClientToScreen(rect.GetPosition() + wx.Point(5, max(1, rect.height // 2)))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)

    listing.ProcessEvent(event)
    assert "Copy" in labels and "Move" in labels and "Paste" in labels
    labels.clear()
    load_language("tr")
    listing.ProcessEvent(event)
    assert "Kopyala" in labels and "Taşı" in labels and "Yapıştır" in labels
    assert "Copy" not in labels and "Move" not in labels


def test_wx_local_context_menu_reopens_with_turkish_labels(wx_app, tmp_path: Path):
    (tmp_path / "job.slurm").write_text("#!/bin/sh", encoding="utf-8")
    show_local_files(path=tmp_path, upload=lambda _paths: None)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    listing = frame._wx_local_controls["listing"]
    listing.Select(0)
    labels = []
    listing.PopupMenu = lambda menu: labels.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    _pump(wx_app, lambda: listing.GetItemCount() > 0)
    rect = listing.GetItemRect(0)
    position = listing.ClientToScreen(rect.GetPosition() + wx.Point(5, max(1, rect.height // 2)))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)

    listing.ProcessEvent(event)
    assert "Open" in labels and "Open with..." in labels and "Rename" in labels
    labels.clear()
    load_language("tr")
    listing.ProcessEvent(event)
    assert "Aç" in labels and "Birlikte aç..." in labels and "Yeniden adlandır" in labels
    assert "Open" not in labels and "Rename" not in labels


def _tab_close_labels(app, frame, notebook):
    """Open the notebook tab context menu and return its item labels."""
    captured = []
    original = notebook.PopupMenu
    notebook.PopupMenu = lambda menu: captured.append(
        [item.GetItemLabelText() for item in menu.GetMenuItems()]
    )
    try:
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, notebook.GetId())
        event.SetPosition(notebook.ClientToScreen(wx.Point(5, 5)))
        notebook.ProcessEvent(event)
    finally:
        notebook.PopupMenu = original
    app.ProcessPendingEvents()
    return captured[-1] if captured else []


def test_wx_remote_tab_close_label_follows_runtime_language(wx_app):
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    notebook = frame._wx_remote_notebook
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)

    assert "Close" in _tab_close_labels(wx_app, frame, notebook)
    load_language("tr")
    assert "Kapat" in _tab_close_labels(wx_app, frame, notebook)
    load_language("en")
    assert "Close" in _tab_close_labels(wx_app, frame, notebook)


def test_wx_local_tab_close_label_follows_runtime_language(wx_app, tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    show_local_files(path=tmp_path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    notebook = frame._wx_local_notebook
    _pump(wx_app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 1)

    assert "Close" in _tab_close_labels(wx_app, frame, notebook)
    load_language("tr")
    assert "Kapat" in _tab_close_labels(wx_app, frame, notebook)
    load_language("en")
    assert "Close" in _tab_close_labels(wx_app, frame, notebook)


def _conflict_labels(parent, files, item):
    from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

    dialog = create_transfer_conflict_dialog(parent, files, item)
    labels = {dialog.GetTitle()}
    for child in dialog.GetChildren():
        for control in child.GetChildren():
            if isinstance(control, wx.Button):
                labels.add(control.GetLabel())
    dialog.Destroy()
    return labels


def test_wx_transfer_conflict_and_progress_follow_runtime_language(wx_app):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_transfer_workspace import create_transfer_progress

    class _Files:
        def resume_upload(self, source, destination):
            return None

    parent = wx.Frame(None)
    item = TransferItem("upload", "a.txt", "/work/a.txt")

    english = _conflict_labels(parent, _Files(), item)
    assert {"Target file already exists", "Overwrite", "Resume"} <= english

    load_language("tr")
    turkish = _conflict_labels(parent, _Files(), item)
    assert {"Hedef dosya zaten var", "Üzerine yaz", "Devam ettir"} <= turkish

    window = create_transfer_progress(parent)
    assert window.GetTitle() == "Aktarımlar"
    window.Destroy()

    load_language("en")
    window = create_transfer_progress(parent)
    assert window.GetTitle() == "Transfers"
    window.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()
