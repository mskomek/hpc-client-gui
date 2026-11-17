"""WebView event bridge and readiness recovery for the wx terminal panel."""

import json

from hpc_gui.core.i18n import t
from hpc_gui.wx_terminal_webview_support import _is_local_file_url
from hpc_gui.wx_terminal_diagnostics import record_terminal_event


class TerminalBridgeMixin:
    def _on_native_created(self, event):
        """Defer loading until WebView2 has completed native initialization.

        A stale CREATED event from a retired controller must never navigate
        the replacement. CallAfter also protects synchronous creation paths.
        """
        try:
            controller = event.GetEventObject()
        except Exception:
            controller = None
        record_terminal_event(
            "webview-native-created",
            created=controller is getattr(self, "_webview", None),
        )
        try:
            if not self._closed:
                import wx
                wx.CallAfter(self._navigate_after_creation, controller)
        finally:
            try:
                event.Skip()
            except Exception:
                pass

    def _navigate_after_creation(self, controller):
        if (self._closed or self._webview is None
                or (controller is not None and controller != self._webview)):
            return
        self._native_created = True
        self._load_terminal_page()

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
        # The legacy wxPython Edge binding has no CREATED event: page-loaded
        # is the first proof that its native controller completed creation.
        self._native_created = True
        self._page_loaded = True
        self._webview_failure_stage = "page-loaded"
        try:
            rect = self._webview.GetClientSize()
            width, height = int(rect.width), int(rect.height)
        except Exception:
            width = height = 0
        try:
            shown = bool(self._webview and self._webview.IsShownOnScreen())
        except Exception:
            shown = False
        record_terminal_event(
            "terminal-page-loaded",
            page_loaded=True,
            ready=self._ready,
            width=width,
            height=height,
            shown=shown,
        )
        self._update_accessibility_label(defer_sync=True)
        try:
            event.Skip()
        except Exception:
            pass

    def _update_accessibility_label(self, *, defer_sync: bool = False) -> None:
        webview = getattr(self, "_webview", None)
        if webview is None:
            return
        label = t("login.terminal_accessible_name")
        try:
            webview.SetName(label)
            webview.SetAccessibleName(label)
        except Exception:
            pass
        if not getattr(self, "_page_loaded", True):
            return
        run_script_async = getattr(webview, "RunScriptAsync", None)
        script = (
            "const terminal = document.getElementById('terminal');"
            f"if (terminal) terminal.setAttribute('aria-label', {json.dumps(label, ensure_ascii=False)});"
        )

        def run_sync() -> None:
            if getattr(self, "_closed", False) or getattr(self, "_webview", webview) is not webview:
                return
            try:
                if webview.IsBeingDeleted():
                    return
            except (AttributeError, RuntimeError):
                pass
            run_script = getattr(webview, "RunScript", None)
            if callable(run_script):
                try:
                    run_script(script)
                except Exception:
                    pass

        if not callable(run_script_async):
            # Some wx backends expose only synchronous RunScript. It is safe
            # for later language changes, but must leave EVT_WEBVIEW_LOADED
            # before entering the native renderer event pump.
            if defer_sync:
                try:
                    import wx

                    wx.CallAfter(run_sync)
                except Exception:
                    pass
                return
            run_sync()
            return

        def update_dom_label() -> None:
            if getattr(self, "_closed", False) or getattr(self, "_webview", webview) is not webview:
                return
            try:
                if webview.IsBeingDeleted():
                    return
            except (AttributeError, RuntimeError):
                pass
            try:
                # The async API queues work without re-entering the native
                # renderer event pump used by EVT_WEBVIEW_LOADED.
                run_script_async(script)
            except Exception:
                # If an async method exists but is unavailable at runtime,
                # use the synchronous API only after the loaded event ends.
                try:
                    import wx

                    wx.CallAfter(run_sync)
                except Exception:
                    pass

        try:
            import wx

            if wx.GetApp() is not None and isinstance(webview, wx.Window):
                # Loaded/language events normally arrive on wx's UI thread.
                # Calling CallAfter here creates a stale native callback if a
                # parent is destroyed before the queued script runs.
                is_main_thread = getattr(wx, "IsMainThread", None)
                if callable(is_main_thread) and is_main_thread():
                    update_dom_label()
                    return
                wx.CallAfter(update_dom_label)
                return
        except Exception:
            pass
        update_dom_label()

    def _on_error(self, event):
        # wxWidgets emits ERROR after its native WebView2 create callback
        # completes with E_ABORT. Do not mistake it for a page load failure:
        # only now is the failed controller safe to retire before retrying.
        try:
            controller = event.GetEventObject()
        except Exception:
            controller = None
        if controller is not None and controller is not self._webview:
            try:
                event.Skip()
            except Exception:
                pass
            return
        try:
            detail = event.GetString() if hasattr(event, "GetString") else ""
        except Exception:
            detail = ""
        import re
        code = re.search(r"0x[0-9a-fA-F]{8}", detail)
        record_terminal_event(
            "webview-error",
            stage=getattr(self, "_webview_failure_stage", "unknown"),
            native_code=code.group(0) if code else None,
            exception_type="native-event",
        )
        if self._is_ready_fragment_navigation_interrupt(event, detail):
            try:
                event.Skip()
            except Exception:
                pass
            return
        aborted = "operation aborted" in detail.casefold() or "0x80004004" in detail.lower()
        native_failed = (
            not getattr(self, "_native_created", False)
            and (
                getattr(self, "_webview_pending_native", False)
                or (getattr(self, "_webview_legacy_edge", False) and aborted)
            )
        )
        try:
            self._webview_failure_stage = (
                "native-create-error" if native_failed else "navigation-error"
            )
            self._webview_failure_detail = detail
            self._diagnostic_text = self._build_diagnostic_text(f"WebView error: {detail}")
        except Exception:
            pass
        try:
            self._status_label.SetLabel(t("login.terminal_page_failed"))
        except Exception:
            pass
        if (native_failed and not self._closed and not self._ready
                and not getattr(self, "_native_retry_scheduled", False)
                and self._webview_create_attempts < self._webview_max_attempts):
            self._native_retry_scheduled = True
            self._native_create_errors = getattr(self, "_native_create_errors", 0) + 1
            try:
                if self._readiness_timer and self._readiness_timer.IsRunning():
                    self._readiness_timer.Stop()
            except Exception:
                pass
            import wx
            wx.CallLater(300, self._retry_webview_creation, True)
        try:
            event.Skip()
        except Exception:
            pass

    def _is_ready_fragment_navigation_interrupt(self, event, detail: str) -> bool:
        """Ignore WebKit's benign interruption while loading an IPC fragment.

        WebKitGTK can emit ERROR(code 7, "Frame load interrupted") while a
        same-document file URL fragment is being delivered. Once the bridge is
        ready, that event does not mean the terminal page or controller failed.
        """
        if (
            not getattr(self, "_gtk_fragment_transport", False)
            or not getattr(self, "_ready", False)
            or detail.strip().casefold() != "frame load interrupted"
        ):
            return False
        try:
            url = event.GetURL() or ""
        except Exception:
            return False
        return "#" in url and _is_local_file_url(url)

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
            record_terminal_event("terminal-bridge-message", message_type=mtype)
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
        record_terminal_event("terminal-bridge-ready", ready=True, page_loaded=self._page_loaded)
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
            self._status_label.SetLabel(t("login.terminal_readiness_timeout"))
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
        if (((getattr(self, "_webview_pending_native", False)
                 or getattr(self, "_webview_legacy_edge", False))
                and not getattr(self, "_native_created", False))
                or getattr(self, "_native_retry_scheduled", False)):
            # Unknown completion state: never start overlapping WebView2
            # controllers while the previous native create is still in flight.
            return
        if (not being_deleted and self._webview is not None
                and self._webview_create_attempts < self._webview_max_attempts):
            self._retry_webview_creation()

    def _retry_webview_creation(self, native_completed=False) -> None:
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
        self._native_retry_scheduled = False
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
                if native_completed:
                    # The native ERROR event was queued after the controller's
                    # completion callback, so its destroy no longer races
                    # CreateCoreWebView2Controller.
                    try:
                        old.Destroy()
                    except Exception:
                        pass
                else:
                    # Never destroy a controller that might still be creating.
                    self._retired_webviews.append(old)
            self._webview_failure_detail = (
                f"recreate attempt {self._webview_create_attempts + 1}"
                f"/{self._webview_max_attempts} after stage={self._webview_failure_stage}"
            )
            if sizer is None:
                return
            # A failed WebView2 controller can poison the cached native
            # environment. Retry with a fresh configuration, not the same one.
            from hpc_gui.wx_terminal_webview_factory import invalidate_failed_edge_configuration
            invalidate_failed_edge_configuration()
            self._mount_webview(sizer)
            try:
                self.Layout()
            except Exception:
                pass
        except Exception:
            pass

    # ---------- Input / Resize ----------

