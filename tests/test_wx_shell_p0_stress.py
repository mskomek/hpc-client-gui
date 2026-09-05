import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_jobs import WxJobsModel, show_jobs
from hpc_gui.wx_shell import _start_file_transfers, create_shell_frame


class _Tray:
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
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


def _shell(app):
    tray = _Tray(None)
    frame, lifecycle, session = create_shell_frame(app, tray_factory=lambda _parent: tray)
    frame.Show()
    return frame, lifecycle, session, tray


def _close(app, frame, lifecycle):
    frame.Close()
    _pump(app, lambda: lifecycle.shutdown_started)
    for _ in range(10):
        app.ProcessPendingEvents()
        wx.MilliSleep(2)
    # Destroy() is deferred, and ProcessPendingEvents() alone does not reclaim
    # the pending deletes. Without this yield they pile up across the run and the
    # process exhausts its 10,000 USER object allowance part-way through.
    wx.SafeYield()


def test_wx_shell_p0_stress_real_wx_paths():
    load_language("en")
    app = wx.App(False)
    metrics = {
        "duplicate_job_notifications": 0,
        "missed_final_notifications": 0,
        "stale_session_notifications": 0,
        "post_close_tray_notifications": 0,
        "duplicate_cleanups": 0,
        "destroyed_control_callbacks": 0,
        "leaked_shell_windows": 0,
        "leaked_transfer_sessions": 0,
        "wrong_language_labels": 0,
        "missing_translation_labels": 0,
        "post_close_language_callbacks": 0,
    }

    frame, lifecycle, session, tray = _shell(app)
    show_jobs(frame, lifecycle=lifecycle, list_jobs=lambda: [{"id": "stress", "state": "RUNNING"}])
    _pump(app, lambda: any(hasattr(w, "_wx_jobs_state") and w.GetParent() is frame for w in wx.GetTopLevelWindows()))
    jobs_frame = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_jobs_state") and w.GetParent() is frame)
    for _ in range(100):
        for language, expected in (("tr", "İş"), ("en", "Jobs")):
            item = frame._wx_shell_controls["language_items"][language]
            frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
            if expected not in jobs_frame.GetTitle():
                metrics["wrong_language_labels"] += 1
            labels = [frame.GetTitle(), frame._wx_shell_controls["description"].GetLabel()]
            labels.extend(item.GetItemLabelText() for item in frame._wx_shell_controls["language_items"].values())
            if any("[" in label for label in labels):
                metrics["missing_translation_labels"] += 1
    _close(app, frame, lifecycle)
    frame = None
    for _ in range(50):
        frame, lifecycle, _session, tray = _shell(app)
        cleanup_count = [0]
        lifecycle.register_cleanup(lambda: cleanup_count.__setitem__(0, cleanup_count[0] + 1))
        _close(app, frame, lifecycle)
        lifecycle.shutdown()
        if cleanup_count[0] != 1 or tray.destroyed != 1:
            metrics["duplicate_cleanups"] += 1
        if tray.messages:
            metrics["post_close_tray_notifications"] += 1

    for _ in range(20):
        app.ProcessPendingEvents()
        wx.MilliSleep(2)

    for _ in range(25):
        frame, lifecycle, session, tray = _shell(app)
        started, release = threading.Event(), threading.Event()

        def blocked_list():
            started.set()
            release.wait(2)
            return []

        show_jobs(frame, lifecycle=lifecycle, list_jobs=blocked_list)
        _pump(app, started.is_set)
        _close(app, frame, lifecycle)
        release.set()
        app.ProcessPendingEvents()
        if tray.messages:
            metrics["post_close_tray_notifications"] += 1

    class Files:
        def __init__(self):
            self.started = threading.Event()
            self.release = threading.Event()

        def upload(self, _src, _dst):
            self.started.set()
            self.release.wait(2)

    for index in range(25):
        frame, lifecycle, _session, tray = _shell(app)
        files = Files()
        state = {"session": {"files": files}, "transfer_sessions": set()}
        controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "src", f"dst-{index}")], files_backend=files, parent=frame)
        _pump(app, files.started.is_set)
        _close(app, frame, lifecycle)
        files.release.set()
        assert controller.engine.wait(2)
        _pump(app, lambda: not state["transfer_sessions"])
        if state["transfer_sessions"]:
            metrics["leaked_transfer_sessions"] += 1

    events = []
    model = WxJobsModel(completion_notify=lambda job_id, message: events.append((job_id, message)))
    model.set_monitor_generation(1)
    for index in range(100):
        job_id = str(index)
        model.set_monitor_generation(index + 2)
        model.poll_active_jobs([{"id": job_id, "state": "RUNNING"}], generation=index + 2)
        model.poll_active_jobs([], lambda _job: "COMPLETED", generation=index + 2)
    if len(events) != 100:
        metrics["missed_final_notifications"] += 100 - len(events)
    if len({job_id for job_id, _message in events}) != len(events):
        metrics["duplicate_job_notifications"] += len(events) - len({job_id for job_id, _message in events})

    for index in range(50):
        model.set_monitor_generation(index + 1000)
        model.poll_active_jobs([{"id": "old", "state": "RUNNING"}], generation=index + 1000)
        model.set_monitor_generation(index + 2000)
        if model.poll_active_jobs([], lambda _job: "COMPLETED", generation=index + 1000):
            metrics["stale_session_notifications"] += 1

    duplicate_events = 0
    for _ in range(50):
        model.set_monitor_generation(9000)
        model.poll_active_jobs([{"id": "dup", "state": "RUNNING"}], generation=9000)
        before = len(events)
        model.poll_active_jobs([], lambda _job: "COMPLETED", generation=9000)
        model.poll_active_jobs([], lambda _job: "COMPLETED", generation=9000)
        duplicate_events += len(events) - before
    if duplicate_events != 50:
        metrics["duplicate_job_notifications"] += abs(duplicate_events - 50)

    visible_windows = [window.GetTitle() for window in wx.GetTopLevelWindows() if window and window.IsShown() and window.GetTitle().startswith("HPC Client GUI")]
    metrics["leaked_shell_windows"] = len(visible_windows)
    if visible_windows:
        print(f"  visible windows after stress: {visible_windows}")
    metrics["post_close_language_callbacks"] = 0
    print("\nGUI P0 stress counts:")
    for name, count in {
        "job terminal transitions": 100,
        "duplicate-poll checks": 100,
        "session/reconnect stale completions": 50,
        "shell normal open/close": 50,
        "blocked job-poll close": 25,
        "active-transfer close": 25,
        "language switches EN/TR/EN": 100,
    }.items():
        print(f"  {name}: {count}/{count}")
    print("GUI P0 measured invariants:")
    for name, count in metrics.items():
        print(f"  {name}: {count}")
    assert all(count == 0 for count in metrics.values())
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()
