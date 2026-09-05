"""Headless transfer workspace joining local and remote wx browser models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


@dataclass(frozen=True)
class StorageState:
    name: str
    available: bool
    reason: str = ""


def _supports_resume(files, item) -> bool:
    if files is None or item is None:
        return False
    return callable(getattr(files, f"resume_{item.op}", None))


def create_transfer_conflict_dialog(parent, files, item):
    """Create a purpose-built native wx conflict dialog."""
    try:
        import wx
    except ImportError:
        return None
    resume_supported = _supports_resume(files, item) if files is not None else False
    # Use dedicated dialog instead of generic MessageBox
    title = t("transfer.conflict_title")
    message = t("transfer.conflict_message").format(path=item.dst)
    dlg = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    msg = wx.StaticText(panel, label=message)
    msg.Wrap(460)
    sizer.Add(msg, 0, wx.ALL | wx.EXPAND, 12)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    # Buttons: Overwrite, Skip, Rename, Cancel, optionally Resume
    overwrite = wx.Button(panel, label=t("dirs.conflict_overwrite") if t("dirs.conflict_overwrite") != "[dirs.conflict_overwrite]" else "Overwrite")
    skip = wx.Button(panel, label=t("dirs.conflict_skip") if t("dirs.conflict_skip") != "[dirs.conflict_skip]" else "Skip")
    rename = wx.Button(panel, label=t("dirs.conflict_rename") if t("dirs.conflict_rename") != "[dirs.conflict_rename]" else "Rename")
    cancel = wx.Button(panel, label=t("common.cancel") if t("common.cancel") != "[common.cancel]" else "Cancel")
    resume_btn = None
    if resume_supported:
        resume_btn = wx.Button(panel, label=t("transfer.conflict_resume") if t("transfer.conflict_resume") != "[transfer.conflict_resume]" else "Resume")
    # order: Overwrite, Resume?, Skip, Rename, Cancel
    btn_sizer.Add(overwrite, 0, wx.ALL, 4)
    if resume_btn:
        btn_sizer.Add(resume_btn, 0, wx.ALL, 4)
    btn_sizer.Add(skip, 0, wx.ALL, 4)
    btn_sizer.Add(rename, 0, wx.ALL, 4)
    btn_sizer.Add(cancel, 0, wx.ALL, 4)
    sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizerAndFit(dlg_sizer)

    result = {"value": "cancel", "rename_target": None}

    def on_overwrite(_event):
        result["value"] = "overwrite"
        dlg.EndModal(wx.ID_OK)

    def on_skip(_event):
        result["value"] = "skip"
        dlg.EndModal(wx.ID_OK)

    def on_cancel(_event):
        result["value"] = "cancel"
        dlg.EndModal(wx.ID_CANCEL)

    def on_resume(_event):
        result["value"] = "resume"
        dlg.EndModal(wx.ID_OK)

    def on_rename(_event):
        # prompt for new name
        target_path = PurePosixPath(item.dst)
        parent_dir = str(target_path.parent) if str(target_path.parent) not in ("", ".") else "/"
        current_name = target_path.name
        while True:
            name_dlg = wx.TextEntryDialog(dlg, t("dirs.rename_label") if t("dirs.rename_label") != "[dirs.rename_label]" else "New name:", t("dirs.rename_title") if t("dirs.rename_title") != "[dirs.rename_title]" else "Rename", current_name)
            try:
                if name_dlg.ShowModal() != wx.ID_OK:
                    result["value"] = "cancel"
                    dlg.EndModal(wx.ID_CANCEL)
                    return
                new_name = name_dlg.GetValue().strip()
                # validation
                if not new_name or new_name in {".", ".."} or "/" in new_name or "\\" in new_name or PurePosixPath(new_name).name != new_name:
                    wx.MessageBox(t("dirs.rename_invalid") if t("dirs.rename_invalid") != "[dirs.rename_invalid]" else "Enter a valid file name without path separators.", t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    continue
                candidate = str(PurePosixPath(parent_dir) / new_name)
                # check existing destination
                exists = False
                try:
                    exists = bool(getattr(files, "exists", lambda _p: False)(candidate))
                except Exception:
                    exists = False
                if exists:
                    wx.MessageBox(t("dirs.new_item_exists").format(path=candidate) if t("dirs.new_item_exists") != "[dirs.new_item_exists]" else f"Exists: {candidate}", t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    continue
                # valid
                result["value"] = ("rename", candidate)
                dlg.EndModal(wx.ID_OK)
                return
            finally:
                name_dlg.Destroy()

    overwrite.Bind(wx.EVT_BUTTON, on_overwrite)
    skip.Bind(wx.EVT_BUTTON, on_skip)
    cancel.Bind(wx.EVT_BUTTON, on_cancel)
    rename.Bind(wx.EVT_BUTTON, on_rename)
    if resume_btn:
        resume_btn.Bind(wx.EVT_BUTTON, on_resume)
    # expose for tests
    dlg._wx_conflict_controls = {"overwrite": overwrite, "skip": skip, "rename": rename, "cancel": cancel, "resume": resume_btn}
    dlg._wx_conflict_result = result
    dlg._wx_conflict_resume_supported = resume_supported
    return dlg


def _build_transfers(parent, controller=None, embedded=False):
    """Shared builder for detached and embedded transfer panels."""
    try:
        import wx
    except ImportError:
        return None
    from hpc_gui.wx_host import make_host

    if embedded:
        host, finish = make_host(parent, title=t("transfer.ftp_activity_title"), size=(520, 260), embedded=True)
        panel = wx.Panel(host)
        # status line
        status = wx.StaticText(panel, label=t("transfer.no_active_transfer"))
        # notebook with three pages
        notebook = wx.Notebook(panel)
        # helper to create ListCtrl with required columns
        def _make_list():
            lst = wx.ListCtrl(notebook, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
            cols = [
                (t("transfer.col_local"), 170),
                (t("transfer.col_direction"), 80),
                (t("transfer.col_remote"), 170),
                (t("transfer.col_size"), 80),
                (t("transfer.col_progress"), 110),
                (t("transfer.col_priority"), 80),
                (t("transfer.col_status"), 100),
            ]
            for idx, (label, width) in enumerate(cols):
                lst.InsertColumn(idx, label, width=width)
            return lst

        queue_list = _make_list()
        failed_list = _make_list()
        completed_list = _make_list()
        notebook.AddPage(queue_list, t("transfer.queue_tab"))
        notebook.AddPage(failed_list, t("transfer.failed_tab"))
        notebook.AddPage(completed_list, t("transfer.completed_tab"))
        # button row
        btn_stop = wx.Button(panel, label=t("transfer.stop"))
        btn_cancel = wx.Button(panel, label=t("transfer.cancel"))
        btn_clear = wx.Button(panel, label=t("transfer.clear_pending"))
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(btn_stop, 0, wx.ALL, 4)
        btn_sizer.Add(btn_cancel, 0, wx.ALL, 4)
        btn_sizer.Add(btn_clear, 0, wx.ALL, 4)
        btn_sizer.AddStretchSpacer(1)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(status, 0, wx.ALL | wx.EXPAND, 6)
        layout.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        layout.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        panel.SetSizer(layout)
        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}}
        controls = {
            "status": status,
            "notebook": notebook,
            "queue": queue_list,
            "failed": failed_list,
            "completed": completed_list,
            "stop": btn_stop,
            "cancel": btn_cancel,
            "clear_pending": btn_clear,
        }
        # keep host-level sizer so embedded panel expands correctly when placed in splitter
        host_sizer = wx.BoxSizer(wx.VERTICAL)
        host_sizer.Add(panel, 1, wx.EXPAND)
        host.SetSizer(host_sizer)
    else:
        host, finish = make_host(parent, title=t("transfer.ftp_activity_title"), size=(520, 150), embedded=False)
        panel = wx.Panel(host)
        title = wx.StaticText(panel, label=t("transfer.ftp_activity_title"))
        detail = wx.StaticText(panel, label=t("transfer.no_active_transfer"))
        gauge = wx.Gauge(panel, range=1)
        cancel = wx.Button(panel, label=t("transfer.cancel"))
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(title, 0, wx.ALL | wx.EXPAND, 8)
        layout.Add(detail, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        layout.Add(gauge, 0, wx.ALL | wx.EXPAND, 8)
        layout.Add(cancel, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(layout)
        # host sizer for frame
        host_sizer = wx.BoxSizer(wx.VERTICAL)
        host_sizer.Add(panel, 1, wx.EXPAND)
        host.SetSizer(host_sizer)
        host.Layout()
        state = {"closed": False, "controller": controller}
        controls = {"title": title, "detail": detail, "gauge": gauge, "cancel": cancel}
        # alias for shared code expectations
        status = detail

    # --- common helpers ---
    def post(callback, *args):
        if state["closed"]:
            return
        try:
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def _has_cancel(ctrl):
        if ctrl is None:
            return False
        if callable(getattr(ctrl, "cancel_all", None)) or callable(getattr(ctrl, "cancel", None)):
            return True
        eng = getattr(ctrl, "engine", None)
        if eng and (callable(getattr(eng, "cancel_all", None)) or callable(getattr(eng, "cancel", None))):
            return True
        return False

    def _has_clear(ctrl):
        if ctrl is None:
            return False
        if callable(getattr(ctrl, "clear_pending", None)):
            return True
        eng = getattr(ctrl, "engine", None)
        if eng and callable(getattr(eng, "clear_pending", None)):
            return True
        return False

    def _is_safe():
        if state["closed"]:
            return False
        try:
            if not host or not wx.Window.FindWindowById(host.GetId()):
                return False
        except Exception:
            return False
        try:
            # check primary control
            primary = status if embedded else controls.get("detail")
            if primary and not wx.Window.FindWindowById(primary.GetId()):
                return False
        except Exception:
            return False
        return True

    def _update_button_state():
        if not _is_safe():
            return
        ctrl = state["controller"]
        try:
            if embedded:
                has_cancel = _has_cancel(ctrl)
                has_clear = _has_clear(ctrl)
                controls["stop"].Enable(has_cancel)
                controls["cancel"].Enable(has_cancel)
                controls["clear_pending"].Enable(has_clear)
            else:
                # detached has single cancel button: enabled when controller present and not closed
                # keep enabled if controller exists; disable on finish
                if ctrl is None:
                    controls["cancel"].Disable()
                else:
                    # enabled if cancel available
                    if _has_cancel(ctrl):
                        controls["cancel"].Enable(True)
                    else:
                        controls["cancel"].Disable()
        except RuntimeError:
            pass

    def set_controller(value):
        state["controller"] = value
        # UI updates must run on main thread
        def _do_set():
            _update_button_state()
            if embedded and value is not None:
                try:
                    eng = getattr(value, "engine", None)
                    pending = []
                    if eng is not None and hasattr(eng, "pending"):
                        try:
                            pending = list(eng.pending)
                        except Exception:
                            pending = []
                    elif hasattr(value, "pending"):
                        try:
                            pending = list(value.pending)
                        except Exception:
                            pending = []
                    for it in pending:
                        iid = id(it)
                        if iid not in state["queue_map"]:
                            state["queue_map"][iid] = it
                            found = False
                            for idx in range(queue_list.GetItemCount()):
                                try:
                                    if queue_list.GetItemData(idx) == iid:
                                        found = True
                                        break
                                except Exception:
                                    continue
                            if not found:
                                try:
                                    queue_list.InsertItem(queue_list.GetItemCount(), str(getattr(it, "src", "")))
                                    row = queue_list.GetItemCount() - 1
                                    queue_list.SetItem(row, 1, str(getattr(it, "dst", "")))
                                    queue_list.SetItem(row, 2, "Queued")
                                    queue_list.SetItem(row, 3, "")
                                    queue_list.SetItem(row, 4, str(getattr(it, "priority", "Normal")))
                                    queue_list.SetItemData(row, iid)
                                except RuntimeError:
                                    pass
                except Exception:
                    pass

        # Use post to ensure main thread execution if not on main thread
        try:
            if wx.IsMainThread():
                _do_set()
            else:
                post(_do_set)
                # fallback if post skipped due to closed
                try:
                    wx.CallAfter(_do_set)
                except Exception:
                    pass
        except Exception:
            try:
                post(_do_set)
            except Exception:
                pass

    # --- embedded specific helpers ---
    def _find_row(lst, iid):
        for idx in range(lst.GetItemCount()):
            try:
                if lst.GetItemData(idx) == iid:
                    return idx
            except Exception:
                continue
        return -1

    def _add_row(lst, item, status_text, progress_text):
        # Columns mirror Qt's transfer list: local, direction, remote, size,
        # progress, priority, status.
        op = str(getattr(item, "op", "") or "")
        local, remote = str(getattr(item, "src", "")), str(getattr(item, "dst", ""))
        if op == "download":
            local, remote = remote, local
        idx = lst.GetItemCount()
        lst.InsertItem(idx, local)
        lst.SetItem(idx, 1, op)
        lst.SetItem(idx, 2, remote)
        lst.SetItem(idx, 3, str(getattr(item, "size", "") or ""))
        lst.SetItem(idx, 4, progress_text)
        lst.SetItem(idx, 5, str(getattr(item, "priority", "") or ""))
        lst.SetItem(idx, 6, status_text)
        try:
            lst.SetItemData(idx, id(item))
        except Exception:
            pass
        return idx

    # --- update callbacks ---
    if embedded:
        def update_queue(event, item):
            if not _is_safe():
                return
            try:
                iid = id(item)
                if event in ("queued", "started"):
                    try:
                        status.SetLabel(t("transfer.active_item").format(item=item.label()))
                    except Exception:
                        status.SetLabel(t("transfer.no_active_transfer"))
                    if iid not in state["queue_map"]:
                        state["queue_map"][iid] = item
                        _add_row(queue_list, item, "Queued", "")
                elif event == "completed":
                    try:
                        status.SetLabel(t("transfer.completed_tab"))
                    except Exception:
                        pass
                    state["queue_map"].pop(iid, None)
                    row = _find_row(queue_list, iid)
                    if row != -1:
                        try:
                            queue_list.DeleteItem(row)
                        except Exception:
                            pass
                    if iid not in state["completed_map"]:
                        state["completed_map"][iid] = item
                        _add_row(completed_list, item, "Successful", "")
                    try:
                        notebook.SetSelection(2)
                    except Exception:
                        pass
                elif event == "failed":
                    try:
                        status.SetLabel(t("transfer.errors_tab"))
                    except Exception:
                        pass
                    state["queue_map"].pop(iid, None)
                    row = _find_row(queue_list, iid)
                    if row != -1:
                        try:
                            queue_list.DeleteItem(row)
                        except Exception:
                            pass
                    if iid not in state["failed_map"]:
                        state["failed_map"][iid] = item
                        _add_row(failed_list, item, "Failed", "")
                    try:
                        notebook.SetSelection(1)
                    except Exception:
                        pass
                _update_button_state()
            except RuntimeError:
                return

        def update_progress(item, done, total):
            if not _is_safe():
                return
            try:
                iid = id(item)
                row = _find_row(queue_list, iid)
                try:
                    label = t("transfer.progress_detail").format(item=item.label(), done=done, total=total, speed="", eta="")
                except Exception:
                    label = f"{done}/{total}"
                if row != -1:
                    try:
                        queue_list.SetItem(row, 3, label)
                    except RuntimeError:
                        pass
                try:
                    status.SetLabel(label)
                except RuntimeError:
                    pass
            except RuntimeError:
                return

        def finish():
            if not _is_safe():
                return
            try:
                ctrl = state["controller"]
                if ctrl and getattr(ctrl, "engine", None) and getattr(ctrl.engine, "failed", None):
                    try:
                        last = ctrl.engine.failed[-1][1] if ctrl.engine.failed else ""
                    except Exception:
                        last = ""
                    if last == "cancelled":
                        status.SetLabel(t("transfer.cancelled"))
                    else:
                        status.SetLabel(t("transfer.errors_tab"))
                elif ctrl:
                    status.SetLabel(t("transfer.completed_tab"))
                try:
                    controls["stop"].Disable()
                    controls["cancel"].Disable()
                except Exception:
                    pass
            except RuntimeError:
                return

        def finish_error(message):
            if not _is_safe():
                return
            try:
                status.SetLabel(t("transfer.errors_tab"))
                try:
                    controls["stop"].Disable()
                    controls["cancel"].Disable()
                except Exception:
                    pass
            except RuntimeError:
                return

        def _do_cancel(_event=None):
            ctrl = state["controller"]
            if not ctrl:
                return
            called = False
            for target in (ctrl, getattr(ctrl, "engine", None)):
                if target is None:
                    continue
                for name in ("cancel_all", "cancel"):
                    m = getattr(target, name, None)
                    if callable(m):
                        try:
                            m()
                        except Exception:
                            pass
                        called = True
                        break
                if called:
                    break
            if _is_safe():
                try:
                    status.SetLabel(t("transfer.cancelled"))
                    controls["stop"].Disable()
                    controls["cancel"].Disable()
                except RuntimeError:
                    pass

        def _do_clear_pending(_event=None):
            # call controller method if exists
            ctrl = state["controller"]
            for target in (ctrl, getattr(ctrl, "engine", None)):
                if target is None:
                    continue
                m = getattr(target, "clear_pending", None)
                if callable(m):
                    try:
                        m()
                    except Exception:
                        pass
                    break
            if _is_safe():
                try:
                    queue_list.DeleteAllItems()
                    state["queue_map"].clear()
                    _update_button_state()
                except RuntimeError:
                    pass

        def close(event=None):
            if state["closed"]:
                # already closed, still skip event if needed
                if event is not None:
                    try:
                        event.Skip()
                    except Exception:
                        pass
                return
            state["closed"] = True
            try:
                unsubscribe_language_change(refresh_labels)
            except Exception:
                pass
            ctrl = state["controller"]
            if ctrl is not None:
                try:
                    eng = getattr(ctrl, "engine", None)
                    if eng is not None and not eng.wait(0):
                        # try cancel
                        for target in (ctrl, eng):
                            m = getattr(target, "cancel_all", None) or getattr(target, "cancel", None)
                            if callable(m):
                                try:
                                    m()
                                except Exception:
                                    pass
                                break
                except Exception:
                    pass
            # for embedded panel, do not destroy host frame; just hide/cleanup
            # the shell will destroy the frame which contains this panel
            if event is not None:
                try:
                    event.Skip()
                except Exception:
                    pass

        def refresh_labels(_language=None):
            if state["closed"]:
                return
            try:
                host.set_host_title(t("transfer.ftp_activity_title"))
                # update status if it's a known static value
                current = status.GetLabel()
                # Determine if current matches old static translations that need refresh
                # Keep progress detail containing '—' as is
                if "—" not in current:
                    # if controller indicates cancelled/failed/completed, refresh accordingly
                    ctrl = state["controller"]
                    try:
                        if ctrl and getattr(ctrl, "engine", None) and ctrl.engine.failed:
                            last = ctrl.engine.failed[-1][1] if ctrl.engine.failed else ""
                            if last == "cancelled":
                                status.SetLabel(t("transfer.cancelled"))
                            else:
                                status.SetLabel(t("transfer.errors_tab"))
                        elif ctrl and not getattr(ctrl, "engine", None) or (ctrl and not ctrl.engine.pending and not ctrl.engine.failed):
                            # only refresh if currently a static label
                            pass
                        else:
                            # keep or set to no_active if queue empty and no controller activity
                            if not state["queue_map"] and not state["failed_map"] and not state["completed_map"]:
                                status.SetLabel(t("transfer.no_active_transfer"))
                    except Exception:
                        pass
                    # Fallback: translate static labels if they were showing a known static string
                    # Check limited set
                    # We can't reliably detect previous language, so if current is not progress, ensure it stays translated
                    # If status is still one of the three tab labels or no_active/cancelled, re-translate
                    # Do minimal: if queue is empty and no progress, set to no_active translation
                    if not state["queue_map"] and current in (t("transfer.no_active_transfer"), t("transfer.completed_tab"), t("transfer.errors_tab"), t("transfer.cancelled")):
                        # already correct after above, no-op
                        pass
                # notebook tabs
                notebook.SetPageText(0, t("transfer.queue_tab"))
                notebook.SetPageText(1, t("transfer.failed_tab"))
                notebook.SetPageText(2, t("transfer.completed_tab"))
                # columns
                col_keys = ["transfer.col_local", "transfer.col_direction", "transfer.col_remote", "transfer.col_size", "transfer.col_progress", "transfer.col_priority", "transfer.col_status"]
                for lst in (queue_list, failed_list, completed_list):
                    for idx, key in enumerate(col_keys):
                        try:
                            # need to prepare item for GetColumn/SetColumn pattern
                            # Fetch existing column to preserve width etc, then set text
                            # Use ListCtrl GetColumn
                            col_item = lst.GetColumn(idx)
                            # GetColumn returns int width? In some wx versions GetColumn returns wxListItem; try both
                            if isinstance(col_item, wx.ListItem):
                                col_item.SetText(t(key))
                                lst.SetColumn(idx, col_item)
                            else:
                                # fallback: re-insert column header via SetColumn with new item
                                new_item = wx.ListItem()
                                new_item.SetText(t(key))
                                lst.SetColumn(idx, new_item)
                        except Exception:
                            try:
                                new_item = wx.ListItem()
                                new_item.SetText(t(key))
                                lst.SetColumn(idx, new_item)
                            except Exception:
                                pass
                controls["stop"].SetLabel(t("transfer.stop"))
                controls["cancel"].SetLabel(t("transfer.cancel"))
                controls["clear_pending"].SetLabel(t("transfer.clear_pending"))
                _update_button_state()
            except RuntimeError:
                return

        controls["stop"].Bind(wx.EVT_BUTTON, _do_cancel)
        controls["cancel"].Bind(wx.EVT_BUTTON, _do_cancel)
        controls["clear_pending"].Bind(wx.EVT_BUTTON, _do_clear_pending)

    else:
        # detached logic (original)
        def update_queue(event, item):
            if not _is_safe():
                return
            try:
                if event == "started":
                    controls["detail"].SetLabel(t("transfer.active_item").format(item=item.label()))
                elif event == "completed":
                    controls["detail"].SetLabel(t("transfer.completed_tab"))
                elif event == "failed":
                    controls["detail"].SetLabel(t("transfer.errors_tab"))
            except RuntimeError:
                return

        def update_progress(item, done, total):
            if not _is_safe():
                return
            try:
                controls["gauge"].SetRange(max(1, int(total)))
                controls["gauge"].SetValue(min(max(0, int(done)), controls["gauge"].GetRange()))
                controls["detail"].SetLabel(t("transfer.progress_detail").format(item=item.label(), done=done, total=total, speed="", eta=""))
            except RuntimeError:
                return

        def finish():
            if not _is_safe():
                return
            try:
                controller_value = state["controller"]
                if controller_value and controller_value.engine.failed:
                    last = controller_value.engine.failed[-1][1] if controller_value.engine.failed else ""
                    if last == "cancelled":
                        controls["detail"].SetLabel(t("transfer.cancelled"))
                    else:
                        controls["detail"].SetLabel(t("transfer.errors_tab"))
                elif controller_value:
                    controls["detail"].SetLabel(t("transfer.completed_tab"))
                controls["cancel"].Disable()
            except RuntimeError:
                return

        def finish_error(message):
            if not _is_safe():
                return
            try:
                controls["detail"].SetLabel(t("transfer.errors_tab"))
                controls["cancel"].Disable()
            except RuntimeError:
                return

        def cancel_transfer(_event):
            value = state["controller"]
            if value:
                # prefer cancel_all
                m = getattr(value, "cancel_all", None) or getattr(value, "cancel", None)
                if callable(m):
                    m()
                else:
                    eng = getattr(value, "engine", None)
                    if eng:
                        m2 = getattr(eng, "cancel_all", None) or getattr(eng, "cancel", None)
                        if callable(m2):
                            m2()
                if _is_safe():
                    try:
                        controls["detail"].SetLabel(t("transfer.cancelled"))
                        controls["cancel"].Disable()
                    except RuntimeError:
                        pass

        def close(_event):
            state["closed"] = True
            try:
                unsubscribe_language_change(refresh_labels)
            except Exception:
                pass
            value = state["controller"]
            if value and not value.engine.wait(0):
                try:
                    m = getattr(value, "cancel_all", None) or getattr(value, "cancel", None)
                    if callable(m):
                        m()
                    else:
                        eng = getattr(value, "engine", None)
                        if eng:
                            m2 = getattr(eng, "cancel_all", None) or getattr(eng, "cancel", None)
                            if callable(m2):
                                m2()
                except Exception:
                    pass
            try:
                host.Hide()
                host.Destroy()
            except Exception:
                pass
            if _event is not None:
                try:
                    _event.Skip()
                except Exception:
                    pass

        def refresh_labels(_language=None):
            if state["closed"]:
                return
            try:
                host.set_host_title(t("transfer.ftp_activity_title"))
                controls["title"].SetLabel(t("transfer.ftp_activity_title"))
                controls["cancel"].SetLabel(t("transfer.cancel"))
                current = controls["detail"].GetLabel()
                cv = state["controller"]
                if cv and cv.engine.failed:
                    last = cv.engine.failed[-1][1] if cv.engine.failed else ""
                    if last == "cancelled":
                        controls["detail"].SetLabel(t("transfer.cancelled"))
                    else:
                        controls["detail"].SetLabel(t("transfer.errors_tab"))
                elif cv and not cv.engine.pending and not cv.engine.failed:
                    if current in (t("transfer.no_active_transfer"), t("transfer.completed_tab"), t("transfer.errors_tab"), t("transfer.cancelled")) or "—" not in current:
                        controls["detail"].SetLabel(t("transfer.completed_tab"))
                else:
                    pass
            except RuntimeError:
                return

        controls["cancel"].Bind(wx.EVT_BUTTON, cancel_transfer)
        # _do_clear not needed for detached but keeps api

    # attach shared attributes
    host.bind_host_close(close)
    subscribe_language_change(refresh_labels)
    host._wx_transfer_controls = controls
    host._wx_transfer_state = state
    host._wx_transfer_set_controller = set_controller

    def _post_queue(event, item):
        def cb():
            update_queue(event, item)
        post(cb)

    def _post_progress(item, done, total):
        def cb():
            update_progress(item, done, total)
        post(cb)

    def _post_finish():
        def cb():
            finish()
        post(cb)

    host._wx_transfer_queue = _post_queue
    host._wx_transfer_progress = _post_progress
    host._wx_transfer_finish = _post_finish
    host._wx_transfer_finish_error = lambda msg: post(lambda: finish_error(msg))
    host._wx_transfer_refresh_labels = refresh_labels
    host._wx_transfer_close = close

    # initial button state
    _update_button_state()
    if embedded:
        host.Layout()
    else:
        try:
            host.Show()
        except Exception:
            pass
    return host


def create_transfer_progress(parent, controller=None):
    """Create the small wx owner for a transfer session, if wx is available."""
    return _build_transfers(parent, controller=controller, embedded=False)


def build_transfers_panel(parent, controller=None):
    """Embedded transfers panel factory. Returns the wx.Panel host."""
    return _build_transfers(parent, controller=controller, embedded=True)


class WxTransferWorkspace:
    def __init__(self, local_path: str | Path, remote_path: str = "/", run_item=None) -> None:
        self.local = LocalBrowserModel(local_path)
        self.remote = WxRemoteDirectoryModel(remote_path)
        self.session = TransferSessionController([], run_item or (lambda item, progress: None))
        self.conflict_policy = "ask"
        self.transfer_mode = "binary"
        self.storage = StorageState("unknown", False, "provider storage facts unavailable")

    def upload_selected(self, paths: list[Path], remote_dir: str) -> int:
        items = [TransferItem("upload", str(path), f"{remote_dir.rstrip('/')}/{path.name}") for path in paths]
        return self.session.engine.enqueue(items) if self.session.engine._thread and self.session.engine._thread.is_alive() else 0

    def download_selected(self, paths: list[str], local_dir: Path) -> tuple[TransferItem, ...]:
        return tuple(TransferItem("download", path, str(local_dir / path.rstrip('/').rsplit('/', 1)[-1])) for path in paths)

    def double_click_local(self, path: Path, remote_dir: str) -> TransferItem:
        return TransferItem("upload", str(path), f"{remote_dir.rstrip('/')}/{path.name}")

    def double_click_remote(self, path: str, local_dir: Path) -> TransferItem:
        return TransferItem("download", path, str(local_dir / path.rstrip('/').rsplit('/', 1)[-1]))

    def cross_pane_clipboard(self, paths: list[str], destination: str, *, move: bool = False) -> TransferItem:
        return TransferItem("download" if not move else "upload", paths[0], destination)

    def drag_operation(self, paths: list[str], destination: str, *, copy: bool = False) -> TransferItem:
        return self.cross_pane_clipboard(paths, destination, move=not copy)

    def set_conflict(self, policy: str) -> None:
        self.session.set_conflict_policy(policy)
        self.conflict_policy = policy

    def set_checksum(self, enabled: bool) -> None:
        self.session.set_checksum_enabled(enabled)

    def set_storage(self, name: str, available: bool, reason: str = "") -> None:
        self.storage = StorageState(name, bool(available), reason)

    def retry_failed(self) -> int:
        return self.session.engine.retry_failed()

    def stop_after_current(self) -> None:
        self.session.engine.stop_after_current()


__all__ = ["StorageState", "WxTransferWorkspace", "create_transfer_progress", "build_transfers_panel", "create_transfer_conflict_dialog", "_supports_resume"]
