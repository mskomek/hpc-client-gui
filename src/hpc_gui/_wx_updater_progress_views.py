"""View builders for updater progress, verification, and recovery states."""

from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui._wx_updater_text import _format_bytes


class _UpdateProgressViewsMixin:
    """Build the updater download and verification screens."""

    def _build_downloading(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        title = wx.StaticText(
            self.panel, label=f"{t('app.title')} {ver}" if ver else t("app.title")
        )
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        status = wx.StaticText(self.panel, label=t("updates.downloading_message"))
        self.content_sizer.Add(status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._status_label = status

        # Byte label and progress
        if self._total:
            byte_txt = f"{_format_bytes(self._downloaded)} / {_format_bytes(self._total)}"
            pct = int(self._downloaded * 100 / self._total) if self._total else 0
        else:
            byte_txt = (
                t("updates.downloaded_bytes").format(bytes=_format_bytes(self._downloaded))
                if self._downloaded
                else t("updates.calculating")
            )
            pct = 0
        byte_lbl = wx.StaticText(self.panel, label=byte_txt)
        self._byte_label = byte_lbl
        self.content_sizer.Add(byte_lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        if self._total:
            gauge.SetValue(pct)
        else:
            gauge.Pulse()
            # indeterminate timer
            self._pulse_timer = wx.Timer(self.dlg)
            self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
            self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        percent = wx.StaticText(self.panel, label=f"{pct}%" if self._total else "")
        self._percent_label = percent
        self.content_sizer.Add(percent, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 4)

        phase = wx.StaticText(self.panel, label=t("updates.downloading_package"))
        self.content_sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._status_label = phase  # reuse for phase updates

        self.content_sizer.AddStretchSpacer(1)

        cancel = wx.Button(self.panel, label=t("common.cancel"))
        try:
            cancel.SetMinSize(wx.Size(88, 30))
        except Exception:
            pass
        cancel.Bind(wx.EVT_BUTTON, lambda e: self._cancel_download())
        self._cancel_btn = cancel
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(cancel, 0)

    def _build_verifying(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        title = wx.StaticText(
            self.panel, label=f"{t('app.title')} {ver}" if ver else t("app.title")
        )
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.verifying"))
        self.content_sizer.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        # indeterminate unless we have real progress
        gauge.Pulse()
        self._pulse_timer = wx.Timer(self.dlg)
        self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
        self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        phase = wx.StaticText(self.panel, label=t("updates.checking_integrity"))
        self.content_sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)

    def _build_ready(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        msg = wx.StaticText(
            self.panel,
            label=t("updates.ready_message_full").format(version=ver),
        )
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        check1 = wx.StaticText(self.panel, label="✓ " + t("updates.download_complete"))
        check2 = wx.StaticText(self.panel, label="✓ " + t("updates.package_verified"))
        self.content_sizer.Add(check1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.Add(check2, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        restart = wx.StaticText(self.panel, label=t("updates.restart_required"))
        try:
            restart.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(restart, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        self.content_sizer.AddStretchSpacer(1)

        btn_size = wx.Size(135, 32)
        later = wx.Button(self.panel, label=t("common.later"))
        install = wx.Button(self.panel, label=t("updates.install_update"))
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
        title = wx.StaticText(self.panel, label=t("updates.error_title"))
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        body = wx.StaticText(
            self.panel,
            label=t("updates.error_message").format(error=self._error_message),
        )
        try:
            body.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(body, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        details_btn = wx.Button(
            self.panel, label=t("common.show_details"), style=wx.BORDER_NONE | wx.BU_EXACTFIT
        )
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
            details.SetFont(
                wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            )
        except Exception:
            pass
        details.Hide()

        def on_details(e):
            if details.IsShown():
                details.Hide()
                details_btn.SetLabel(t("common.show_details"))
            else:
                details.Show()
                details_btn.SetLabel(t("common.hide_details"))
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
        close = wx.Button(self.panel, label=t("common.close"))
        retry = wx.Button(self.panel, label=t("common.retry"))
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
        title = wx.StaticText(self.panel, label=t("updates.download_cancelled_title"))
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.download_cancelled_message"))
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)
        close = wx.Button(self.panel, label=t("common.close"))
        retry = wx.Button(self.panel, label=t("common.retry"))
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        retry.Bind(wx.EVT_BUTTON, lambda e: self._retry())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(retry, 0)
