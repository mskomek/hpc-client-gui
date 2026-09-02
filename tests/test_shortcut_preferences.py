from unittest.mock import patch

import pytest

from hpc_gui.services.shortcut_preferences import SCHEMA_VERSION, ShortcutPreferences


def test_remap_conflict_reset_and_versioned_persistence():
    prefs = ShortcutPreferences("windows")
    prefs.set_binding("FILE-REFRESH", "Ctrl+R")
    assert any(item.command_id == "FILE-REFRESH" and item.binding == "Ctrl+R" for item in prefs.bindings())
    with pytest.raises(ValueError, match="shortcut conflict"):
        prefs.set_binding("FILE-DELETE", "Ctrl+R")
    prefs.reset_command("FILE-REFRESH")
    assert any(item.command_id == "FILE-REFRESH" and item.binding == "F5" for item in prefs.bindings())
    with patch("hpc_gui.services.shortcut_preferences.update_settings") as update:
        value = prefs.persist()
    assert value["version"] == SCHEMA_VERSION
    update.assert_called_once()


def test_legacy_migration_and_context_scoped_duplicates():
    prefs = ShortcutPreferences("macos", {"shortcut_preferences": {"FILE-FIND": ["Cmd+K"]}})
    assert any(item.command_id == "FILE-FIND" and item.binding == "Cmd+K" for item in prefs.bindings())
    prefs.set_binding("TERM-COPY", "Cmd+C")
    assert not prefs.conflicts()
    prefs.reset_all()
    assert any(item.command_id == "TERM-COPY" and item.binding == "Cmd+C" for item in prefs.bindings())
