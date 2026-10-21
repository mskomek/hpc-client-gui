"""Embedded transfer panel callbacks (branch-internal leaf)."""

from __future__ import annotations

from typing import Any

from hpc_gui._wx_transfer_common import (
    add_row,
    find_row,
    is_safe,
    update_button_state,
    update_tab_counts,
)
from hpc_gui.core.i18n import t


def bind_embedded(host, state: dict[str, Any], controls: dict[str, Any]):
    """Create embedded callbacks closing over explicit host/state/controls."""
    try:
        import wx
    except ImportError:
        wx = None  # type: ignore[assignment]
    status = controls["status"]
    notebook = controls["notebook"]
    queue_list = controls["queue"]
    failed_list = controls["failed"]
    completed_list = controls["completed"]

    def update_queue(event, item):
        if not is_safe(host, state, status):
            return
        try:
            iid = id(item)
            if event in ("queued", "started"):
                for _map_name, _list in (("failed_map", failed_list), ("completed_map", completed_list)):
                    if iid in state[_map_name]:
                        state[_map_name].pop(iid, None)
                        _row = find_row(state, _list, iid)
                        if _row != -1:
                            try:
                                _list.DeleteItem(_row)
                            except Exception:
                                pass
                try:
                    status.SetLabel(t("transfer.active_item").format(item=item.label()))
                except Exception:
                    status.SetLabel(t("transfer.no_active_transfer"))
                if iid not in state["queue_map"]:
                    state["queue_map"][iid] = item
                    add_row(state, queue_list, item, "Queued", "")
            elif event == "completed":
                try:
                    status.SetLabel(t("transfer.completed_tab"))
                except Exception:
                    pass
                state["queue_map"].pop(iid, None)
                row = find_row(state, queue_list, iid)
                if row != -1:
                    try:
                        queue_list.DeleteItem(row)
                    except Exception:
                        pass
                if iid not in state["completed_map"]:
                    state["completed_map"][iid] = item
                    add_row(state, completed_list, item, "Successful", "")
            elif event == "failed":
                try:
                    status.SetLabel(t("transfer.errors_tab"))
                except Exception:
                    pass
                state["queue_map"].pop(iid, None)
                row = find_row(state, queue_list, iid)
                if row != -1:
                    try:
                        queue_list.DeleteItem(row)
                    except Exception:
                        pass
                if iid not in state["failed_map"]:
                    state["failed_map"][iid] = item
                    add_row(state, failed_list, item, "Failed", "")
            update_tab_counts(notebook, state)
            update_button_state(host, state, controls, True)
        except RuntimeError:
            return

    def update_progress(item, done, total):
        if not is_safe(host, state, status):
            return
        try:
            iid = id(item)
            row = find_row(state, queue_list, iid)
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
        if not is_safe(host, state, status):
            return
        try:
            ctrl = state.get("controller")
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
            update_button_state(host, state, controls, True)
        except RuntimeError:
            return

    def finish_error(message):
        if not is_safe(host, state, status):
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

    def do_cancel(_event=None):
        ctrl = state.get("controller")
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
        if is_safe(host, state, status):
            try:
                status.SetLabel(t("transfer.cancelled"))
                controls["stop"].Disable()
                controls["cancel"].Disable()
            except RuntimeError:
                pass

    def do_clear_pending(_event=None):
        ctrl = state.get("controller")
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
        if is_safe(host, state, status):
            try:
                queue_list.DeleteAllItems()
                state["queue_map"].clear()
                update_button_state(host, state, controls, True)
            except RuntimeError:
                pass

    def do_retry_failed(_event=None):
        ctrl = state.get("controller")
        engine = getattr(ctrl, "engine", None) if ctrl else None
        retry = getattr(engine, "retry_failed", None)
        if not callable(retry):
            return
        try:
            if retry():
                starter = getattr(ctrl, "start", None) or getattr(engine, "start", None)
                if callable(starter):
                    starter()
        except Exception:
            return
        update_button_state(host, state, controls, True)

    def close(event=None):
        if state.get("closed"):
            if event is not None:
                try:
                    event.Skip()
                except Exception:
                    pass
            return
        state["closed"] = True
        try:
            from hpc_gui.core.i18n import unsubscribe_language_change as _unsub

            # refresh_labels unsubscribed by facade (holds reference); best-effort here
            _unsub(refresh_labels)
        except Exception:
            pass
        ctrl = state.get("controller")
        if ctrl is not None:
            try:
                eng = getattr(ctrl, "engine", None)
                if eng is not None and not eng.wait(0):
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
        if event is not None:
            try:
                event.Skip()
            except Exception:
                pass

    def refresh_labels(_language=None):
        if state.get("closed"):
            return
        try:
            host.set_host_title(t("transfer.ftp_activity_title"))
            current = status.GetLabel()
            if "—" not in current:
                try:
                    ctrl = state.get("controller")
                    if ctrl and getattr(ctrl, "engine", None) and ctrl.engine.failed:
                        last = ctrl.engine.failed[-1][1] if ctrl.engine.failed else ""
                        if last == "cancelled":
                            status.SetLabel(t("transfer.cancelled"))
                        else:
                            status.SetLabel(t("transfer.errors_tab"))
                    elif ctrl and not getattr(ctrl, "engine", None) or (ctrl and not ctrl.engine.pending and not ctrl.engine.failed):
                        pass
                    else:
                        if not state.get("queue_map") and not state.get("failed_map") and not state.get("completed_map"):
                            status.SetLabel(t("transfer.no_active_transfer"))
                except Exception:
                    pass
                if not state.get("queue_map") and current in (t("transfer.no_active_transfer"), t("transfer.completed_tab"), t("transfer.errors_tab"), t("transfer.cancelled")):
                    pass
            update_tab_counts(notebook, state)
            col_keys = ["transfer.col_local", "transfer.col_direction", "transfer.col_remote", "transfer.col_size", "transfer.col_progress", "transfer.col_priority", "transfer.col_status"]
            for lst in (queue_list, failed_list, completed_list):
                for idx, key in enumerate(col_keys):
                    try:
                        col_item = lst.GetColumn(idx)
                        if isinstance(col_item, wx.ListItem):
                            col_item.SetText(t(key))
                            lst.SetColumn(idx, col_item)
                        else:
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
            controls["retry_failed"].SetLabel(t("transfer.retry_failed"))
            update_button_state(host, state, controls, True)
        except RuntimeError:
            return

    if wx is not None:
        controls["stop"].Bind(wx.EVT_BUTTON, do_cancel)
        controls["cancel"].Bind(wx.EVT_BUTTON, do_cancel)
        controls["clear_pending"].Bind(wx.EVT_BUTTON, do_clear_pending)
        controls["retry_failed"].Bind(wx.EVT_BUTTON, do_retry_failed)

    return {
        "update_queue": update_queue,
        "update_progress": update_progress,
        "finish": finish,
        "finish_error": finish_error,
        "do_cancel": do_cancel,
        "do_clear_pending": do_clear_pending,
        "do_retry_failed": do_retry_failed,
        "close": close,
        "refresh_labels": refresh_labels,
    }


__all__ = ["bind_embedded"]
