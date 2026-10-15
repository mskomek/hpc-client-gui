"""Private wx remote-file navigation component."""

from pathlib import PurePosixPath
from threading import Thread
from hpc_gui.core.i18n import t


def install_navigation(view):
    _apply_sort = view._apply_sort
    _current_navigation_store = view._current_navigation_store
    _filtered_entries = view._filtered_entries
    _populate_listing = view._populate_listing
    active_tab_state = view.active_tab_state
    btn_back = view.btn_back
    btn_forward = view.btn_forward
    btn_up = view.btn_up
    loader = view.loader
    lock = view.lock
    model = view.model
    notebook = view.notebook
    path = view.path
    safe_call_after = view.safe_call_after
    state = view.state
    tab_label = view.tab_label
    tabs = view.tabs
    wx = view.wx

    def _update_navigation_buttons():
        tstate = active_tab_state()
        btn_back.Enable(bool(tstate and tstate.get("back_stack")))
        btn_forward.Enable(bool(tstate and tstate.get("forward_stack")))
        btn_up.Enable(bool(tstate and tstate.get("path", "/") != "/"))

    def navigate(target, *, history_action="new"):
        tstate = active_tab_state()
        if not tstate:
            return
        target = str(PurePosixPath(str(target or "/"))) or "/"
        tstate_path_before = tstate["path"]
        if target != tstate_path_before:
            tstate["pending_navigation"] = (
                tstate_path_before,
                list(tstate.get("back_stack", ())),
                list(tstate.get("forward_stack", ())),
            )
            if history_action == "new":
                tstate["back_stack"].append(tstate_path_before)
                tstate["forward_stack"].clear()
            elif history_action == "back":
                if tstate["back_stack"] and tstate["back_stack"][-1] == target:
                    tstate["back_stack"].pop()
                tstate["forward_stack"].append(tstate_path_before)
            elif history_action == "forward":
                if tstate["forward_stack"] and tstate["forward_stack"][-1] == target:
                    tstate["forward_stack"].pop()
                tstate["back_stack"].append(tstate_path_before)
            state["view_generation"] += 1
            tstate["view_generation"] += 1
        model.navigate(target)
        tstate["path"] = model.current_path
        idx = notebook.GetSelection()
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        path.SetValue(model.current_path)
        try:
            notebook.SetPageText(idx, tab_label(model.current_path))
        except Exception:
            pass
        _update_navigation_buttons()
        store = _current_navigation_store()
        if store:
            try:
                store.record_visit(model.current_path)
            except Exception:
                pass

    def _restore_navigation(tstate):
        pending = tstate.get("pending_navigation")
        if not pending:
            return
        old_path, back_stack, forward_stack = pending
        tstate["path"] = old_path
        tstate["back_stack"] = back_stack
        tstate["forward_stack"] = forward_stack
        tstate["pending_navigation"] = None
        model.navigate(old_path)
        path.SetValue(old_path)
        idx = notebook.GetSelection()
        if 0 <= idx < notebook.GetPageCount():
            notebook.SetPageText(idx, tab_label(old_path))
        _update_navigation_buttons()

    def _commit_navigation(tstate):
        tstate["pending_navigation"] = None
        tstate["highlight_path"] = tstate.get("highlight_path", "")
        _update_navigation_buttons()

    def _go_back(_event=None):
        tstate = active_tab_state()
        if not tstate or not tstate.get("back_stack"):
            return
        target = tstate["back_stack"][-1]
        navigate(target, history_action="back")
        load()

    def _go_forward(_event=None):
        tstate = active_tab_state()
        if not tstate or not tstate.get("forward_stack"):
            return
        target = tstate["forward_stack"][-1]
        navigate(target, history_action="forward")
        load()

    def _go_up(_event=None):
        tstate = active_tab_state()
        if tstate and tstate.get("path", "/") != "/":
            navigate(str(PurePosixPath(tstate["path"]).parent))
            load()

    def render_for_tab(tab_entry, entries):
        tab_entry["full_entries"] = list(entries)
        _apply_sort(tab_entry)
        visible = _filtered_entries(tab_entry, tab_entry.get("_sorted_entries", entries))
        tab_entry["entries"] = visible
        try:
            _populate_listing(tab_entry["listing"], visible, tab_entry)
        except RuntimeError:
            return

    def load(_event=None):
        tstate = active_tab_state()
        if not tstate or not loader:
            return
        requested_path_text = path.GetValue().strip()
        if requested_path_text != tstate["path"]:
            try:
                navigate(requested_path_text)
                tstate = active_tab_state()
                requested_path_text = tstate["path"]
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                path.SetValue(tstate["path"])
                return
        else:
            # also ensure navigation sync
            requested_path_text = tstate["path"]
        with lock:
            if state["closed"] or tstate.get("closed"):
                return
            state["listing_busy"] = True
            state["listing_request_id"] += 1
            tstate["listing_busy"] = True
            tstate["listing_request_id"] += 1
            tstate["view_generation"] = tstate.get("view_generation", 0)
            request_id = tstate["listing_request_id"]
            request_generation = tstate["view_generation"]
            requested_path = requested_path_text
            tab_id = tstate["id"]

        def done(entries, error):
            # LIFECYCLE-NATIVE-001: completion may arrive after the Notebook
            # was destroyed (host close/disconnect race). Never touch wx
            # objects once closed/destroyed; stale results are dropped.
            try:
                with lock:
                    tab_entry = next((tt for tt in tabs if tt["id"] == tab_id), None)
                    if not tab_entry or tab_entry.get("closed"):
                        return
                    current = (
                        not state["closed"]
                        and request_id == tab_entry["listing_request_id"]
                        and request_generation == tab_entry["view_generation"]
                        and requested_path == tab_entry["path"]
                    )
                    if current:
                        tab_entry["listing_busy"] = False
                        state["listing_busy"] = False
                if not current:
                    return
                try:
                    alive = notebook and not state["closed"]
                    if alive:
                        try:
                            notebook.GetSelection()
                        except Exception:
                            return
                    else:
                        return
                except Exception:
                    return
                if error:
                    _restore_navigation(tab_entry)
                    # only show error if this tab is active
                    try:
                        if notebook.GetSelection() == tabs.index(tab_entry):
                            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    except Exception:
                        return
                else:
                    _commit_navigation(tab_entry)
                    try:
                        render_for_tab(tab_entry, entries)
                    except Exception:
                        return
            except Exception:
                return

        def worker():
            try:
                safe_call_after(done, model.list_entries(loader, path=requested_path, force=True), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    view._update_navigation_buttons = _update_navigation_buttons
    view.navigate = navigate
    view._restore_navigation = _restore_navigation
    view._commit_navigation = _commit_navigation
    view._go_back = _go_back
    view._go_forward = _go_forward
    view._go_up = _go_up
    view.render_for_tab = render_for_tab
    view.load = load
