import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import current_language, load_language
from hpc_gui import __version__
from hpc_gui.wx_jobs import show_jobs
from hpc_gui.wx_shell import create_shell_frame


def _pump(app, predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(10)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def shell_i18n():
    load_language("en")
    app = wx.App(False)
    frame, lifecycle, _session = create_shell_frame(app, tray_factory=lambda _parent: None)
    frame.Show()
    show_jobs(frame, lifecycle=lifecycle, list_jobs=lambda: [{"id": "1", "state": "RUNNING"}])
    _pump(app, lambda: any(hasattr(w, "_wx_jobs_state") for w in wx.GetTopLevelWindows()))
    yield app, frame, lifecycle
    if not lifecycle.shutdown_started:
        frame.Close()
    _pump(app, lambda: lifecycle.shutdown_started)
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _choose(frame, language):
    item = frame._wx_shell_controls["language_items"][language]
    frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))


def test_wx_shell_language_menu_has_english_turkish_flags_and_check_state(shell_i18n):
    _app, frame, _lifecycle = shell_i18n
    items = frame._wx_shell_controls["language_items"]
    assert {item.GetItemLabelText() for item in items.values()} == {"English", "Türkçe"}
    assert all(item.GetBitmap().IsOk() for item in items.values())
    assert items["en"].IsChecked() and not items["tr"].IsChecked()
    _choose(frame, "tr")
    assert current_language() == "tr" and items["tr"].IsChecked() and not items["en"].IsChecked()


def test_wx_shell_language_selection_retranslates_open_jobs_window(shell_i18n):
    _app, frame, _lifecycle = shell_i18n
    jobs = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_jobs_state") and w.GetParent() is frame)
    assert frame.GetTitle() == f"HPC Client GUI {__version__}" and jobs.GetTitle() == "Jobs"
    _choose(frame, "tr")
    assert "İş" in jobs.GetTitle() and frame._wx_shell_controls["description"].GetLabel() != "wxPython migration shell"
    _choose(frame, "en")
    assert jobs.GetTitle() == "Jobs"


def test_wx_shell_exposes_navigation_tabs_and_terminal(shell_i18n):
    _app, frame, _lifecycle = shell_i18n
    controls = frame._wx_shell_controls
    notebook = controls["notebook"]
    assert notebook.GetPageCount() == 7
    # Qt reference order (main_window.py): Login, Jobs, Directories, FTP, Editor, Logs.
    # Terminal is an accepted wx-only tab, placed before Logs.
    assert [notebook.GetPageText(index) for index in range(7)] == [
        "Connection", "Jobs & Outputs", "Directories", "Files",
        "Script Editor", "Terminal", "Logs"
    ]
    assert controls["pages"]["NAV-TERMINAL"]["output"].IsEnabled()
    # GUI-WORKSPACE-001: no primary page may be a bare launcher button.
    import wx

    for index in range(7):
        page = notebook.GetPage(index)
        descendants = list(page.GetChildren())
        for child in tuple(descendants):
            descendants.extend(child.GetChildren())
        buttons = [c for c in descendants if isinstance(c, wx.Button)]
        assert descendants, f"page {index} has no controls"
        assert descendants != buttons, f"page {index} is a launcher-only page"
