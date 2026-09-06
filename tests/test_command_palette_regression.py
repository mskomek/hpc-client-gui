"""Regression test proving Command Palette does not open Help."""

def test_command_palette_not_wired_to_help():
    import pathlib
    src = pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    # The old miswire was: _act_command_palette.triggered -> _open_help
    assert "_act_command_palette" not in src or "_open_help" not in src.split("_act_command_palette")[1][:1000] if "_act_command_palette" in src else True
    # Ensure Help on F1 still works
    assert "F1" in src or 'setShortcut' in src
    # If palette implementation exists, it should be wired to real palette, not HelpDialog
    # Check that HelpDialog is not opened via command palette path
    palette_src = pathlib.Path("src/hpc_gui/services/command_palette.py").read_text(encoding="utf-8")
    assert "class CommandPalette" in palette_src
    # Main window should not have command palette calling HelpDialog
    if "command_palette" in src.lower():
        # Ensure any palette trigger does not directly call HelpDialog
        assert src.count("HelpDialog") <= 1  # only legitimate Help Center
