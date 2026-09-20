"""W02 error-governance regression tests for the wx shell dispatch.

Purpose IDs:
  DEF-W02-001  silent ``except Exception: pass`` on user-visible dispatch
               (FIX-W02-A). Every branch below must produce a visible,
               diagnosable error instead of a silent no-op.
  DEF-W02-002  ``PLUGIN-REQUEST`` ignored ``webbrowser.open() == False``
               (FIX-W02-B). No exception is raised in that case, so the old
               code left the UI in a success-looking state with no browser.
  REQ-W02-TRACE-001  each baseline-visible action reaches its canonical
               owner (dispatch -> view/function contract).
  NEG-W02-*    negative-path proof for every repaired behavior.
  GUI-W02-001  real wx event routing into the failure path.

Owned requirements: ``HPC-W01-TRACE-001``, ``HPC-W01-TODO-ERROR-GOV-001``,
``HPC-W01-TODO-018``, ``HPC-W01-TODO-ERROR-GOV-002``, ``HPC-W01-TODO-020``.
"""

from __future__ import annotations

import logging
import pathlib
import re

import pytest

wx = pytest.importorskip("wx")

from hpc_gui import wx_shell  # noqa: E402
from hpc_gui.core.i18n import load_language  # noqa: E402


@pytest.fixture(autouse=True)
def _english_bundle():
    """Resolve ``t()`` against the English bundle (repo convention)."""
    load_language("en")
    yield
    load_language("en")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MessageBoxCapture:
    """Stand-in for ``wx.MessageBox`` that records instead of blocking."""

    def __init__(self, monkeypatch):
        self.calls = []
        monkeypatch.setattr(wx, "MessageBox", self)

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return wx.OK

    @property
    def texts(self):
        return [args[0] for args, _ in self.calls]


def _fail_dispatch(monkeypatch, command_id, fail_target, fail_module_attr, exc=None):
    """Force ``fail_target`` to raise and run the real dispatch branch."""
    boom = exc if exc is not None else RuntimeError(f"boom-{command_id}")
    monkeypatch.setattr(fail_module_attr[0], fail_module_attr[1], _raise(boom))
    capture = _MessageBoxCapture(monkeypatch)
    wx_shell._dispatch(command_id, None, None, {})
    return capture, boom


def _raise(exc):
    def _impl(*args, **kwargs):
        raise exc

    return _impl


def _assert_visible_error_with_code(capture, boom, area, message_fragment, caplog):
    assert len(capture.calls) == 1, "exactly one visible error dialog is required"
    text = capture.texts[0]
    assert message_fragment in text, f"user message missing from dialog: {text!r}"
    assert "Diagnostic code" in text, f"diagnostic code label missing: {text!r}"
    match = re.search(rf"{area}-[0-9A-F]{{6}}", text)
    assert match, f"stable {area}-XXXXXX code missing from dialog: {text!r}"
    # Structured log entry carries the same error id (no silent failure).
    assert f"Error-ID={match.group(0)}" in caplog.text
    assert f"{type(boom).__name__}: boom" in caplog.text or "boom" in caplog.text
    return match.group(0)


# ---------------------------------------------------------------------------
# FIX-W02-A (DEF-W02-001): silent dispatch failures become visible errors
# NEG-W02-001..005 + HPC-W01-TODO-020 (no success-looking UI on failure)
# ---------------------------------------------------------------------------


def test_settings_failure__dispatch__visible_error_with_code(monkeypatch, caplog):
    """NEG-W02-001: failed Settings open shows a coded error, not silence."""
    import hpc_gui.wx_settings_view as settings_view

    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        capture, boom = _fail_dispatch(
            monkeypatch, "APP-SETTINGS", None, (settings_view, "show_settings")
        )
    _assert_visible_error_with_code(capture, boom, "SETTINGS", "Settings", caplog)


