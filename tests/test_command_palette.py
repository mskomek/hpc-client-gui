import pytest

from hpc_gui.core.i18n import load_language
from hpc_gui.services.command_palette import CommandPalette


def test_palette_search_ranking_and_required_commands():
    load_language("en")
    palette = CommandPalette()
    assert palette.search("refresh")[0].command.id == "FILE-REFRESH"
    ids = {item.command.id for item in palette.search("cluster")}
    assert "JOB-TEST-CLUSTER" in ids
    assert {"APP-COMMAND-PALETTE", "JOB-TEST-CLUSTER", "EDITOR-NEW-SLURM", "PLUGIN-ANSYS-LINTER"} <= {item.command.id for item in palette.items()}


def test_palette_disables_wrong_context_and_executes_by_id():
    palette = CommandPalette()
    assert not palette.search("save", context="terminal")[0].enabled
    with pytest.raises(PermissionError):
        palette.execute("EDIT-SAVE", "terminal", {"EDIT-SAVE": lambda: True})
    assert palette.execute("EDIT-SAVE", "editor", {"EDIT-SAVE": lambda: "saved"}) == "saved"
