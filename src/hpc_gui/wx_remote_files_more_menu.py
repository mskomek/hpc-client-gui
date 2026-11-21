"""Compact secondary-action menu for the wx remote file browser."""

from __future__ import annotations

from collections.abc import Callable, Iterable


def build_more_actions_menu(wx, translate, actions: Iterable[tuple[str, Callable]]) :
    """Build a translated menu from action keys and their event handlers."""
    menu = wx.Menu()
    for key, callback in actions:
        item = menu.Append(wx.ID_ANY, translate(key))
        menu.Bind(wx.EVT_MENU, callback, item)
    return menu
