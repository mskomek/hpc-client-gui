import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.services.editor_controller import LintResult
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_editor_view import show_editor


def test_editor_dirty_save_template_and_lint_aggregation():
    model = WxEditorModel()
    assert model.open("/remote/job.slurm", "old") == 0
    model.controller.update_content("new")
    assert model.controller.active.dirty and model.save_target() == "submit"
    diagnostics = model.aggregate_lint((("builtin", LintResult(1, 1, "bad")), ("ansys", LintResult(1, 1, "bad")), ("plugin", LintResult(2, 1, "other"))))
    assert len(diagnostics) == 2


def test_shortcut_routing_and_model_has_no_qt():
    model = WxEditorModel()
    assert model.route_shortcut("Ctrl+C", "editor", text_input=True) is None
    source = open("src/hpc_gui/wx_editor.py", encoding="utf-8").read()
    assert "PySide6" not in source and "import wx" not in source


def test_wx_editor_view_has_async_remote_save_and_distinct_actions():
    source = open("src/hpc_gui/wx_editor_view.py", encoding="utf-8").read()
    assert "save_remote=None" in source
    assert "Thread(target=worker" in source
    assert "on_submit=None" in source and "on_run=None" in source
    assert "event.Veto()" in source and "save_document(on_done=destroy_after_save)" in source


def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _click(control):
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))


@pytest.fixture
def wx_app():
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _open_view(model=None, **callbacks):
    show_editor(model=model, path="/remote/job.slurm", content="initial", **callbacks)
    return [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "job.slurm"][-1]


def _close(frame, app):
    frame.Close()
    app.ProcessPendingEvents()
    wx.Yield()


def test_wx_remote_save_backend_runs_off_gui_thread(wx_app):
    gui_thread = threading.get_ident()
    save_threads = []
    model = WxEditorModel()
    frame = _open_view(model, save_remote=lambda _path, _content: save_threads.append(threading.get_ident()))
    controls = frame._wx_editor_controls
    controls["editor"].SetValue("latest")
    _click(controls["save"])
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert save_threads and save_threads[0] != gui_thread
    assert not model.controller.active.dirty
    assert all(button.IsEnabled() for button in (controls["save"], controls["submit"], controls["run"]))
    _close(frame, wx_app)


def test_wx_remote_save_submit_runs_in_order_off_gui_thread(wx_app):
    gui_thread = threading.get_ident()
    events, threads, contents = [], {}, []
    model = WxEditorModel()

    def save(path, content):
        events.append("save")
        threads["save"] = threading.get_ident()
        contents.append((path, content))

    def submit(document):
        events.append("submit")
        threads["submit"] = threading.get_ident()
        contents.append(document.content)

    frame = _open_view(model, save_remote=save, on_submit=submit)
    controls = frame._wx_editor_controls
    controls["editor"].SetValue("latest submit")
    _click(controls["submit"])
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert events == ["save", "submit"]
    assert threads["save"] != gui_thread and threads["submit"] != gui_thread
    assert contents == [("/remote/job.slurm", "latest submit"), "latest submit"]
    _close(frame, wx_app)


def test_wx_remote_save_run_runs_in_order_off_gui_thread(wx_app):
    gui_thread = threading.get_ident()
    events, threads = [], {}
    model = WxEditorModel()
    frame = _open_view(
        model,
        save_remote=lambda _path, _content: (events.append("save"), threads.setdefault("save", threading.get_ident())),
        on_run=lambda _document: (events.append("run"), threads.setdefault("run", threading.get_ident())),
    )
    _click(frame._wx_editor_controls["run"])
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert events == ["save", "run"]
    assert threads["save"] != gui_thread and threads["run"] != gui_thread
    _close(frame, wx_app)


@pytest.mark.parametrize("mode", ["submit", "run"])
def test_wx_remote_save_failure_prevents_followup(wx_app, mode):
    called = []
    model = WxEditorModel()
    callbacks = {"save_remote": lambda _path, _content: (_ for _ in ()).throw(RuntimeError("save failed"))}
    callbacks[f"on_{mode}"] = lambda _document: called.append(mode)
    frame = _open_view(model, **callbacks)
    frame._wx_editor_controls["editor"].SetValue("unsaved")
    _click(frame._wx_editor_controls[mode])
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert called == []
    assert "save failed" in frame._wx_editor_controls["status"].GetLabel()
    assert model.controller.active.dirty
    model.controller.mark_saved()
    _close(frame, wx_app)


def test_wx_remote_submit_failure_keeps_saved_document_and_surfaces_error(wx_app):
    events = []
    model = WxEditorModel()

    def submit(_document):
        events.append("submit")
        raise RuntimeError("submit failed")

    frame = _open_view(model, save_remote=lambda _path, _content: events.append("save"), on_submit=submit)
    _click(frame._wx_editor_controls["submit"])
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert events == ["save", "submit"]
    assert not model.controller.active.dirty
    assert "submit failed" in frame._wx_editor_controls["status"].GetLabel()
    _close(frame, wx_app)


def test_wx_remote_save_duplicate_click_is_ignored(wx_app):
    started, release = threading.Event(), threading.Event()
    calls = []
    model = WxEditorModel()

    def save(_path, _content):
        calls.append(threading.get_ident())
        started.set()
        release.wait(2)

    frame = _open_view(model, save_remote=save)
    controls = frame._wx_editor_controls
    _click(controls["save"])
    assert started.wait(1)
    _click(controls["save"])
    assert len(calls) == 1
    release.set()
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    _close(frame, wx_app)


def test_wx_remote_save_close_while_in_flight_discards_late_ui_callback(wx_app):
    started, release = threading.Event(), threading.Event()
    model = WxEditorModel()

    def save(_path, _content):
        started.set()
        release.wait(2)

    frame = _open_view(model, save_remote=save)
    _click(frame._wx_editor_controls["save"])
    assert started.wait(1)
    _close(frame, wx_app)
    release.set()
    wx_app.ProcessPendingEvents()
    assert not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle() == "job.slurm"]


def test_wx_editor_dirty_close_save_changes_popup_saves_then_closes(wx_app, monkeypatch):
    saved = []
    model = WxEditorModel()
    frame = _open_view(model, save_remote=lambda path, content: saved.append((path, content)))
    frame._wx_editor_controls["editor"].SetValue("popup-approved")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)

    frame.Close()
    _pump(wx_app, lambda: saved == [("/remote/job.slurm", "popup-approved")])
    wx.Yield()
    _pump(wx_app, lambda: not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle() == "job.slurm"])
    assert not model.controller.active.dirty
