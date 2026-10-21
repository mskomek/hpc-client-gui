"""Detached transfer progress callbacks (branch-internal leaf)."""

from __future__ import annotations

from typing import Any

from hpc_gui._wx_transfer_common import is_safe
from hpc_gui.core.i18n import t


def bind_detached(host, state: dict[str, Any], controls: dict[str, Any]):
    """Create detached callbacks closing over explicit host/state/controls."""
    try:
        import wx
    except ImportError:
        wx = None  # type: ignore[assignment]

    def update_queue(event, item):
        if not is_safe(host, state, controls.get("detail")):
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
        if not is_safe(host, state, controls.get("detail")):
            return
        try:
            controls["gauge"].SetRange(max(1, int(total)))
            controls["gauge"].SetValue(min(max(0, int(done)), controls["gauge"].GetRange()))
            controls["detail"].SetLabel(t("transfer.progress_detail").format(item=item.label(), done=done, total=total, speed="", eta=""))
        except RuntimeError:
            return

    def finish():
        if not is_safe(host, state, controls.get("detail")):
            return
        try:
            controller_value = state.get("controller")
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
        if not is_safe(host, state, controls.get("detail")):
            return
        try:
            controls["detail"].SetLabel(t("transfer.errors_tab"))
            controls["cancel"].Disable()
        except RuntimeError:
            return

    def cancel_transfer(_event):
        value = state.get("controller")
        if value:
            m = getattr(value, "cancel_all", None) or getattr(value, "cancel", None)
            if callable(m):
                m()
            else:
                eng = getattr(value, "engine", None)
                if eng:
                    m2 = getattr(eng, "cancel_all", None) or getattr(eng, "cancel", None)
                    if callable(m2):
                        m2()
            if is_safe(host, state, controls.get("detail")):
                try:
                    controls["detail"].SetLabel(t("transfer.cancelled"))
                    controls["cancel"].Disable()
                except RuntimeError:
                    pass

    def close(_event):
        state["closed"] = True
        try:
            from hpc_gui.core.i18n import unsubscribe_language_change as _unsub

            _unsub(refresh_labels)
        except Exception:
            pass
        value = state.get("controller")
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
        if state.get("closed"):
            return
        try:
            host.set_host_title(t("transfer.ftp_activity_title"))
            controls["title"].SetLabel(t("transfer.ftp_activity_title"))
            controls["cancel"].SetLabel(t("transfer.cancel"))
            current = controls["detail"].GetLabel()
            cv = state.get("controller")
            if cv and cv.engine.failed:
                last = cv.engine.failed[-1][1] if cv.engine.failed else ""
                if last == "cancelled":
                    controls["detail"].SetLabel(t("transfer.cancelled"))
                else:
                    controls["detail"].SetLabel(t("transfer.errors_tab"))
            elif cv and not cv.engine.pending and not cv.engine.failed:
                if current in (t("transfer.no_active_transfer"), t("transfer.completed_tab"), t("transfer.errors_tab"), t("transfer.cancelled")) or "—" not in current:
                    controls["detail"].SetLabel(t("transfer.completed_tab"))
        except RuntimeError:
            return

    if wx is not None:
        controls["cancel"].Bind(wx.EVT_BUTTON, cancel_transfer)

    return {
        "update_queue": update_queue,
        "update_progress": update_progress,
        "finish": finish,
        "finish_error": finish_error,
        "cancel_transfer": cancel_transfer,
        "close": close,
        "refresh_labels": refresh_labels,
    }


__all__ = ["bind_detached"]
