"""Legacy show_* wrappers for the wx updater dialog (split out of wx_updater_view)."""

from __future__ import annotations

from hpc_gui import __version__
from hpc_gui.core.i18n import t


class _LazyView:
    """Resolve wx_updater_view on attribute access.

    The wrappers are re-exported from wx_updater_view, so importing it here at module
    level would be circular. Resolving lazily also keeps the long-standing test seam
    (monkeypatching hpc_gui.wx_updater_view.WxUpdateDialog) working.
    """

    def __getattr__(self, name):
        from hpc_gui import wx_updater_view

        return getattr(wx_updater_view, name)


view = _LazyView()


def show_update_dialog(parent, release, *, mandatory: bool = False):
    """Entry point for the single-dialog flow. Returns True if update was started (download)."""
    dlg = view.WxUpdateDialog(parent, release, mandatory=mandatory)
    result = dlg.ShowModal()
    ok_id = dlg.wx.ID_OK
    # dlg is destroyed inside _start_install or on close
    try:
        dlg.Destroy()
    except Exception:
        pass
    return result == ok_id


# Backward compat wrappers

def show_update_checking(parent=None, lifecycle=None):
    # Return a checking dialog that can be used as before, but now delegates to WxUpdateDialog checking state
    dlg = view.WxUpdateDialog(parent, None)
    dlg._build_for_state(view.STATE_CHECKING)
    # Don't show modally here, let caller handle
    # For compat, create a simple dialog as before but we return the WxUpdateDialog's dlg
    c = dlg.dlg
    # Need to provide cancelled and timer for old API
    cancelled = {"v": False}
    timer = getattr(dlg, "_pulse_timer", None)
    # Wrap
    return c, cancelled, timer


def show_up_to_date(parent, version: str = __version__):
    dlg = view.WxUpdateDialog(parent, None)
    dlg._build_for_state(view.STATE_UP_TO_DATE)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res


def show_update_available(parent, current: str, latest: str, release_info: str = "", release=None):
    """Show the legacy availability dialog and return whether download began.

    The original wrapper returned ``True`` when the user pressed Download and
    ``False`` for Later or close.  The current dialog continues through the
    download/install flow, so modal return IDs alone no longer represent that
    compatibility contract.

    Production passes the real ``release``; without one a placeholder release
    is built for previews/tests only.
    """
    if release is None:
        from hpc_gui.services.app_updater import UpdateRelease
        release = UpdateRelease(version=latest or "1.9.0", tag=f"v{latest}", zip_name="hpc-client-gui_windows_onedir.zip", zip_url="https://example.com/fake.zip", sha_name="fake.sha256", sha_url="https://example.com", html_url="https://example.com", body=release_info, size=None)
    dlg = view.WxUpdateDialog(parent, release)
    dlg._build_for_state(view.STATE_UPDATE_AVAILABLE)
    download_requested = False
    start_download = dlg._start_download

    def track_download_request(*args, **kwargs):
        nonlocal download_requested
        download_requested = True
        return start_download(*args, **kwargs)

    dlg._start_download = track_download_request
    try:
        dlg.ShowModal()
    finally:
        dlg.Destroy()
    return download_requested


def show_download_progress(parent, release_version: str, lifecycle=None):
    # For compat, create a WxUpdateDialog in downloading state with fake release
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version=release_version, tag=f"v{release_version}", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com", size=410*1024*1024)
    dlg = view.WxUpdateDialog(parent, fake)
    dlg._build_for_state(view.STATE_DOWNLOADING)
    # Expose old API surface
    # Create a wrapper dialog that has _wx_updater_update etc for tests that call it
    # Map to new dialog's methods
    outer = dlg.dlg
    outer._wx_updater_controls = {"byte_label": dlg._byte_label, "gauge": dlg._gauge, "percent": dlg._percent_label, "status": dlg._status_label, "cancel": dlg._cancel_btn}
    def upd(downloaded, total, phase="downloading"):
        # Delegate to dlg's internal update
        try:
            dlg._downloaded = downloaded
            if total:
                dlg._total = total
            if dlg._byte_label:
                if total:
                    dlg._byte_label.SetLabel(f"{view._format_bytes(downloaded)} / {view._format_bytes(total)}")
                    pct = int(downloaded*100/total) if total else 0
                    if dlg._gauge:
                        dlg._gauge.SetValue(pct)
                    if dlg._percent_label:
                        dlg._percent_label.SetLabel(f"{pct}%")
                else:
                    dlg._byte_label.SetLabel(t("updates.downloaded_bytes").format(bytes=view._format_bytes(downloaded)))
                if dlg._status_label:
                    dlg._status_label.SetLabel(phase)
                dlg.panel.Layout()
        except Exception:
            pass
    outer._wx_updater_update = upd
    outer._wx_updater_state = {"cancelled": False}
    # Override cancel to set flag
    orig_cancel = dlg._cancel_download
    def new_cancel(e=None):
        outer._wx_updater_state["cancelled"] = True
        dlg._cancelled = True
        orig_cancel()
    if dlg._cancel_btn:
        try:
            dlg._cancel_btn.Unbind(dlg.wx.EVT_BUTTON)
        except Exception:
            pass
        dlg._cancel_btn.Bind(dlg.wx.EVT_BUTTON, lambda e: new_cancel())
    return outer


def show_verifying(parent):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = view.WxUpdateDialog(parent, fake)
    dlg._build_for_state(view.STATE_VERIFYING)
    outer = dlg.dlg
    outer._wx_timer = getattr(dlg, "_pulse_timer", None)
    return outer


def show_update_ready(parent, version: str):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version=version, tag=f"v{version}", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = view.WxUpdateDialog(parent, fake)
    dlg._build_for_state(view.STATE_READY_TO_INSTALL)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res == dlg.wx.ID_OK


def show_installing_splash(parent, version: str):
    # Keep original implementation but ensure size 620x360 per spec §19
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.installing_title"), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dlg.SetSize(wx.Size(620, 360))
    dlg.CentreOnParent()
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.installing_title"))
    try:
        fnt = title.GetFont()
        fnt.SetPointSize(12)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    status = wx.StaticText(panel, label=t("updates.installing_message"))
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
    gauge.SetMinSize(wx.Size(-1, 16))
    percent = wx.StaticText(panel, label="0%")
    phase = wx.StaticText(panel, label="")
    file_label = wx.StaticText(panel, label="")
    try:
        file_label.SetForegroundColour(wx.Colour(90, 90, 90))
        file_label.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    except Exception:
        pass
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(status, 0, wx.LEFT | wx.RIGHT, 16)
    sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
    sizer.Add(percent, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 4)
    sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    sizer.Add(file_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    def update(value: int, message: str, current_file: str = ""):
        try:
            gauge.SetValue(max(0, min(100, int(value))))
            percent.SetLabel(f"{max(0,min(100,int(value)))}%")
            phase.SetLabel(str(message))
            file_label.SetLabel(str(current_file))
            panel.Layout()
        except Exception:
            pass
    dlg._wx_install_controls = {"gauge": gauge, "percent": percent, "phase": phase, "file": file_label, "status": status}
    dlg._wx_install_update = update
    return dlg


def show_update_error(parent, message: str):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = view.WxUpdateDialog(parent, fake)
    dlg._error_message = message
    dlg._error_details = message
    dlg._build_for_state(view.STATE_FAILED)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res == dlg.wx.ID_OK
