"""wx updater dialogs per spec §83-90 — real bytes, progress, verifying, install splash."""

from __future__ import annotations

from threading import Thread
from pathlib import Path

from hpc_gui import __version__
from hpc_gui.core.i18n import t


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def show_update_checking(parent=None, lifecycle=None):
    """Spec §84: Checking dialog with indeterminate progress."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.title") if t("updates.title") != "[updates.title]" else "Check for Updates", style=wx.DEFAULT_DIALOG_STYLE)
    dlg.SetMinSize(wx.Size(420, 200))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.checking_title") if t("updates.checking_title") != "[updates.checking_title]" else "Check for Updates")
    try:
        fnt = title.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    msg = wx.StaticText(panel, label=t("updates.checking_message") if t("updates.checking_message") != "[updates.checking_message]" else "Checking for updates...")
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
    gauge.Pulse()
    timer = wx.Timer(dlg)
    dlg.Bind(wx.EVT_TIMER, lambda _e: gauge.Pulse(), timer)
    timer.Start(100)
    cancel = wx.Button(panel, label=t("common.cancel"))
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    btns = wx.BoxSizer(wx.HORIZONTAL)
    btns.AddStretchSpacer(1)
    btns.Add(cancel, 0, wx.RIGHT, 8)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()
    cancelled = {"v": False}
    def on_cancel(_e):
        cancelled["v"] = True
        if lifecycle is not None:
            try:
                lifecycle.cancel_update()
            except Exception:
                pass
        timer.Stop()
        dlg.EndModal(wx.ID_CANCEL)
    cancel.Bind(wx.EVT_BUTTON, on_cancel)
    dlg.Bind(wx.EVT_CLOSE, lambda e: (timer.Stop(), e.Skip()))
    return dlg, cancelled, timer


def show_up_to_date(parent, version: str = __version__):
    """Spec §85: You're up to date."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    msg = t("updates.up_to_date").format(version=version) if t("updates.up_to_date") != "[updates.up_to_date]" else f"You're up to date\n\nInstalled version: {version}\n\nNo newer version is available."
    # Fallback formatting per spec
    if "Installed version" not in msg:
        msg = f"You're up to date\n\nInstalled version: {version}\n\nNo newer version is available."
    wx.MessageBox(msg, t("updates.title") if t("updates.title") != "[updates.title]" else "Updates", wx.OK | wx.ICON_INFORMATION, parent)


