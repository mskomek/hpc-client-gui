from hpc_gui.services.focus_command_router import FocusCommandRouter


def test_focus_precedence_and_native_keys():
    router = FocusCommandRouter()
    assert router.resolve("Ctrl+Z", "remote_files").id == "FILE-REMOTE-UNDO"
    assert router.resolve("Ctrl+C", "local_files").id == "FILE-LOCAL-COPY"
    assert router.resolve("Ctrl+S", "editor").id == "EDIT-SAVE"
    assert router.resolve("Ctrl+S", "terminal") is None
    assert router.resolve("Ctrl+C", "terminal") is None
    assert router.resolve("Ctrl+V", "editor", text_input=True) is None


def test_unknown_focus_or_binding_is_not_invented():
    router = FocusCommandRouter()
    assert router.resolve("Ctrl+Q", "local_files") is None
    assert router.resolve("Ctrl+Z", "local_files") is None
