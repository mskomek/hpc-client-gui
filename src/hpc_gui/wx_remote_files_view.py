"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock, Thread
from pathlib import PurePosixPath

from hpc_gui.core.i18n import t
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


def show_remote_files(parent=None, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxRemoteDirectoryModel()
    frame = wx.Frame(parent, title=t("tabs.ftp"), size=(920, 620))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    path = wx.TextCtrl(panel, value=model.current_path, style=wx.TE_PROCESS_ENTER)
    listing = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_MULTIPLE)
    listing.InsertColumn(0, t("dirs.col_name"))
    listing.InsertColumn(1, t("dirs.col_size"))
    refresh = wx.Button(panel, label=t("dirs.refresh"))
    root.Add(path, 0, wx.EXPAND | wx.ALL, 6)
    root.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    root.Add(refresh, 0, wx.ALIGN_RIGHT | wx.ALL, 6)
    panel.SetSizer(root)
    state = {"entries": [], "busy": False, "closed": False}
    lock = Lock()

    def render(entries):
        state["entries"] = list(entries)
        listing.DeleteAllItems()
        for entry in state["entries"]:
            index = listing.InsertItem(listing.GetItemCount(), PurePosixPath(entry.path).name or entry.path)
            listing.SetItem(index, 1, str(entry.size))

    def load(_event=None):
        if not loader:
            return
        with lock:
            if state["closed"] or state["busy"]:
                return
            state["busy"] = True

        def done(entries, error):
            with lock:
                state["busy"] = False
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                render(entries)

        def worker():
            try:
                wx.CallAfter(done, model.list_entries(loader, force=True), None)
            except Exception as error:
                wx.CallAfter(done, (), error)

        Thread(target=worker, daemon=True).start()

    def activate(event):
        entry = state["entries"][event.GetIndex()]
        if entry.is_dir:
            model.navigate(entry.path)
            path.SetValue(model.current_path)
            load()

    def context(event):
        index, _flags = listing.HitTest(event.GetPosition())
        if index < 0:
            return
        if not listing.IsSelected(index):
            listing.ClearSelections()
            listing.Select(index)
        selected = tuple(entry.path for idx, entry in enumerate(state["entries"]) if listing.IsSelected(idx))
        menu = wx.Menu()
        for action in ("copy", "move", "rename", "delete"):
            item = menu.Append(wx.ID_ANY, t(f"dirs.{action}"))
            listing.Bind(wx.EVT_MENU, lambda _event, action=action: operation(action, selected) if operation else None, item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def close(_event):
        state["closed"] = True
        frame.Destroy()

    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
    listing.Bind(wx.EVT_CONTEXT_MENU, context)
    refresh.Bind(wx.EVT_BUTTON, load)
    path.Bind(wx.EVT_TEXT_ENTER, load)
    frame.Bind(wx.EVT_CLOSE, close)
    load()
    frame.Show()
    return wx.ID_OK


__all__ = ["show_remote_files"]
