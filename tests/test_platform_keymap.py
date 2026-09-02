import pytest

from hpc_gui.services.platform_keymap import bindings_for, conflicts, display_binding


def test_windows_linux_defaults_and_terminal_boundary():
    for platform in ("windows", "win32", "linux"):
        bindings = bindings_for(platform)
        assert ("APP-SETTINGS", "Ctrl+,") in {(item.command_id, item.binding) for item in bindings}
        assert ("APP-COMMAND-PALETTE", "Ctrl+Shift+P") in {(item.command_id, item.binding) for item in bindings}
        assert ("TERM-COPY", "Ctrl+Shift+C") in {(item.command_id, item.binding) for item in bindings}
        assert not any(item.context == "terminal" and item.binding in {"Ctrl+C", "Ctrl+Z"} for item in bindings)
        assert not conflicts(bindings)


def test_optional_aliases_and_unsupported_platform():
    bindings = bindings_for("linux")
    assert sum(item.command_id == "FILE-LOCATION" for item in bindings) == 2
    assert sum(item.command_id == "FILE-NEW-FOLDER" for item in bindings) == 2
    with pytest.raises(ValueError, match="unsupported keymap platform"):
        bindings_for("freebsd")


def test_macos_uses_command_and_preserves_terminal_interrupt():
    bindings = bindings_for("macos")
    pairs = {(item.command_id, item.binding, item.context) for item in bindings}
    assert ("EDIT-REDO", "Shift+Cmd+Z", "editor") in pairs
    assert ("TERM-COPY", "Cmd+C", "terminal") in pairs
    assert ("TERM-PASTE", "Cmd+V", "terminal") in pairs
    assert not any(item.context == "terminal" and item.binding in {"Ctrl+C", "Ctrl+Z"} for item in bindings)
    assert display_binding("Shift+Cmd+S", "macos") == "⇧⌘S"
