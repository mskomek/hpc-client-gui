"""wx updater dialogs per spec 1-41 — single-dialog state machine, real progress, i18n."""

from __future__ import annotations

import threading

from hpc_gui.core.i18n import t
from hpc_gui.wx_updater_actions import UpdateActionsMixin as UpdateActionsMixin
from hpc_gui.wx_updater_content import UpdateContentMixin as UpdateContentMixin
from hpc_gui.wx_updater_core import (
    STATE_CHECKING as STATE_CHECKING,
    STATE_DOWNLOADING as STATE_DOWNLOADING,
    STATE_DOWNLOAD_CANCELLED as STATE_DOWNLOAD_CANCELLED,
    STATE_FAILED as STATE_FAILED,
    STATE_IDLE as STATE_IDLE,
    STATE_INSTALLING as STATE_INSTALLING,
    STATE_READY_TO_INSTALL as STATE_READY_TO_INSTALL,
    STATE_RESTART_REQUIRED as STATE_RESTART_REQUIRED,
    STATE_UP_TO_DATE as STATE_UP_TO_DATE,
    STATE_UPDATE_AVAILABLE as STATE_UPDATE_AVAILABLE,
    STATE_VERIFYING as STATE_VERIFYING,
    _UpdateViewState as _UpdateViewState,
    _format_bytes as _format_bytes,
    _parse_whats_new as _parse_whats_new,
)
from hpc_gui.wx_updater_dialogs import (
    show_download_progress as show_download_progress,
    show_installing_splash as show_installing_splash,
    show_update_available as show_update_available,
    show_update_checking as show_update_checking,
    show_update_dialog as show_update_dialog,
    show_update_error as show_update_error,
    show_update_ready as show_update_ready,
    show_up_to_date as show_up_to_date,
    show_verifying as show_verifying,
)
from hpc_gui.wx_updater_stateful import UpdateStateContentMixin as UpdateStateContentMixin

# Re-export for tests
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
    "WxUpdateDialog",
    "show_update_dialog",
]



class WxUpdateDialog(UpdateContentMixin, UpdateStateContentMixin, UpdateActionsMixin):
    """Single dialog that transitions through update states per spec 1-41."""

    def __init__(self, parent, release, *, mandatory: bool = False):
        try:
            import wx
        except ImportError as exc:
            raise RuntimeError("wxPython is not installed") from exc
        self.wx = wx
        self.parent = parent
        self.release = release
        self.mandatory = bool(mandatory)
        self.state = STATE_UPDATE_AVAILABLE if release else STATE_IDLE
        self._cancelled = False
        self._closed = False
        self._worker: threading.Thread | None = None
        self._downloaded = 0
        self._total: int | None = getattr(release, "size", None) if release else None
        self._pulse_timer = None
        self._zip_path = None
        self._artifact_verified = False
        if self._total == 0:
            self._total = None

        # Use release body for What's new
        body = getattr(release, "body", "") if release else ""
        self._whats_new = _parse_whats_new(body)
        if not self._whats_new:
            # fallback generic but spec says don't generate generic if none available — keep empty and hide section
            self._whats_new = []

        # Spec §2: 520×390 fixed, compact, not vertically resizable
        self.dlg = wx.Dialog(parent, title=t("updates.available_title"), style=wx.DEFAULT_DIALOG_STYLE)
        self.dlg.SetMinSize(wx.Size(520, 390))
        self.dlg.SetSize(wx.Size(520, 390))
        self.dlg.SetMaxSize(wx.Size(520, 390))
        self.dlg.CentreOnParent()

        self.panel = wx.Panel(self.dlg)
        self.root = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.root)

        # Content sizer — fixed height, will be cleared per state
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.root.Add(self.content_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Footer sizer (buttons) — fixed at bottom
        self.footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.root.Add(self.footer_sizer, 0, wx.EXPAND | wx.ALL, 12)

        # Progress state
        self._gauge: wx.Gauge | None = None
        self._byte_label: wx.StaticText | None = None
        self._percent_label: wx.StaticText | None = None
        self._status_label: wx.StaticText | None = None
        self._cancel_btn: wx.Button | None = None

        self._build_for_state(self.state)

        # Handle close
        self.dlg.Bind(wx.EVT_CLOSE, self._on_close)

        # Expose for tests
        self.dlg._wx_update_dialog = self
        self.dlg._wx_update_state = self.state



    def _on_close(self, evt):
        wx = self.wx
        # Spec §26, §27: During download, confirm cancel
        if self.state == STATE_DOWNLOADING and not self._cancelled:
            res = wx.MessageBox(t("updates.cancel_confirm_message"), t("updates.cancel_confirm_title"), wx.YES_NO | wx.ICON_WARNING, self.dlg)
            if res != wx.YES:
                try:
                    evt.Veto()
                except Exception:
                    pass
                return
            self._cancel_download()
            try:
                evt.Veto()
            except Exception:
                pass
            return
        # For mandatory update, don't allow bypass
        if self.mandatory and self.state in (STATE_UPDATE_AVAILABLE, STATE_FAILED):
            try:
                evt.Skip()
            except Exception:
                pass
            self._closed = True
            try:
                if hasattr(self, "_pulse_timer"):
                    self._pulse_timer.Stop()
            except Exception:
                pass
            try:
                if self.dlg.IsModal():
                    self.dlg.EndModal(wx.ID_CANCEL)
                else:
                    self.dlg.Hide()
            except Exception:
                pass
            return
        self._closed = True
        try:
            if hasattr(self, "_pulse_timer"):
                self._pulse_timer.Stop()
        except Exception:
            pass
        try:
            evt.Skip()
        except Exception:
            pass
        try:
            if self.dlg.IsModal():
                self.dlg.EndModal(wx.ID_CANCEL)
            else:
                self.dlg.Hide()
        except Exception:
            pass

    def ShowModal(self):
        return self.dlg.ShowModal()

    def Destroy(self):
        self._closed = True
        try:
            if hasattr(self, "_pulse_timer"):
                self._pulse_timer.Stop()
        except Exception:
            pass
        try:
            self.dlg.Destroy()
        except Exception:
            pass
