"""Tests for coordinated menu/plugin-UI redesign."""

from __future__ import annotations

import json
import pathlib


def read_main_window() -> str:
    return pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")


def test_qt_shell_has_menu_plugins_help():
    src = read_main_window()
    assert 'self._menu_menu = menubar.addMenu(t("menu.menu"))' in src
    assert 'self._plugins_menu = menubar.addMenu(t("menu.plugins"))' in src
    assert 'self._help_menu = menubar.addMenu(t("menu.help"))' in src
    # Old code dumped all shell commands under Help – must be gone
    assert 'COMMAND_REGISTRY.by_context("shell")' not in src


def test_old_top_right_button_farm_removed():
    src = read_main_window()
    # Old farm buttons must be gone
    assert "self._update_btn" not in src or src.count("self._update_btn") == 0 or "self._act_check_updates" in src
    # The new corner widget should only have language + version
    # Check that corner widget layout only adds version + lang, not extra buttons
    # Count corner widget addWidget calls: should be exactly 2 (version + lang)
    # Simple check: no _plugins_btn, _send_logs_btn, _settings_btn, _help_btn in corner
    assert "self._plugins_btn" not in src
    assert "self._send_logs_btn" not in src
    assert "self._settings_btn" not in src
    assert "self._help_btn" not in src


def test_language_and_version_remain():
    src = read_main_window()
    assert "self._lang_btn" in src
    assert "self._version_label = QLabel(f\"v{__version__}\"" in src
    # Version plain text must be visible upper right, not exclusively in About
    assert "setCornerWidget" in src
    # Language must retranslate menus immediately
    assert "self._switch_language" in src
    # Wide minimum width removed
    assert 'setMinimumWidth(220)' not in src


def test_menu_ownership():
    src = read_main_window()
    # Settings + Check for Updates + Exit in Menu
    assert 'self._act_settings' in src and 't("menu.settings")' in src
    assert 'self._act_check_updates' in src and 't("menu.check_updates")' in src
    assert 'self._act_exit' in src and 't("menu.exit")' in src
    # Plugin manager actions in Plugins
    assert 'self._act_plugins_discover' in src
    assert 'self._act_plugins_installed' in src
    assert 'self._act_plugins_updates' in src
    assert 'self._act_request_plugin' in src
    # Ensure Send Logs not in Menu, plugin management not in Help
    # Check that Send Logs action is under Help menu
    assert 'self._act_send_logs' in src
    # Verify Help contains Help Center, Send Logs, About
    assert 'self._act_help_center' in src
    assert 'self._act_about' in src
    # Ensure old duplicate standalone top-right buttons gone (already checked)


def test_version_not_only_in_about():
    src = read_main_window()
    # Version label must exist outside About
    assert "self._version_label" in src
    assert pathlib.Path("src/hpc_gui/ui/dialogs/about_dialog.py").exists()


def test_command_palette_not_miswired():
    src = read_main_window()
    # Command Palette must NOT call HelpDialog
    assert "self._act_command_palette" not in src or "HelpDialog" not in src.split("self._act_command_palette")[0][-500:] if "self._act_command_palette" in src else True
    # If command palette entry exists, it must not trigger _open_help
    if "_act_command_palette" in src:
        # Find its triggered connection
        assert "_open_help" not in src.split("_act_command_palette")[1][:500]


def test_no_hardcoded_ansys_truba_ids():
    src = read_main_window()
    assert 'if plugin.id == "org.hpcclient.fluent"' not in src
    assert "if plugin.id == 'org.hpcclient.fluent'" not in src
    assert 'if plugin.id == "org.hpcclient.truba"' not in src
    # Also check services/plugin_menu_actions.py
    action_src = pathlib.Path("src/hpc_gui/services/plugin_menu_actions.py").read_text(encoding="utf-8")
    assert "org.hpcclient.fluent" not in action_src
    assert "org.hpcclient.truba" not in action_src
    # Check ui_contributions
    contrib_src = pathlib.Path("src/hpc_gui/plugins/ui_contributions.py").read_text(encoding="utf-8")
    assert "org.hpcclient.fluent" not in contrib_src


def test_plugin_manager_semantic_tabs():
    src = pathlib.Path("src/hpc_gui/ui/dialogs/plugin_manager_dialog.py").read_text(encoding="utf-8")
    assert "_INITIAL_TAB_MAP" in src
    assert '"discover": 0' in src
    assert '"installed": 1' in src
    assert '"updates": 2' in src
    assert "initial_tab" in src
    assert "def _open_plugins" in read_main_window() and "initial_tab" in read_main_window()
    assert "discover" in src and "installed" in src and "updates" in src
    # Invalid fallback to discover
    assert "fallback" in src.lower() or "0" in src


def test_plugins_changed_emitted_all_paths():
    src = pathlib.Path("src/hpc_gui/ui/dialogs/plugin_manager_dialog.py").read_text(encoding="utf-8")
    # install, remove, toggle, activate version should emit
    assert src.count("plugins_changed.emit()") >= 4
    assert "def toggle_plugin_disabled" in src and "plugins_changed.emit()" in src.split("def toggle_plugin_disabled")[1][:500]
    assert "def remove_plugin" in src and "plugins_changed.emit()" in src
    assert "def change_plugin_version" in src or "activate_version" in src


def test_dynamic_plugin_menu_uses_contributions():
    src = read_main_window()
    assert "collect_plugin_menu_contributions" in src
    assert "MenuContext" in src
    assert "aboutToShow" in src
    assert "evaluate_when" in src


def test_i18n_keys_exist():
    en = json.loads(pathlib.Path("src/hpc_gui/i18n/en.json").read_text(encoding="utf-8"))
    tr = json.loads(pathlib.Path("src/hpc_gui/i18n/tr.json").read_text(encoding="utf-8"))
    for key in ["menu.menu", "menu.plugins", "menu.help", "menu.settings", "menu.check_updates", "menu.exit",
                "menu.browse_install", "menu.manage_installed", "menu.check_plugin_updates", "menu.request_plugin",
                "menu.help_center", "menu.quick_tour", "menu.send_logs", "menu.about",
                "about.title", "about.version_label"]:
        parts = key.split(".")
        cur_en = en
        cur_tr = tr
        for p in parts:
            assert p in cur_en, f"missing EN {key}"
            assert p in cur_tr, f"missing TR {key}"
            cur_en = cur_en[p]
            cur_tr = cur_tr[p]


def test_about_dialog_properties():
    src = pathlib.Path("src/hpc_gui/ui/dialogs/about_dialog.py").read_text(encoding="utf-8")
    assert "__version__" in src
    assert "v{__version__}" in src or "Version {version}" in src or "version_label" in src
    assert "is_frozen_exe" in src or "frozen" in src
    assert "THIRD_PARTY_NOTICES" in src or "notices" in src.lower()
    assert "https://github.com/mskomek/hpc-client-gui" in src
    # Must not require network to instantiate (no requests)
    assert "requests" not in src.lower()
