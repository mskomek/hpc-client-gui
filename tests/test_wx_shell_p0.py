import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import current_language, load_language
from hpc_gui.wx_jobs import WxJobsModel, show_jobs
from hpc_gui.wx_shell import create_shell_frame


class Tray:
    def __init__(self, _parent):
        self.messages = []
        self.destroyed = 0

    def notify(self, message):
        self.messages.append(message)

    def destroy(self):
        self.destroyed += 1


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(10)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def shell():
    load_language("en")
    app = wx.App(False)
    tray = Tray(None)
    frame, lifecycle, session = create_shell_frame(app, tray_factory=lambda _parent: tray)
    frame.Show()
    yield app, frame, lifecycle, session, tray
    if frame:
        frame.Destroy()
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _open_jobs(app, frame, lifecycle, rows, final_state=None, generation=None):
    calls = []

    def list_jobs():
        calls.append(1)
        return rows[len(calls) - 1] if len(calls) <= len(rows) else rows[-1]

    show_jobs(
        frame,
        lifecycle=lifecycle,
        list_jobs=list_jobs,
        final_state=final_state,
        generation=generation,
    )
    jobs = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_jobs_state")][-1]
    _pump(app, lambda: len(calls) >= 1)
    return jobs, calls


def _select_menu(frame, language):
    item = frame._wx_shell_controls["language_items"][language]
    event = wx.CommandEvent(wx.wxEVT_MENU, item.GetId())
    frame.ProcessEvent(event)


def test_wx_shell_language_menu_has_flags_and_tracks_selection(shell):
    _app, frame, _lifecycle, _session, _tray = shell
    items = frame._wx_shell_controls["language_items"]
    assert {item.GetItemLabelText() for item in items.values()} == {"English", "Türkçe"}
    assert all(item.GetBitmap().IsOk() for item in items.values())
    assert items["en"].IsChecked()
    _select_menu(frame, "tr")
    assert current_language() == "tr" and items["tr"].IsChecked() and not items["en"].IsChecked()
    _select_menu(frame, "en")
    assert current_language() == "en" and items["en"].IsChecked() and not items["tr"].IsChecked()


def test_wx_shell_switch_retranslates_visible_shell(shell):
    _app, frame, _lifecycle, _session, _tray = shell
    english = (frame.GetTitle(), frame._wx_shell_controls["settings"].GetLabel(), frame.GetStatusBar().GetStatusText())
    _select_menu(frame, "tr")
    turkish = (frame.GetTitle(), frame._wx_shell_controls["settings"].GetLabel(), frame.GetStatusBar().GetStatusText())
    assert english != turkish
    _select_menu(frame, "en")
    assert (frame.GetTitle(), frame._wx_shell_controls["settings"].GetLabel(), frame.GetStatusBar().GetStatusText()) == english


def test_wx_shell_job_completion_uses_disappeared_job_final_state(shell):
    app, frame, lifecycle, _session, tray = shell
    jobs, calls = _open_jobs(app, frame, lifecycle, [[{"id": "123", "state": "RUNNING"}], []], lambda _job: "COMPLETED")
    jobs._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls) >= 2 and len(tray.messages) == 1)
    assert "123" in tray.messages[0] and "completed" in tray.messages[0].lower()


def test_wx_shell_job_failure_emits_translated_notification(shell):
    app, frame, lifecycle, _session, tray = shell
    jobs, calls = _open_jobs(app, frame, lifecycle, [[{"id": "124", "state": "RUNNING"}], []], lambda _job: "TIMEOUT")
    jobs._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls) >= 2 and len(tray.messages) == 1)
    assert "124" in tray.messages[0] and "TIMEOUT" in tray.messages[0]


def test_wx_shell_completion_states_and_deduplication(shell):
    app, frame, lifecycle, _session, tray = shell
    rows = [[{"id": "123", "state": "RUNNING"}], [{"id": "123", "state": "COMPLETING"}], []]
    jobs, calls = _open_jobs(app, frame, lifecycle, rows, lambda _job: "COMPLETED")
    jobs._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls) >= 2 and jobs._wx_jobs_controls["jobs"].GetItemCount() == 1 and jobs._wx_jobs_controls["jobs"].GetItemText(0, 1) == "COMPLETING")
    jobs._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls) >= 3 and len(tray.messages) == 1)
    for _ in range(5):
        jobs._wx_jobs_refresh_jobs()
        _pump(app, lambda: len(calls) >= 3)
    assert len(tray.messages) == 1


