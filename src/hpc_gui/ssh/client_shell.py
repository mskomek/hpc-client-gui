"""Interactive shell, PTY and X11 bridges for the SSH client wrapper.

The shell lifecycle itself lives in
:class:`hpc_gui.ssh.shell_session.InteractiveShellSession`; this mixin keeps the
historical wrapper attribute surface so callers can inject a channel or decoder
directly and inspect the active X11 forwarder.
"""

from __future__ import annotations


class ShellBridgeMixin:
    """Bridge the wrapper's shell attributes onto the interactive session."""

    def _invoke_shell(self, **kwargs):
        assert self.client is not None
        if not (self.info is not None and getattr(self.info, "x11_forwarding", False)):
            return self.client.invoke_shell(**kwargs)
        forwarder = self._prepare_x11_forwarder()
        if forwarder is None:
            return self.client.invoke_shell(**kwargs)
        transport = self.client.get_transport()
        assert transport is not None
        channel = transport.open_session()
        channel.get_pty(kwargs.get("term", "vt100"), kwargs.get("width", 80), kwargs.get("height", 24))
        try:
            forwarder.request(channel)
            self._x11_forwarder = forwarder
            self.log(f"X11: yönlendirme etkin (yerel ekran {forwarder.display.name})")
        except Exception as exc:
            forwarder.close()
            self.log(f"X11: sunucu X11 yönlendirmeyi reddetti ({exc.__class__.__name__}: {exc})")
        channel.invoke_shell()
        return channel

    def _prepare_x11_forwarder(self):
        """Ensure a local X server and build a forwarder (None -> no X11)."""
        from hpc_gui.ssh.x11_forward import X11Forwarder, local_display_from_env

        self._close_x11_forwarder()
        try:
            from hpc_gui.services import xserver_manager

            if xserver_manager._is_windows():
                ready = xserver_manager.ensure_x_server_running(self.log, parent=None, allow_download=False)
            elif xserver_manager._is_macos():
                ready = xserver_manager.ensure_xquartz_available(self.log)
            else:
                ready = xserver_manager.is_local_x_available(self.log)
        except Exception as exc:
            self.log(f"X11: yerel X sunucusu denetlenemedi ({exc.__class__.__name__})")
            ready = False
        if not ready:
            self.log("X11: yerel X sunucusu hazır değil; terminal X11 olmadan açılıyor.")
            return None
        return X11Forwarder(local_display_from_env(), log=self.log)

    def _close_x11_forwarder(self) -> None:
        forwarder = getattr(self, "_x11_forwarder", None)
        self._x11_forwarder = None
        if forwarder is not None:
            try:
                forwarder.close()
            except Exception:
                pass

    def _on_shell_unexpected_disconnect(self, reason: str) -> None:
        try:
            self.close()
        except Exception:
            pass
        self._notify_disconnect(reason)

    @property
    def _shell_channel(self):
        return self._shell_session.channel if self._shell_session else None

    @_shell_channel.setter
    def _shell_channel(self, channel) -> None:
        if channel is None:
            if self._shell_session is not None:
                self._shell_session.channel = None
            return
        session = self._ensure_shell_session()
        session.channel = channel

    @property
    def _shell_decoder(self):
        return self._ensure_shell_session().decoder

    @_shell_decoder.setter
    def _shell_decoder(self, decoder) -> None:
        self._ensure_shell_session().decoder = decoder

    def activate_shell_output(self) -> None:
        """Release shell startup output after a terminal view subscribes."""
        if self._shell_session is not None:
            self._shell_session.activate_output()

    def resize_shell_pty(self, cols: int, rows: int) -> None:
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        self._shell_geometry = (cols, rows)
        if self._shell_session is not None:
            self._shell_session.resize(cols, rows)

    def send_shell_text(self, text: str) -> bool:
        return self._ensure_shell_session().send_text(text)

    def send_shell_input(self, data: str) -> bool:
        return self._ensure_shell_session().send_input(data)

    def _send_shell_payload(self, payload: bytes) -> bool:
        return self._ensure_shell_session().send_payload(payload)

    def _decode_shell_bytes(self, data: bytes, *, final: bool = False) -> None:
        self._ensure_shell_session().decode_bytes(data, final=final)

    def _stop_shell_session(self) -> None:
        if self._shell_session is not None:
            try:
                self._shell_session.stop()
            finally:
                self._shell_session = None
