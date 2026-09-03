import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
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
