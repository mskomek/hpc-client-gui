"""Real wx ANSYS view test — event → model → engine → visible grouped UI."""
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from hpc_gui.plugins.linter_tools import LinterTool
from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation

wx = pytest.importorskip("wx")


def _fake_tool(monkeypatch, module_name="_fake_ansys_view", suffixes=(".wbjn",)):
    fake = SimpleNamespace(
        SUPPORTED_SUFFIXES=frozenset(suffixes),
        lint_text=lambda text, file_name="": [
            SimpleNamespace(
                code="ANSYS001",
                message="demo issue",
                line=2,
                column=1,
                severity=SimpleNamespace(value="error"),
                explanation="why flagged detail",
                is_heuristic=False,
                suggested_fix="fix it",
                source_url="https://docs.ansys.com/rule",
            )
        ],
    )
    # Create fake package with api submodule fallback
    import sys
    sys.modules[module_name] = fake
    # also need .api for suffix fallback if needed
    sys.modules[f"{module_name}.api"] = fake
    tool = LinterTool("org.hpcclient.ansyslint", "0.1.0", "ANSYS", "", lambda **kwargs: None, module_name)
    return tool


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_view_single_file_lint_shows_grouped_results(monkeypatch, tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame

    app = wx.App.Get() or wx.App(False)
    tool = _fake_tool(monkeypatch, "_fake_ansys_view1")
    presentation = AnsysToolPresentation(tool)
    frame = build_ansys_frame(None, presentation)
    assert frame.IsShown()
    # simulate user picking file via direct model path: call do_lint_files
    tmp = tmp_path / "sample.wbjn"
    tmp.write_text("journal content", encoding="utf-8")
    try:
        # use model directly to ensure engine works
        model = frame._wx_ansys_model
        results = model.lint_files(((str(tmp), tmp.read_text(encoding="utf-8")),))
        assert results and results[0].state.status == "completed"
        # render via view helper
        frame._wx_ansys_render(results)
        wx.Yield()
        lst = frame._wx_ansys_controls["results"]
        assert lst.GetItemCount() >= 1
        # severity grouping: check summary
        summary = frame._wx_ansys_controls["summary"].GetLabel()
        assert "1" in summary  # 1 error
        # detail panel should update after selection
        lst.Select(0)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, lst.GetId())
        evt.SetIndex(0)
        evt.SetEventObject(lst)
        lst.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        detail = frame._wx_ansys_controls["detail"].GetValue()
        assert "why flagged detail" in detail
        assert model.group_results(results)  # grouping by status exists
    finally:
        frame.Destroy()
        wx.Yield()
        app.ProcessPendingEvents()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_view_empty_and_failed_cases(monkeypatch):
    from hpc_gui.wx_ansys_view import build_ansys_frame

    app = wx.App.Get() or wx.App(False)
    # broken engine
    broken_mod = "_fake_ansys_broken_view"
    import sys
    # need object with lint_text
    class FB:
        def lint_text(self, text, file_name=""):
            raise RuntimeError("boom")
    sys.modules[broken_mod] = FB()
    sys.modules[f"{broken_mod}.api"] = SimpleNamespace(SUPPORTED_SUFFIXES=frozenset({".wbjn"}))
    tool = LinterTool("x", "1", "broken", "", lambda **kwargs: None, broken_mod)
    # patch _engine_module to return our fake
    tool2 = _fake_tool(monkeypatch, "_fake_empty_view", suffixes=(".wbjn",))
    for presentation, check_empty in [
        (AnsysToolPresentation(tool), False),
        (AnsysToolPresentation(tool2), True),
    ]:
        frame = build_ansys_frame(None, presentation)
        assert frame.IsShown()
        model = frame._wx_ansys_model
        if check_empty:
            # suffix mismatch gives empty
            res = model.lint_files((("a.txt", "x"),))
            assert res == ()
            frame._wx_ansys_render(res)
            wx.Yield()
            assert frame._wx_ansys_controls["results"].GetItemCount() == 0
        else:
            res = model.lint_files((("a.wbjn", "x"),))
            assert res[0].state.status == "failed"
            frame._wx_ansys_render(res)
            wx.Yield()
            assert frame._wx_ansys_controls["results"].GetItemCount() >= 1
        frame.Destroy()
        wx.Yield()
        app.ProcessPendingEvents()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_folder_cap(monkeypatch, tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame

    _app = wx.App.Get() or wx.App(False)
    tool = _fake_tool(monkeypatch, "_fake_folder_cap_view")
    presentation = AnsysToolPresentation(tool)
    frame = build_ansys_frame(None, presentation)
    for i in range(205):
        (tmp_path / f"{i}.wbjn").write_text("x", encoding="utf-8")
    model = frame._wx_ansys_model
    results = model.lint_folder(tmp_path, lambda p: Path(p).read_text(encoding="utf-8"))
    assert len(results) == 200
    frame._wx_ansys_render(results)
    wx.Yield()
    # capped list may produce many rows (one per file diagnostic)
    assert frame._wx_ansys_controls["results"].GetItemCount() >= 200
    frame.Destroy()
    wx.Yield()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_pick_files_button_real_event(tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame
    _app = wx.App.Get() or wx.App(False)
    tool = _fake_tool(monkeypatch=None, module_name="_fake_ansys_pick_files")
    # ensure suffix is .wbjn
    # reuse helper but without monkeypatch arg
    presentation = AnsysToolPresentation(tool)
    tmp = tmp_path / "a.wbjn"
    tmp.write_text("journal", encoding="utf-8")
    frame = build_ansys_frame(None, presentation, file_chooser=lambda: [str(tmp)])
    try:
        ctrls = frame._wx_ansys_controls
        # real button event
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["pick_files"].GetEventHandler().ProcessEvent(evt)
        # wait for worker
        for _ in range(50):
            wx.Yield()
            if ctrls["results"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        assert ctrls["results"].GetItemCount() >= 1
        assert "1" in ctrls["summary"].GetLabel()
    finally:
        frame.Destroy()
        wx.Yield()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_pick_folder_button_real_event(tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame
    _app = wx.App.Get() or wx.App(False)
    tool = _fake_tool(monkeypatch=None, module_name="_fake_ansys_pick_folder")
    presentation = AnsysToolPresentation(tool)
    for i in range(5):
        (tmp_path / f"{i}.wbjn").write_text("x", encoding="utf-8")
    frame = build_ansys_frame(None, presentation, folder_chooser=lambda: str(tmp_path))
    try:
        ctrls = frame._wx_ansys_controls
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["pick_folder"].GetEventHandler().ProcessEvent(evt)
        for _ in range(50):
            wx.Yield()
            if ctrls["results"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        assert ctrls["results"].GetItemCount() >= 5
    finally:
        frame.Destroy()
        wx.Yield()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_ansys_details_copy_and_docs(tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame
    _app = wx.App.Get() or wx.App(False)
    tool = _fake_tool(monkeypatch=None, module_name="_fake_ansys_details")
    presentation = AnsysToolPresentation(tool)
    launched = []
    frame = build_ansys_frame(None, presentation, browser_launcher=lambda url: launched.append(url))
    try:
        tmp = tmp_path / "b.wbjn"
        tmp.write_text("x", encoding="utf-8")
        # use direct do_lint to populate
        frame._wx_ansys_do_lint_files([str(tmp)])
        for _ in range(50):
            wx.Yield()
            if frame._wx_ansys_controls["results"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        lst = frame._wx_ansys_controls["results"]
        assert lst.GetItemCount() >= 1
        lst.Select(0)
        # trigger selection handler via event
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, lst.GetId())
        evt.SetIndex(0)
        lst.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        detail = frame._wx_ansys_controls["detail"].GetValue()
        assert "why flagged" in detail.lower() or "why" in detail.lower()
        # copy diagnostic should not crash
        evt2 = wx.CommandEvent(wx.wxEVT_BUTTON)
        frame._wx_ansys_controls["copy_diag"].GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        # open docs with allowlisted url
        evt3 = wx.CommandEvent(wx.wxEVT_BUTTON)
        frame._wx_ansys_controls["open_doc"].GetEventHandler().ProcessEvent(evt3)
        wx.Yield()
        assert launched and "docs.ansys.com" in launched[0]
    finally:
        frame.Destroy()
        wx.Yield()


@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.gui
def test_wx_ansys_close_in_flight_safe(tmp_path: Path, monkeypatch):
    from hpc_gui.wx_ansys_view import build_ansys_frame
    _app = wx.App.Get() or wx.App(False)
    import sys
    mod = "_fake_ansys_slow"
    worker_started = threading.Event()
    release_worker = threading.Event()
    def slow_lint(text, file_name=""):
        worker_started.set()
        release_worker.wait(3)
        return [SimpleNamespace(code="X", message="m", line=1, column=1, severity=SimpleNamespace(value="error"), explanation="e", is_heuristic=False, suggested_fix="", source_url="")]
    fake = SimpleNamespace(SUPPORTED_SUFFIXES=frozenset({".wbjn"}), lint_text=slow_lint)
    sys.modules[mod] = fake
    sys.modules[f"{mod}.api"] = fake
    from hpc_gui.plugins.linter_tools import LinterTool
    tool = LinterTool("org.hpcclient.ansyslint", "0.1.0", "ANSYS", "", lambda **kwargs: None, mod)
    from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation
    presentation = AnsysToolPresentation(tool)
    tmp = tmp_path / "c.wbjn"
    tmp.write_text("x", encoding="utf-8")
    frame = build_ansys_frame(None, presentation, file_chooser=lambda: [str(tmp)])
    callbacks = []
    callback_queued = threading.Event()

    def defer_callback(callback, *args, **kwargs):
        callbacks.append((callback, args, kwargs))
        callback_queued.set()

    monkeypatch.setattr(wx, "CallAfter", defer_callback)
    try:
        ctrls = frame._wx_ansys_controls
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["pick_files"].GetEventHandler().ProcessEvent(evt)
        assert worker_started.wait(2), "linter worker did not start"
        frame.Close()
        wx.Yield()
        with pytest.raises(RuntimeError):
            frame.IsShown()
        release_worker.set()
        assert callback_queued.wait(2), "linter worker did not queue completion"
        assert len(callbacks) == 1
        callback, args, kwargs = callbacks[0]
        callback(*args, **kwargs)
        with pytest.raises(RuntimeError):
            frame.IsShown()
    finally:
        release_worker.set()
        try:
            frame.Destroy()
        except Exception:
            pass
        wx.Yield()


@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.gui
def test_wx_ansys_i18n_refresh(monkeypatch, tmp_path: Path):
    from hpc_gui.wx_ansys_view import build_ansys_frame
    from hpc_gui.core import i18n
    _app = wx.App.Get() or wx.App(False)
    monkeypatch.setattr(i18n, "app_data_dir", lambda: tmp_path)
    tool = _fake_tool(monkeypatch=None, module_name="_fake_ansys_i18n")
    presentation = AnsysToolPresentation(tool)
    frame = build_ansys_frame(None, presentation)
    original_language = i18n.current_language()
    try:
        ctrls = frame._wx_ansys_controls
        i18n.set_language("en")
        before = ctrls["pick_files"].GetLabel()
        i18n.set_language("tr")
        wx.Yield()
        after_tr = ctrls["pick_files"].GetLabel()
        assert after_tr == i18n.t("ansyslint.pick_files")
        assert after_tr != before
        i18n.set_language("en")
        wx.Yield()
        after_en = ctrls["pick_files"].GetLabel()
        assert after_en == i18n.t("ansyslint.pick_files")
        assert after_en == before
    finally:
        i18n.set_language(original_language)
        wx.Yield()
        frame.Destroy()
        wx.Yield()