def test_update_check_failure__dispatch__visible_error_with_code(monkeypatch, caplog):
    """NEG-W02-002: failed update dialog shows a coded error, not silence."""
    import hpc_gui.wx_updater_view as updater_view

    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        capture, boom = _fail_dispatch(
            monkeypatch, "APP-UPDATE-CHECK", None, (updater_view, "WxUpdateDialog")
        )
    _assert_visible_error_with_code(capture, boom, "UPDATE", "update dialog", caplog)


def test_send_logs_failure__dispatch__visible_error_with_code(monkeypatch, caplog):
    """NEG-W02-003: failed Send Logs open shows a coded error, not silence."""
    import hpc_gui.wx_send_logs_view as send_logs_view

    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        capture, boom = _fail_dispatch(
            monkeypatch, "APP-SEND-LOGS", None, (send_logs_view, "show_send_logs")
        )
    _assert_visible_error_with_code(capture, boom, "LOGS", "Send Logs", caplog)


def test_about_failure__dispatch__visible_error_with_code(monkeypatch, caplog):
    """NEG-W02-004: failed About open shows a coded error, not silence.

    The success path still uses the real ``wx.Dialog`` (W01 FIX-W01-002);
    only the failure path reports through the error helper.
    """
    import hpc_gui.wx_about as about_view

    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        capture, boom = _fail_dispatch(
            monkeypatch, "APP-ABOUT", None, (about_view, "show_about")
        )
    _assert_visible_error_with_code(capture, boom, "ABOUT", "About", caplog)


def test_plugin_manager_failure__dispatch__visible_error_with_code(monkeypatch, caplog):
    """NEG-W02-005: failed Plugin Manager open shows a coded error."""
    import hpc_gui.wx_plugins_view as plugins_view

    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        capture, boom = _fail_dispatch(
            monkeypatch, "PLUGIN-MANAGE", None, (plugins_view, "show_plugins")
        )
    _assert_visible_error_with_code(capture, boom, "PLUGIN", "Plugin Manager", caplog)


def test_plugin_manager_legacy_signature__dispatch__falls_back_without_error(monkeypatch):
    """Happy-path guard: the ``TypeError`` fallback still opens the manager
    without showing an error (pre-existing contract preserved)."""
    import hpc_gui.wx_plugins_view as plugins_view

    seen = []

    def fake_show_plugins(*args, **kwargs):
        if "initial_tab" in kwargs:
            raise TypeError("unexpected keyword 'initial_tab'")
        seen.append((args, kwargs))

    monkeypatch.setattr(plugins_view, "show_plugins", fake_show_plugins)
    capture = _MessageBoxCapture(monkeypatch)
    wx_shell._dispatch("PLUGIN-BROWSE", None, None, {})
    assert len(seen) == 1, "legacy fallback must still open the manager"
    assert capture.calls == [], "no error dialog on the successful fallback path"


def test_about_success__dispatch__no_error_dialog(monkeypatch):
    """Happy-path guard: a working About open shows no error dialog."""
    import hpc_gui.wx_about as about_view

    seen = []
    monkeypatch.setattr(about_view, "show_about", lambda *a, **k: seen.append((a, k)))
    capture = _MessageBoxCapture(monkeypatch)
    wx_shell._dispatch("APP-ABOUT", None, None, {})
    assert len(seen) == 1
    assert capture.calls == []


def test_error_codes__unique_per_failure(monkeypatch, caplog):
    """ERROR-GOV-002: every visible failure gets its own diagnosable code."""
    import hpc_gui.wx_about as about_view

    monkeypatch.setattr(about_view, "show_about", _raise(RuntimeError("boom-one")))
    capture = _MessageBoxCapture(monkeypatch)
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        wx_shell._dispatch("APP-ABOUT", None, None, {})
        first = capture.texts[0]
    monkeypatch.setattr(about_view, "show_about", _raise(RuntimeError("boom-two")))
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        wx_shell._dispatch("APP-ABOUT", None, None, {})
        second = capture.texts[1]
    first_id = re.search(r"ABOUT-[0-9A-F]{6}", first).group(0)
    second_id = re.search(r"ABOUT-[0-9A-F]{6}", second).group(0)
    assert first_id != second_id, "each failure needs a distinct diagnostic code"