def test_wx_shell_initial_poll_does_not_notify_existing_jobs(shell):
    app, frame, lifecycle, _session, tray = shell
    jobs, _calls = _open_jobs(app, frame, lifecycle, [[{"id": "100", "state": "COMPLETED"}]], lambda _job: "COMPLETED")
    assert tray.messages == []
    assert jobs._wx_jobs_controls["jobs"].GetItemCount() == 1


def test_wx_shell_reconnect_ignores_old_session_completion(shell):
    app, frame, lifecycle, session, tray = shell
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def list_jobs():
        started.set()
        release.wait(2)
        finished.set()
        return []

    show_jobs(frame, lifecycle=lifecycle, list_jobs=list_jobs, final_state=lambda _job: "COMPLETED", generation=lambda: session["generation"])
    _pump(app, started.is_set)
    session["generation"] = 1
    release.set()
    _pump(app, finished.is_set)
    app.ProcessPendingEvents()
    assert tray.messages == []


def test_wx_shell_tray_unavailable_keeps_job_tracking(shell):
    app, frame, lifecycle, _session, _tray = shell
    frame.Destroy()
    frame, lifecycle, _session = create_shell_frame(app, tray_factory=lambda _parent: None)
    jobs, _calls = _open_jobs(app, frame, lifecycle, [[{"id": "100", "state": "RUNNING"}]])
    assert jobs._wx_jobs_controls["jobs"].GetItemCount() == 1
    assert not lifecycle.notify_job("ignored", job_id="100")


def test_wx_shell_close_is_idempotent_and_cleans_tray(shell):
    app, frame, lifecycle, _session, tray = shell
    calls = []
    lifecycle.register_cleanup(lambda: calls.append("resource"))
    frame.Close()
    _pump(app, lambda: tray.destroyed == 1)
    lifecycle.shutdown()
    assert calls == ["resource"] and tray.destroyed == 1
    assert not lifecycle.notify_job("late", job_id="late")


def test_wx_job_model_completing_is_not_final():
    events = []
    model = WxJobsModel(completion_notify=lambda job_id, message: events.append((job_id, message)))
    assert not model.update_job_state("42", "RUNNING")
    assert not model.update_job_state("42", "COMPLETING")
    assert model.update_job_state("42", "COMPLETED")
    assert len(events) == 1 and "42" in events[0][1]


def test_wx_shell_job_notifications_use_current_runtime_language(shell):
    app, frame, lifecycle, _session, tray = shell
    jobs, calls = _open_jobs(app, frame, lifecycle, [[{"id": "en-1", "state": "RUNNING"}], []], lambda _job: "COMPLETED")
    jobs._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls) >= 2 and len(tray.messages) == 1)
    assert "Job completed" in tray.messages[0]
    _select_menu(frame, "tr")
    jobs2, calls2 = _open_jobs(app, frame, lifecycle, [[{"id": "tr-1", "state": "RUNNING"}], []], lambda _job: "COMPLETED")
    jobs2._wx_jobs_refresh_jobs()
    _pump(app, lambda: len(calls2) >= 2 and len(tray.messages) == 2)
    assert "İş başarıyla" in tray.messages[1]


def test_wx_shell_open_jobs_window_retranslates_runtime(shell):
    app, frame, lifecycle, _session, _tray = shell
    jobs, _calls = _open_jobs(app, frame, lifecycle, [[{"id": "1", "state": "RUNNING"}]])
    assert jobs.GetTitle() == "Jobs"
    _select_menu(frame, "tr")
    assert jobs.GetTitle() == "İşler"
    _select_menu(frame, "en")
    assert jobs.GetTitle() == "Jobs"


def test_wx_shell_close_ignores_blocked_job_poll(shell):
    app, frame, lifecycle, _session, tray = shell
    started = threading.Event()
    release = threading.Event()

    def list_jobs():
        started.set()
        release.wait(2)
        return [{"id": "late", "state": "COMPLETED"}]

    show_jobs(frame, lifecycle=lifecycle, list_jobs=list_jobs)
    _pump(app, started.is_set)
    frame.Close()
    release.set()
    _pump(app, lambda: lifecycle.shutdown_started)
    app.ProcessPendingEvents()
    assert tray.messages == []
