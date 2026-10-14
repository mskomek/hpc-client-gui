"""Windows-style quick navigation around the local file browser."""

from __future__ import annotations

from pathlib import Path


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
    locations = (
        (home, "ftp.local_nav_home"),
        (home / "Desktop", "ftp.local_nav_desktop"),
        (home / "Documents", "ftp.local_nav_documents"),
        (home / "Downloads", "ftp.local_nav_downloads"),
    )
    seen: set[str] = set()

    def open_location(target: Path) -> None:
        try:
            target = target.expanduser().resolve()
            if not target.is_dir():
                return
            browser._wx_local_model.navigate(target)
            browser._wx_local_controls["path"].SetValue(str(target))
            browser._wx_local_refresh()
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
    }
    return workspace
