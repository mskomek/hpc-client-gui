"""Regression coverage for wx notebook page geometry after shell resize."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_shell_frame import create_shell_frame
from hpc_gui.wx_remote_files_more_menu import build_more_actions_menu
from hpc_gui.core.i18n import set_language, t


def _pump(app, rounds: int = 3) -> None:
    for _ in range(rounds):
        app.ProcessPendingEvents()
        wx.Yield()
        wx.MilliSleep(5)


def _close(app, frame, lifecycle) -> None:
    try:
        frame.Close()
    except Exception:
        pass
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not lifecycle.shutdown_started:
        app.ProcessPendingEvents()
        wx.SafeYield()
        wx.MilliSleep(5)


@pytest.mark.gui
@pytest.mark.wx
def test_notebook_pages_follow_shell_resize():
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    frame, lifecycle, _session = create_shell_frame(
        app, tray_factory=lambda _parent: None
    )
    try:
        frame.Show()
        _pump(app, rounds=8)
        if wx.Platform == "__WXGTK__":
            # The shell fits its minimum size to the display after native
            # chrome is realized. Lower it afterward to exercise real resize
            # events within the small guest desktop.
            area = wx.Display(frame).GetClientArea()
            frame.SetMinSize(wx.Size(1, 1))
            frame.SetSize(
                max(640, int(area.width * 0.65)),
                max(480, int(area.height * 0.65)),
            )
            _pump(app, rounds=4)
        notebook = frame._wx_shell_controls["notebook"]
        initial_size = tuple(frame.GetSize())

        def resize_and_check(target_size, direction):
            before_client = notebook.GetClientSize()
            before_pages = [
                tuple(notebook.GetPage(index).GetSize())
                for index in range(notebook.GetPageCount())
            ]
            frame.SetSize(target_size)
            frame.Layout()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                _pump(app, rounds=1)
                client = notebook.GetClientSize()
                sizes = [
                    notebook.GetPage(index).GetSize()
                    for index in range(notebook.GetPageCount())
                ]
                changed = any(
                    tuple(size) != before_pages[index]
                    for index, size in enumerate(sizes)
                )
                moved = (
                    client.width > before_client.width
                    if direction == "grow"
                    else client.width < before_client.width
                )
                if moved and changed and all(
                    size.width <= client.width and size.height <= client.height
                    for size in sizes
                ):
                    break

            client = notebook.GetClientSize()
            assert (
                client.width > before_client.width
                if direction == "grow"
                else client.width < before_client.width
            )
            sizes = [
                notebook.GetPage(index).GetSize()
                for index in range(notebook.GetPageCount())
            ]
            assert all(
                tuple(size) != before_pages[index]
                for index, size in enumerate(sizes)
            )
            assert len({tuple(size) for size in sizes}) == 1
            assert all(
                size.width <= client.width and size.height <= client.height
                for size in sizes
            )

        if wx.Platform == "__WXGTK__":
            area = wx.Display(frame).GetClientArea()
            grow_size = (
                max(initial_size[0] + 80, int(area.width * 0.82)),
                max(initial_size[1] + 60, int(area.height * 0.82)),
            )
        else:
            grow_size = (initial_size[0] + 180, initial_size[1] + 120)
        resize_and_check(grow_size, "grow")
        resize_and_check(initial_size, "shrink")
    finally:
        _close(app, frame, lifecycle)
        if owns_app:
            try:
                app.Destroy()
            except Exception:
                pass


@pytest.mark.gui
@pytest.mark.wx
def test_nested_remote_listing_page_is_sized_when_shell_tab_activates():
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    frame, lifecycle, _session = create_shell_frame(
        app, tray_factory=lambda _parent: None
    )
    try:
        frame.Show()
        _pump(app, rounds=8)
        pages = frame._wx_shell_controls["pages"]
        files_page = pages["NAV-FILES"]["page"]
        main_notebook = frame._wx_shell_controls["notebook"]
        main_notebook.SetSelection(main_notebook.FindPage(files_page))
        _pump(app, rounds=8)

        remote_notebook = pages["NAV-FILES"]["remote"]._wx_remote_controls[
            "notebook"
        ]
        remote_controls = pages["NAV-FILES"]["remote"]._wx_remote_controls
        listing = remote_controls["listing"]
        assert remote_controls["btn_more"].IsShownOnScreen()
        assert remote_controls["btn_download"].GetLabel() == t("dirs.download")
        assert (
            remote_controls["btn_download"].GetToolTip().GetTip()
            == t("dirs.download_selected")
        )
        def more_menu_labels():
            callbacks = tuple(
                (key, lambda _event: None)
                for key in (
                    "dirs.new_file",
                    "dirs.delete",
                    "dirs.undo",
                    "dirs.refresh",
                    "dirs.favorites",
                    "dirs.history",
                )
            )
            menu = build_more_actions_menu(wx, t, callbacks)
            try:
                return [
                    item.GetItemLabelText() for item in menu.GetMenuItems()
                ]
            finally:
                menu.Destroy()

        expected_actions = (
            "dirs.new_file",
            "dirs.delete",
            "dirs.undo",
            "dirs.refresh",
            "dirs.favorites",
            "dirs.history",
        )
        assert more_menu_labels() == [t(key) for key in expected_actions]
        set_language("tr")
        _pump(app, rounds=4)
        assert remote_controls["btn_more"].GetLabel() == t("dirs.more_actions")
        assert remote_controls["btn_download"].GetLabel() == t("dirs.download")
        assert more_menu_labels() == [t(key) for key in expected_actions]
        set_language("en")
        _pump(app, rounds=4)
        active_page = remote_notebook.GetCurrentPage()
        client_size = remote_notebook.GetClientSize()
        window_size = remote_notebook.GetSize()
        assert client_size.width > 0 and client_size.height > 0
        page_size = active_page.GetSize()
        assert 0 < page_size.width <= window_size.width
        assert 0 < page_size.height < window_size.height
        assert listing.GetSize().height > 0
        listing_parent = listing.GetParent()
        listing_position = listing.GetPosition()
        assert (
            listing_position.y + listing.GetSize().height
            <= listing_parent.GetClientSize().height
        )
    finally:
        _close(app, frame, lifecycle)
        if owns_app:
            try:
                app.Destroy()
            except Exception:
                pass
