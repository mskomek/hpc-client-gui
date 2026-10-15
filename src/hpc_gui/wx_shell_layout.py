"""Persist the user-selected proportions of embedded wx splitters."""

from __future__ import annotations

from hpc_gui.config.storage import load_settings, update_settings


_MIN_RATIO = 0.05
_MAX_RATIO = 0.95


def _coerce_ratio(value, default: float) -> float:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return default
    if not _MIN_RATIO <= ratio <= _MAX_RATIO:
        return default
    return ratio


def _saved_ratio(key: str, default: float) -> float:
    try:
        settings = load_settings()
        ratios = settings.get("wx_splitter_ratios", {})
        value = ratios.get(key) if isinstance(ratios, dict) else None
        return _coerce_ratio(value, default)
    except Exception:
        return default


def _extent(splitter, orientation: str) -> int:
    size = splitter.GetClientSize()
    return int(size.width if orientation == "vertical" else size.height)


def _position_for_ratio(splitter, extent: int, ratio: float) -> int:
    minimum = max(0, int(splitter.GetMinimumPaneSize()))
    if extent < minimum * 2:
        return extent // 2
    return max(minimum, min(extent - minimum, round(extent * ratio)))


def _persist_ratio(key: str, ratio: float) -> None:
    try:
        settings = load_settings()
        ratios = settings.get("wx_splitter_ratios", {})
        updated = dict(ratios) if isinstance(ratios, dict) else {}
        updated[key] = ratio
        update_settings({"wx_splitter_ratios": updated})
    except Exception:
        # A settings write must never interrupt a sash drag or window close.
        pass


def install_splitter_ratio(
    wx,
    splitter,
    *,
    key: str,
    default_ratio: float = 0.5,
    orientation: str = "vertical",
) -> None:
    """Restore, resize, and persist a splitter's sash proportion.

    ``orientation`` is the split direction: vertical splitters use their
    width, horizontal splitters use their height.
    """
    if splitter is None or orientation not in {"vertical", "horizontal"}:
        return

    ratio = _saved_ratio(key, _coerce_ratio(default_ratio, 0.5))
    state = {"alive": True, "restored": False, "ratio": ratio}
    try:
        # Keep the constructor's pixel sash fixed until the first real layout;
        # applying gravity before the widget has its final size skews it.
        splitter.SetSashGravity(0.0)
    except Exception:
        pass

    def restore(_event=None):
        if not state["alive"] or state["restored"]:
            return
        try:
            if not splitter.IsSplit():
                return
            extent = _extent(splitter, orientation)
            if extent <= 0:
                return
            splitter.SetSashPosition(
                _position_for_ratio(splitter, extent, state["ratio"])
            )
            splitter.SetSashGravity(state["ratio"])
            state["restored"] = True
        except Exception:
            pass
        if _event is not None:
            _event.Skip()

    def resized(event):
        if not state["restored"]:
            wx.CallAfter(restore)
        event.Skip()

    def sash_changed(event):
        if state["alive"] and state["restored"]:
            try:
                extent = _extent(splitter, orientation)
                if extent > 0:
                    actual = int(splitter.GetSashPosition()) / extent
                    actual = max(_MIN_RATIO, min(_MAX_RATIO, actual))
                    state["ratio"] = actual
                    splitter.SetSashGravity(actual)
                    _persist_ratio(key, actual)
            except Exception:
                pass
        event.Skip()

    def destroyed(event=None):
        state["alive"] = False
        if event is not None:
            event.Skip()

    splitter.Bind(wx.EVT_SIZE, resized)
    splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, sash_changed)
    destroy_event = getattr(wx, "EVT_WINDOW_DESTROY", None)
    if destroy_event is not None:
        splitter.Bind(destroy_event, destroyed)
    wx.CallAfter(restore)


def install_shell_splitter_ratios(wx, directories_panel, session_state) -> None:
    """Attach saved ratios to the shell's directories and Files splitters."""
    directories = getattr(directories_panel, "_wx_dirs_controls", {})
    splitters = (
        (directories.get("splitter"), "directories_remote_panels", 0.5, "vertical"),
        (
            session_state.get("_embedded_files_panes_splitter"),
            "files_local_remote",
            0.5,
            "vertical",
        ),
        (
            session_state.get("_embedded_files_transfer_splitter"),
            "files_browser_transfers",
            0.72,
            "horizontal",
        ),
    )
    for splitter, key, default_ratio, orientation in splitters:
        install_splitter_ratio(
            wx,
            splitter,
            key=key,
            default_ratio=default_ratio,
            orientation=orientation,
        )
