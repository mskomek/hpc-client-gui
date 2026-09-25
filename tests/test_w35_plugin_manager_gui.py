"""W35 execution tests: wx Plugin Manager backend-driven GUI.

Owned requirements (waves/pending/W35.md):
  H0 Browse/Manage/Updates + search/filter + refresh + install/update +
  remove/enable/disable + compat/status + restart-required + offline/cache
  distinguishability + close-in-flight lifetime safety.

Live owners:
  src/hpc_gui/wx_plugins.py (WxPluginManagerModel)
  src/hpc_gui/wx_plugins_view.py (wx event wiring)

All storage uses disposable tmp roots; registry fetchers are injected; no
network, no real user config, no CWD dependence. GUI claims use real wx
runtime (event -> backend -> list/status readback).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from hpc_gui.wx_plugins import WxPluginManagerModel

APP_VERSION = "1.5.9"

REPO_META = {
    "owner": "mskomek",
    "name": "hpc-client-gui-plugins",
    "raw_base": "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/",
}

VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": dict(REPO_META),
    "plugins": [
        {
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": "1.0.0",
            "plugin_api": 1,
            "type": "cluster-profile",
            "description": "TRUBA system profile.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=1.3.0",
            "manifest_path": "plugins/truba/1.0.0/manifest.json",
            "manifest_sha256": "a" * 64,
            "official": True,
        },
        {
            "id": "org.hpcclient.future",
            "name": "Future",
            "version": "9.9.9",
            "plugin_api": 1,
            "type": "lint-rules",
            "description": "Needs a newer app.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=99.0.0",
            "manifest_path": "plugins/future/9.9.9/manifest.json",
            "manifest_sha256": "b" * 64,
            "official": True,
        },
    ],
}


def _payload(registry: dict | None = None) -> bytes:
    return json.dumps(registry if registry is not None else VALID_REGISTRY).encode()


def _pump(wx, seconds: float = 0.05) -> None:
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass
    time.sleep(seconds)
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass


def _wait_until(predicate, timeout: float = 8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import wx as _wx

            try:
                _wx.YieldIfNeeded()
            except Exception:
                pass
        except Exception:
            pass
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


# ---------------------------------------------------------------------------
# FIX-A: real refresh path with network/cache/offline distinguishability
# REQ-H0 refresh + offline + browse truthfulness
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_w35_model_refresh_merges_registry_with_source(tmp_path: Path):
    """REQ-H0/DEF-W35-001: registry+installed+compat merge exposes the source."""
    from hpc_gui.plugins.storage import write_active_versions

    model = WxPluginManagerModel(root=tmp_path, app_version=APP_VERSION)
    cards = model.build_cards_from_registry(
        json.loads(json.dumps(VALID_REGISTRY)), "network", root=tmp_path
    )
    assert model.registry_source == "network"
    by_id = {c.plugin_id: c for c in cards}
    # Compatible entry is offered; incompatible entry is visible but gated.
    assert by_id["org.hpcclient.truba"].compatible is True
    assert by_id["org.hpcclient.future"].compatible is False
    assert by_id["org.hpcclient.truba"].installed is False
    # Installing (activating) flips the Manage Installed readback.
    write_active_versions({"org.hpcclient.truba": "1.0.0"}, root=tmp_path)
    cards2 = model.build_cards_from_registry(
        json.loads(json.dumps(VALID_REGISTRY)), "cache", root=tmp_path
    )
    assert model.registry_source == "cache"
    by_id2 = {c.plugin_id: c for c in cards2}
    assert by_id2["org.hpcclient.truba"].installed is True
    # NEG: unknown source fails closed to offline.
    model.build_cards_from_registry({"plugins": []}, "satellite", root=tmp_path)
    assert model.registry_source == "offline"


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w35_wx_refresh_event_drives_real_backend_and_status(tmp_path: Path):
    """FIX-A FULL (REQ-H0 refresh/offline): wx event -> fetch -> list+status readback."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_plugins_view import build_plugins_panel

    def network_fetch(url: str, limit: int) -> bytes:
        assert "raw.githubusercontent.com" in url
        return _payload()

    model = WxPluginManagerModel(
        root=tmp_path, fetcher=network_fetch, app_version=APP_VERSION
    )
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w35-refresh-probe")
    try:
        panel = build_plugins_panel(frame, model, root=tmp_path, initial_tab="discover")
        controls = panel._wx_plugins_controls
        state = panel._wx_plugins_state
        listing = controls["listing"]
        status = controls["status"]
        refresh_btn = controls["refresh"]
        assert listing.GetItemCount() == 0
        # Real wx runtime: post a genuine button event through the handler.
        click = wx.CommandEvent(wx.EVT_BUTTON.typeId, refresh_btn.GetId())
        refresh_btn.GetEventHandler().ProcessEvent(click)
        assert state["in_flight"] is True
        ok = _wait_until(lambda: state["in_flight"] is False, timeout=8.0)
        assert ok, "refresh worker never completed"
        assert model.registry_source == "network"
        assert "Online" in status.GetLabel()
        assert listing.GetItemCount() == 2
        assert listing.GetItemText(0, 1) != ""
        # NEG: network down with a good cache falls back to distinguishable cache.
        def failing_fetch(url: str, limit: int) -> bytes:
            raise OSError("network down")

        model.fetcher = failing_fetch
        click2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, refresh_btn.GetId())
        refresh_btn.GetEventHandler().ProcessEvent(click2)
        ok2 = _wait_until(lambda: state["in_flight"] is False, timeout=8.0)
        assert ok2
        assert model.registry_source == "cache"
        assert "Cached" in status.GetLabel()
        # NEG2: network down with no cache is distinguishable offline (fresh root).
        from pathlib import Path as _Path
        import tempfile as _tempfile

        with _tempfile.TemporaryDirectory() as fresh:
            from hpc_gui.wx_plugins_view import build_plugins_panel as _build2

            fresh_model = WxPluginManagerModel(
                root=_Path(fresh), fetcher=failing_fetch, app_version=APP_VERSION
            )
            frame2 = wx.Frame(None, title="w35-offline-probe")
            try:
                panel2 = _build2(frame2, fresh_model, root=_Path(fresh))
                controls2 = panel2._wx_plugins_controls
                state2 = panel2._wx_plugins_state
                refresh2 = controls2["refresh"]
                status2 = controls2["status"]
                click3 = wx.CommandEvent(wx.EVT_BUTTON.typeId, refresh2.GetId())
                refresh2.GetEventHandler().ProcessEvent(click3)
                ok3 = _wait_until(lambda: state2["in_flight"] is False, timeout=8.0)
                assert ok3
                assert fresh_model.registry_source == "offline"
                assert "Offline" in status2.GetLabel()
            finally:
                try:
                    frame2.Destroy()
                except Exception:
                    pass
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FIX-B: truthful search + distinct Browse/Manage/Updates views
# REQ-H0 search/filter + Browse/Manage/Updates distinct states
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_w35_model_views_and_search_are_distinct(tmp_path: Path):
    """REQ-H0/DEF-W35-002+003: views differ and search actually filters."""
    from hpc_gui.plugins.storage import write_active_versions

    model = WxPluginManagerModel(root=tmp_path, app_version=APP_VERSION)
    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": dict(REPO_META),
        "plugins": [
            {
                "id": "org.hpcclient.truba",
                "name": "TRUBA",
                "version": "1.0.0",
                "type": "cluster-profile",
                "description": "TRUBA profile",
                "publisher": "HPC Client GUI",
                "requires_app": ">=1.3.0",
            },
            {
                "id": "org.hpcclient.fluent",
                "name": "Fluent Tools",
                "version": "0.2.0",
                "type": "lint-rules",
                "description": "Fluent lint pack",
                "publisher": "HPC Client GUI",
                "requires_app": ">=1.3.0",
            },
        ],
    }
    write_active_versions({"org.hpcclient.truba": "0.9.0"}, root=tmp_path)
    model.build_cards_from_registry(registry, "network", root=tmp_path)
    # Distinct states: discover has both, installed only the installed one,
    # updates only the stale installed one with a newer compatible release.
    assert len(model.filtered_cards("discover", "")) == 2
    installed = model.filtered_cards("installed", "")
    assert [c.plugin_id for c in installed] == ["org.hpcclient.truba"]
    updates = model.filtered_cards("updates", "")
    assert [c.plugin_id for c in updates] == ["org.hpcclient.truba"]
    assert updates[0].update_available is True
    # Search truthfulness: a visible query box with a no-op handler is forbidden.
    assert len(model.filtered_cards("discover", "fluent")) == 1
    assert model.filtered_cards("discover", "fluent")[0].plugin_id == "org.hpcclient.fluent"
    assert model.filtered_cards("discover", "no-such-plugin-xyz") == ()
    # NEG: unknown view fails closed to discover (never an empty trap).
    assert len(model.filtered_cards("bogus-view", "")) == 2


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w35_wx_search_and_views_rebuild_truthful_lists(tmp_path: Path):
    """FIX-B FULL: search text + view choice rebuild the visible list."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_plugins_view import build_plugins_panel

    model = WxPluginManagerModel(root=tmp_path, app_version=APP_VERSION)
    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": dict(REPO_META),
        "plugins": [
            {
                "id": "org.hpcclient.truba",
                "name": "TRUBA",
                "version": "1.0.0",
                "type": "cluster-profile",
                "description": "TRUBA profile",
                "publisher": "HPC Client GUI",
                "requires_app": ">=1.3.0",
            },
            {
                "id": "org.hpcclient.fluent",
                "name": "Fluent Tools",
                "version": "0.2.0",
                "type": "lint-rules",
                "description": "Fluent lint pack",
                "publisher": "HPC Client GUI",
                "requires_app": ">=1.3.0",
            },
        ],
    }
    from hpc_gui.plugins.storage import write_active_versions

    write_active_versions({"org.hpcclient.truba": "1.0.0"}, root=tmp_path)
    model.build_cards_from_registry(registry, "cache", root=tmp_path)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w35-search-probe")
    try:
        panel = build_plugins_panel(frame, model, root=tmp_path, initial_tab="discover")
        controls = panel._wx_plugins_controls
        listing = controls["listing"]
        search = controls["search"]
        view = controls["view"]
        assert listing.GetItemCount() == 2
        # Search actually filters the visible rows (ListCtrl rebuild, not hide).
        search.SetValue("fluent")
        _pump(wx)
        assert listing.GetItemCount() == 1
        assert listing.GetItemText(0, 0) == "Fluent Tools"
        search.SetValue("no-such-plugin-xyz")
        _pump(wx)
        assert listing.GetItemCount() == 0
        search.SetValue("")
        _pump(wx)
        assert listing.GetItemCount() == 2
        # Distinct views: Manage Installed shows only the installed card.
        view.SetSelection(1)  # installed
        evt = wx.CommandEvent(wx.EVT_CHOICE.typeId, view.GetId())
        view.GetEventHandler().ProcessEvent(evt)
        _pump(wx)
        assert listing.GetItemCount() == 1
        assert listing.GetItemText(0, 0) == "TRUBA"
        # Browse restores both.
        view.SetSelection(0)  # discover
        evt2 = wx.CommandEvent(wx.EVT_CHOICE.typeId, view.GetId())
        view.GetEventHandler().ProcessEvent(evt2)
        _pump(wx)
        assert listing.GetItemCount() == 2
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Fail-closed install + lifecycle safety (H0 items 3 and 5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_w35_install_without_backend_action_is_not_success(tmp_path: Path):
    """REQ-H0/DEF-W35-004: no installer callback means no success signal."""
    model = WxPluginManagerModel(root=tmp_path, app_version=APP_VERSION)
    assert model.install is None
    # NEG: without a backend the call yields no action (caller must show error).
    assert model.install_or_update({"id": "org.hpcclient.truba", "version": "1.0.0"}) is None
    assert model.install_or_update({}) is None
    # Happy path with a real callback still reaches the backend exactly once.
    seen: list[dict] = []
    model2 = WxPluginManagerModel(
        root=tmp_path, install=seen.append, app_version=APP_VERSION
    )
    model2.install_or_update({"id": "org.hpcclient.truba", "version": "1.0.0"})
    assert len(seen) == 1 and seen[0]["id"] == "org.hpcclient.truba"


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w35_wx_close_in_flight_never_touches_destroyed_controls(tmp_path: Path):
    """REQ-H0 lifecycle: closing mid-refresh drops the stale callback safely."""
    wx = pytest.importorskip("wx")
    import threading

    from hpc_gui.wx_plugins_view import build_plugins_panel

    release = threading.Event()

    def slow_fetch(url: str, limit: int) -> bytes:
        assert release.wait(timeout=8.0)
        return _payload()

    model = WxPluginManagerModel(
        root=tmp_path, fetcher=slow_fetch, app_version=APP_VERSION
    )
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w35-lifecycle-probe")
    try:
        panel = build_plugins_panel(frame, model, root=tmp_path)
        controls = panel._wx_plugins_controls
        state = panel._wx_plugins_state
        refresh_btn = controls["refresh"]
        click = wx.CommandEvent(wx.EVT_BUTTON.typeId, refresh_btn.GetId())
        refresh_btn.GetEventHandler().ProcessEvent(click)
        assert state["in_flight"] is True
        # Close while the worker is still in flight (stale generation).
        state["closed"] = True
        stale_gen = state["gen"]
        release.set()
        ok = _wait_until(lambda: state["in_flight"] is False, timeout=8.0)
        assert ok
        # The stale callback was dropped: no cards were pushed after close.
        assert state["gen"] == stale_gen
        assert model.cards == ()
    finally:
        release.set()
        try:
            frame.Destroy()
        except Exception:
            pass
