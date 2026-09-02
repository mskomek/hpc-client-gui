from hpc_gui.core.i18n import load_language
from hpc_gui.services.help_catalog import HELP_CATALOG
from hpc_gui.services.platform_keymap import bindings_for


def test_shortcut_reference_uses_active_platform_and_keeps_context_duplicates():
    load_language("en")
    windows = HELP_CATALOG.shortcut_reference("windows")
    macos = HELP_CATALOG.shortcut_reference("macos")
    assert any(row.binding == "Ctrl+Shift+C" and row.context == "terminal" for row in windows)
    assert any(row.binding == "⇧⌘Z" and row.command_id == "EDIT-REDO" for row in macos)
    assert sum(row.binding == "⌘C" for row in macos) == 2


def test_custom_active_map_is_rendered_without_manual_table():
    custom = list(bindings_for("linux"))
    custom[0] = type(custom[0])(custom[0].command_id, "Ctrl+Alt+S", custom[0].context)
    rows = HELP_CATALOG.shortcut_reference("linux", tuple(custom))
    assert rows[0].binding == "Ctrl+Alt+S"
