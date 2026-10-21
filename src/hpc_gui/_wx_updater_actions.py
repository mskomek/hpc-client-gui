"""Download, cancellation, and retry actions for the wx updater."""

from __future__ import annotations

import threading

from hpc_gui.core.i18n import t
from hpc_gui._wx_updater_text import _format_bytes
from hpc_gui._wx_updater_state import (
    STATE_DOWNLOAD_CANCELLED,
    STATE_DOWNLOADING,
    STATE_FAILED,
    STATE_READY_TO_INSTALL,
    STATE_UPDATE_AVAILABLE,
    STATE_VERIFYING,
)


class _UpdateDownloadActionsMixin:
    """Coordinate download work and state transitions."""

    unsaved_probe = None
    confirm_fn = None

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
                                    self._byte_label.SetLabel(
                                        f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
                                    )
                                    pct = int(downloaded * 100 / total) if total else 0
                                    if self._gauge:
                                        self._gauge.SetValue(pct)
                                    if self._percent_label:
                                        self._percent_label.SetLabel(f"{pct}%")
                                else:
                                    self._byte_label.SetLabel(
                                        t("updates.downloaded_bytes").format(
                                            bytes=_format_bytes(downloaded)
                                        )
                                    )
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
                    wx.CallAfter(
                        lambda: (
                            self._build_for_state(STATE_DOWNLOAD_CANCELLED)
                            if not self._closed
                            else None
                        )
                    )
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

    def _retry(self):
        # Retry from failed -> go back to available
        self._cancelled = False
        self._closed = False
        self._build_for_state(STATE_UPDATE_AVAILABLE)