def show_update_available(parent, current: str, latest: str, release_info: str = ""):
    """Spec §86: Update available with Installed + new version, Later / Download."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.available_title") if t("updates.available_title") != "[updates.available_title]" else "Update available", style=wx.DEFAULT_DIALOG_STYLE)
    dlg.SetMinSize(wx.Size(480, 260))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.available_title") if t("updates.available_title") != "[updates.available_title]" else "Update available")
    try:
        fnt = title.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        fnt.SetPointSize(11)
        title.SetFont(fnt)
    except Exception:
        pass
    body = wx.StaticText(panel, label=f"Installed version: {current}\nNew version:       {latest}" + (f"\n\n{release_info}" if release_info else ""))
    try:
        body.Wrap(440)
    except Exception:
        pass
    btns = wx.StdDialogButtonSizer()
    later = wx.Button(panel, label=t("common.later") if t("common.later") != "[common.later]" else "Later")
    download = wx.Button(panel, label=t("updates.download") if t("updates.download") != "[updates.download]" else "Download")
    try:
        download.SetMinSize(wx.Size(88, 30))
        fnt = download.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        download.SetFont(fnt)
        download.SetDefault()
    except Exception:
        pass
    btns.AddButton(later)
    btns.AddButton(download)
    btns.Realize()
    later.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_CANCEL))
    download.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_OK))
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(body, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_OK


def show_download_progress(parent, release_version: str, lifecycle=None):
    """Spec §87 + §88: Downloading update with bytes/percentage/gauge."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.downloading_title") if t("updates.downloading_title") != "[updates.downloading_title]" else "Downloading update", style=wx.DEFAULT_DIALOG_STYLE)
    # §87 requires bytes + percentage + progress bar + cancel
    dlg.SetMinSize(wx.Size(480, 280))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.downloading_title") if t("updates.downloading_title") != "[updates.downloading_title]" else "Downloading update")
    try:
        fnt = title.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    ver_label = wx.StaticText(panel, label=f"HPC Client {release_version}")
    byte_label = wx.StaticText(panel, label="0 B / 0 B")
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
    gauge.SetMinSize(wx.Size(-1, 14))
    percent_label = wx.StaticText(panel, label="0%")
    try:
        percent_label.SetForegroundColour(wx.Colour(60, 60, 60))
    except Exception:
        pass
    status = wx.StaticText(panel, label=t("updates.downloading_message") if t("updates.downloading_message") != "[updates.downloading_message]" else "Downloading...")
    cancel = wx.Button(panel, label=t("common.cancel"))
    try:
        cancel.SetMinSize(wx.Size(88, 30))
    except Exception:
        pass

    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(ver_label, 0, wx.LEFT | wx.RIGHT, 16)
    sizer.Add(byte_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
    sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
    sizer.Add(percent_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 4)
    sizer.Add(status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    btns = wx.BoxSizer(wx.HORIZONTAL)
    btns.AddStretchSpacer(1)
    btns.Add(cancel, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()

    state = {"cancelled": False}
    def on_cancel(_e):
        state["cancelled"] = True
        if lifecycle is not None:
            try:
                lifecycle.cancel_update()
            except Exception:
                pass
        dlg.EndModal(wx.ID_CANCEL)
    cancel.Bind(wx.EVT_BUTTON, on_cancel)

    def update_progress(downloaded: int, total: int, phase: str = "downloading"):
        try:
            byte_label.SetLabel(f"{_format_bytes(downloaded)} / {_format_bytes(total)}" if total else f"{_format_bytes(downloaded)} downloaded")
            pct = int(downloaded * 100 / total) if total else 0
            gauge.SetValue(max(0, min(100, pct)))
            percent_label.SetLabel(f"{pct}%")
            if phase == "verifying":
                status.SetLabel(t("updates.verifying") if t("updates.verifying") != "[updates.verifying]" else "Verifying downloaded update...")
            elif phase == "ready":
                status.SetLabel(t("updates.ready") if t("updates.ready") != "[updates.ready]" else "Update ready to install")
            else:
                status.SetLabel(t("updates.downloading_message") if t("updates.downloading_message") != "[updates.downloading_message]" else "Downloading...")
            panel.Layout()
        except Exception:
            pass

    dlg._wx_updater_controls = {"byte_label": byte_label, "gauge": gauge, "percent": percent_label, "status": status, "cancel": cancel}
    dlg._wx_updater_update = update_progress
    dlg._wx_updater_state = state
    return dlg


def show_verifying(parent):
    """Spec §88 verifying step."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.verifying_title") if t("updates.verifying_title") != "[updates.verifying_title]" else "Verifying update", style=wx.DEFAULT_DIALOG_STYLE)
    dlg.SetMinSize(wx.Size(420, 180))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    msg = wx.StaticText(panel, label=t("updates.verifying") if t("updates.verifying") != "[updates.verifying]" else "Verifying downloaded update...")
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
    gauge.Pulse()
    timer = wx.Timer(dlg)
    dlg.Bind(wx.EVT_TIMER, lambda _e: gauge.Pulse(), timer)
    timer.Start(100)
    sizer.Add(msg, 0, wx.ALL, 16)
    sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()
    dlg._wx_timer = timer
    return dlg


def show_update_ready(parent, version: str):
    """Spec §88 after verifying: Update ready to install."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.ready_title") if t("updates.ready_title") != "[updates.ready_title]" else "Update ready to install", style=wx.DEFAULT_DIALOG_STYLE)
    dlg.SetMinSize(wx.Size(480, 220))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.ready_title") if t("updates.ready_title") != "[updates.ready_title]" else "Update ready to install")
    try:
        fnt = title.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    body = wx.StaticText(panel, label=t("updates.ready_message").format(version=version) if t("updates.ready_message") != "[updates.ready_message]" else f"The update {version} has been downloaded and verified.")
    later = wx.Button(panel, label=t("common.later") if t("common.later") != "[common.later]" else "Later")
    install = wx.Button(panel, label=t("updates.install") if t("updates.install") != "[updates.install]" else "Install")
    try:
        install.SetMinSize(wx.Size(88, 30))
        fnt = install.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        install.SetFont(fnt)
        install.SetDefault()
    except Exception:
        pass
    btns = wx.BoxSizer(wx.HORIZONTAL)
    btns.AddStretchSpacer(1)
    btns.Add(later, 0, wx.RIGHT, 8)
    btns.Add(install, 0)
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(body, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()
    later.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_CANCEL))
    install.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_OK))
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_OK


