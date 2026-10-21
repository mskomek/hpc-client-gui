"""wx plugins view backed by WxPluginManagerModel (W35 backend-driven GUI)."""

from __future__ import annotations

from ._wx_plugins_view_shared import *  # noqa: F403
from ._wx_plugins_view_shared import WxPluginManagerModel
from ._wx_plugins_view_builder import _build_plugins

def build_plugins_panel(
    parent,
    model: WxPluginManagerModel | None = None,
    *,
    root=None,
    install=None,
    fetcher=None,
    initial_tab: str = "discover",
):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_plugins(
        parent,
        model,
        root=root,
        install=install,
        fetcher=fetcher,
        initial_tab=initial_tab,
        embedded=True,
    )


def show_plugins(
    parent=None,
    model: WxPluginManagerModel | None = None,
    *,
    root=None,
    install=None,
    fetcher=None,
    initial_tab: str = "discover",
) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_plugins(
        parent,
        model,
        root=root,
        install=install,
        fetcher=fetcher,
        initial_tab=initial_tab,
        embedded=False,
    )
    return wx.ID_OK


__all__ = ["build_plugins_panel", "show_plugins"]
