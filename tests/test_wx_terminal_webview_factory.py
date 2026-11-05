"""Native WebView2 startup contracts without requiring GUI hardware."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from hpc_gui import wx_terminal_webview_factory as factory
from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin


class _Config:
    def __init__(self):
        self.path = ""

    def SetDataPath(self, path):
        self.path = path


class _View:
    def __init__(self):
        self.events = []
        self.created = False

    def Bind(self, name, handler):
        self.events.append((name, handler))

    def Create(self, parent):
        self.created = True
        self.parent = parent
        return True


class _Backend:
    config_count = 0
    instances = []

    @classmethod
    def NewConfiguration(cls):
        cls.config_count += 1
        return _Config()

    @classmethod
    def New(cls, arg):
        obj = _View()
        cls.instances.append((arg, obj))
        return obj


def test_windows_uses_one_writable_data_dir_and_binds_before_create(monkeypatch, tmp_path):
    monkeypatch.setattr(factory, "_WINDOWS", True)
    monkeypatch.setattr(factory, "_EDGE_CONFIG", None)
    monkeypatch.setattr(factory, "app_data_dir", lambda: tmp_path)
    monkeypatch.delenv("WEBVIEW2_USER_DATA_FOLDER", raising=False)
    _Backend.config_count = 0
    _Backend.instances = []
    html2 = SimpleNamespace(WebView=_Backend, EVT_WEBVIEW_CREATED="created")
    def handler(event):
        return None

    first, must_create = factory.new_terminal_webview("frame1", html2, handler)
    assert must_create is True
    assert first.events == [("created", handler)]
    assert first.created is False
    assert first.Create("frame1") is True
    assert first.created is True

    second, must_create = factory.new_terminal_webview("frame2", html2, handler)
    assert must_create is True
    assert second.Create("frame2")
    assert _Backend.config_count == 1
    assert _Backend.instances[0][0] is _Backend.instances[1][0]
    assert _Backend.instances[0][0].path == str((tmp_path / "webview2").resolve())
    assert (tmp_path / "webview2").is_dir()


def test_explicit_smoke_user_data_folder_is_preserved(monkeypatch, tmp_path):
    monkeypatch.setattr(factory, "_WINDOWS", True)
    monkeypatch.setattr(factory, "_EDGE_CONFIG", None)
    monkeypatch.setenv("WEBVIEW2_USER_DATA_FOLDER", str(tmp_path / "isolated"))
    html2 = SimpleNamespace(WebView=_Backend, EVT_WEBVIEW_CREATED="created")
    factory.new_terminal_webview("frame", html2, lambda event: None)
    assert factory._EDGE_CONFIG.path == str((tmp_path / "isolated").resolve())
    assert (tmp_path / "isolated").is_dir()


def test_non_windows_uses_existing_one_step_creation(monkeypatch):
    monkeypatch.setattr(factory, "_WINDOWS", False)
    class Backend:
        @staticmethod
        def New(parent):
            return ("existing", parent)
    view, waiting = factory.new_terminal_webview(
        "frame", SimpleNamespace(WebView=Backend), lambda event: None,
    )
    assert view == ("existing", "frame")
    assert waiting is False


def test_native_created_navigates_current_not_retired_controller(monkeypatch):
    scheduled = []
    monkeypatch.setitem(
        sys.modules, "wx",
        SimpleNamespace(CallAfter=lambda callback, *args: scheduled.append((callback, args))),
    )
    class Panel(TerminalBridgeMixin):
        _closed = False
        _webview = None

        def __init__(self):
            self.loaded = 0

        def _load_terminal_page(self):
            self.loaded += 1

    panel = Panel()
    current = object()
    old = object()
    panel._webview = current
    class Event:
        def __init__(self, obj):
            self.obj = obj
            self.skipped = False

        def GetEventObject(self):
            return self.obj

        def Skip(self):
            self.skipped = True

    stale = Event(old)
    panel._on_native_created(stale)
    assert stale.skipped
    cb, args = scheduled.pop()
    cb(*args)
    assert panel.loaded == 0

    live = Event(current)
    panel._on_native_created(live)
    cb, args = scheduled.pop()
    cb(*args)
    assert panel.loaded == 1

    panel._closed = True
    panel._on_native_created(Event(current))
    assert scheduled == []


def test_failed_edge_environment_recreates_configuration_without_data_loss(monkeypatch, tmp_path):
    monkeypatch.setattr(factory, "_WINDOWS", True)
    monkeypatch.setattr(factory, "_EDGE_CONFIG", None)
    monkeypatch.setenv("WEBVIEW2_USER_DATA_FOLDER", str(tmp_path / "shared"))
    _Backend.config_count = 0
    _Backend.instances = []
    html2 = SimpleNamespace(WebView=_Backend, EVT_WEBVIEW_CREATED="created")

    first, pending = factory.new_terminal_webview("parent", html2, lambda event: None)
    assert pending and not first.created
    first_config = _Backend.instances[-1][0]
    sentinel = tmp_path / "shared" / "preserve.txt"
    sentinel.write_text("existing browser data", encoding="utf-8")

    factory.invalidate_failed_edge_configuration()
    second, pending = factory.new_terminal_webview("parent", html2, lambda event: None)
    assert pending and not second.created
    second_config = _Backend.instances[-1][0]
    assert first_config is not second_config
    assert first_config.path == second_config.path
    assert sentinel.read_text(encoding="utf-8") == "existing browser data"
    assert _Backend.config_count == 2


def test_destroying_retired_child_never_closes_live_terminal_panel():
    from hpc_gui.wx_terminal_webview_lifecycle import TerminalLifecycleMixin

    class Panel(TerminalLifecycleMixin):
        def __init__(self):
            self.close_count = 0

        def close(self):
            self.close_count += 1

    class DestroyEvent:
        def __init__(self, window):
            self.window = window
            self.skipped = False

        def GetWindow(self):
            return self.window

        def Skip(self):
            self.skipped = True

    panel = Panel()
    child_destroy = DestroyEvent(object())
    panel._on_destroy(child_destroy)
    assert child_destroy.skipped
    assert panel.close_count == 0

    own_destroy = DestroyEvent(panel)
    panel._on_destroy(own_destroy)
    assert own_destroy.skipped
    assert panel.close_count == 1


def test_child_destroy_event_object_fallback_is_safe():
    from hpc_gui.wx_terminal_webview_lifecycle import TerminalLifecycleMixin

    class Panel(TerminalLifecycleMixin):
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class Event:
        def __init__(self, target):
            self.target = target
            self.skipped = False

        def GetEventObject(self):
            return self.target

        def Skip(self):
            self.skipped = True

    panel = Panel()
    event = Event(object())
    panel._on_destroy(event)
    assert not panel.closed
    assert event.skipped


def test_windows_legacy_wx_binding_without_created_or_configuration(monkeypatch):
    """Current packaged wx may not expose the documented 4.3 async APIs."""
    monkeypatch.setattr(factory, "_WINDOWS", True)

    class LegacyWebView:
        @staticmethod
        def New(parent):
            return ("legacy-async-edge", parent)

    html2 = SimpleNamespace(WebView=LegacyWebView)
    view, modern_created_event = factory.new_terminal_webview(
        "actual-wx-parent", html2, lambda event: None,
    )
    assert view == ("legacy-async-edge", "actual-wx-parent")
    assert modern_created_event is False
