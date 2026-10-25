"""Regression coverage for wx notebook page geometry after shell resize."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_shell_frame import create_shell_frame


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
        notebook = frame._wx_shell_controls["notebook"]
        initial_client = notebook.GetClientSize()
        initial_pages = [
            tuple(notebook.GetPage(index).GetSize())
            for index in range(notebook.GetPageCount())
        ]

        frame.SetSize((frame.GetSize().width + 180, frame.GetSize().height + 120))
        frame.Layout()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            _pump(app, rounds=1)
            client = notebook.GetClientSize()
            sizes = [
                notebook.GetPage(index).GetSize()
                for index in range(notebook.GetPageCount())
            ]
            if client.width > initial_client.width and all(
                size.width <= client.width and size.height <= client.height
                for size in sizes
            ):
                break

        assert notebook.GetClientSize().width > initial_client.width
        assert all(
            size.width <= notebook.GetClientSize().width
            and size.height <= notebook.GetClientSize().height
            for index in range(notebook.GetPageCount())
            for size in (notebook.GetPage(index).GetSize(),)
        )
        if wx.Platform == "__WXGTK__":
            assert any(
                tuple(notebook.GetPage(index).GetSize()) != initial_pages[index]
                for index in range(notebook.GetPageCount())
            )
    finally:
        _close(app, frame, lifecycle)
        if owns_app:
            try:
                app.Destroy()
            except Exception:
                pass
