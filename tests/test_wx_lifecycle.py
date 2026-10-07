import pytest
from threading import Event, get_ident

from hpc_gui.wx_lifecycle import WxLifecycleController


@pytest.mark.unit
def test_update_progress_cancel_splash_and_shutdown_cleanup():
    events, cleaned, cleanup_threads = [], [], []
    controller = WxLifecycleController(tray_notify=events.append)
    assert controller.set_splash("Loading") == "Loading"
    controller.begin_update("checking")
    assert controller.update_progress(50, 100).percent == 50
    assert controller.notify_job("Job complete") and events == ["Job complete"]
    controller.register_cleanup(lambda: (cleaned.append("connection"), cleanup_threads.append(get_ident())))
    controller.register_cleanup(lambda: cleaned.append("transfer"))
    controller.cancel_update()
    assert controller.cancel_token.is_set() and controller.progress.phase == "cancelled"
    controller.shutdown()
    controller.shutdown()
    assert cleaned == ["transfer", "connection"]
    assert cleanup_threads == [get_ident()]
    assert controller.cleanup_complete is True
    assert controller.cleanup_timed_out is False


@pytest.mark.unit
def test_shutdown_reports_cleanup_timeout_without_blocking():
    release = Event()
    controller = WxLifecycleController()
    controller.CLEANUP_TIMEOUT_S = 0.01
    controller.register_cleanup(lambda: release.wait(1), worker_safe=True)
    controller.shutdown()
    assert controller.cleanup_complete is False
    assert controller.cleanup_timed_out is True
    release.set()


@pytest.mark.unit
def test_tray_unavailable_is_fail_soft():
    controller = WxLifecycleController()
    assert not controller.notify_job("done")


@pytest.mark.unit
def test_tray_notifications_are_connected_late_and_deduplicated():
    events = []
    controller = WxLifecycleController()
    controller.set_tray_notifier(events.append)
    assert controller.notify_job("done", job_id="42")
    assert not controller.notify_job("done again", job_id="42")
    assert controller.notify_job("other", job_id="43")
    assert events == ["done", "other"]
