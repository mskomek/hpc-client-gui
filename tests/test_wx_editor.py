from hpc_gui.services.editor_controller import LintResult
from hpc_gui.wx_editor import WxEditorModel


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
    assert "event.Veto()" in source and "save_document(on_done=frame.Close)" in source
