"""W41 updater routing regression (ROUTE-001 / ROUTE-002).

Owned requirements: ``HPC-W09-TODO-UPDATER-ROUTE-001``,
``HPC-W09-TODO-UPDATER-ROUTE-002`` (plus state-machine surface
``HPC-W09-UPD-022`` / ``HPC-W09-UPD-075`` exercised through the shared
controller transitions).

Mock boundaries (legitimate only): ``wx.CallAfter`` inline (product posts to
it; no event loop headlessly), ``threading.Thread`` inline join, network
``get_latest_release`` stub returning synthetic releases, ``wx.MessageBox``
capture for the manual-install fallback, ``webbrowser.open`` stub.
``WxUpdateDialog`` is a recording fake driving the real state constants;
dialog construction/layout itself is covered by ``test_wx_updater_spec``.
No product behavior under test is replaced.
"""

from __future__ import annotations

import threading

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.services.app_updater import UpdateRelease
from hpc_gui.wx_updater_view import (
    STATE_CHECKING,
    STATE_FAILED,
    STATE_UPDATE_AVAILABLE,
    STATE_UP_TO_DATE,
)
from hpc_gui import wx_shell


class _FakeInner:
    def Show(self):
        self.shown = True


class _FakeDialog:
    seen_states: list = []

    def __init__(self, parent, release):
        self.parent = parent
        self.release = release
        self.states = []
        self._total = None
        self._whats_new = []
        self._error_message = ""
        self._error_details = ""
        self.dlg = _FakeInner()
        type(self).seen_states.append(self)

    def _build_for_state(self, state):
        self.states.append(state)

    def Destroy(self):
        self.destroyed = True


def _inline_run(monkeypatch):
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    # Liveness probe needs a real top-level window; stub it: the routing
    # under test is worker start + state transition, not window lookup.
    monkeypatch.setattr(wx.Window, "FindWindowById", staticmethod(lambda *a, **k: object()))

    class _InlineThread:
        def __init__(self, target=None, daemon=None, **kwargs):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(threading, "Thread", _InlineThread)


class _FakeParent:
    def GetId(self):
        return 12345


def _release(version, strategy="windows-portable", size=10 * 1024 * 1024):
    return UpdateRelease(
        version=version,
        tag=f"v{version}",
        zip_name="a.zip",
        zip_url="https://example.com/a.zip",
        sha_name="a.sha",
        sha_url="https://example.com/a.sha",
        html_url="https://example.com",
        install_strategy=strategy,
        body="- note",
        size=size,
    )


def test_menu_update_check_reaches_up_to_date_via_real_worker(monkeypatch):
    """ROUTE-001: APP-UPDATE-CHECK starts the worker (no stuck CHECKING)."""
    import hpc_gui.wx_updater_view as updater_view
    import hpc_gui.services.app_updater as au

    _FakeDialog.seen_states = []
    _inline_run(monkeypatch)
    monkeypatch.setattr(updater_view, "WxUpdateDialog", _FakeDialog)
    monkeypatch.setattr(wx_shell, "run_wx_update_check", wx_shell.run_wx_update_check)
    from hpc_gui import __version__ as cur

    monkeypatch.setattr(au, "get_latest_release", lambda timeout=10: _release(cur))
    parent = _FakeParent()
    wx_shell._dispatch("APP-UPDATE-CHECK", parent, None, {})
    assert _FakeDialog.seen_states, "update dialog was never opened"
    states = _FakeDialog.seen_states[-1].states
    assert states[0] == STATE_CHECKING
    assert STATE_UP_TO_DATE in states, f"worker never transitioned: {states}"


def test_menu_update_check_newer_release_reaches_available(monkeypatch):
    import hpc_gui.wx_updater_view as updater_view
    import hpc_gui.services.app_updater as au

    _FakeDialog.seen_states = []
    _inline_run(monkeypatch)
    monkeypatch.setattr(updater_view, "WxUpdateDialog", _FakeDialog)
    monkeypatch.setattr(au, "get_latest_release", lambda timeout=10: _release("99.0.0"))
    parent = _FakeParent()
    wx_shell._dispatch("APP-UPDATE-CHECK", parent, None, {})
    states = _FakeDialog.seen_states[-1].states
    assert STATE_UPDATE_AVAILABLE in states, f"expected UPDATE_AVAILABLE: {states}"


def test_menu_update_check_failure_reaches_failed(monkeypatch):
    import hpc_gui.wx_updater_view as updater_view
    import hpc_gui.services.app_updater as au

    _FakeDialog.seen_states = []
    _inline_run(monkeypatch)
    monkeypatch.setattr(updater_view, "WxUpdateDialog", _FakeDialog)

    def _boom(timeout=10):
        raise RuntimeError("network down")

    monkeypatch.setattr(au, "get_latest_release", _boom)
    parent = _FakeParent()
    wx_shell._dispatch("APP-UPDATE-CHECK", parent, None, {})
    states = _FakeDialog.seen_states[-1].states
    assert STATE_FAILED in states, f"expected FAILED: {states}"
    assert "network down" in _FakeDialog.seen_states[-1]._error_message


def test_single_authoritative_controller(monkeypatch):
    """ROUTE-002: menu dispatch and shell handler share one controller."""
    import inspect
    import pathlib

    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "def run_wx_update_check" in src
    block_start = src.find('command_id == "APP-UPDATE-CHECK"')
    assert block_start != -1
    block = src[block_start : src.find("\n    elif ", block_start)]
    assert "run_wx_update_check" in block, "dispatch must call the shared controller"
    # The shell _on_update handler must delegate (no divergent worker copy).
    on_update = src[src.find("def _on_update") : src.find("def _on_plugins")]
    assert "run_wx_update_check" in on_update
    assert "get_latest_release" not in on_update, "duplicate worker copy forbidden"
    assert callable(wx_shell.run_wx_update_check)
    sig = inspect.signature(wx_shell.run_wx_update_check)
    assert "parent" in sig.parameters
