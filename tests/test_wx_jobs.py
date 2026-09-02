from types import SimpleNamespace

from hpc_gui.wx_jobs import WxJobsModel, clean_output


def test_jobs_polling_ansi_detached_minimize_and_cancel():
    cancelled = []
    model = WxJobsModel(notify=cancelled.append)
    model.tracking.set_session({"connected": True})
    model.set_output("/out", "/err")
    assert model.poll_allowed()
    assert clean_output("\x1b[31mred\nblue") == "red\nblue\n"
    assert model.open_detached("/out", "/err", "split").mode == "split"
    assert model.update_detached("1", "one\ntwo\n", 1) == "two\n"
    assert model.resize_detached("1", 120, 40).cols == 120
    assert model.cancel_job(lambda job_id: job_id, "42") == "42"
    model.tracking.set_minimized(True)
    assert not model.tracking.should_follow_output(True)


def test_failure_backoff_and_provenance_hook():
    model = WxJobsModel()
    assert model.record_tail_failure() == 1
    model.record_tail_success()
    assert model.tail_failures == 0
    explanation = model.explain_failure(SimpleNamespace(state="OUT_OF_MEMORY", reason="limit", exit_code="1"))
    assert explanation.category == "oom"


def test_jobs_model_has_no_qt_import():
    source = open("src/hpc_gui/wx_jobs.py", encoding="utf-8").read()
    assert "PySide6" not in source and "import wx" not in source