def show_installing_splash(parent, version: str):
    """Spec §89: Installation progress splash 620×360 with phase, file, verification."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.installing_title") if t("updates.installing_title") != "[updates.installing_title]" else "Updating HPC Client", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dlg.SetSize(wx.Size(620, 360))
    dlg.CentreOnParent()
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.installing_title") if t("updates.installing_title") != "[updates.installing_title]" else "Updating HPC Client")
    try:
        fnt = title.GetFont()
        fnt.SetPointSize(12)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    status = wx.StaticText(panel, label=t("updates.installing_message") if t("updates.installing_message") != "[updates.installing_message]" else "Installing update...")
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
    """Spec §90: Update failed with Show Details."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.error_title") if t("updates.error_title") != "[updates.error_title]" else "Update failed", style=wx.DEFAULT_DIALOG_STYLE)
    dlg.SetMinSize(wx.Size(420, 260))
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.error_title") if t("updates.error_title") != "[updates.error_title]" else "Update failed")
    try:
        fnt = title.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    body = wx.StaticText(panel, label=t("updates.error_message").format(error=message) if t("updates.error_message") != "[updates.error_message]" else f"The update could not be installed.\n\n{message}")
    body.Wrap(380)
    details_btn = wx.Button(panel, label=t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details")
    details_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    details_text.SetMinSize(wx.Size(-1, 100))
    details_text.SetValue(str(message))
    details_text.Hide()
    try:
        details_text.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    except Exception:
        pass
    def on_details(_e):
        if details_text.IsShown():
            details_text.Hide()
            details_btn.SetLabel(t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details")
        else:
            details_text.Show()
            details_btn.SetLabel(t("common.hide_details") if t("common.hide_details") != "[common.hide_details]" else "Hide Details")
        panel.Layout()
        dlg.Layout()
        dlg.Fit()
    details_btn.Bind(wx.EVT_BUTTON, on_details)
    btns = wx.BoxSizer(wx.HORIZONTAL)
    close = wx.Button(panel, label=t("common.close"))
    retry = wx.Button(panel, label=t("common.retry"))
    try:
        retry.SetMinSize(wx.Size(88, 30))
        fnt = retry.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        retry.SetFont(fnt)
    except Exception:
        pass
    btns.AddStretchSpacer(1)
    btns.Add(close, 0, wx.RIGHT, 8)
    btns.Add(retry, 0)
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(body, 0, wx.LEFT | wx.RIGHT, 16)
    sizer.Add(details_btn, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    sizer.Add(details_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    dlg.Fit()
    close.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_CANCEL))
    retry.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_OK))
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_OK


__all__ = [
    "show_update_checking",
    "show_up_to_date",
    "show_update_available",
    "show_download_progress",
    "show_verifying",
    "show_update_ready",
    "show_installing_splash",
    "show_update_error",
    "_format_bytes",
]
