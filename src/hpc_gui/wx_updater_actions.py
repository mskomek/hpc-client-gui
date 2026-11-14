"""Action half of the wx updater dialog: download, cancel and install transitions."""

from __future__ import annotations

import threading

from hpc_gui.core.i18n import t
from hpc_gui.wx_updater_core import (
    STATE_DOWNLOAD_CANCELLED as STATE_DOWNLOAD_CANCELLED,
    STATE_DOWNLOADING as STATE_DOWNLOADING,
    STATE_FAILED as STATE_FAILED,
    STATE_READY_TO_INSTALL as STATE_READY_TO_INSTALL,
    STATE_UPDATE_AVAILABLE as STATE_UPDATE_AVAILABLE,
    STATE_VERIFYING as STATE_VERIFYING,
    _format_bytes as _format_bytes,
)


def _view():
    """Resolve the view module at call time so its show_* seams stay patchable."""
    from hpc_gui import wx_updater_view

    return wx_updater_view


class UpdateActionsMixin:
    """Download, cancel and install transitions of the single update dialog."""

    def _start_download(self):
        # Transition to downloading and start worker with real progress
        self._zip_path = None
        self._artifact_verified = False
        self._build_for_state(STATE_DOWNLOADING)
        self._downloaded = 0
        self._cancelled = False
        rel = self.release
        wx = self.wx

        def download_worker():
            try:
                from hpc_gui.services.app_updater import download_and_verify_release

                def prog(value, status, downloaded, total):
                    def upd():
                        if self._closed or self._cancelled:
                            return
                        self._downloaded = downloaded
                        if total:
                            self._total = total
                        try:
                            if self._byte_label:
                                if total:
                                    self._byte_label.SetLabel(f"{_format_bytes(downloaded)} / {_format_bytes(total)}")
                                    pct = int(downloaded * 100 / total) if total else 0
                                    if self._gauge:
                                        self._gauge.SetValue(pct)
                                    if self._percent_label:
                                        self._percent_label.SetLabel(f"{pct}%")
                                else:
                                    self._byte_label.SetLabel(t("updates.downloaded_bytes").format(bytes=_format_bytes(downloaded)))
                                if self._status_label:
                                    mapping = {
                                        "downloading": t("updates.downloading_package"),
                                        "verifying": t("updates.verifying"),
                                        "preparing": t("updates.preparing"),
                                    }
                                    self._status_label.SetLabel(mapping.get(status, status))
                                self.panel.Layout()
                        except Exception:
                            pass
                    try:
                        wx.CallAfter(upd)
                    except Exception:
                        pass

                def cancelled():
                    return self._cancelled or self._closed

                zip_path = download_and_verify_release(rel, progress_cb=prog, cancelled=cancelled)
                if self._cancelled or self._closed:
                    return
                self._artifact_verified = True

                def on_ok():
                    if self._closed or self._cancelled:
                        return
                    try:
                        if hasattr(self, "_pulse_timer"):
                            self._pulse_timer.Stop()
                    except Exception:
                        pass
                    self._build_for_state(STATE_VERIFYING)

                    def to_ready():
                        if self._closed or self._cancelled:
                            return
                        try:
                            if hasattr(self, "_pulse_timer"):
                                self._pulse_timer.Stop()
                        except Exception:
                            pass
                        self._build_for_state(STATE_READY_TO_INSTALL)
                        self._zip_path = zip_path

                    wx.CallAfter(to_ready)

                wx.CallAfter(on_ok)
            except Exception as e:
                if self._cancelled:
                    wx.CallAfter(lambda: self._build_for_state(STATE_DOWNLOAD_CANCELLED) if not self._closed else None)
                    return
                msg = str(e)
                det = f"{type(e).__name__}: {e}"

                def on_err():
                    if not self._closed:
                        self._error_message = msg
                        self._error_details = det
                        self._build_for_state(STATE_FAILED)

                wx.CallAfter(on_err)

        self._worker = threading.Thread(target=download_worker, daemon=True)
        self._worker.start()

    def _cancel_download(self):
        self._cancelled = True
        # Real cancellation reaches downloader via cancelled callback
        # Show cancelled state after brief delay to let worker notice
        def do_cancelled():
            if not self._closed:
                try:
                    if hasattr(self, "_pulse_timer"):
                        self._pulse_timer.Stop()
                except Exception:
                    pass
                self._build_for_state(STATE_DOWNLOAD_CANCELLED)
        self.wx.CallAfter(do_cancelled)

    # W43 (HPC-W09-UPD-039..043): restart-safety hooks. Tests may set
    # ``unsaved_probe`` (()-> int) and ``confirm_fn`` ((count)-> bool) to
    # drive the defer path without a live editor. Production editors may
    # alternatively register providers via update_restart_policy.
    unsaved_probe = None
    confirm_fn = None

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
            splash = _view().show_installing_splash(self.parent, ver)
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
                        _view().show_update_error(self.parent, error_message)
                    wx_local.CallAfter(on_fail)
            threading.Thread(target=install_worker, daemon=True).start()
        except Exception as e:
            _view().show_update_error(self.parent, str(e))

    def _retry(self):
        # Retry from failed -> go back to available
        self._cancelled = False
        self._closed = False
        self._build_for_state(STATE_UPDATE_AVAILABLE)
