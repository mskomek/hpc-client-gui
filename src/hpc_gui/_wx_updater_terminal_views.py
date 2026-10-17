from __future__ import annotations

from hpc_gui import __version__
from hpc_gui.core.i18n import t

class _UpdateDialogTerminalViews:
    def _build_ready(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        msg = wx.StaticText(self.panel, label=t("updates.ready_message_full").format(version=ver) if t("updates.ready_message_full") != "[updates.ready_message_full]" else f"HPC Client {ver} has been downloaded and verified.")
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        check1 = wx.StaticText(self.panel, label="✓ " + (t("updates.download_complete") if t("updates.download_complete") != "[updates.download_complete]" else "Download complete"))
        check2 = wx.StaticText(self.panel, label="✓ " + (t("updates.package_verified") if t("updates.package_verified") != "[updates.package_verified]" else "Package verified"))
        self.content_sizer.Add(check1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.Add(check2, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        restart = wx.StaticText(self.panel, label=t("updates.restart_required") if t("updates.restart_required") != "[updates.restart_required]" else "The application must restart to install the update.")
        try:
            restart.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(restart, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        self.content_sizer.AddStretchSpacer(1)

        btn_size = wx.Size(135, 32)
        later = wx.Button(self.panel, label=t("common.later") if t("common.later") != "[common.later]" else "Later")
        install = wx.Button(self.panel, label=t("updates.install_update") if t("updates.install_update") != "[updates.install_update]" else "Install Update")
        try:
            later.SetMinSize(btn_size)
            install.SetMinSize(btn_size)
            fnt = install.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            install.SetFont(fnt)
            install.SetDefault()
        except Exception:
            pass
        later.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        install.Bind(wx.EVT_BUTTON, lambda e: self._start_install())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(later, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(install, 0)


    def _build_failed(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.error_title") if t("updates.error_title") != "[updates.error_title]" else "Update Failed")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        body = wx.StaticText(self.panel, label=t("updates.error_message").format(error=self._error_message) if t("updates.error_message") != "[updates.error_message]" else f"The update could not be installed.\n\n{self._error_message}")
        try:
            body.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(body, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        details_btn = wx.Button(self.panel, label=t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details", style=wx.BORDER_NONE | wx.BU_EXACTFIT)
        try:
            details_btn.SetBackgroundColour(self.panel.GetBackgroundColour())
            fnt = details_btn.GetFont()
            fnt.SetUnderlined(True)
            details_btn.SetFont(fnt)
            details_btn.SetForegroundColour(wx.Colour(37, 99, 235))
        except Exception:
            pass
        details = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        details.SetMinSize(wx.Size(-1, 120))
        details.SetValue(self._error_details or self._error_message)
        try:
            details.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        except Exception:
            pass
        details.Hide()
        def on_details(e):
            if details.IsShown():
                details.Hide()
                details_btn.SetLabel(t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details")
            else:
                details.Show()
                details_btn.SetLabel(t("common.hide_details") if t("common.hide_details") != "[common.hide_details]" else "Hide Details")
            self.panel.Layout()
            self.dlg.Layout()
            try:
                self.dlg.Fit()
            except Exception:
                pass
        details_btn.Bind(wx.EVT_BUTTON, on_details)
        self.content_sizer.Add(details_btn, 0, wx.LEFT | wx.TOP, 12)
        self.content_sizer.Add(details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)

        btn_size = wx.Size(135, 32)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        retry = wx.Button(self.panel, label=t("common.retry") if t("common.retry") != "[common.retry]" else "Retry")
        try:
            close.SetMinSize(btn_size)
            retry.SetMinSize(btn_size)
            fnt = retry.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            retry.SetFont(fnt)
        except Exception:
            pass
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        retry.Bind(wx.EVT_BUTTON, lambda e: self._retry())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(retry, 0)


    def _build_cancelled(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.download_cancelled_title") if t("updates.download_cancelled_title") != "[updates.download_cancelled_title]" else "Download cancelled")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.download_cancelled_message") if t("updates.download_cancelled_message") != "[updates.download_cancelled_message]" else "The update was not installed.")
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        retry = wx.Button(self.panel, label=t("common.retry") if t("common.retry") != "[common.retry]" else "Retry")
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        retry.Bind(wx.EVT_BUTTON, lambda e: self._retry())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(retry, 0)


    def _build_up_to_date(self):
        wx = self.wx
        msg = wx.StaticText(self.panel, label=t("updates.up_to_date").format(version=__version__) if t("updates.up_to_date") != "[updates.up_to_date]" else f"You\u2019re up to date\n\nInstalled version: {__version__}\n\nNo newer version is available.")
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 1, wx.EXPAND | wx.ALL, 16)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_OK))
        try:
            close.SetDefault()
        except Exception:
            pass
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0)


    def _build_checking(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.checking_title") if t("updates.checking_title") != "[updates.checking_title]" else "Checking for updates...")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.checking_message") if t("updates.checking_message") != "[updates.checking_message]" else "Checking for updates...")
        self.content_sizer.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        gauge.Pulse()
        self._pulse_timer = wx.Timer(self.dlg)
        self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
        self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)