# ---------------------------------------------------------------------------
# FIX-W02-B (DEF-W02-002): PLUGIN-REQUEST honors webbrowser.open() == False
# ---------------------------------------------------------------------------


def test_plugin_request__browser_false__visible_error(monkeypatch, caplog):
    """DEF-W02-002: no browser and no exception still shows a coded error."""
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: False)
    capture = _MessageBoxCapture(monkeypatch)
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        wx_shell._dispatch("PLUGIN-REQUEST", None, None, {})
    assert len(capture.calls) == 1
    assert "plugin request page" in capture.texts[0]
    assert re.search(r"PLUGIN-[0-9A-F]{6}", capture.texts[0])


def test_plugin_request__browser_exception__visible_error(monkeypatch, caplog):
    """PLUGIN-REQUEST raising inside webbrowser.open shows a coded error."""
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", _raise(OSError("boom-browser")))
    capture = _MessageBoxCapture(monkeypatch)
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        wx_shell._dispatch("PLUGIN-REQUEST", None, None, {})
    assert len(capture.calls) == 1
    assert "plugin request page" in capture.texts[0]
    assert re.search(r"PLUGIN-[0-9A-F]{6}", capture.texts[0])
    assert "boom-browser" in caplog.text


def test_plugin_request__browser_ok__no_error(monkeypatch):
    """Happy-path guard: an opened browser shows no error dialog."""
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: True)
    capture = _MessageBoxCapture(monkeypatch)
    wx_shell._dispatch("PLUGIN-REQUEST", None, None, {})
    assert capture.calls == []


# ---------------------------------------------------------------------------
# REQ-W02-TRACE-001: dispatch reaches its canonical owner (contract test)
# ---------------------------------------------------------------------------

