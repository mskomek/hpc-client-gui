from hpc_gui.services.editor_controller import DocumentModel, EditorCommandService, EditorController, LintResult


def test_dirty_tracking_local_remote_and_duplicate_paths():
    controller = EditorController()
    index = controller.open(DocumentModel("/remote/a.sh", "old", "old"))
    assert not controller.active.dirty
    controller.update_content("new")
    assert controller.active.dirty and controller.active.is_local is False
    assert controller.open(DocumentModel("/remote/a.sh", "ignored")) == index
    controller.mark_saved()
    assert not controller.active.dirty


def test_submit_run_template_and_lint_navigation_data():
    assert EditorCommandService.execute_mode("a.slurm") == "submit"
    assert EditorCommandService.execute_mode("a.sh") == "run"
    assert EditorCommandService.execute_mode("a.txt") == "save"
    assert EditorCommandService.suggested_filename("") == "untitled.sh"
    result = LintResult(3, 4, "bad directive")
    assert (result.line, result.column) == (3, 4)


def test_editor_models_have_no_qt_imports():
    source = __import__("inspect").getsource(EditorController)
    assert "PySide" not in source
