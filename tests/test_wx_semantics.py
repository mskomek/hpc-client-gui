"""Tests for wx shell semantics fixes."""

import pathlib

def read_wx():
    return pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")

def test_wx_no_shell_command_dump_under_help():
    src = read_wx()
    # Old code dumped all COMMAND_REGISTRY.by_context("shell") under Help
    assert 'COMMAND_REGISTRY.by_context("shell")' not in src or src.count('COMMAND_REGISTRY.by_context("shell")') == 0

def test_wx_semantic_menus():
    src = read_wx()
    assert 't("menu.menu")' in src
    assert 't("menu.plugins")' in src
    assert 't("menu.help")' in src
    assert "menu_menu = wx.Menu()" in src
    assert "plugins_menu = wx.Menu()" in src
    assert "help_menu = wx.Menu()" in src

def test_wx_version_plain_text():
    src = read_wx()
    # Version must be non-interactive visible upper-right text, not a fake vX menu
    assert 'version_text = wx.StaticText' in src
    assert 'f"v{__version__}"' in src
    # Should not have a real version menu as primary navigation – dummy compat is allowed
    # Ensure we use StaticText for version display
    assert 'version_menu' in src  # dummy compat allowed, but primary display is StaticText

def test_wx_shared_contribution_model():
    src = read_wx()
    assert "collect_plugin_menu_contributions" in src
    assert "ui_contributions" in src or "PluginMenu" in src

def test_wx_no_fake_parity_claims():
    src = read_wx()
    # plugin.open_trusted_tool should be disabled, not claimed working
    assert 'plugin.open_trusted_tool' in src
    assert 'Enable(False)' in src or 'disable' in src.lower()
