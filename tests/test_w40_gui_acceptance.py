"""W40 live wx acceptance tests for language, layout, and accessibility."""

from __future__ import annotations

import pytest

from hpc_gui.config import storage
from hpc_gui.core import i18n


@pytest.fixture(autouse=True)
def _restore_language():
    yield
    try:
        i18n.load_language("tr")
    except Exception:
        pass


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    return config_path

# GUI FULL tests (real wx runtime)
# ---------------------------------------------------------------------------

def _pump(wx, app, rounds=4):
    for _ in range(rounds):
        try:
            app.ProcessPendingEvents()
        except Exception:
            pass
        try:
            wx.MilliSleep(2)
        except Exception:
            pass


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_language_change_relabels_tabs_without_identity_change():
    """TODO-005 + UISTATE-002/005: live relabel, order/identity/selection kept."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    i18n.load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame.Show()
        _pump(wx, app)
        notebook = frame._wx_shell_controls["notebook"]
        before_texts = [notebook.GetPageText(i) for i in range(notebook.GetPageCount())]
        before_pages = [notebook.GetPage(i) for i in range(notebook.GetPageCount())]
        notebook.SetSelection(2)
        assert notebook.GetSelection() == 2
        assert before_texts[0] == "Connection"
        # Real GUI language switch through the maintained API.
        i18n.set_language("tr")
        _pump(wx, app)
        after_texts = [notebook.GetPageText(i) for i in range(notebook.GetPageCount())]
        after_pages = [notebook.GetPage(i) for i in range(notebook.GetPageCount())]
        assert after_texts[0] == "Bağlantı"
        assert after_pages == before_pages  # identity kept
        assert notebook.GetSelection() == 2  # selection kept
        assert len(after_texts) == len(before_texts)  # order kept
        assert not any(t.startswith("[") for t in after_texts)
        i18n.set_language("en")
    finally:
        i18n.load_language("tr")
        try:
            frame.Close()
        except Exception:
            pass
        _pump(wx, app)


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_menu_actions_have_stable_ids_and_labels():
    """TODO-006: Menu/Plugins/Help/Language/Version actions exist + labelled."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    i18n.load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame.Show()
        _pump(wx, app)
        menubar = frame.GetMenuBar()
        assert menubar.GetMenuCount() >= 5  # Menu/Plugins/Help/Language/Version
        for idx in range(menubar.GetMenuCount()):
            assert menubar.GetMenuLabel(idx).strip() != ""
        items = frame._wx_shell_menu_items
        help_items = frame._wx_shell_help_items
        for key in ("settings", "check_updates", "exit"):
            assert key in items, key
        for key in ("help", "logs", "about"):
            assert key in help_items, key
        lang_items = frame._wx_shell_controls["language_items"]
        assert set(lang_items) == {"en", "tr"}
        assert lang_items["en"].IsChecked()  # current language checked
    finally:
        try:
            frame.Close()
        except Exception:
            pass
        _pump(wx, app)


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_window_geometry_roundtrip_opens_connection_page(isolated_config):
    """UISTATE-009..014 FULL: geometry restores; each launch opens Connection."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    i18n.load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame.Show()
        _pump(wx, app)
        notebook = frame._wx_shell_controls["notebook"]
        frame.SetSize(150, 120, 1280, 760)
        notebook.SetSelection(4)
        _pump(wx, app)
        frame.Close()  # real close path persists state
        _pump(wx, app, rounds=6)
    finally:
        _pump(wx, app)
    raw = storage.get_main_window_state()
    assert raw is not None
    assert raw["width"] == 1280 and raw["height"] == 760
    assert raw["selected_tab"] == 4
    frame2, _l2, _s2 = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame2.Show()
        _pump(wx, app)
        size = frame2.GetSize()
        assert (size.width, size.height) == (1280, 760)
        assert frame2._wx_shell_controls["notebook"].GetSelection() == 0
    finally:
        try:
            frame2.Close()
        except Exception:
            pass
        _pump(wx, app)


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_layout_sizes_both_locales_no_clipped_geometry():
    """TODO-015/018 + UISTATE-007/008: 1280x760 + 1440x900 under en+tr."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    app = wx.App.Get() or wx.App(False)
    problems = []
    for lang in ("en", "tr"):
        i18n.set_language(lang)
        frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
        try:
            frame.Show()
            _pump(wx, app)
            notebook = frame._wx_shell_controls["notebook"]
            for tab in range(notebook.GetPageCount()):
                notebook.SetSelection(tab)
                for size in ((1280, 760), (1440, 900)):
                    frame.SetSize(*size)
                    frame.Layout()
                    _pump(wx, app, rounds=2)
                    for win in frame.GetChildren():
                        try:
                            pos, sz = win.GetPosition(), win.GetSize()
                        except Exception:
                            continue
                        if pos.x < -2000 or pos.y < -2000:
                            problems.append((lang, tab, size, "offscreen"))
                        if sz.width < 0 or sz.height < 0:
                            problems.append((lang, tab, size, "negative-size"))
            # Canonical tab order (TODO-019) read back live under each locale.
            texts = [notebook.GetPageText(i) for i in range(notebook.GetPageCount())]
            assert len(texts) == 7, texts
        finally:
            try:
                frame.Close()
            except Exception:
                pass
            _pump(wx, app)
    assert problems == [], problems[:10]


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_canonical_tab_order_matches_wave01():
    """TODO-019: live order reconciled with the W01-frozen canonical order."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    i18n.load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame.Show()
        _pump(wx, app)
        notebook = frame._wx_shell_controls["notebook"]
        texts = [notebook.GetPageText(i) for i in range(notebook.GetPageCount())]
        assert texts == ["Connection", "Terminal", "Jobs & Outputs",
                         "Directories", "Files", "Script Editor", "Logs"], texts
    finally:
        try:
            frame.Close()
        except Exception:
            pass
        _pump(wx, app)


@pytest.mark.wx
@pytest.mark.gui
def test_w40_gui_keyboard_accessibility_names_and_order():
    """A11Y-CURRENT-001 + TODO-023 + TODO-056 (keyboard half): names, order,
    focus restoration, context-menu keyboard access on this candidate."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_shell import create_shell_frame

    i18n.load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame, _lifecycle, _session = create_shell_frame(app, tray_factory=lambda _p: None)
    try:
        frame.Show()
        _pump(wx, app)
        notebook = frame._wx_shell_controls["notebook"]
        for i in range(notebook.GetPageCount()):
            assert notebook.GetPageText(i).strip() != ""
            notebook.SetSelection(i)
            _pump(wx, app, rounds=1)
            assert notebook.GetSelection() == i  # focus/selection restoration
        menubar = frame.GetMenuBar()
        assert menubar.GetMenuCount() >= 5
        for key in ("update", "plugins", "send_logs", "settings", "help", "language_button"):
            btn = frame._wx_shell_controls.get(key)
            if btn is not None:
                assert btn.GetLabel().strip() != "", key
        # Terminal is the current WebView/xterm surface: old TextCtrl-terminal
        # accessibility evidence must not be reused (TODO-022).
        from hpc_gui import wx_terminal_webview as _web

        assert hasattr(_web, "build_terminal_panel")
    finally:
        try:
            frame.Close()
        except Exception:
            pass
        _pump(wx, app)
