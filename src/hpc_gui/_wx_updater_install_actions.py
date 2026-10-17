from __future__ import annotations

import threading
from hpc_gui.core.i18n import t
from hpc_gui._wx_updater_state import (
    STATE_DOWNLOADING, STATE_FAILED,
    STATE_READY_TO_INSTALL, STATE_UPDATE_AVAILABLE,
)

class _UpdateDialogInstallActions:
    def _unsaved_count(self) -> int:
        probe = getattr(self, "unsaved_probe", None)
        if callable(probe):
            try:
                return max(0, int(probe() or 0))
            except Exception:
                return 0
        try:
            from hpc_gui.services.update_restart_policy import get_unsaved_count
            return max(0, int(get_unsaved_count() or 0))
        except Exception:
            return 0


    def _confirm_unsaved_install(self, count: int) -> bool:
        confirm = getattr(self, "confirm_fn", None)
        if callable(confirm):
            try:
                return bool(confirm(int(count)))
            except Exception:
                return False
        try:
            from hpc_gui.services.update_restart_policy import deferral_message
            res = self.wx.MessageBox(
                deferral_message(count),
                "Unsaved changes",
                self.wx.YES_NO | self.wx.ICON_WARNING,
                self.dlg,
            )
            return res == self.wx.YES
        except Exception:
            return False


    def _start_install(self):
        # Close this dialog and open installation splash per §19
        rel = self.release
        zip_path = getattr(self, "_zip_path", None)
        ver = getattr(rel, "version", "") if rel else ""
        wx = self.wx
        if not zip_path or not self._artifact_verified:
            self._error_message = "Verified update artifact is unavailable."
            self._error_details = self._error_message
            self._build_for_state(STATE_FAILED)
            return
        # W43: never install silently with unsaved editor state. Defer
        # (stay in READY) unless the user explicitly confirms.
        try:
            unsaved = self._unsaved_count()
        except Exception:
            unsaved = 0
        self._install_deferred_due_to_unsaved = False
        if unsaved > 0:
            try:
                confirmed = self._confirm_unsaved_install(unsaved)
            except Exception:
                confirmed = False
            if not confirmed:
                self._install_deferred_due_to_unsaved = True
                self._build_for_state(STATE_READY_TO_INSTALL)
                self._zip_path = zip_path
                return
            self._install_confirmed_with_unsaved = int(unsaved)
        # Close update dialog
        try:
            self._closed = True
            try:
                if hasattr(self, "_pulse_timer"):
                    self._pulse_timer.Stop()
            except Exception:
                pass
            self.dlg.EndModal(wx.ID_OK)
        except Exception:
            pass
        # Open installation splash 620x360
        try:
            splash = self._show_installing_splash(self.parent, ver)
            splash.Show()
            wx_local = self.wx
            def install_worker():
                try:
                    from hpc_gui.services.app_updater import launch_update_installer
                    if not rel:
                        raise RuntimeError("Update release metadata is unavailable.")
                    launch_update_installer(zip_path, ver, rel.install_strategy)
                    def do_quit():
                        try:
                            splash.Destroy()
                        except Exception:
                            pass
                        try:
                            wx_local.GetApp().ExitMainLoop()
                        except Exception:
                            pass
                    wx_local.CallAfter(do_quit)
                except Exception as exc:
                    error_message = str(exc)
                    def on_fail():
                        try:
                            splash.Destroy()
                        except Exception:
                            pass
                        self._show_update_error(self.parent, error_message)
                    wx_local.CallAfter(on_fail)
            threading.Thread(target=install_worker, daemon=True).start()
        except Exception as e:
            self._show_update_error(self.parent, str(e))


    def _retry(self):
        # Retry from failed -> go back to available
        self._cancelled = False
        self._closed = False
        self._build_for_state(STATE_UPDATE_AVAILABLE)


    def _on_close(self, evt):
        wx = self.wx
        # Spec §26, §27: During download, confirm cancel
        if self.state == STATE_DOWNLOADING and not self._cancelled:
            res = wx.MessageBox(t("updates.cancel_confirm_message") if t("updates.cancel_confirm_message") != "[updates.cancel_confirm_message]" else "Cancel update download?\n\nThe update is still being downloaded.", t("updates.cancel_confirm_title") if t("updates.cancel_confirm_title") != "[updates.cancel_confirm_title]" else "Cancel update download?", wx.YES_NO | wx.ICON_WARNING, self.dlg)
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

