from hpc_gui.wx_lifecycle import WxLifecycleController


def test_update_progress_cancel_splash_and_shutdown_cleanup():
    events, cleaned = [], []
    controller = WxLifecycleController(tray_notify=events.append)
    assert controller.set_splash("Loading") == "Loading"
    controller.begin_update("checking")
    assert controller.update_progress(50, 100).percent == 50
    assert controller.notify_job("Job complete") and events == ["Job complete"]
    controller.register_cleanup(lambda: cleaned.append("connection"))
    controller.register_cleanup(lambda: cleaned.append("transfer"))
    controller.cancel_update()
    assert controller.cancel_token.is_set() and controller.progress.phase == "cancelled"
    controller.shutdown()
    controller.shutdown()
    assert cleaned == ["transfer", "connection"]


def test_tray_unavailable_is_fail_soft():
    controller = WxLifecycleController()
    assert not controller.notify_job("done")
