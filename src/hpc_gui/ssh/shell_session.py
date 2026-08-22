"""Interactive SSH shell session lifecycle.

Owns one interactive shell channel: PTY geometry, the reader thread, the
incremental UTF-8 decoder, ordered sending, and stop/join semantics. It never
authenticates, opens SFTP, executes commands, or imports Qt — the owner of the
connection supplies an ``invoke_shell`` callable bound to an authenticated
client plus output/disconnect/log callbacks.
"""

from __future__ import annotations

import codecs
import socket
import threading
import time
from typing import Callable, Optional, Tuple

_ACS_MAP = {
    "j": "┘",
    "k": "┐",
    "l": "┌",
    "m": "└",
    "n": "┼",
    "q": "─",
    "t": "├",
    "u": "┤",
    "v": "┴",
    "w": "┬",
    "x": "│",
    "o": "█",
    "s": "·",
    "a": "▒",
    "f": "°",
    "g": "±",
    "h": "␋",
    "i": "␌",
    "`": "◆",
}


def _sanitize_terminal_text(text: str) -> str:
    """Remove terminal control sequences and normalize redraw-heavy output."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    alt_charset = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        code = ord(ch)
        if ch == "\x1b" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "[":
                i += 2
                while i < n and not ("@" <= text[i] <= "~"):
                    i += 1
                i += 1
                continue
            if nxt in "()":
                if i + 2 < n:
                    spec = nxt + text[i + 2]
                    if spec in ("(0", ")0"):
                        alt_charset = True
                    elif spec in ("(B", ")B"):
                        alt_charset = False
                i += 3
                continue
            if nxt in "PX^_":
                i += 2
                while i < n:
                    if text[i] == "\x1b" and i + 1 < n and text[i + 1] == "\\":
                        i += 2
                        break
                    i += 1
                continue
            if "@" <= nxt <= "_":
                i += 2
                continue
            i += 1
            continue
        if ch in ("\x0e", "\x0f"):
            alt_charset = ch == "\x0e"
            i += 1
            continue
        if code < 32 and ch not in ("\n", "\t"):
            i += 1
            continue
        if alt_charset and ch in _ACS_MAP:
            out.append(_ACS_MAP[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


class InteractiveShellSession:
    """One interactive shell channel and everything that serves it."""

    def __init__(
        self,
        *,
        invoke_shell: Callable[..., object],
        geometry: Tuple[int, int] = (120, 40),
        on_output: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[str], None]] = None,
        log: Optional[Callable[[str], None]] = None,
        sanitize: Callable[[str], str] = _sanitize_terminal_text,
    ) -> None:
        self._invoke_shell = invoke_shell
        self.geometry = (max(1, int(geometry[0])), max(1, int(geometry[1])))
        self._on_output_cb = on_output
        self._on_disconnect_cb = on_disconnect
        self._log = log or (lambda msg: None)
        self._sanitize = sanitize

        self.channel = None
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    # ---------- lifecycle ----------

    def start(self) -> bool:
        self.stop()
        try:
            cols, rows = self.geometry
            try:
                channel = self._invoke_shell(term="xterm-256color", width=cols, height=rows)
            except Exception as preferred_exc:
                self._log(
                    f"SSH: xterm-256color unavailable; falling back to xterm ({preferred_exc.__class__.__name__})"
                )
                channel = self._invoke_shell(term="xterm", width=cols, height=rows)
            try:
                channel.settimeout(0.2)
            except Exception:
                pass
        except Exception as exc:
            self._log(f"SSH: interactive shell unavailable ({exc})")
            return False

        self.channel = channel
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._reader_loop,
            args=(channel,),
            name="hpc_gui_ssh_shell",
            daemon=True,
        )
        self.drain_initial_output(channel)
        self._thread.start()
        self._log("SSH: interactive shell session started")
        return True

    def stop(self) -> None:
        self._stop.set()
        channel = self.channel
        self.channel = None
        thread = self._thread
        self._thread = None
        try:
            if channel is not None:
                self.decode_bytes(b"", final=True)
                try:
                    channel.close()
                except Exception:
                    pass
        finally:
            if thread is not None and thread.is_alive() and thread is not threading.current_thread():
                try:
                    thread.join(timeout=1.0)
                except Exception:
                    pass
            self.decode_bytes(b"", final=True)

    # ---------- input ----------

    def send_text(self, text: str) -> bool:
        payload = (text or "").rstrip("\r\n")
        if not payload:
            return True
        return self.send_payload((payload + "\n").encode("utf-8"))

    def send_input(self, data: str) -> bool:
        payload = data or ""
        if not payload:
            return True
        return self.send_payload(payload.encode("utf-8"))

    def send_payload(self, payload: bytes) -> bool:
        if not payload:
            return True
        with self._send_lock:
            channel = self.channel
            if channel is None or getattr(channel, "closed", False):
                return False
            offset = 0
            try:
                while offset < len(payload):
                    sent = channel.send(payload[offset:])
                    if not sent:
                        return False
                    offset += sent
                return True
            except Exception:
                return False

    def resize(self, cols: int, rows: int) -> None:
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        self.geometry = (cols, rows)
        channel = self.channel
        if channel is None:
            return
        try:
            channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    # ---------- output ----------

    def decode_bytes(self, data: bytes, *, final: bool = False) -> None:
        try:
            text = self.decoder.decode(data, final=final)
        except Exception:
            return
        self._handle_output(text)

    def drain_initial_output(self, channel, duration: float = 0.35) -> None:
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline and not self._stop.is_set():
            try:
                if not channel.recv_ready():
                    time.sleep(0.05)
                    continue
                data = channel.recv(4096)
                if not data:
                    break
                self.decode_bytes(data)
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_output(self, text: str) -> None:
        if not text:
            return
        if self._on_output_cb is not None:
            try:
                self._on_output_cb(text)
                return
            except Exception:
                pass
        sanitized = self._sanitize(text)
        if sanitized.strip():
            self._log(sanitized.rstrip("\n"))

    # ---------- reader ----------

    def _reader_loop(self, channel) -> None:
        unexpected_disconnect = False
        disconnect_reason = ""
        while not self._stop.is_set():
            try:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        self.decode_bytes(data)
                    continue
                if getattr(channel, "closed", False) or channel.exit_status_ready():
                    unexpected_disconnect = True
                    disconnect_reason = "SSH shell session ended."
                    break
            except socket.timeout:
                continue
            except Exception as exc:
                if not self._stop.is_set():
                    self._log(f"SSH: shell session read failed ({exc})")
                    unexpected_disconnect = True
                    disconnect_reason = str(exc)
                break
            time.sleep(0.1)
        if unexpected_disconnect and not self._stop.is_set():
            if self._on_disconnect_cb is not None:
                try:
                    self._on_disconnect_cb(disconnect_reason or "SSH shell session ended.")
                except Exception:
                    pass
