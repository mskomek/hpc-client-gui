"""W04 support matrix acceptance tests: menu actions."""

import pytest
import re
import types
import hpc_gui.wx_shell as wx_shell
from hpc_gui.core.i18n import load_language
from w04_support_freeze_support import _MessageBoxCapture, _close_shell, _fake_plugin, _fire_menu, _parse_freeze_matrix, wx


@pytest.fixture(autouse=True)
def _english_bundle():
    load_language("en")
    yield
    load_language("en")


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            if window:
                window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def test_menu_events__route_to_canonical_owners(wx_app, monkeypatch):
    """Real EVT_MENU from each static menu item reaches its canonical
    implementation owner with the shell parent (one shell, per-leg asserts)."""
    import threading

    import hpc_gui.wx_about as about_view
    import hpc_gui.wx_help as help_view
    import hpc_gui.wx_plugins_view as plugins_view
    import hpc_gui.wx_send_logs_view as logs_view
    import hpc_gui.wx_settings_view as settings_view
    import hpc_gui.wx_updater_view as updater_view

    calls = {}

    def _recorder(name, **accept):
        def _impl(*args, **kwargs):
            calls[name] = (args, kwargs)
            if name == "updater":
                dialog = types.SimpleNamespace(
                    _build_for_state=lambda *a, **k: calls.setdefault("updater_state", (a, k)),
                    dlg=types.SimpleNamespace(Show=lambda *a, **k: None),
                )
                return dialog
            return wx.ID_OK

        return _impl

    monkeypatch.setattr(settings_view, "show_settings", _recorder("settings"))
    monkeypatch.setattr(about_view, "show_about", _recorder("about"))
    monkeypatch.setattr(help_view, "show_help", _recorder("help"))
    monkeypatch.setattr(logs_view, "show_send_logs", _recorder("logs"))
    monkeypatch.setattr(plugins_view, "show_plugins", _recorder("plugins"))

    real_dialog_cls = updater_view.WxUpdateDialog

    def _fake_dialog(parent, arg):
        calls["updater"] = ((parent, arg), {})
        return types.SimpleNamespace(
            _build_for_state=lambda *a, **k: calls.setdefault("updater_state", (a, k)),
            dlg=types.SimpleNamespace(Show=lambda *a, **k: None),
        )

    monkeypatch.setattr(updater_view, "WxUpdateDialog", _fake_dialog)
    # This test owns the menu-to-controller dispatch boundary. The updater's
    # network worker is covered by its own tests; do not race wx.App teardown.
    monkeypatch.setattr(threading.Thread, "start", lambda _thread: None)

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        _fire_menu(frame, frame._wx_shell_menu_items["settings"])
        assert "settings" in calls, "APP-SETTINGS must reach show_settings"
        assert calls["settings"][1].get("parent") is frame

        _fire_menu(frame, frame._wx_shell_help_items["about"])
        assert "about" in calls, "APP-ABOUT must reach show_about"

        _fire_menu(frame, frame._wx_shell_help_items["help"])
        assert "help" in calls, "APP-HELP must reach show_help"

        _fire_menu(frame, frame._wx_shell_help_items["logs"])
        assert "logs" in calls, "APP-SEND-LOGS must reach show_send_logs"

        _fire_menu(frame, frame._wx_shell_menu_items["check_updates"])
        assert "updater" in calls, "APP-UPDATE-CHECK must reach WxUpdateDialog"

        # PLUGIN-BROWSE via the preserved TypeError fallback: the real view
        # takes no initial_tab, so exactly one parent-only call must land.
        _fire_menu(frame, frame._wx_shell_plugins_menu.GetMenuItems()[0])
        assert "plugins" in calls, "PLUGIN-BROWSE must reach show_plugins"
    finally:
        monkeypatch.setattr(updater_view, "WxUpdateDialog", real_dialog_cls, raising=False)
        _close_shell(frame)


def test_settings__visible_option_changes_owned_value():
    """A visible option mutates its owned model value; unknown keys fail
    loudly (KeyError), never silently."""
    from hpc_gui.wx_settings import WxSettingsModel

    model = WxSettingsModel({})
    model.set_global("remote_directory_cache", False)
    model.set_profile("transfer_parallelism", 4)
    snapshot = model.snapshot()
    assert snapshot.global_settings["remote_directory_cache"] is False
    assert snapshot.profile_settings["transfer_parallelism"] == 4
    with pytest.raises(KeyError):
        model.set_global("no_such_option", True)
    with pytest.raises(KeyError):
        model.set_profile("no_such_option", True)


def test_settings__shell_apply_gap_stays_ledgered():
    """The shell-Apply persistence gap is honestly EXPERIMENTAL with its
    W37 owner — classified, not fixed or hidden here."""
    _, rows = _parse_freeze_matrix()
    by_id = {row["ID"].strip("`"): row for row in rows}
    dlg = by_id["SET-DLG"]
    assert dlg["Support disposition"] == "EXPERIMENTAL"
    assert "DEF-W03-001" in dlg["Open gap"]
    assert "W37" in dlg["Verification owner Wave"]


def test_capability_gate__lacking_capability_is_not_executable():
    """TRUTH-068 at the contract layer: a missing capability refuses with a
    diagnosable reason; a declared one allows."""
    from hpc_gui.services.plugin_menu_actions import can_execute_action

    allowed, _ = can_execute_action("editor.lint_current", _fake_plugin(capabilities=("lint-rules",)))
    assert allowed is True
    allowed, reason = can_execute_action("editor.lint_current", _fake_plugin(capabilities=()))
    assert allowed is False
    assert "capability" in reason
    allowed, _ = can_execute_action("no.such.action", _fake_plugin(capabilities=("lint-rules",)))
    assert allowed is False


