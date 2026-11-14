"""State-specific content builders of the wx updater dialog (failed, cancelled, up-to-date, checking)."""

from __future__ import annotations

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.wx_updater_core import (
    STATE_CHECKING as STATE_CHECKING,
    STATE_DOWNLOAD_CANCELLED as STATE_DOWNLOAD_CANCELLED,
    STATE_FAILED as STATE_FAILED,
    STATE_UP_TO_DATE as STATE_UP_TO_DATE,
)


class UpdateStateContentMixin:
    """Failed, cancelled, up-to-date and checking layouts of the single update dialog."""

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
        details_btn = wx.Button(self.panel, label=t("common.show_details"), style=wx.BORDER_NONE | wx.BU_EXACTFIT)
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

    def _build_up_to_date(self):
        wx = self.wx
        msg = wx.StaticText(
            self.panel,
            label=t("updates.up_to_date").format(version=__version__),
        )
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 1, wx.EXPAND | wx.ALL, 16)
        close = wx.Button(self.panel, label=t("common.close"))
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_OK))
        try:
            close.SetDefault()
        except Exception:
            pass
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0)

    def _build_checking(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.checking_title"))
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.checking_message"))
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

    def _on_view_notes(self, evt):
        wx = self.wx
        rel = self.release
        body = getattr(rel, "body", "") if rel else ""
        ver = getattr(rel, "version", "") if rel else ""
        dlg2 = wx.Dialog(self.dlg, title=t("updates.release_notes_title").format(version=ver) if ver else t("updates.release_notes"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg2.SetMinSize(wx.Size(700, 600))
        dlg2.SetSize(wx.Size(700, 600))
        dlg2.CentreOnParent()
        panel = wx.Panel(dlg2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        txt.SetValue(body or t("updates.no_release_notes"))
        try:
            txt.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        except Exception:
            pass
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 12)
        close = wx.Button(panel, label=t("common.close"))
        close.Bind(wx.EVT_BUTTON, lambda e: dlg2.EndModal(wx.ID_OK))
        sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        panel.SetSizer(sizer)
        dlg2.ShowModal()
        dlg2.Destroy()
