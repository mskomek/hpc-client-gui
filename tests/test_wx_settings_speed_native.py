from __future__ import annotations

import threading
import time

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]


@pytest.fixture
def app():
    instance = wx.App.Get() or wx.App(False)
    yield instance


def _pump(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not predicate():
        app.Yield(True)
        time.sleep(0.01)
    assert predicate(), "wx event loop did not reach expected state"


def _connection():
    class Files:
        def upload(self, _local, _remote):
            pass

        def download(self, _remote, _local):
            pass

        def remove(self, _remote):
            pass

    session = {
        "connected": True,
        "files": Files(),
        "profile": {"system": {"scratch_dir": "/scratch/{user}"}, "username": "tester"},
    }
    return {"connection_status": "connected", "session": session, "generation": 1}


def test_settings_speed_test_button_runs_in_worker_and_prevents_duplicate(app, monkeypatch):
    import hpc_gui.wx_settings_view as view

    started = threading.Event()
    release = threading.Event()
    worker_ids = []
    shown = []

    def run(files, *, remote_dir, size_mib):
        worker_ids.append(threading.get_ident())
        assert files is not None
        assert remote_dir == "/scratch/tester"
        assert size_mib == 32
        started.set()
        assert release.wait(3)
        return {"size_mib": 32, "upload_mib_s": 10.0, "download_mib_s": 12.0}

    monkeypatch.setattr(view, "run_transfer_speed_test", run)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)
    from hpc_gui.wx_settings import WxSettingsModel

    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, WxSettingsModel(), session_state=_connection())
    controls = host._wx_settings_controls
    controls["speed_test_size"].SetSelection(1)
    gui_thread = threading.get_ident()
    controls["speed_test"].Command(wx.CommandEvent(wx.wxEVT_BUTTON, controls["speed_test"].GetId()))
    assert started.wait(2)
    assert not controls["speed_test"].IsEnabled()
    controls["speed_test"].Command(wx.CommandEvent(wx.wxEVT_BUTTON, controls["speed_test"].GetId()))
    assert len(worker_ids) == 1
    release.set()
    _pump(app, lambda: bool(shown))
    assert worker_ids[0] != gui_thread
    assert "32" in shown[0]
    host.Close()
    frame.Destroy()


def test_settings_speed_test_result_is_ignored_after_session_change(app, monkeypatch):
    import hpc_gui.wx_settings_view as view
    from hpc_gui.wx_settings import WxSettingsModel

    started = threading.Event()
    release = threading.Event()
    shown = []

    def run(*_args, **_kwargs):
        started.set()
        assert release.wait(3)
        return {"size_mib": 8, "upload_mib_s": 1.0, "download_mib_s": 1.0}

    monkeypatch.setattr(view, "run_transfer_speed_test", run)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)
    frame = wx.Frame(None)
    state = _connection()
    host = view.build_settings_panel(frame, WxSettingsModel(), session_state=state)
    button = host._wx_settings_controls["speed_test"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    assert started.wait(2)
    state["generation"] += 1
    release.set()
    _pump(app, lambda: not host._wx_settings_state["speed_test_running"] if "speed_test_running" in host._wx_settings_state else True)
    for _ in range(20):
        app.Yield(True)
        time.sleep(0.01)
    assert not shown
    host.Close()
    frame.Destroy()
