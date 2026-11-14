"""wx shell shortcut parsing, preference routing and collision contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.wx_shortcuts import (
    parse_binding,
    shell_accelerators,
    shell_bindings,
    to_wx_accel,
)


pytestmark = pytest.mark.unit


class _Wx:
    ACCEL_NORMAL = 0
    ACCEL_CTRL = 1
    ACCEL_ALT = 2
    ACCEL_SHIFT = 4
    WXK_F1 = 112
    WXK_RETURN = 13


def test_parser_retains_modifiers_and_literal_plus_key():
    assert parse_binding("Ctrl+Shift+N") == (frozenset({"ctrl", "shift"}), "N")
    assert parse_binding("Ctrl++") == (frozenset({"ctrl"}), "+")


def test_ctrl_shift_named_and_punctuation_shortcuts():
    wx = _Wx()
    assert to_wx_accel(wx, "Ctrl+Shift+H") == (5, ord("H"))
    assert to_wx_accel(wx, "Ctrl+,") == (1, ord(","))
    assert to_wx_accel(wx, "F1") == (0, wx.WXK_F1)
    assert to_wx_accel(wx, "Cmd+Return") == (1, wx.WXK_RETURN)
    assert to_wx_accel(wx, "Ctrl++") == (1, ord("+"))


@pytest.mark.parametrize("binding", ["", "Ctrl+BadModifier+A", "F25", "Ctrl+Hyper", "Ctrl+"])
def test_invalid_bindings_do_not_crash_shell_startup(binding):
    assert to_wx_accel(_Wx(), binding) is None


def test_missing_named_constant_does_not_raise():
    assert to_wx_accel(_Wx(), "Delete") is None


def test_preferred_shell_help_and_settings_are_loaded_and_help_first():
    settings = {
        "shortcut_preferences": {
            "version": 1,
            "bindings": {
                "APP-HELP": ["Ctrl+H"],
                "APP-SETTINGS": ["Ctrl+K"],
            },
        },
    }
    bindings = shell_bindings("windows", settings)
    assert bindings[:2] == [("APP-HELP", "Ctrl+H"), ("APP-SETTINGS", "Ctrl+K")]
    assert shell_accelerators(_Wx(), bindings) == [
        ("APP-HELP", 1, ord("H")),
        ("APP-SETTINGS", 1, ord("K")),
    ]


def test_shortcut_collisions_are_deduplicated_with_first_winner():
    combos = shell_accelerators(_Wx(), [
        ("APP-HELP", "F1"),
        ("APP-SETTINGS", "F1"),
        ("APP-SETTINGS", "Ctrl+,"),
    ])
    assert combos == [
        ("APP-HELP", 0, _Wx.WXK_F1),
        ("APP-SETTINGS", 1, ord(",")),
    ]


def test_shell_frame_prefers_ctrl_tab_navigation_and_help_fallback():
    path = Path(__file__).resolve().parents[1] / "src/hpc_gui/wx_shell_frame.py"
    frame = path.read_text(encoding="utf-8")
    assert "shell_accelerators(wx, shell_bindings(current_os()))" in frame
    assert "_used_accels = {" in frame
    assert "if _shortcut in _used_accels:" in frame
    assert '_shell_accels.insert(0, ("APP-HELP"' in frame
