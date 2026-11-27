from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from hpc_gui.wx_file_dragdrop import (
    REMOTE_PATHS_FORMAT,
    begin_local_file_drag,
    begin_remote_file_drag,
    install_local_file_drop,
    install_remote_file_drop,
)
from hpc_gui.wx_local_files import build_local_files_panel
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import build_remote_files_panel


class _DataObject:
    def __init__(self, _format=None):
        self.value = b""
        self.files = []

    def SetData(self, value):
        self.value = bytes(value)

    def GetData(self):
        return self.value

    def AddFile(self, path):
        self.files.append(path)


class _DropTarget:
    def __init__(self, data=None):
        self.data = data

    def GetData(self):
        return True


class _FileDropTarget:
    pass


class _DropSource:
    def __init__(self, _window):
        self.data = None
        self.result = None

    def SetData(self, data):
        self.data = data

    def DoDragDrop(self, result):
        self.result = result


class _Wx:
    CustomDataObject = _DataObject
    FileDataObject = _DataObject
    DropTarget = _DropTarget
    FileDropTarget = _FileDropTarget
    DropSource = _DropSource
    DataFormat = staticmethod(lambda value: value)
    DragNone = 0
    DragCopy = 1
    Drag_CopyOnly = 1


class _Listing:
    def __init__(self):
        self.selected = {0, 1}
        self.target = None

    def GetFirstSelected(self):
        return min(self.selected) if self.selected else -1

    def GetNextSelected(self, index):
        later = [value for value in self.selected if value > index]
        return min(later) if later else -1

    def IsSelected(self, index):
        return index in self.selected

    def Select(self, index):
        self.selected.add(index)

    def SetDropTarget(self, target):
        self.target = target


class _Control:
    def SetDropTarget(self, target):
        self.target = target


class _Event:
    def __init__(self, index=0):
        self.index = index

    def GetIndex(self):
        return self.index


def test_remote_drop_downloads_to_active_local_directory():
    listing = _Listing()
    calls = []
    active_directory = ["C:/first"]
    target = install_remote_file_drop(
        _Wx, listing, lambda: active_directory[0],
        lambda paths, destination: calls.append((paths, destination)),
    )
    target.data.SetData(b'{"paths":["/remote/a.txt","/remote/b.txt"]}')

    assert target.OnData(0, 0, _Wx.DragCopy) == _Wx.DragCopy
    assert calls == [(("/remote/a.txt", "/remote/b.txt"), "C:/first")]
    active_directory[0] = "C:/second"
    target.data.SetData(b'{"paths":["/remote/c.txt"]}')
    target.OnData(0, 0, _Wx.DragCopy)
    assert calls[-1] == (("/remote/c.txt",), "C:/second")
    assert target is listing.target


def test_local_drop_uploads_files_to_active_remote_directory():
    control = _Control()
    calls = []
    target = install_local_file_drop(
        _Wx, control, lambda: "/remote/current",
        lambda paths, destination: calls.append((paths, destination)),
    )

    assert target.OnDropFiles(0, 0, ["C:/scratch/a.txt", "C:/scratch/b.sh"])
    assert calls == [(("C:/scratch/a.txt", "C:/scratch/b.sh"), "/remote/current")]
    assert control.target is target


def test_local_drag_exports_selected_files_as_file_data(monkeypatch):
    listing = _Listing()
    source = _Wx.DropSource(listing)
    monkeypatch.setattr(_Wx, "DropSource", lambda _window: source)
    entries = [SimpleNamespace(path="C:/a.txt"), SimpleNamespace(path="C:/b.sh")]

    begin_local_file_drag(_Wx, listing, entries, _Event())

    assert source.data.files == ["C:/a.txt", "C:/b.sh"]
    assert source.result == _Wx.Drag_CopyOnly


def test_remote_drag_exports_selected_paths_with_registered_format(monkeypatch):
    listing = _Listing()
    source = _Wx.DropSource(listing)
    monkeypatch.setattr(_Wx, "DropSource", lambda _window: source)
    entries = [SimpleNamespace(path="/remote/a.txt"), SimpleNamespace(path="/remote/b.sh")]

    begin_remote_file_drag(_Wx, listing, entries, _Event())

    assert source.data.value == b'{"paths":["/remote/a.txt","/remote/b.sh"]}'
    assert REMOTE_PATHS_FORMAT == "application/x-hpc-client-gui-remote-paths"
    assert source.result == _Wx.Drag_CopyOnly


@pytest.mark.gui
@pytest.mark.wx
def test_file_panels_install_cross_pane_drop_targets(tmp_path):
    app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    local = build_local_files_panel(
        frame,
        tmp_path,
        download_remote=lambda _paths, _destination: None,
    )
    remote = build_remote_files_panel(
        frame,
        WxRemoteDirectoryModel("/scratch"),
        operation=lambda *_args: None,
    )
    try:
        local_listing = local._wx_local_controls["listing"]
        remote_listing = remote._wx_remote_controls["listing"]
        assert local_listing.GetDropTarget() is not None
        assert remote_listing.GetDropTarget() is not None
        assert remote._wx_remote_tabs[0]["panel"].GetDropTarget() is not None
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()
