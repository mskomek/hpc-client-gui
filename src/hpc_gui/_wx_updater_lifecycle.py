"""Close and modal lifecycle for the wx updater dialog."""

from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui._wx_updater_state import (
    STATE_DOWNLOADING,
    STATE_FAILED,
    STATE_UPDATE_AVAILABLE,
)


class _UpdateDialogLifecycleMixin:
    """Handle close confirmation and dialog teardown."""

    def _on_close(self, evt):
        wx = self.wx
        # Spec §26, §27: During download, confirm cancel
        if self.state == STATE_DOWNLOADING and not self._cancelled:
            res = wx.MessageBox(
                t("updates.cancel_confirm_message"),
                t("updates.cancel_confirm_title"),
                wx.YES_NO | wx.ICON_WARNING,
                self.dlg,
            )
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
