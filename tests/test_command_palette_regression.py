"""Command palette and Help dispatch stay on the active wx services."""

from hpc_gui.services.command_palette import CommandPalette


def test_command_palette_dispatches_help_through_wx_action(monkeypatch):
    import hpc_gui.wx_help as wx_help
    from hpc_gui.wx_shell_dispatch import _dispatch

    opened = []
    parent = object()
    monkeypatch.setattr(wx_help, "show_help", lambda owner: opened.append(owner))

    palette = CommandPalette()
    help_items = palette.search("help", context="shell")
    assert help_items[0].command.id == "APP-HELP"

    result = palette.execute(
        "APP-HELP",
        "shell",
        {"APP-HELP": lambda: _dispatch("APP-HELP", parent)},
    )

    assert result is None
    assert opened == [parent]
