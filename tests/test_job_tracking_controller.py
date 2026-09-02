from hpc_gui.services.job_tracking_controller import JobTrackingController


def test_polling_selection_reconnect_and_output_metadata():
    controller = JobTrackingController()
    session = {"connected": True}
    controller.set_session(session)
    controller.select_job("42")
    controller.set_output_metadata(stdout_path="/out", stderr_path="/err", workdir="/work")
    assert controller.should_poll_jobs(True, True)
    assert controller.should_follow_output(True)
    assert controller.selected_job_id == "42"
    assert controller.output.workdir == "/work"
    controller.set_minimized(True)
    assert not controller.should_poll_jobs(True, True)
    controller.set_session({"connected": False})
    assert not controller.should_follow_output(True)
    assert controller.selected_job_id == ""


def test_controller_has_no_qt_dependency():
    source = __import__("inspect").getsource(JobTrackingController)
    assert "PySide" not in source
