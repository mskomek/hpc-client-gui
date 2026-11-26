"""Native transfer list context actions, scoped to the current queue owner."""
from __future__ import annotations

from hpc_gui._wx_transfer_common import find_row, update_button_state, update_tab_counts
from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TRANSFER_PRIORITIES


def _selected_items(listing, state, map_name):
    by_token = {state["row_token"].get(iid): item
                for iid, item in state[map_name].items()}
    items = []
    row = listing.GetFirstSelected()
    while row != -1:
        item = by_token.get(listing.GetItemData(row))
        if item is not None:
            items.append(item)
        row = listing.GetNextSelected(row)
    return items


def build_transfer_menu(wx, host, state, controls, kind):
    """Build actual native menu commands from a snapshot of the selection."""
    owner = state.get("controller")
    engine = getattr(owner, "engine", None)
    listing = controls[kind]
    map_name = f"{kind}_map"
    chosen = _selected_items(listing, state, map_name)
    menu = wx.Menu()

    def current():
        return not state.get("closed") and state.get("controller") is owner

    def append(target, key, action, enabled=True):
        entry = target.Append(wx.ID_ANY, t(key))
        entry.Enable(bool(enabled))

        def invoke(_event):
            if current() and entry.IsEnabled():
                action()
                update_tab_counts(controls["notebook"], state)
                update_button_state(host, state, controls, True)

        target.Bind(wx.EVT_MENU, invoke, entry)

    def forget(items):
        for item in items:
            iid = id(item)
            state[map_name].pop(iid, None)
            row = find_row(state, listing, iid)
            if row != -1:
                listing.DeleteItem(row)
            state["row_token"].pop(iid, None)

    if kind == "queue":
        pending_ids = {id(item) for item in getattr(engine, "pending", ())}
        selected = [item for item in chosen if id(item) in pending_ids]
        transferable = [item for item in selected if item.op in {"upload", "download"}]
        priorities = wx.Menu()
        for priority in TRANSFER_PRIORITIES:
            append(priorities, f"transfer.priority_{priority.lower()}",
                   lambda p=priority: engine.set_pending_priorities(transferable, p),
                   transferable)
        submenu = menu.AppendSubMenu(priorities, t("transfer.set_priority"))
        submenu.Enable(bool(transferable))
        append(menu, "transfer.remove_selected",
               lambda: engine.remove_pending_items(selected), selected)
        append(menu, "transfer.clear_pending", lambda: engine.clear_pending(), pending_ids)
    elif kind == "failed":
        failed_ids = {id(item) for item, _ in getattr(engine, "failed", ())}
        retryable = [item for item in chosen if id(item) in failed_ids]

        def retry():
            if engine.retry_failed_items(retryable):
                owner.start()

        append(menu, "transfer.retry_selected", retry,
               retryable and not engine.running)

        def remove(items):
            if engine is not None:
                engine.remove_failed_items(items)
            forget(items)

        append(menu, "transfer.remove_selected", lambda: remove(chosen), chosen)
        append(menu, "transfer.clear_failed",
               lambda: remove(list(state[map_name].values())), state[map_name])
    elif kind == "completed":
        def remove(items):
            if engine is not None:
                engine.remove_completed_items(items)
            forget(items)

        append(menu, "transfer.remove_selected", lambda: remove(chosen), chosen)
        append(menu, "transfer.clear_completed",
               lambda: remove(list(state[map_name].values())), state[map_name])
    return menu


def bind_transfer_menus(wx, host, state, controls):
    for kind in ("queue", "failed", "completed"):
        listing = controls[kind]

        def open_menu(event, kind=kind, listing=listing):
            index = event.GetIndex()
            if index >= 0 and not listing.IsSelected(index):
                row = listing.GetFirstSelected()
                while row != -1:
                    listing.Select(row, False)
                    row = listing.GetFirstSelected()
                listing.Select(index)
            menu = build_transfer_menu(wx, host, state, controls, kind)
            try:
                listing.PopupMenu(menu)
            finally:
                menu.Destroy()

        listing.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, open_menu)
