"""Native wx drag-and-drop adapters for local and remote file panels."""

from __future__ import annotations

import json


REMOTE_PATHS_FORMAT = "application/x-hpc-client-gui-remote-paths"


def _selected_paths(listing, entries, event):
    index = event.GetIndex()
    if index >= 0 and not listing.IsSelected(index):
        listing.Select(index)
    paths = []
    index = listing.GetFirstSelected()
    while index != -1:
        if 0 <= index < len(entries):
            path = getattr(entries[index], "path", None)
            if path:
                paths.append(str(path))
        index = listing.GetNextSelected(index)
    return tuple(paths)


def _remote_paths_object(wx, paths):
    data = wx.CustomDataObject(wx.DataFormat(REMOTE_PATHS_FORMAT))
    payload = json.dumps({"paths": list(paths)}, separators=(",", ":"))
    data.SetData(payload.encode("utf-8"))
    return data


def _decode_remote_paths(payload):
    try:
        value = json.loads(bytes(payload).decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return ()
    paths = value.get("paths") if isinstance(value, dict) else None
    if not isinstance(paths, list):
        return ()
    return tuple(path for path in paths if isinstance(path, str) and path)


def begin_local_file_drag(wx, listing, entries, event):
    paths = _selected_paths(listing, entries, event)
    if not paths:
        return
    data = wx.FileDataObject()
    for path in paths:
        data.AddFile(path)
    source = wx.DropSource(listing)
    source.SetData(data)
    source.DoDragDrop(wx.Drag_CopyOnly)


def begin_remote_file_drag(wx, listing, entries, event):
    paths = _selected_paths(listing, entries, event)
    if not paths:
        return
    source = wx.DropSource(listing)
    source.SetData(_remote_paths_object(wx, paths))
    source.DoDragDrop(wx.Drag_CopyOnly)


def install_remote_file_drop(wx, listing, local_directory, download_remote):
    """Accept remote-path payloads on a local file listing."""

    class RemoteFileDropTarget(wx.DropTarget):
        def __init__(self):
            self.data = wx.CustomDataObject(wx.DataFormat(REMOTE_PATHS_FORMAT))
            super().__init__(self.data)

        def OnData(self, _x, _y, _default_result):
            if not self.GetData():
                return wx.DragNone
            paths = _decode_remote_paths(self.data.GetData())
            destination = local_directory()
            if not paths or not destination:
                return wx.DragNone
            download_remote(paths, str(destination))
            return wx.DragCopy

    target = RemoteFileDropTarget()
    listing.SetDropTarget(target)
    listing._hpc_remote_file_drop_target = target
    return target


def install_local_file_drop(wx, control, remote_directory, upload_local):
    """Accept OS or wx file objects on a remote file panel."""

    class LocalFileDropTarget(wx.FileDropTarget):
        def OnDropFiles(self, _x, _y, filenames):
            paths = tuple(str(path) for path in filenames if path)
            destination = remote_directory()
            if not paths or not destination:
                return False
            upload_local(paths, str(destination))
            return True

    target = LocalFileDropTarget()
    control.SetDropTarget(target)
    control._hpc_local_file_drop_target = target
    return target


__all__ = [
    "REMOTE_PATHS_FORMAT",
    "begin_local_file_drag",
    "begin_remote_file_drag",
    "install_local_file_drop",
    "install_remote_file_drop",
]
