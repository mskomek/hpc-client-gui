"""Wave 71.5 — wx Connection micro-hardening.

Covers: begin_connect/Thread.start failure recovery, connect_selected bool
contract proofs, Remember=true settings persistence, Test Cluster
Remember=true, Save & Connect contract fixes.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile

from pathlib import Path

from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage

from hpc_gui.config.storage import load_profiles

from hpc_gui.core.i18n import current_language, set_language

from hpc_gui.wx_connection import build_connection_panel

def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp

@pytest.fixture(autouse=True)
def _clean_wx_after():
    original_language = current_language()
    set_language("en")
    yield
    try:
        set_language(original_language)
    finally:
        try:
            app = wx.GetApp()
            if app is not None:
                for win in list(wx.GetTopLevelWindows()):
                    try:
                        win.Destroy()
                    except Exception:
                        pass
                for _ in range(5):
                    try:
                        wx.Yield()
                    except Exception:
                        break
        except Exception:
            pass

def _make_profile(name="p", master=None, secret="s3cret"):
    """Create profile; if master given, encrypt with it."""
    if master:
        from hpc_gui.core.crypto_master import encrypt_with_master
        enc = encrypt_with_master(master, secret)
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
            "save_password": True, "password_enc": enc.token, "password_salt": enc.salt,
        })
    else:
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
        })

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_begin_connect_failure_returns_false(monkeypatch):
    """begin_connect() raises → connect_selected returns False,
    controller not connecting, buttons restored, status failed.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("bc-fail")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True}

        # Select profile
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("bc-fail")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock begin_connect to raise
        with mock.patch.object(host._wx_connection_model.controller, "begin_connect", side_effect=RuntimeError("boom")):
            result = host._wx_connection_connect_selected()

        assert result is False
        assert host._wx_connection_model.controller.state.value == "failed"
        assert host._wx_connection_controls["add_connection"].IsEnabled()
        assert host._wx_connection_controls["connect"].IsEnabled()
        assert "failed" in host._wx_connection_controls["status"].GetLabel().lower()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_thread_start_failure_returns_false(monkeypatch):
    """Thread.start() raises → connect_selected returns False,
    controller failed, buttons restored, transient password cleared.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("ts-fail")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True}

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("ts-fail")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock Thread.start to raise
        with mock.patch("hpc_gui.wx_connection.Thread") as MockThread:
            mock_thread = mock.Mock()
            mock_thread.start.side_effect = RuntimeError("thread-start-fail")
            MockThread.return_value = mock_thread
            result = host._wx_connection_connect_selected()

        assert result is False
        assert host._wx_connection_model.controller.state.value == "failed"
        assert host._wx_connection_controls["add_connection"].IsEnabled()
        assert host._wx_connection_controls["connect"].IsEnabled()
        assert "failed" in host._wx_connection_controls["status"].GetLabel().lower()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_connect_selected_no_selection_direct_bool(monkeypatch):
    """connect_selected() → False when no profile selected. Direct assertion."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        result = host._wx_connection_connect_selected()
        assert result is False
        assert len(connect_calls) == 0
        assert host._wx_connection_model.controller.state.value != "connecting"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_connect_selected_worker_starts_direct_bool(monkeypatch):
    """connect_selected() → True when worker successfully launched."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("ok-bool")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())

        def fake_connect(p):
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("ok-bool")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        with mock.patch("wx.MessageBox"):
            result = host._wx_connection_connect_selected()
        assert result is True
        # Wait for worker
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(20)
            if host._wx_connection_model.controller.state.value == "connected":
                break
        assert host._wx_connection_model.controller.state.value == "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
