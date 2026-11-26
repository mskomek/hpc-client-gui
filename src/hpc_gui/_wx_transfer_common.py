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
        hint = controls.get("parallel_hint")
        if hint is not None:
            configured = getattr(ctrl, "configured_parallel_limit", None)
            effective = getattr(getattr(ctrl, "engine", None), "parallel_limit", None)
            label = ""
            if type(configured) is int and type(effective) is int:
                if configured != effective:
                    label = t("transfer.parallel_hint_pair").format(
                        configured=configured, effective=effective,
                        reason=t("transfer.parallel_reduced_backend"),
                    )
                else:
                    label = t("transfer.parallel_hint_effective").format(
                        configured=configured, effective=effective,
                    )
            hint.SetLabel(label)
        engine = getattr(ctrl, "engine", None)
        running = bool(getattr(engine, "running", False))
        pending = bool(getattr(engine, "pending", ()))
        stopping = bool(getattr(engine, "stop_requested", False))
        cancelling = bool(getattr(engine, "cancel_requested", False))
        if embedded:
            controls["stop"].Enable(running and not stopping)
            controls["cancel"].Enable(running and not cancelling and _has_cancel(ctrl))
            controls["clear_pending"].Enable(pending and _has_clear(ctrl))
            controls["process_queue"].Enable(pending and not running)
            controls["retry_failed"].Enable(_has_failed(ctrl))
        else:
            controls["cancel"].Enable(running and not cancelling and _has_cancel(ctrl))
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


def priority_label(item) -> str:
    from hpc_gui.services.transfer_controller import TRANSFER_PRIORITIES

    value = getattr(item, "priority", "Normal")
    return t(f"transfer.priority_{value.lower()}") if value in TRANSFER_PRIORITIES else str(value)


def add_row(state, lst, item, status_text: str, progress_text: str) -> int:
    op = str(getattr(item, "op", "") or "")
    local, remote = str(getattr(item, "src", "")), str(getattr(item, "dst", ""))
    if op == "download":
        local, remote = remote, local
    idx = lst.GetItemCount()
    lst.InsertItem(idx, local)
    lst.SetItem(idx, 1, op)
    lst.SetItem(idx, 2, remote)
    size = getattr(item, "cached_size", None)
    if size is None:
        size = getattr(item, "size", None)
    lst.SetItem(idx, 3, "" if size is None else str(size))
    lst.SetItem(idx, 4, progress_text)
    lst.SetItem(idx, 5, priority_label(item))
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
