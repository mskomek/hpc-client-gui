import pytest

from hpc_gui.core.i18n import load_language
from hpc_gui.services.command_registry import COMMAND_REGISTRY, CommandDefinition, CommandRegistry


def test_registry_ids_labels_queries_and_serialization():
    load_language("tr")
    commands = COMMAND_REGISTRY.all()
    assert len({command.id for command in commands}) == len(commands)
    assert all(not command.label().startswith("[") for command in commands)
    assert COMMAND_REGISTRY.get("EDIT-SAVE").label()
    assert COMMAND_REGISTRY.get("EDIT-SAVE").default_bindings == ("Ctrl+S",)
    assert any(command.id == "FILE-REFRESH" for command in COMMAND_REGISTRY.by_context("directory"))
    assert COMMAND_REGISTRY.serialize()[0]["id"] == commands[0].id


def test_unknown_and_duplicate_commands_fail():
    with pytest.raises(KeyError, match="unknown command"):
        COMMAND_REGISTRY.get("missing")
    command = CommandDefinition("DUP", "help.open_help", "help", "shell", "help.open_help")
    with pytest.raises(ValueError, match="duplicate"):
        CommandRegistry((command, command))