def test_plugin_menu__lacking_capability_renders_disabled_and_unbound(wx_app, monkeypatch):
    """TRUTH-065/068 behaviorally: an action whose capability the provider
    lacks renders disabled AND unbound (forcing its event is a provable
    no-op); policy-blocked trusted-tool stays disabled even with caps."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.plugins.ui_contributions as contributions
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake_a = _fake_plugin("w04-fake-a", capabilities=())
    fake_b = _fake_plugin("w04-fake-b", capabilities=("linter-tool",))
    contrib_a = contributions.PluginMenuContribution(
        plugin_id="w04-fake-a",
        plugin_version="0",
        label="W04 Fake A",
        labels={},
        items=(
            contributions.PluginMenuAction(
                id="a-lint",
                label="Lint now",
                labels={},
                action="editor.lint_current",
                when={},
                unavailable="disable",
            ),
        ),
    )
    contrib_b = contributions.PluginMenuContribution(
        plugin_id="w04-fake-b",
        plugin_version="0",
        label="W04 Fake B",
        labels={},
        items=(
            contributions.PluginMenuAction(
                id="a-tool",
                label="Open tool",
                labels={},
                action="plugin.open_trusted_tool",
                when={},
                unavailable="disable",
            ),
        ),
    )
    monkeypatch.setattr(
        loader_module,
        "load_installed_plugins",
        lambda: types.SimpleNamespace(plugins=[fake_a, fake_b]),
    )
    monkeypatch.setattr(
        contributions,
        "collect_plugin_menu_contributions",
        lambda _plugins: [contrib_a, contrib_b],
    )
    dispatched = []
    monkeypatch.setattr(
        actions_module,
        "dispatch_plugin_menu_action",
        lambda *args, **kwargs: dispatched.append((args, kwargs)) or True,
    )

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert callable(frame._wx_rebuild_plugins_menu)
        frame._wx_rebuild_plugins_menu()
        plugins_menu = frame._wx_shell_plugins_menu
        roots = [
            item
            for item in plugins_menu.GetMenuItems()
            if item.GetSubMenu() is not None
            and item.GetItemLabelText() in ("W04 Fake A", "W04 Fake B")
        ]
        assert len(roots) == 2, "fake contributions must rebuild into the Plugins menu"
        children = [
            item
            for root in roots
            for item in root.GetSubMenu().GetMenuItems()
            if not item.IsSeparator()
        ]
        assert len(children) == 2
        for child in children:
            assert not child.IsEnabled(), f"{child.GetItemLabelText()} must render disabled"
            # Forced delivery to a disabled+unbound item must not dispatch.
            frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, child.GetId()))
            wx.Yield()
        assert dispatched == [], "disabled capability-gated items must stay unbound"
    finally:
        _close_shell(frame)


def test_plugin_action__stale_plugin__visible_coded_error(wx_app, monkeypatch):
    """TRUTH-067/072: clicking a menu action whose plugin vanished (rebuild
    raced an uninstall) shows exactly one coded error, never silence."""
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "ghost-plugin-id")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(capture.calls) == 1, "stale plugin click must produce exactly one error dialog"
    text = capture.texts[0]
    assert "could not be completed" in text
    assert "ghost-plugin-id" in text, "stale identity must be diagnosable"
    assert re.search(r"PLUGIN-[0-9A-F]{6}", text), f"stable code missing: {text!r}"


def test_plugin_action__exception__visible_coded_error(wx_app, monkeypatch):
    """TRUTH-072: a dispatch exception is a visible coded error, not a
    log-only entry with a success-looking UI."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake = _fake_plugin("w04-p1", capabilities=("lint-rules",))
    monkeypatch.setattr(
        loader_module, "load_installed_plugins", lambda: types.SimpleNamespace(plugins=[fake])
    )

    boom = RuntimeError("boom-plugin-action")

    def _raise(*args, **kwargs):
        raise boom

    monkeypatch.setattr(actions_module, "dispatch_plugin_menu_action", _raise)
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "w04-p1")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(capture.calls) == 1
    assert re.search(r"PLUGIN-[0-9A-F]{6}", capture.texts[0])


def test_plugin_action__success__silent(wx_app, monkeypatch):
    """Happy-path guard: a successful plugin action dispatches once and
    shows no error dialog."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake = _fake_plugin("w04-p1", capabilities=("lint-rules",))
    monkeypatch.setattr(
        loader_module, "load_installed_plugins", lambda: types.SimpleNamespace(plugins=[fake])
    )
    dispatched = []
    monkeypatch.setattr(
        actions_module,
        "dispatch_plugin_menu_action",
        lambda *args, **kwargs: dispatched.append((args, kwargs)) or True,
    )
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "w04-p1")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(dispatched) == 1
    assert capture.calls == []


def test_terminal__disconnected_warns_instead_of_dead_session(wx_app, monkeypatch):
    """TRUTH-066: opening the terminal with no session warns visibly and
    returns CANCEL — never a dead terminal frame."""
    from hpc_gui.wx_terminal import show_terminal

    capture = _MessageBoxCapture(monkeypatch)
    before = set(wx.GetTopLevelWindows())
    assert show_terminal(None, ssh=None) == wx.ID_CANCEL
    assert len(capture.calls) == 1
    assert set(wx.GetTopLevelWindows()) == before
