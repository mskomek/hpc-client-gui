from types import SimpleNamespace
from threading import Lock
from unittest.mock import Mock

import pytest

from hpc_gui.wx_jobs import WxJobsModel, clean_output
from hpc_gui.jobs.output_workspace import (
    _finalize_output_window, _handle_output_window_destroy,
    _stop_window_timer,
)


@pytest.mark.unit
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


@pytest.mark.unit
def test_failure_backoff_and_provenance_hook():
    model = WxJobsModel()
    assert model.record_tail_failure() == 1
    model.record_tail_success()
    assert model.tail_failures == 0
    explanation = model.explain_failure(SimpleNamespace(state="OUT_OF_MEMORY", reason="limit", exit_code="1"))
    assert explanation.category == "oom"


@pytest.mark.unit
def test_job_completion_notifies_once_per_terminal_state():
    events = []
    model = WxJobsModel(completion_notify=lambda job_id, message: events.append((job_id, message)))
    assert not model.update_job_state("42", "RUNNING")
    assert model.update_job_state("42", "COMPLETED", "done")
    assert not model.update_job_state("42", "COMPLETED", "again")
    assert events == [("42", "done")]


@pytest.mark.unit
def test_detached_output_timer_is_stopped_and_unbound():
    timer = SimpleNamespace(Stop=Mock(), SetOwner=Mock())
    frame = SimpleNamespace(Unbind=Mock())
    wx = SimpleNamespace(EVT_TIMER=object())
    handler = Mock()

    _stop_window_timer(wx, frame, timer, handler)

    timer.Stop.assert_called_once_with()
    timer.SetOwner.assert_called_once_with(None)
    frame.Unbind.assert_called_once_with(
        wx.EVT_TIMER, handler=handler, source=timer,
    )


@pytest.mark.unit
def test_detached_output_timer_cleanup_survives_deleted_wrapper():
    timer = SimpleNamespace(
        Stop=Mock(side_effect=RuntimeError("deleted")), SetOwner=Mock(),
    )
    frame = SimpleNamespace(Unbind=Mock())
    wx = SimpleNamespace(EVT_TIMER=object())

    _stop_window_timer(wx, frame, timer, Mock())

    frame.Unbind.assert_called_once()
    timer.SetOwner.assert_called_once_with(None)


@pytest.mark.unit
def test_detached_output_direct_destroy_releases_follower_and_callbacks(monkeypatch):
    timer = SimpleNamespace(Stop=Mock(), SetOwner=Mock())
    frame = SimpleNamespace(Unbind=Mock())
    wx = SimpleNamespace(EVT_TIMER=object())
    follower = SimpleNamespace(close=Mock())
    refresh_labels = Mock()
    on_closed = Mock()
    state = {"closed": False}
    unsubscribe = Mock()
    monkeypatch.setattr(
        "hpc_gui.jobs.output_workspace.unsubscribe_language_change", unsubscribe,
    )

    finalized = _finalize_output_window(
        wx=wx, frame=frame, timer=timer, handler=Mock(), state=state,
        state_lock=Lock(), follower=follower, refresh_labels=refresh_labels,
        on_closed=on_closed,
    )
    repeated = _finalize_output_window(
        wx=wx, frame=frame, timer=timer, handler=Mock(), state=state,
        state_lock=Lock(), follower=follower, refresh_labels=refresh_labels,
        on_closed=on_closed,
    )

    assert finalized is True and repeated is False
    assert state["closed"] is True
    follower.close.assert_called_once_with()
    unsubscribe.assert_called_once_with(refresh_labels)
    on_closed.assert_called_once_with()
    timer.Stop.assert_called_once_with()
    timer.SetOwner.assert_called_once_with(None)


@pytest.mark.unit
def test_output_destroy_handler_matches_distinct_native_wrapper():
    frame = SimpleNamespace(GetHandle=lambda: 123)
    event = SimpleNamespace(GetEventObject=lambda: SimpleNamespace(GetHandle=lambda: 123), Skip=Mock())
    finalize = Mock()

    _handle_output_window_destroy(event, frame, 123, finalize)

    finalize.assert_called_once_with()
    event.Skip.assert_called_once_with()


@pytest.mark.unit
def test_output_destroy_handler_uses_cached_id_after_wrapper_invalidation():
    def deleted_handle():
        raise RuntimeError("destroyed wx wrapper")

    frame = SimpleNamespace(GetHandle=deleted_handle)
    event_window = SimpleNamespace(GetHandle=deleted_handle)
    event = SimpleNamespace(
        GetEventObject=lambda: event_window, GetId=lambda: 321, Skip=Mock(),
    )
    finalize = Mock()

    _handle_output_window_destroy(event, frame, 321, finalize)

    finalize.assert_called_once_with()
    event.Skip.assert_called_once_with()


@pytest.mark.audit
@pytest.mark.wx
def test_jobs_model_has_no_qt_import():
    source = open("src/hpc_gui/wx_jobs.py", encoding="utf-8").read()
    from hpc_gui.wx_jobs import show_job_output

    assert "PySide6" not in source and callable(show_job_output)
    assert "from hpc_gui.jobs.output_workspace import" in source


@pytest.mark.audit
@pytest.mark.wx
def test_job_output_view_has_live_timer_and_resize_hooks():
    output_source = open("src/hpc_gui/jobs/output_workspace.py", encoding="utf-8").read()
    cancel_source = open("src/hpc_gui/jobs/cancel_job_controller.py", encoding="utf-8").read()
    output_interactions = open("src/hpc_gui/jobs/output_panel_interactions.py", encoding="utf-8").read()
    refresh_source = open("src/hpc_gui/jobs/jobs_refresh_controller.py", encoding="utf-8").read()
    selection_source = open("src/hpc_gui/jobs/job_selection_controller.py", encoding="utf-8").read()
    channels_source = open("src/hpc_gui/jobs/output_channels_controller.py", encoding="utf-8").read()
    assert "EVT_TIMER" in output_source and "EVT_SIZE" in output_source and "update_detached" in output_source
    assert "lifecycle.register_cleanup(closed)" in output_source
    assert "build_cancel_confirmation" in cancel_source and "Thread(target=worker" in cancel_source
    assert "files.auto_scroll" in channels_source and "checkbox.GetValue()" in channels_source
    assert "model.open_detached()" in output_interactions and "show_job_output(" in output_interactions
    assert "def closed(_event=None):" in output_source
    assert "items = tuple(result or ())" in refresh_source and "for item in items" in refresh_source
    assert "SimpleNamespace(**item)" in selection_source and "failure.as_lines()" in selection_source
