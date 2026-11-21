"""SSH attachment and teardown behavior for the wx WebView terminal panel."""

from hpc_gui.core.i18n import t, unsubscribe_language_change


class TerminalLifecycleMixin:
    def _attach_ssh(self, ssh):
        self._ssh = ssh
        if ssh is None:
            self._update_status("disconnected")
            return
        # Resolve callbacks if not yet set
        if self._send_input is None:
            self._send_input = getattr(ssh, "send_shell_input", None)
        if self._resize_pty is None:
            self._resize_pty = getattr(ssh, "resize_shell_pty", None)
        # Subscribe to output with generation guard
        subs = getattr(ssh, "_wx_output_subscribers", None)
        if subs is not None and isinstance(subs, list):
            gen = self._generation

            def subscriber(data, _self=self, _gen=gen):
                if _self._closed or _gen != _self._generation:
                    return
                try:
                    import wx as _wx
                    _wx.CallAfter(_self._safe_deliver, _gen, data)
                except Exception:
                    pass

            self._subscriber = subscriber
            self._subscribers_list = subs
            subs.append(subscriber)
        # Update header status
        self._update_status("connected")
        self._update_identity(ssh)

    def _safe_deliver(self, gen, data):
        """Deliver output only if generation matches (stale output rejection)."""
        if self._closed or gen != self._generation:
            return
        self.hpc_write(data)

    def set_ssh(self, new_ssh):
        # Detach old subscriber
        if self._subscriber is not None and self._subscribers_list is not None:
            try:
                self._subscribers_list.remove(self._subscriber)
            except Exception:
                pass
            self._subscriber = None
            self._subscribers_list = None
        # Increment generation to reject any in-flight stale callbacks
        self._generation += 1
        self._ssh = new_ssh
        try:
            self._terminal_ssh = new_ssh
        except Exception:
            pass
        if new_ssh is not None:
            self._send_input = getattr(new_ssh, "send_shell_input", self._send_input)
            self._resize_pty = getattr(new_ssh, "resize_shell_pty", self._resize_pty)
            self._attach_ssh(new_ssh)
        else:
            self._send_input = None
            self._resize_pty = None
            # The compat model is not the xterm input path, but it must not
            # retain a stale send callback to a dead transport either.
            try:
                compat = getattr(self, "_terminal_model", None)
                if compat is not None:
                    compat._send_input = None
                    compat._resize_pty = None
            except Exception:
                pass
            self._update_status("disconnected")
            self._identity_text = ""
            try:
                self._identity_label.SetLabel("")
            except Exception:
                pass

    def close(self):
        """Release Python state without double-destroying parent-owned children.

        Keep the zero-argument callback contract for cleanup registries and
        compatibility subclasses. Destroy/EVT_WINDOW_DESTROY mark native
        parent ownership before calling this hook.
        """
        if self._closed:
            return
        parent_teardown = bool(getattr(self, "_native_parent_teardown", False))
        webview = self._webview
        self._closed = True
        self._webview = None
        self._is_parity = False
        self._native_retry_scheduled = False
        # Drop retired controllers without touching them: still-attached
        # children are destroyed natively at panel teardown, and an explicit
        # Destroy here would repeat the in-flight-teardown race.
        try:
            self._retired_webviews = []
        except Exception:
            pass
        # Increment generation to cancel any in-flight callbacks
        self._generation += 1
        try:
            if self._readiness_timer and self._readiness_timer.IsRunning():
                self._readiness_timer.Stop()
        except Exception:
            pass
        try:
            if self._resize_timer and self._resize_timer.IsRunning():
                self._resize_timer.Stop()
        except Exception:
            pass
        # Retain the CallLater handle so shutdown can cancel retries that
        # would otherwise keep a destroyed native panel alive until firing.
        retry = getattr(self, "_native_retry_timer", None)
        self._native_retry_timer = None
        if retry is not None:
            try:
                retry.Stop()
            except Exception:
                pass
        self._stop_fragment_ack_timer()
        self._gtk_queue.reset()
        self._gtk_screen_snapshot = None
        self._gtk_query_pending = False
        self._gtk_send_scheduled = False
        # Unsubscribe
        if self._subscriber is not None and self._subscribers_list is not None:
            try:
                self._subscribers_list.remove(self._subscriber)
            except Exception:
                pass
            self._subscriber = None
            self._subscribers_list = None
        # Clear pending
        self._pending.clear()
        self._pending_bytes = 0
        self._pending_paste.clear()
        self._pending_paste_bytes = 0
        self._write_failure_shown = False
        try:
            unsubscribe_language_change(self._lang_cb)
        except Exception:
            pass
        # The owning wx panel controls the native lifetime of its WebView
        # children. close() also runs as a cleanup callback while the frame is
        # still alive, so destroying the child here can race queued WebView2
        # creation events or a later parent-driven teardown. Only detach our
        # Python reference; wx will destroy the child once with its parent.
        #
        # Stop() is useful for an initialized, still-live view, but it is not
        # safe during a native destroy event or while a WebView2 controller is
        # still being created asynchronously.
        being_deleted = False
        try:
            is_being_deleted = getattr(self, "IsBeingDeleted", None)
            if callable(is_being_deleted):
                being_deleted = bool(is_being_deleted())
        except Exception:
            being_deleted = False
        native_create_pending = (
            not getattr(self, "_native_created", False)
            and (
                getattr(self, "_webview_pending_native", False)
                or getattr(self, "_webview_legacy_edge", False)
            )
        )
        if (
            webview is not None
            and not parent_teardown
            and not being_deleted
            and not native_create_pending
        ):
            try:
                webview.Stop()
            except Exception:
                pass

    def _update_status(self, state: str):
        """Update the connection status label. States: disconnected, connecting, connected, reconnecting."""
        label_map = {
            "disconnected": t("login.status_disconnected"),
            "connecting": t("login.status_connecting"),
            "connected": t("login.status_connected"),
            "reconnecting": t("login.status_reconnecting"),
        }
        self._status_text = label_map.get(state, state)
        try:
            self._status_label.SetLabel(self._status_text)
        except Exception:
            pass

    def _update_identity(self, ssh):
        """Update the identity label with user@host from SSH, if available."""
        identity = ""
        try:
            user = getattr(ssh, "_username", None) or getattr(ssh, "username", None)
            host = getattr(ssh, "_hostname", None) or getattr(ssh, "hostname", None) or getattr(ssh, "_host", None)
            if user and host:
                identity = f"{user}@{host}"
        except Exception:
            pass
        self._identity_text = identity
        try:
            self._identity_label.SetLabel(identity)
        except Exception:
            pass

    def _on_destroy(self, event):
        # wx.WindowDestroyEvent is a CommandEvent: child destruction can
        # propagate to this panel. Retired WebView2 controls are deliberately
        # destroyed after replacement reaches ready; their destroy events must
        # NEVER close the still-live terminal panel.
        try:
            destroyed = event.GetWindow()
        except (AttributeError, RuntimeError):
            try:
                destroyed = event.GetEventObject()
            except (AttributeError, RuntimeError):
                destroyed = None
        try:
            if destroyed is self or (destroyed is not None and destroyed == self):
                self._native_parent_teardown = True
                self.close()
        except RuntimeError:
            pass
        try:
            event.Skip()
        except Exception:
            pass

    # ---------- Compat seam for old wx_terminal tests ----------

    # Note: _wx_terminal_is_webview and _wx_terminal_is_parity are plain
    # attributes set in _build_ui (not properties) to avoid setter conflicts.
    # _ready is the readiness flag; expose via _wx_terminal_ready for tests via
    # regular attribute.

    # For lifecycle
    def Destroy(self):  # type: ignore[override]
        self._native_parent_teardown = True
        self.close()
        try:
            return super().Destroy()  # type: ignore
        except Exception:
            return False

    @property
    def _wx_terminal_ready(self):
        return getattr(self, "_ready", False)
