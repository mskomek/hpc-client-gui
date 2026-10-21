"""Shared transfer panel helpers (branch-internal, no host creation)."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def post_to(state, callback, *args) -> None:
    if state.get("closed"):
        return
    try:
        import wx

        if wx.GetApp() is None:
            return
        wx.CallAfter(callback, *args)
    except BaseException:
        return


def _has_cancel(ctrl) -> bool:
    if ctrl is None:
        return False
    if callable(getattr(ctrl, "cancel_all", None)) or callable(getattr(ctrl, "cancel", None)):
        return True
    eng = getattr(ctrl, "engine", None)
    if eng and (callable(getattr(eng, "cancel_all", None)) or callable(getattr(eng, "cancel", None))):
        return True
    return False


def _has_clear(ctrl) -> bool:
    if ctrl is None:
        return False
    if callable(getattr(ctrl, "clear_pending", None)):
        return True
    eng = getattr(ctrl, "engine", None)
    if eng and callable(getattr(eng, "clear_pending", None)):
        return True
    return False


def _has_failed(ctrl) -> bool:
    engine = getattr(ctrl, "engine", None) if ctrl is not None else None
    if engine is None or not callable(getattr(engine, "retry_failed", None)):
        return False
    try:
        return bool(engine.failed) and engine.wait(0)
    except Exception:
        return False


def is_safe(host, state, primary) -> bool:
    if state.get("closed"):
        return False
    try:
        import wx

        if not host or not wx.Window.FindWindowById(host.GetId()):
            return False
    except Exception:
        return False
    try:
        import wx

        if primary is not None and not wx.Window.FindWindowById(primary.GetId()):
            return False
    except Exception:
        return False
    return True


def update_button_state(host, state, controls, embedded: bool) -> None:
    primary = controls.get("status") if embedded else controls.get("detail")
    if not is_safe(host, state, primary):
        return
    ctrl = state.get("controller")
    try:
        if embedded:
            has_cancel = _has_cancel(ctrl)
            has_clear = _has_clear(ctrl)
            controls["stop"].Enable(has_cancel)
            controls["cancel"].Enable(has_cancel)
            controls["clear_pending"].Enable(has_clear)
            controls["retry_failed"].Enable(_has_failed(ctrl))
        else:
            if ctrl is None:
                controls["cancel"].Disable()
            else:
                if _has_cancel(ctrl):
                    controls["cancel"].Enable(True)
                else:
                    controls["cancel"].Disable()
    except RuntimeError:
        pass


def row_token(state, item) -> int:
    """Stable small row token (HPC-W06-XFER-001/003/012)."""
    iid = id(item)
    token = state["row_token"].get(iid)
    if token is None:
        state["row_seq"] = state.get("row_seq", 0) + 1
        token = state["row_seq"]
        state["row_token"][iid] = token
    return token


def find_row(state, lst, iid: int) -> int:
    token = state["row_token"].get(iid, iid)
    for idx in range(lst.GetItemCount()):
        try:
            if lst.GetItemData(idx) == token:
                return idx
        except Exception:
            continue
    return -1


def add_row(state, lst, item, status_text: str, progress_text: str) -> int:
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
        lst.SetItemData(idx, row_token(state, item))
    except Exception:
        pass
    return idx


def update_tab_counts(notebook, state) -> None:
    """Keep translated queue labels and counts synchronized with row maps."""
    for index, (key, map_name) in enumerate(
        (
            ("transfer.queue_tab", "queue_map"),
            ("transfer.failed_tab", "failed_map"),
            ("transfer.completed_tab", "completed_map"),
        )
    ):
        notebook.SetPageText(index, f"{t(key)} ({len(state[map_name])})")


__all__ = [
    "post_to",
    "_has_cancel",
    "_has_clear",
    "_has_failed",
    "is_safe",
    "update_button_state",
    "row_token",
    "find_row",
    "add_row",
    "update_tab_counts",
]
