"""WebView event bridge and readiness recovery for the wx terminal panel."""

import json

from hpc_gui.core.i18n import t
from hpc_gui.wx_terminal_webview_support import _is_local_file_url


class TerminalBridgeMixin:
    def _on_navigating(self, event):
        try:
            url = event.GetURL() or ""
            if not _is_local_file_url(url):
                # Block external navigation / popup
                event.Veto()
                return
        except Exception:
            try:
                event.Veto()
                return
            except Exception:
                pass
        try:
            event.Skip()
        except Exception:
            pass

    def _on_new_window(self, event):
        try:
            event.Veto()
        except Exception:
            pass

    def _on_loaded(self, event):
        # Page loaded — xterm will post {type:"ready"} when bridge is ready
        self._page_loaded = True
        self._webview_failure_stage = "page-loaded"
        try:
            event.Skip()
        except Exception:
            pass

    def _on_error(self, event):
        # Page load failed
        try:
            detail = event.GetString() if hasattr(event, "GetString") else ""
            self._webview_failure_stage = "navigation-error"
            self._webview_failure_detail = detail
            self._diagnostic_text = self._build_diagnostic_text(f"WebView load error: {detail}")
        except Exception:
            pass
        # Show diagnostic in dimensions label?
        try:
            self._status_label.SetLabel(t("login.terminal_page_failed"))
        except Exception:
            pass
        try:
            event.Skip()
        except Exception:
            pass

    def _on_script_message(self, event):
        if self._closed:
            return
        try:
            raw = ""
            # wx API varies: GetString / GetMessage / GetValue
            if hasattr(event, "GetString"):
                raw = event.GetString()
            elif hasattr(event, "GetMessage"):
                raw = event.GetMessage()
            else:
                raw = str(event)
            # Some backends wrap JSON in extra quoting; handle both
            msg = None
            try:
                msg = json.loads(raw)
                # If the payload was double-encoded (string containing JSON), decode again
                if isinstance(msg, str):
                    try:
                        msg = json.loads(msg)
                    except Exception:
                        pass
            except Exception:
                # Try to extract JSON substring
                try:
                    # Find first { and last }
                    s = raw.strip()
                    if s.startswith('"') and s.endswith('"'):
                        s = json.loads(s)
                    msg = json.loads(s)
                except Exception:
                    return
            if not isinstance(msg, dict):
                return
            mtype = msg.get("type")
            if mtype == "bridge-ack":
                self._fragment_acknowledged(msg.get("seq"))
                return
            if mtype == "bridge-response":
                current = self._gtk_queue.inflight
                if (current is not None and current.method == "hpcGetScreenState"
                        and msg.get("seq") == current.seq):
                    value = msg.get("value")
                    self._gtk_screen_snapshot = value if isinstance(value, dict) else None
                    self._gtk_query_pending = False
                return
            if mtype == "ready":
                self._on_bridge_ready()
            elif mtype == "input":
                data = msg.get("data") or ""
                # Single bridge must not log terminal input — do not log data
                self._handle_input(data)
            elif mtype == "resize":
                cols = int(msg.get("cols") or 0)
                rows = int(msg.get("rows") or 0)
                pw = int(msg.get("pixelWidth") or 0)
                ph = int(msg.get("pixelHeight") or 0)
                self._handle_resize(cols, rows, pw, ph)
        except Exception:
            pass

    def _on_bridge_ready(self):
        if self._closed or self._ready:
            return
        self._webview_failure_stage = "ready"
        self._ready = True
        # A replacement made it: retired controllers have been silent since
        # their own readiness timeout, so they are quiescent and safe to
        # destroy now (never destroy a possibly in-flight controller).
        retired, self._retired_webviews = self._retired_webviews, []
        for dead in retired:
            try:
                dead.Destroy()
            except Exception:
                pass
        try:
            if self._readiness_timer and self._readiness_timer.IsRunning():
                self._readiness_timer.Stop()
        except Exception:
            pass
        self._flush_pending()
        self._flush_pending_paste()
        # Initial fit after ready
        self._schedule_fit()

    def _on_readiness_timeout(self, _evt=None):
        if self._closed or self._ready:
            return
        self._webview_failure_stage = "bridge-timeout"
        # Readiness timeout — show diagnostic but remain functional if ready arrives later
        try:
            self._status_label.SetLabel(t("login.terminal_readiness_timeout") if t("login.terminal_readiness_timeout") != "[login.terminal_readiness_timeout]" else "Terminal did not become ready in time.")
        except Exception:
            pass
        # REL-046: a native controller that aborted silently (e.g. WebView2
        # E_ABORT 0x80004004 on cold start) never fires loaded/ready/error, so
        # polling alone cannot recover it. Bounded recreate while attempts
        # remain; the last attempt keeps the diagnostic state above.
        # Do not clear pending — if ready arrives late, flush then
        try:
            being_deleted = False
            is_being_deleted = getattr(self, "IsBeingDeleted", None)
            if callable(is_being_deleted):
                being_deleted = bool(is_being_deleted())
        except Exception:
            being_deleted = False
        if (not being_deleted and self._webview is not None
                and self._webview_create_attempts < self._webview_max_attempts):
            self._retry_webview_creation()

    def _retry_webview_creation(self) -> None:
        """Detach a never-ready native controller and mount a fresh one.

        Bounded by _webview_max_attempts, never runs after close(), never
        touches a panel under destruction, never duplicates the mount (the
        old controller is detached from the sizer first). The old controller
        is NOT destroyed here: destroying a controller whose async native
        creation may still be in flight caused a native fastfail (0xC0000409).
        It is retired and destroyed only after the replacement reaches
        bridge-ready (see _on_bridge_ready); if no replacement ever readies,
        panel teardown destroys it natively. Stale callbacks are impossible:
        the old control leaves the layout before the new one exists and the
        generation is bumped.
        """
        try:
            if self._closed or self._ready:
                return
            is_being_deleted = getattr(self, "IsBeingDeleted", None)
            if callable(is_being_deleted) and bool(is_being_deleted()):
                return
            # Invalidate anything in flight from the aborted controller.
            self._generation += 1
            self._page_loaded = False
            old = self._webview
            self._webview = None
            for timer_attr in ("_readiness_timer", "_resize_timer"):
                try:
                    timer = getattr(self, timer_attr, None)
                    if timer is not None:
                        try:
                            if timer.IsRunning():
                                timer.Stop()
                        except Exception:
                            pass
                        try:
                            timer.Destroy()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    setattr(self, timer_attr, None)
                except Exception:
                    pass
            sizer = None
            try:
                sizer = self.GetSizer()
            except Exception:
                sizer = None
            if old is not None:
                try:
                    if sizer is not None:
                        sizer.Detach(old)
                except Exception:
                    pass
                # Retire without destroying: the native creation may still be
                # in flight; Destroy happens in _on_bridge_ready or natively
                # at panel teardown.
                try:
                    self._retired_webviews.append(old)
                except Exception:
                    pass
            self._webview_failure_detail = (
                f"recreate attempt {self._webview_create_attempts + 1}"
                f"/{self._webview_max_attempts} after stage={self._webview_failure_stage}"
            )
            if sizer is None:
                return
            self._mount_webview(sizer)
            try:
                self.Layout()
            except Exception:
                pass
        except Exception:
            pass

    # ---------- Input / Resize ----------

