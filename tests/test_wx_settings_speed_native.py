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


@pytest.fixture(autouse=True)
def _english_ui():
    from hpc_gui.core.i18n import load_language
    load_language("en")
    yield
    load_language("en")


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


@pytest.mark.parametrize("invalidation", ["session-change", "disconnect"])
def test_settings_speed_test_result_is_ignored_after_session_change(app, monkeypatch, invalidation):
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
    if invalidation == "session-change":
        state["generation"] += 1
        state["session"] = _connection()["session"]
    else:
        state["connection_status"] = "disconnected"
        state["session"]["connected"] = False
    release.set()
    _pump(app, lambda: not host._wx_settings_state["speed_test_running"] if "speed_test_running" in host._wx_settings_state else True)
    for _ in range(20):
        app.Yield(True)
        time.sleep(0.01)
    assert not shown
    host.Close()
    frame.Destroy()


def test_settings_close_while_speed_test_runs_ignores_late_result(app, monkeypatch):
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
    host = view.build_settings_panel(frame, WxSettingsModel(), session_state=_connection())
    state = host._wx_settings_state
    button = host._wx_settings_controls["speed_test"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    assert started.wait(2)
    host.Destroy()
    release.set()
    _pump(app, lambda: not state["speed_test_running"])
    assert not shown
    frame.Destroy()


def test_settings_speed_test_failure_is_visible_and_reenables_button(app, monkeypatch, caplog):
    import hpc_gui.wx_settings_view as view
    from hpc_gui.wx_settings import WxSettingsModel

    shown = []

    def fail(*_args, **_kwargs):
        raise OSError("disposable download failure")

    monkeypatch.setattr(view, "run_transfer_speed_test", fail)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, WxSettingsModel(), session_state=_connection())
    button = host._wx_settings_controls["speed_test"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    _pump(app, lambda: bool(shown))
    assert button.IsEnabled()
    assert "Diagnostic code" in shown[0]
    assert "disposable download failure" in caplog.text
    host.Destroy()
    frame.Destroy()


def test_settings_file_associations_list_change_cancel_and_clear(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings_view as view
    from hpc_gui.wx_settings import WxSettingsModel

    associations = {".slurm": "C:/old/editor.exe"}
    writes = []
    monkeypatch.setattr(storage, "get_file_associations", lambda: dict(associations))

    def set_association(extension, path):
        writes.append((extension, path))
        if path:
            associations[extension] = path
        else:
            associations.pop(extension, None)
        return dict(associations)

    monkeypatch.setattr(storage, "set_file_association", set_association)
    monkeypatch.setattr(storage, "clear_file_association", lambda extension: set_association(extension, ""))
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, WxSettingsModel())
    controls = host._wx_settings_controls
    listing = controls["file_associations"]
    change = controls["file_association_change"]
    clear = controls["file_association_clear"]
    assert listing.GetCount() == 1
    assert change.IsEnabled()
    assert not clear.IsEnabled()
    listing.SetSelection(0)
    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_LISTBOX, listing.GetId()))
    assert clear.IsEnabled()

    class FileDialog:
        answer = wx.ID_CANCEL

        def __init__(self, *_args, **_kwargs):
            pass

        def ShowModal(self):
            return self.answer

        def GetPath(self):
            return "C:/new/editor.exe"

        def Destroy(self):
            pass

    monkeypatch.setattr(wx, "FileDialog", FileDialog)
    change.Command(wx.CommandEvent(wx.wxEVT_BUTTON, change.GetId()))
    assert writes == []
    FileDialog.answer = wx.ID_OK
    change.Command(wx.CommandEvent(wx.wxEVT_BUTTON, change.GetId()))
    assert writes == [(".slurm", "C:/new/editor.exe")]
    assert "new/editor.exe" in listing.GetString(0)
    listing.SetSelection(0)
    clear.Command(wx.CommandEvent(wx.wxEVT_BUTTON, clear.GetId()))
    assert listing.GetCount() == 0
    assert not change.IsEnabled()
    assert not clear.IsEnabled()
    host.Close()
    frame.Destroy()
