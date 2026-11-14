"""Content half of the wx updater dialog: the per-state builders."""

from __future__ import annotations

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.wx_updater_core import (
    STATE_CHECKING as STATE_CHECKING,
    STATE_DOWNLOADING as STATE_DOWNLOADING,
    STATE_DOWNLOAD_CANCELLED as STATE_DOWNLOAD_CANCELLED,
    STATE_FAILED as STATE_FAILED,
    STATE_INSTALLING as STATE_INSTALLING,
    STATE_READY_TO_INSTALL as STATE_READY_TO_INSTALL,
    STATE_UPDATE_AVAILABLE as STATE_UPDATE_AVAILABLE,
    STATE_UP_TO_DATE as STATE_UP_TO_DATE,
    STATE_VERIFYING as STATE_VERIFYING,
    _format_bytes as _format_bytes,
)


class UpdateContentMixin:
    """Per-state content builders of the single update dialog."""

    def _clear_content(self):
        if self._pulse_timer is not None:
            try:
                if self._pulse_timer.IsRunning():
                    self._pulse_timer.Stop()
            except Exception:
                pass
            self._pulse_timer = None
        # Clear content sizer
        self.content_sizer.Clear(delete_windows=True)
        self.footer_sizer.Clear(delete_windows=True)
        self._gauge = None
        self._byte_label = None
        self._percent_label = None
        self._status_label = None
        self._cancel_btn = None

    def _build_for_state(self, state: str):
        self._clear_content()
        self.state = state
        try:
            self.dlg._wx_update_state = state
        except Exception:
            pass
        wx = self.wx
        # Update title per state — mandatory uses Update Required
        if self.mandatory and state == STATE_UPDATE_AVAILABLE:
            titles = {STATE_UPDATE_AVAILABLE: t("updates.required_title")}
        else:
            titles = {
                STATE_UPDATE_AVAILABLE: t("updates.available_title"),
                STATE_DOWNLOADING: t("updates.downloading_title"),
                STATE_VERIFYING: t("updates.verifying_title"),
                STATE_READY_TO_INSTALL: t("updates.ready_title"),
                STATE_INSTALLING: t("updates.installing_title"),
                STATE_FAILED: t("updates.error_title"),
                STATE_UP_TO_DATE: t("updates.title"),
            }
        if state in titles:
            try:
                self.dlg.SetTitle(titles[state])
            except Exception:
                pass

        if state == STATE_UPDATE_AVAILABLE:
            self._build_available()
        elif state == STATE_DOWNLOADING:
            self._build_downloading()
        elif state == STATE_VERIFYING:
            self._build_verifying()
        elif state == STATE_READY_TO_INSTALL:
            self._build_ready()
        elif state == STATE_FAILED:
            self._build_failed()
        elif state == STATE_DOWNLOAD_CANCELLED:
            self._build_cancelled()
        elif state == STATE_UP_TO_DATE:
            self._build_up_to_date()
        elif state == STATE_CHECKING:
            self._build_checking()
        else:
            self._build_available()

        self.panel.Layout()
        self.dlg.Layout()
        try:
            # Spec §2: fixed 520×390, not growing with changelog
            self.dlg.SetSize(wx.Size(520, 390))
        except Exception:
            pass
        # Ensure visible focus
        try:
            self.panel.SetFocusIgnoringChildren()
        except Exception:
            pass

    def _build_available(self):
        wx = self.wx
        rel = self.release
        cur = __version__
        new = getattr(rel, "version", "") if rel else ""
        # Spec §3-4: compact header and version form with fixed label width 115-130
        if self.mandatory:
            hdr_text = t("updates.required_header")
        else:
            hdr_text = t("updates.available_header")
        header = wx.StaticText(self.panel, label=hdr_text)
        try:
            header.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Version grid: Current, New/Required, Download size — label col 120px per spec §4
        grid = wx.FlexGridSizer(3, 2, 6, 12)
        grid.AddGrowableCol(1, 1)
        # Current
        lbl_cur = wx.StaticText(self.panel, label=t("updates.current_version"))
        try:
            lbl_cur.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        val_cur = wx.StaticText(self.panel, label=cur)
        grid.Add(lbl_cur, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_cur, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        # New / Required
        if self.mandatory:
            lbl_new_text = t("updates.required_version")
        else:
            lbl_new_text = t("updates.new_version")
        lbl_new = wx.StaticText(self.panel, label=lbl_new_text)
        try:
            lbl_new.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        val_new = wx.StaticText(self.panel, label=new)
        try:
            fnt2 = val_new.GetFont()
            fnt2.SetWeight(wx.FONTWEIGHT_BOLD)
            val_new.SetFont(fnt2)
        except Exception:
            pass
        grid.Add(lbl_new, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_new, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        # Download size row — always visible per spec §5, real size or Calculating...
        lbl_sz = wx.StaticText(self.panel, label=t("updates.download_size_label"))
        try:
            lbl_sz.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        size = self._total
        if size is not None and size > 0:
            sz_val = _format_bytes(size)
        else:
            # Try to get from release size, else Calculating...
            sz_val = t("updates.calculating")
            # If we truly have no size, keep Calculating... per spec, don't omit
            if size is None and not getattr(rel, "size", None):
                sz_val = t("updates.calculating")
        val_sz = wx.StaticText(self.panel, label=sz_val)
        grid.Add(lbl_sz, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_sz, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.content_sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        if self.mandatory:
            mand_msg = wx.StaticText(self.panel, label=t("updates.mandatory_message"))
            try:
                mand_msg.Wrap(480)
            except Exception:
                pass
            self.content_sizer.Add(mand_msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Separator
        line = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        self.content_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # What's new — fixed-height scrollable TextCtrl per spec §6
        title = wx.StaticText(self.panel, label=t("updates.whats_new"))
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Build changelog text from _whats_new or body
        body = getattr(rel, "body", "") if rel else ""
        if self._whats_new:
            txt_content = "\n".join(f"• {b}" for b in self._whats_new[:5])
        elif body:
            # Use body as plain text, truncated
            txt_content = body.strip()[:2000]
        else:
            txt_content = t("updates.no_changelog")
        # Fixed-height read-only multiline vertically scrollable word-wrapped selectable
        changelog = wx.TextCtrl(self.panel, value=txt_content, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        changelog.SetMinSize(wx.Size(-1, 100))
        changelog.SetMaxSize(wx.Size(-1, 100))
        try:
            changelog.SetBackgroundColour(wx.Colour(248, 249, 250))
        except Exception:
            pass
        # Ensure no horizontal scrollbar for wrapped text
        try:
            changelog.SetWindowStyle(changelog.GetWindowStyle() & ~wx.HSCROLL)
        except Exception:
            pass
        self.content_sizer.Add(changelog, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # Store for tests
        self._changelog_ctrl = changelog

        # View full release notes link directly below changelog
        link = wx.Button(self.panel, label=t("updates.view_release_notes"), style=wx.BORDER_NONE | wx.BU_EXACTFIT)
        try:
            link.SetBackgroundColour(self.panel.GetBackgroundColour())
            fnt = link.GetFont()
            fnt.SetUnderlined(True)
            link.SetFont(fnt)
            link.SetForegroundColour(wx.Colour(37, 99, 235))
        except Exception:
            pass
        link.Bind(wx.EVT_BUTTON, self._on_view_notes)
        self.content_sizer.Add(link, 0, wx.LEFT | wx.TOP, 8)

        # Footer buttons per §8 and §30 — Later and Download same size
        btn_size = wx.Size(135, 32)
        if self.mandatory:
            exit_btn = wx.Button(self.panel, label=t("common.exit"))
            dl_btn = wx.Button(self.panel, label=t("updates.download_update"))
            try:
                exit_btn.SetMinSize(btn_size)
                dl_btn.SetMinSize(btn_size)
                fnt = dl_btn.GetFont()
                fnt.SetWeight(wx.FONTWEIGHT_BOLD)
                dl_btn.SetFont(fnt)
                dl_btn.SetDefault()
            except Exception:
                pass
            exit_btn.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
            dl_btn.Bind(wx.EVT_BUTTON, lambda e: self._start_download())
            self.footer_sizer.AddStretchSpacer(1)
            self.footer_sizer.Add(exit_btn, 0, wx.RIGHT, 8)
            self.footer_sizer.Add(dl_btn, 0)
        else:
            later = wx.Button(self.panel, label=t("common.later"))
            dl_btn = wx.Button(self.panel, label=t("updates.download_update"))
            try:
                later.SetMinSize(btn_size)
                dl_btn.SetMinSize(btn_size)
                fnt = dl_btn.GetFont()
                fnt.SetWeight(wx.FONTWEIGHT_BOLD)
                dl_btn.SetFont(fnt)
                dl_btn.SetDefault()
            except Exception:
                pass
            later.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
            dl_btn.Bind(wx.EVT_BUTTON, lambda e: self._start_download())
            self.footer_sizer.AddStretchSpacer(1)
            self.footer_sizer.Add(later, 0, wx.RIGHT, 8)
            self.footer_sizer.Add(dl_btn, 0)

    def _build_downloading(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        title = wx.StaticText(self.panel, label=f"{t('app.title')} {ver}" if ver else t("app.title"))
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
            byte_txt = t("updates.downloaded_bytes").format(bytes=_format_bytes(self._downloaded)) if self._downloaded else t("updates.calculating")
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
        title = wx.StaticText(self.panel, label=f"{t('app.title')} {ver}" if ver else t("app.title"))
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
        # No cancel unless explicitly supported — per spec, normally no action

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
