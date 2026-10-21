"""Transfer workspace facade (host/panel wiring, delegates to branch leaves)."""

from __future__ import annotations

from hpc_gui._wx_transfer_common import post_to, row_token, update_button_state
from hpc_gui._wx_transfer_conflict import _supports_resume, create_transfer_conflict_dialog
from hpc_gui._wx_transfer_detached import bind_detached
from hpc_gui._wx_transfer_embedded import bind_embedded
from hpc_gui.core.i18n import subscribe_language_change, t
from hpc_gui.wx_transfer_workspace_model import StorageState, WxTransferWorkspace


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
        status = wx.StaticText(panel, label=t("transfer.no_active_transfer"))
        notebook = wx.Notebook(panel)

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
        notebook.AddPage(queue_list, f"{t('transfer.queue_tab')} (0)")
        notebook.AddPage(failed_list, f"{t('transfer.failed_tab')} (0)")
        notebook.AddPage(completed_list, f"{t('transfer.completed_tab')} (0)")
        btn_stop = wx.Button(panel, label=t("transfer.stop"))
        btn_cancel = wx.Button(panel, label=t("transfer.cancel"))
        btn_clear = wx.Button(panel, label=t("transfer.clear_pending"))
        btn_retry = wx.Button(panel, label=t("transfer.retry_failed"))
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(btn_stop, 0, wx.ALL, 4)
        btn_sizer.Add(btn_cancel, 0, wx.ALL, 4)
        btn_sizer.Add(btn_clear, 0, wx.ALL, 4)
        btn_sizer.Add(btn_retry, 0, wx.ALL, 4)
        btn_sizer.AddStretchSpacer(1)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(status, 0, wx.ALL | wx.EXPAND, 6)
        layout.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        layout.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        panel.SetSizer(layout)
        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}, "row_token": {}, "row_seq": 0}
        controls = {
            "status": status,
            "notebook": notebook,
            "queue": queue_list,
            "failed": failed_list,
            "completed": completed_list,
            "stop": btn_stop,
            "cancel": btn_cancel,
            "clear_pending": btn_clear,
            "retry_failed": btn_retry,
        }
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
        host_sizer = wx.BoxSizer(wx.VERTICAL)
        host_sizer.Add(panel, 1, wx.EXPAND)
        host.SetSizer(host_sizer)
        host.Layout()
        state = {"closed": False, "controller": controller}
        controls = {"title": title, "detail": detail, "gauge": gauge, "cancel": cancel}
        status = detail

    def post(callback, *args):
        post_to(state, callback, *args)

    def set_controller(value):
        state["controller"] = value

        def _do_set():
            update_button_state(host, state, controls, embedded)
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
                            token = row_token(state, it)
                            for idx in range(queue_list.GetItemCount()):
                                try:
                                    if queue_list.GetItemData(idx) == token:
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
                                    queue_list.SetItemData(row, row_token(state, it))
                                except RuntimeError:
                                    pass
                except Exception:
                    pass

        try:
            if wx.IsMainThread():
                _do_set()
            else:
                post(_do_set)
                try:
                    wx.CallAfter(_do_set)
                except Exception:
                    pass
        except Exception:
            try:
                post(_do_set)
            except Exception:
                pass

    if embedded:
        bound = bind_embedded(host, state, controls)
        update_queue = bound["update_queue"]
        update_progress = bound["update_progress"]
        finish = bound["finish"]
        finish_error = bound["finish_error"]
        close = bound["close"]
        refresh_labels = bound["refresh_labels"]
    else:
        bound = bind_detached(host, state, controls)
        update_queue = bound["update_queue"]
        update_progress = bound["update_progress"]
        finish = bound["finish"]
        finish_error = bound["finish_error"]
        close = bound["close"]
        refresh_labels = bound["refresh_labels"]

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

    update_button_state(host, state, controls, embedded)
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


__all__ = ["StorageState", "WxTransferWorkspace", "create_transfer_progress", "build_transfers_panel", "create_transfer_conflict_dialog", "_supports_resume"]