_DISPATCH_OWNERS = [
    ("APP-SETTINGS", "wx_settings_view", "show_settings"),
    ("APP-UPDATE-CHECK", "wx_updater_view", "WxUpdateDialog"),
    ("APP-SEND-LOGS", "wx_send_logs_view", "show_send_logs"),
    ("APP-ABOUT", "wx_about", "show_about"),
    ("PLUGIN-BROWSE", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-MANAGE", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-UPDATES", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-REQUEST", "plugin_manager_dialog", "PLUGIN_REQUEST_URL"),
    ("APP-HELP", "wx_help", "show_help"),
    ("APP-CONNECT", "wx_connection", "show_connection"),
    ("NAV-FILES", "wx_local_files", "show_local_files"),
    ("NAV-DIRECTORIES", "wx_directories_view", "show_directories"),
    ("NAV-LOGS", "wx_logs_view", "show_logs"),
    ("NAV-JOBS", "wx_jobs", "show_jobs"),
    ("NAV-TERMINAL", "wx_terminal", "show_terminal"),
    ("NAV-EDITOR", "wx_shell", "open_primary"),
]


def _dispatch_block(src, command_id):
    """Extract the ``_dispatch`` branch handling ``command_id``.

    Branches use either ``command_id == "X"`` or
    ``command_id in {"X", ...}``; menu bindings elsewhere reference the same
    ids, so anchor on the ``if/elif command_id`` statement itself.
    """
    pattern = re.compile(
        r"(?:if|elif)\s+command_id\s*(?:==|in)\s*[^\n]*\"" + re.escape(command_id) + r"\"[^\n]*\n"
    )
    match = pattern.search(src)
    assert match, f"no dispatch branch for {command_id}"
    start = match.start()
    end = src.find("\n    elif ", start)
    return src[start : end if end != -1 else len(src)]


@pytest.mark.parametrize("command_id,owner_module,owner_symbol", _DISPATCH_OWNERS)
def test_dispatch__reaches_canonical_owner(command_id, owner_module, owner_symbol):
    """REQ-W02-TRACE-001: every baseline-visible action traces
    requirement -> live implementation owner in ``_dispatch``."""
    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    block = _dispatch_block(src, command_id)
    assert owner_symbol in block, (
        f"{command_id} does not reach canonical owner {owner_module}.{owner_symbol}"
    )


def test_dispatch__no_silent_pass_on_mandatory_branches():
    """ERROR-GOV-001 inventory lock: the six remediated mandatory branches
    must not regress to bare ``except ...: pass``."""
    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    for command_id in (
        "APP-SETTINGS",
        "APP-UPDATE-CHECK",
        "APP-SEND-LOGS",
        "APP-ABOUT",
        "PLUGIN-BROWSE",
        "PLUGIN-REQUEST",
    ):
        block = _dispatch_block(src, command_id)
        lines = [line.strip() for line in block.splitlines()]
        for i, line in enumerate(lines):
            if line == "pass" and i > 0 and lines[i - 1].startswith("except"):
                raise AssertionError(f"silent except-pass regressed in {command_id}")
        assert "report_wx_action_error" in block, (
            f"{command_id} must report failures through the error helper"
        )


def test_error_helper__wx_unavailable__still_logs_with_code(monkeypatch, caplog):
    """Capability absence: without an importable ``wx``, the failure is still
    logged with a stable code instead of becoming silent (dialog best-effort)."""
    import sys

    from hpc_gui.core import wx_errors

    monkeypatch.setitem(sys.modules, "wx", None)
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        err_id = wx_errors.report_wx_action_error(
            None,
            area="SETTINGS",
            message_key="settings.open_failed",
            exc=RuntimeError("boom-no-wx"),
        )
    assert str(err_id).startswith("SETTINGS-")
    assert f"Error-ID={err_id}" in caplog.text


def test_editor_save__local_and_remote_paths_have_distinct_owners():
    """TRACE-001: local editor save and remote (SFTP) editor save are not
    collapsed into one path — they have different semantics and owners."""
    shell_src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    editor_src = pathlib.Path("src/hpc_gui/wx_editor_view.py").read_text(encoding="utf-8")
    # Remote save: SFTP backend through the session file service.
    assert "def save_remote(path, content)" in shell_src
    assert "files.write_text(path, content)" in shell_src
    # Local save: local filesystem through the editor view.
    assert "Path(snapshot.path).write_text" in editor_src
    assert "def save_remote" not in editor_src, (
        "remote save must stay with the session/SFTP owner, not the local view"
    )


# ---------------------------------------------------------------------------
# FIX-W02-C (DEF-W02-003): Settings Apply never reports success on failure
# NEG-W02-006/007 + HPC-W01-TODO-020 + HPC-W01-TODO-ERROR-GOV-002
# ---------------------------------------------------------------------------


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def _build_settings_host(model=None):
    from hpc_gui.wx_settings_view import build_settings_panel

    parent = wx.Frame(None, title="w02-settings-parent")
    host = build_settings_panel(parent, model=model)
    return parent, host


def _click(button):
    button.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))


def _wait_for_dialog(capture, timeout_s=10.0):
    import time

    deadline = time.monotonic() + timeout_s
    while not capture.calls and time.monotonic() < deadline:
        time.sleep(0.01)
    assert capture.calls, "expected a visible dialog from the Apply worker"


def test_settings_apply__staging_failure__coded_error_no_ok(wx_app, monkeypatch):
    """NEG-W02-006: a rejected setting shows a coded error, never "OK"."""
    from hpc_gui.wx_settings import WxSettingsModel

    model = WxSettingsModel({})

    def _reject(key, value):
        raise KeyError(key)

    monkeypatch.setattr(model, "set_global", _reject)
    # Apply worker runs on a daemon thread; run CallAfter inline for determinism.
    monkeypatch.setattr(wx, "CallAfter", lambda func, *a, **k: func(*a, **k))
    capture = _MessageBoxCapture(monkeypatch)
    parent, host = _build_settings_host(model)
    try:
        _click(host._wx_settings_controls["apply"])
        _wait_for_dialog(capture)
    finally:
        parent.Destroy()
    assert len(capture.calls) == 1
    text = capture.texts[0]
    assert "could not be applied" in text
    assert re.search(r"SETTINGS-[0-9A-F]{6}", text), f"stable code missing: {text!r}"


