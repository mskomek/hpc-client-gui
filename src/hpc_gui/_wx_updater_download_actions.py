from __future__ import annotations

import threading
from hpc_gui.core.i18n import t
from hpc_gui._wx_updater_state import (
    STATE_DOWNLOAD_CANCELLED, STATE_DOWNLOADING, STATE_FAILED,
    STATE_READY_TO_INSTALL, STATE_VERIFYING, _format_bytes,
)

class _UpdateDialogDownloadActions:
    def _on_view_notes(self, evt):
        wx = self.wx
        rel = self.release
        body = getattr(rel, "body", "") if rel else ""
        ver = getattr(rel, "version", "") if rel else ""
        dlg2 = wx.Dialog(self.dlg, title=f"Release Notes — HPC Client {ver}" if ver else "Release Notes", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg2.SetMinSize(wx.Size(700, 600))
        dlg2.SetSize(wx.Size(700, 600))
        dlg2.CentreOnParent()
        panel = wx.Panel(dlg2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        txt.SetValue(body or "No release notes available.")
        try:
            txt.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        except Exception:
            pass
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 12)
        close = wx.Button(panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        close.Bind(wx.EVT_BUTTON, lambda e: dlg2.EndModal(wx.ID_OK))
        sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        panel.SetSizer(sizer)
        dlg2.ShowModal()
        dlg2.Destroy()


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
                                    self._byte_label.SetLabel(f"{_format_bytes(downloaded)} downloaded")
                                if self._status_label:
                                    mapping = {
                                        "downloading": t("updates.downloading_package") if t("updates.downloading_package") != "[updates.downloading_package]" else "Downloading package...",
                                        "verifying": t("updates.verifying") if t("updates.verifying") != "[updates.verifying]" else "Verifying downloaded update...",
                                        "preparing": t("updates.preparing") if t("updates.preparing") != "[updates.preparing]" else "Preparing download...",
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

