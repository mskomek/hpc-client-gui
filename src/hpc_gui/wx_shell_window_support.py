"""Window geometry, status, and tray support for the wx shell."""
from __future__ import annotations

from pathlib import Path
from hpc_gui.core.i18n import t


def _flag_bitmap(wx, language):
    path = Path(__file__).resolve().parent / "assets" / "flags" / ("gb.svg" if language == "en" else "tr.svg")
    try:
        import wx.svg

        return wx.svg.SVGimage.CreateFromBytes(path.read_bytes()).ConvertToBitmap(18, 12)
    except Exception:
        bitmap = wx.Bitmap(18, 12)
        dc = wx.MemoryDC(bitmap)
        dc.SetBrush(wx.Brush("#1f4e79" if language == "en" else "#e30a17"))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bitmap


class _WxTrayAdapter:
    def __init__(self, wx, frame):
        import wx.adv

        class TrayIcon(wx.adv.TaskBarIcon):
            def CreatePopupMenu(self):
                menu = wx.Menu()
                close = menu.Append(wx.ID_EXIT, t("common.close"))
                self.Bind(wx.EVT_MENU, lambda _event: frame.Close(), close)
                return menu

        self._tray = TrayIcon()
        self._tray.SetIcon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION), "HPC Client GUI")

    def notify(self, message):
        return self._tray.ShowBalloon(t("login.job_notification_title"), message, 5000)

    def destroy(self):
        tray, self._tray = self._tray, None
        if tray is not None:
            tray.Destroy()


def _make_tray(wx, frame, tray_factory):
    if tray_factory is not None:
        try:
            return tray_factory(frame)
        except (ImportError, RuntimeError):
            return None
    try:
        return _WxTrayAdapter(wx, frame)
    except (ImportError, RuntimeError):
        return None


def _window_work_areas(wx):
    """Current display work areas for geometry recovery (never raises)."""
    try:
        areas = []
        for idx in range(wx.Display.GetCount()):
            try:
                area = wx.Display(idx).GetClientArea()
                areas.append((area.x, area.y, area.width, area.height))
            except Exception:
                continue
        return tuple(areas)
    except Exception:
        return ()


def _restore_main_window_state(wx, frame, notebook):
    """Apply persisted main-window geometry/selection (HPC-W09-UISTATE-009..014).

    Best-effort: absent/corrupt/off-screen state resolves to fresh defaults
    and the frame keeps its constructed size. Never raises.
    """
    try:
        from hpc_gui.config.storage import get_main_window_state
        from hpc_gui.services.geometry_policy import Rect, resolve_main_window_state

        raw = get_main_window_state()
        if raw is None:
            return "fresh-defaults"
        areas = tuple(Rect(*a) for a in _window_work_areas(wx))
        try:
            tab_count = int(notebook.GetPageCount())
        except Exception:
            tab_count = None
        state = resolve_main_window_state(raw, areas, tab_count=tab_count)
        rect = state["rect"]
        try:
            frame.SetSize(rect.x, rect.y, rect.width, rect.height)
        except Exception:
            pass
        if state["selected_tab"] is not None:
            try:
                notebook.SetSelection(int(state["selected_tab"]))
            except Exception:
                pass
        if state["maximized"]:
            try:
                frame.Maximize(True)
            except Exception:
                pass
        return "restored"
    except Exception:
        return "fresh-defaults"


def _save_main_window_state(frame, notebook):
    """Persist current main-window geometry/selection (best-effort, never raises)."""
    try:
        from hpc_gui.config.storage import save_main_window_state

        try:
            pos = frame.GetPosition()
            size = frame.GetSize()
            maximized = bool(frame.IsMaximized())
        except Exception:
            return False
        try:
            selected = int(notebook.GetSelection())
        except Exception:
            selected = None
        if maximized:
            # A maximized frame reports its zoomed size; keep the record but
            # mark it so restore re-applies Maximize instead of a zoomed rect.
            pass
        save_main_window_state(
            x=int(pos.x),
            y=int(pos.y),
            width=int(size.width),
            height=int(size.height),
            maximized=maximized,
            selected_tab=selected,
        )
        return True
    except Exception:
        return False


def _set_shell_status_color(frame, bar, state: str, wx_module=None) -> None:
    try:
        if wx_module is None:
            import wx as wx_module
        defaults = getattr(frame, "_wx_shell_statusbar_colors", None)
        if defaults is None:
            defaults = (bar.GetBackgroundColour(), bar.GetForegroundColour())
            frame._wx_shell_statusbar_colors = defaults
        color = {
            "connecting": wx_module.Colour(179, 38, 30),
            "connected": wx_module.Colour(28, 120, 56),
        }.get(state)
        if color is None:
            background, foreground = defaults
        else:
            background, foreground = color, wx_module.Colour(255, 255, 255)
        bar.SetBackgroundColour(background)
        bar.SetForegroundColour(foreground)
        bar.Refresh()
    except Exception:
        pass


def _update_shell_status_text(frame, session_state) -> None:
    """Reflect connection state in the shell status bar and its background."""
    try:
        if frame is None:
            return
        try:
            if hasattr(frame, "IsBeingDeleted") and frame.IsBeingDeleted():
                return
        except Exception:
            pass
        bar = None
        try:
            bar = frame.GetStatusBar()
        except Exception:
            bar = None
        if bar is None:
            return
        session = None
        state = ""
        try:
            session = (session_state or {}).get("session")
            state = str((session_state or {}).get("connection_status") or "")
        except Exception:
            session = None
        connected = False
        if session is not None:
            try:
                connected = bool(
                    session.get("connected")
                    if isinstance(session, dict)
                    else session
                )
            except Exception:
                connected = False
        is_connecting = state in {"connecting", "authenticating"}
        if is_connecting or state == "failed":
            connected = False
        elif state == "connected":
            connected = True
        try:
            if connected:
                profile = session.get("profile") if isinstance(session, dict) else None
                name = profile.get("name") if isinstance(profile, dict) else None
                label = t("login.status_connected")
                text = f"{label}: {name}" if name else str(label)
            elif is_connecting:
                text = t("login.status_connecting")
            elif state == "failed":
                text = t("connection.status_failed")
            else:
                text = t("common.ready")
        except Exception:
            text = "connected" if connected else "ready"
        try:
            bar.SetStatusText(str(text))
        except Exception:
            pass
        color_state = "connecting" if is_connecting else (
            "connected" if connected else state
        )
        _set_shell_status_color(frame, bar, color_state)
    except Exception:
        pass