def test_settings_apply__success__ok_without_error(wx_app, monkeypatch):
    """Happy-path guard: a clean Apply still reports "OK" with no error code."""
    from hpc_gui.wx_settings import WxSettingsModel

    model = WxSettingsModel({})
    monkeypatch.setattr(wx, "CallAfter", lambda func, *a, **k: func(*a, **k))
    capture = _MessageBoxCapture(monkeypatch)
    parent, host = _build_settings_host(model)
    try:
        _click(host._wx_settings_controls["apply"])
        _wait_for_dialog(capture)
    finally:
        parent.Destroy()
    assert len(capture.calls) == 1
    assert "Diagnostic code" not in capture.texts[0]


def test_settings_apply__backend_failure__coded_error_no_ok(wx_app, monkeypatch):
    """NEG-W02-007: a failing persistence callback shows a coded error."""

    def _boom(snapshot):
        raise OSError("boom-persist")

    from hpc_gui.wx_settings import WxSettingsModel

    model = WxSettingsModel({}, apply=_boom)
    monkeypatch.setattr(wx, "CallAfter", lambda func, *a, **k: func(*a, **k))
    capture = _MessageBoxCapture(monkeypatch)
    parent, host = _build_settings_host(model)
    try:
        _click(host._wx_settings_controls["apply"])
        _wait_for_dialog(capture)
    finally:
        parent.Destroy()
    assert len(capture.calls) == 1
    assert re.search(r"SETTINGS-[0-9A-F]{6}", capture.texts[0])


# ---------------------------------------------------------------------------
# GUI-W02-001: real wx event routing into the failure path
# Required GUI evidence class for W02 (controller-only calls do not count).
# ---------------------------------------------------------------------------


def test_about_menu_event__failure__visible_coded_error(wx_app, monkeypatch):
    """GUI-W02-001: a real EVT_MENU from the Help > About item reaches the
    dispatch failure path and produces a visible, diagnosable error."""
    import hpc_gui.wx_about as about_view
    from hpc_gui.wx_shell import create_shell_frame

    monkeypatch.setattr(about_view, "show_about", _raise(RuntimeError("boom-gui-event")))
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = create_shell_frame(wx_app)
    try:
        about_item = frame._wx_shell_help_items["about"]
        frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, about_item.GetId()))
        wx.Yield()
    finally:
        # Controlled teardown (Close + yields + conditional Destroy): an
        # abrupt Destroy() of the full shell frame corrupts the heap at
        # interpreter exit (see W02 report findings).
        try:
            frame.Close()
        except Exception:
            pass
        for _ in range(3):
            wx.Yield()
        try:
            if not frame.IsBeingDeleted():
                frame.Destroy()
        except Exception:
            pass
        for _ in range(3):
            wx.Yield()
    assert len(capture.calls) == 1, "menu event must produce exactly one error dialog"
    text = capture.texts[0]
    assert "About" in text
    assert re.search(r"ABOUT-[0-9A-F]{6}", text), f"stable code missing: {text!r}"


# ---------------------------------------------------------------------------
# FIX-W02-A2 (DEF-W02-001, post-green review): chrome handlers route through
# the governed _dispatch chokepoint instead of duplicating silent handlers.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "handler,command_id",
    [
        ("_on_plugins", "PLUGIN-BROWSE"),
        ("_on_send_logs", "APP-SEND-LOGS"),
        ("_on_settings", "APP-SETTINGS"),
    ],
)
def test_chrome_handler__routes_through_dispatch(handler, command_id):
    """Post-green review: no duplicate silent implementation path may survive
    next to the remediated ``_dispatch`` branches."""
    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    start = src.index(f"def {handler}(")
    end = src.find("\n    def ", start + 1)
    block = src[start : end if end != -1 else len(src)]
    assert f'_dispatch("{command_id}"' in block, (
        f"{handler} must route through the governed _dispatch chokepoint"
    )
    lines = [line.strip() for line in block.splitlines()]
    for i, line in enumerate(lines):
        if line == "pass" and i > 0 and lines[i - 1].startswith("except"):
            raise AssertionError(f"silent except-pass survives in {handler}")
