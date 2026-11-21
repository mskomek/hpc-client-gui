"""Accessible names stay in wx and never call the native WebView script API."""

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin
from hpc_gui.wx_terminal_webview_labels import TerminalLabelsMixin


class _Harness(TerminalBridgeMixin):
    def __init__(self, webview):
        self._webview = webview
        self._closed = False
        self._ready = False


class _LanguageHarness(TerminalLabelsMixin, TerminalBridgeMixin):
    def __init__(self, webview):
        self._webview = webview
        self._closed = False


class _FakeWebView(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.accessible_name = ""
        self.script_calls = 0

    def SetAccessibleName(self, value):
        self.accessible_name = value

    def RunScript(self, _script):
        self.script_calls += 1

    def RunScriptAsync(self, _script):
        self.script_calls += 1


@pytest.mark.gui
@pytest.mark.regression
def test_accessible_label_uses_native_wx_name_without_webview_script(monkeypatch):
    _app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    webview = _FakeWebView(frame)
    monkeypatch.setattr(
        wx,
        "CallAfter",
        lambda *_args, **_kwargs: pytest.fail("accessible names do not schedule WebView work"),
    )
    try:
        load_language("en")
        _Harness(webview)._update_accessibility_label()
        assert webview.GetName() == t("login.terminal_accessible_name")
        assert webview.accessible_name == webview.GetName()
        assert webview.script_calls == 0
    finally:
        frame.Destroy()
        wx.Yield()


@pytest.mark.gui
@pytest.mark.regression
def test_live_language_change_updates_native_name_without_webview_script():
    _app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    webview = _FakeWebView(frame)
    try:
        load_language("en")
        harness = _LanguageHarness(webview)
        harness._refresh_labels()
        assert webview.GetName() == "Remote terminal"

        load_language("tr")
        harness._refresh_labels()
        assert webview.GetName() == "Uzak terminal"
        assert webview.accessible_name == webview.GetName()
        assert webview.script_calls == 0
    finally:
        load_language("tr")
        frame.Destroy()
        wx.Yield()


@pytest.mark.gui
@pytest.mark.regression
def test_page_loaded_sets_accessible_name_without_entering_renderer(monkeypatch):
    _app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    webview = _FakeWebView(frame)
    harness = _Harness(webview)

    class Event:
        skipped = False

        def Skip(self):
            self.skipped = True

    event = Event()
    monkeypatch.setattr(
        wx,
        "CallAfter",
        lambda *_args, **_kwargs: pytest.fail("page load must not schedule WebView scripts"),
    )
    try:
        load_language("en")
        harness._on_loaded(event)
        assert event.skipped
        assert webview.GetName() == "Remote terminal"
        assert webview.script_calls == 0
    finally:
        frame.Destroy()
        wx.Yield()
