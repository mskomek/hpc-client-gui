"""Contracts for coordinated menu/plugin UI in the active wx shell."""

from __future__ import annotations

import json
import pathlib

import pytest


def read_source(*modules):
    return "\n".join(pathlib.Path("src/hpc_gui", module).read_text(encoding="utf-8") for module in modules)


@pytest.mark.audit
def test_wx_shell_has_menu_plugins_help():
    src = read_source("wx_shell_frame.py")
    for name in ("menu", "plugins", "help"):
        assert f'menubar.Append({name}_menu, t("menu.{name}"))' in src
    assert 'COMMAND_REGISTRY.by_context("shell")' not in src


@pytest.mark.audit
def test_old_top_right_button_farm_removed():
    src = read_source("wx_shell_frame.py")
    for name in ("_update_btn", "_plugins_btn", "_send_logs_btn", "_settings_btn", "_help_btn"):
        assert name not in src
    assert "frame.SetMenuBar(menubar)" in src


@pytest.mark.audit
def test_language_and_version_remain():
    src = read_source("wx_shell_frame.py")
    assert 'menubar.Append(language_menu, t("help.language"))' in src
    assert 'menubar.Append(version_menu, f"v{__version__}")' in src
    assert "set_language(language)" in src
    assert 'menubar.SetMenuLabel(0, t("menu.menu"))' in src
    assert 'menubar.SetMenuLabel(1, t("menu.plugins"))' in src
    assert 'menubar.SetMenuLabel(2, t("menu.help"))' in src


@pytest.mark.audit
def test_menu_ownership():
    src = read_source("wx_shell_frame.py")
    for key in ("settings", "check_updates", "exit"):
        assert f't("menu.{key}")' in src
    assert "APP-UPDATE-CHECK" in src
    for key in ("browse_install", "manage_installed", "check_plugin_updates", "request_plugin"):
        assert f'plugins_menu.Append(wx.ID_ANY, t("menu.{key}"))' in src
    assert 'act_logs = help_menu.Append(wx.ID_ANY, t("menu.send_logs"))' in src
    assert 'act_help = help_menu.Append(wx.ID_HELP, t("menu.help_center"))' in src
    assert 'help_items["about"] = act_about' in src


@pytest.mark.audit
def test_version_not_only_in_about():
    assert 'menubar.Append(version_menu, f"v{__version__}")' in read_source("wx_shell_frame.py")
    assert pathlib.Path("src/hpc_gui/wx_about.py").exists()


@pytest.mark.audit
def test_command_palette_not_miswired():
    src = read_source("wx_shell_frame.py")
    dispatch = read_source("wx_shell_dispatch.py")
    assert 'wx.EVT_MENU, lambda _e: _dispatch("APP-HELP"' in src
    for line in src.splitlines():
        if "PALETTE" in line.upper() and "Bind(" in line:
            assert "APP-HELP" not in line
    assert 'from hpc_gui.wx_help import show_help' in dispatch


@pytest.mark.audit
def test_no_hardcoded_ansys_truba_ids():
    src = read_source("wx_shell_plugins.py", "services/plugin_menu_actions.py", "plugins/ui_contributions.py")
    assert "org.hpcclient.fluent" not in src
    assert "org.hpcclient.truba" not in src


@pytest.mark.audit
def test_plugin_manager_semantic_tabs():
    shared = read_source("_wx_plugins_view_shared.py")
    builder = read_source("_wx_plugins_view_builder.py")
    dispatch = read_source("wx_shell_dispatch.py")
    assert '_VIEW_IDS = ("discover", "installed", "updates")' in shared
    assert 'if normalized_tab not in _VIEW_IDS:' in builder
    assert 'normalized_tab = "discover"' in builder
    for command, tab in (("BROWSE", "discover"), ("MANAGE", "installed"), ("UPDATES", "updates")):
        assert f'"PLUGIN-{command}": "{tab}"' in dispatch
    assert "show_plugins(parent=parent, initial_tab=initial)" in dispatch


@pytest.mark.audit
def test_plugins_changed_emitted_all_paths():
    builder = read_source("_wx_plugins_view_builder.py")
    management = read_source("_wx_plugins_management.py")
    for handler in ("do_install", "do_remove", "do_toggle"):
        body = builder.split(f"def {handler}(", 1)[1].split("\n    def ", 1)[0]
        assert "notify_plugin_change(parent)" in body
    assert "notify_changed()" in management.split("def change_version(", 1)[1]
    assert "_wx_rebuild_plugins_menu" in management


@pytest.mark.audit
def test_dynamic_plugin_menu_uses_contributions():
    src = read_source("wx_shell_plugins.py")
    for marker in ("collect_plugin_menu_contributions", "MenuContext", "wx.EVT_MENU_OPEN", "evaluate_when"):
        assert marker in src


@pytest.mark.contract
@pytest.mark.semantic
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


@pytest.mark.audit
def test_about_dialog_properties():
    src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
    assert "__version__" in src
    assert "v{__version__}" in src or "Version {version}" in src or "version_label" in src
    assert "is_frozen_exe" in src or "frozen" in src
    assert "THIRD_PARTY_NOTICES" in src or "notices" in src.lower()
    assert "https://github.com/mskomek/hpc-client-gui" in src
    # Must not require network to instantiate (no requests)
    assert "requests" not in src.lower()
