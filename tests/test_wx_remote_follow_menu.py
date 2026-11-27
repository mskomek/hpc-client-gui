from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from mock_hpc_files import MockRemoteFilesBackend
from hpc_gui.services.output_channel_resolver import TrackedOutput
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files


class _Item:
    def __init__(self, item_id, label):
        self.item_id = item_id
        self.label = label

    def GetId(self):
        return self.item_id


class _Menu:
    instances = []
    next_id = 1

    def __init__(self):
        self.items = []
        self.handlers = {}
        _Menu.instances.append(self)

    def Append(self, _id, label):
        item = _Item(_Menu.next_id, label)
        _Menu.next_id += 1
        self.items.append(item)
        return item

    def AppendSeparator(self):
        self.items.append(None)

    def AppendSubMenu(self, menu, label):
        item = _Item(_Menu.next_id, label)
        _Menu.next_id += 1
        self.items.append((item, menu))
        return item

    def Bind(self, _event, callback, id):
        self.handlers[id] = callback

    def Destroy(self):
        pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("new_tab", ("/work/a.txt", "new_tab")),
        ("new_window", ("/work/a.txt", "new_window")),
        ("existing", ("/work/a.txt", "existing", "follower-1")),
    ],
)
def test_wx_remote_follow_menu_routes_selected_file(wx_app, choice, expected, monkeypatch):
    _Menu.instances.clear()
    _Menu.next_id = 1
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = next(
        window for window in wx.GetTopLevelWindows()
        if hasattr(window, "_wx_remote_controls")
    )
    calls = []
    panel = frame._wx_remote_controls["notebook"].GetParent()
    panel._follow_callback = lambda *args: calls.append(args)
    frame._wx_jobs_controls = {"output_channels": {}}
    frame._wx_jobs_state = {
        "tracked_outputs": [TrackedOutput(
            tracking_id="follower-1",
            channel_id=None,
            label="Output 1",
            path="/work/previous.out",
            origin="manual",
            job_id="123",
        )]
    }
    chosen = {"value": choice}

    def popup(_menu):
        menu = _Menu.instances[0]
        if chosen["value"] == "existing":
            callback = menu.handlers[max(menu.handlers)]
        else:
            callback = menu.handlers[1 if chosen["value"] == "new_tab" else 2]
        callback(None)

    monkeypatch.setattr(wx, "Menu", _Menu)
    monkeypatch.setattr(panel, "PopupMenu", popup)
    try:
        frame._wx_remote_run_action("follow_track", ("/work/a.txt",), "/work")
        assert calls == [expected]
    finally:
        frame.Close()
        wx.Yield()
