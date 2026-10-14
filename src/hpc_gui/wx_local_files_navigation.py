"""Windows-style quick navigation around the local file browser."""

from __future__ import annotations

from pathlib import Path

from hpc_gui.services.local_navigation_store import LocalNavigationStore


def _navigate_local_browser(browser, target) -> None:
    """Synchronize the model, active tab, address bar, and visible listing."""
    model = browser._wx_local_model
    target = Path(target).expanduser().resolve()
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    notebook = browser._wx_local_notebook
    tabs = browser._wx_local_tabs
    index = notebook.GetSelection()
    if index < 0 or index >= len(tabs):
        return
    tab = tabs[index]
    if target != tab["path"]:
        state = browser._wx_local_state
        state["view_generation"] += 1
        tab["view_generation"] += 1
    model.active_tab = index
    model.navigate(target)
    tab["path"] = target
    controls = browser._wx_local_controls
    controls["path"].SetValue(str(target))
    notebook.SetPageText(index, target.name or str(target))
    controls["btn_back"].Enable(model.can_go_back())
    controls["btn_forward"].Enable(model.can_go_forward())
    browser._wx_local_refresh()


def _show_local_favorites(wx, browser, store, translate) -> None:
    menu = wx.Menu()
    favorites = store.favorites()
    for favorite in favorites:
        path = favorite.get("path", "")
        item = menu.Append(wx.ID_ANY, favorite.get("label") or path)
        menu.Bind(
            wx.EVT_MENU,
            lambda _event, target=path: _navigate_local_browser(browser, target),
            item,
        )
    if not favorites:
        menu.Append(wx.ID_NONE, translate("ftp.local_favorites_empty"))
    menu.AppendSeparator()
    current = browser._wx_local_model.current_path
    if store.is_favorite(current):
        action = menu.Append(wx.ID_ANY, translate("dirs.favorite_remove"))
        menu.Bind(wx.EVT_MENU, lambda _event: store.remove_favorite(current), action)
    else:
        action = menu.Append(wx.ID_ANY, translate("dirs.favorite_add"))
        menu.Bind(wx.EVT_MENU, lambda _event: store.add_favorite(current), action)
    browser.PopupMenu(menu)
    menu.Destroy()


def _show_local_history(wx, browser, store, translate) -> None:
    menu = wx.Menu()
    history = store.history()
    for entry in history[:20]:
        path = entry.get("path", "")
        item = menu.Append(wx.ID_ANY, path)
        menu.Bind(
            wx.EVT_MENU,
            lambda _event, target=path: _navigate_local_browser(browser, target),
            item,
        )
    if not history:
        menu.Append(wx.ID_NONE, translate("ftp.local_history_empty"))
    menu.AppendSeparator()
    clear = menu.Append(wx.ID_ANY, translate("dirs.history_clear"))
    menu.Bind(wx.EVT_MENU, lambda _event: store.clear_history(), clear)
    browser.PopupMenu(menu)
    menu.Destroy()


def build_local_files_navigation(wx, parent, browser, translate):
    """Wrap the existing local browser with a compact quick-access sidebar."""
    workspace = wx.Panel(parent)
    layout = wx.BoxSizer(wx.HORIZONTAL)
    sidebar = wx.Panel(workspace)
    sidebar.SetMinSize(wx.Size(166, -1))
    sidebar.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
    navigation = wx.BoxSizer(wx.VERTICAL)

    heading = wx.StaticText(sidebar, label=translate("ftp.local_nav_title"))
    heading_font = heading.GetFont()
    heading_font.SetWeight(wx.FONTWEIGHT_BOLD)
    heading.SetFont(heading_font)
    navigation.Add(heading, 0, wx.LEFT | wx.TOP | wx.RIGHT, 12)
    navigation.AddSpacer(8)

    home = Path.home()
    model = getattr(browser, "_wx_local_model", None)
    if model is None:
        raise RuntimeError("local browser model is unavailable")
    store = LocalNavigationStore()
    original_list_entries = model.list_entries

    def record_successful_visit(path=None):
        entries = original_list_entries(path)
        store.record_visit(path if path is not None else model.current_path)
        return entries

    model.list_entries = record_successful_visit
    store.record_visit(model.current_path)

    locations = (
        (home, "ftp.local_nav_home"),
        (home / "Desktop", "ftp.local_nav_desktop"),
        (home / "Documents", "ftp.local_nav_documents"),
        (home / "Downloads", "ftp.local_nav_downloads"),
    )
    seen: set[str] = set()

    def open_location(target: Path) -> None:
        try:
            _navigate_local_browser(browser, target)
        except (AttributeError, OSError, RuntimeError):
            return

    for target, label_key in locations:
        try:
            identity = str(target.resolve()).casefold()
            if identity in seen or not target.is_dir():
                continue
            seen.add(identity)
        except OSError:
            continue
        button = wx.Button(sidebar, label=translate(label_key), style=wx.BU_LEFT)
        button.SetMinSize(wx.Size(150, 34))
        button.SetToolTip(str(target))
        button.Bind(wx.EVT_BUTTON, lambda _event, path=target: open_location(path))
        navigation.Add(button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

    navigation.AddSpacer(4)
    navigation.Add(wx.StaticLine(sidebar), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    drives = wx.Button(sidebar, label=translate("ftp.local_nav_drives"), style=wx.BU_LEFT)
    drives.SetMinSize(wx.Size(150, 34))

    def show_drives(_event=None):
        control = getattr(browser, "_wx_local_controls", {}).get("btn_drives")
        if control is not None:
            wx.PostEvent(control, wx.CommandEvent(wx.EVT_BUTTON.typeId, control.GetId()))

    drives.Bind(wx.EVT_BUTTON, show_drives)
    navigation.Add(drives, 0, wx.EXPAND | wx.ALL, 5)
    favorites = wx.Button(sidebar, label=translate("dirs.favorites"), style=wx.BU_LEFT)
    history = wx.Button(sidebar, label=translate("dirs.history"), style=wx.BU_LEFT)
    for button in (favorites, history):
        button.SetMinSize(wx.Size(150, 34))
        navigation.Add(button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
    favorites.Bind(
        wx.EVT_BUTTON,
        lambda _event: _show_local_favorites(wx, browser, store, translate),
    )
    history.Bind(
        wx.EVT_BUTTON,
        lambda _event: _show_local_history(wx, browser, store, translate),
    )
    navigation.AddStretchSpacer(1)
    sidebar.SetSizer(navigation)

    browser.Reparent(workspace)
    layout.Add(sidebar, 0, wx.EXPAND | wx.RIGHT, 6)
    layout.Add(browser, 1, wx.EXPAND)
    workspace.SetSizer(layout)
    workspace._wx_local_browser = browser
    workspace._wx_local_navigation_controls = {
        "heading": heading,
        "locations": tuple(button for button in sidebar.GetChildren() if isinstance(button, wx.Button)),
        "drives": drives,
        "favorites": favorites,
        "history": history,
        "store": store,
    }
    return workspace
