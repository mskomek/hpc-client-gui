"""Local file-fragment transport for WebKitGTK terminal commands."""

import time
import sys
import uuid

try:
    import wx
except ImportError:  # keep non-GUI protocol tooling importable without wxPython
    wx = None

from hpc_gui.wx_terminal_url_bridge import encode_terminal_fragment
from hpc_gui.wx_terminal_fragment_queue import TerminalFragmentQueue

ACK_TIMEOUT_MS = 5000


class TerminalFragmentTransportMixin:
    """Serialize bounded commands over same-document local fragment changes."""

    def _init_fragment_transport(self, base_url):
        self._gtk_fragment_transport = sys.platform.startswith("linux")
        self._gtk_base_url = base_url
        self._gtk_queue = TerminalFragmentQueue()
        self._gtk_channel = uuid.uuid4().hex
        self._gtk_send_scheduled = False
        self._gtk_ack_timer = None
        self._gtk_ack_timer_seq = None
        self._gtk_ack_deadline = 0.0
        self._gtk_screen_snapshot = None
        self._gtk_query_pending = False

    def _init_fragment_timer(self):
        if self._gtk_fragment_transport and wx is not None:
            self._gtk_ack_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_fragment_ack_timeout, self._gtk_ack_timer)

    def _fragment_enqueue(self, method, arg=None):
        if self._closed or self._webview is None:
            return
        if method in {"hpcWrite", "hpcClear"}:
            self._gtk_screen_snapshot = None
            self._gtk_query_pending = False
        accepted = self._gtk_queue.enqueue(method, arg)
        if not accepted and method == "hpcGetScreenState":
            self._gtk_query_pending = False
        if method == "hpcWrite":
            if not self._gtk_send_scheduled:
                self._gtk_send_scheduled = True
                if wx is not None:
                    wx.CallAfter(self._send_scheduled_fragment)
                else:
                    self._send_scheduled_fragment()
        else:
            self._send_next_fragment()

    def _send_scheduled_fragment(self):
        self._gtk_send_scheduled = False
        self._send_next_fragment()

    def _send_next_fragment(self):
        if self._closed or self._webview is None:
            return
        command = self._gtk_queue.start_next()
        if command is None:
            return
        self._load_fragment(command)
        self._start_fragment_ack_timer(command.seq)

    def _load_fragment(self, command):
        try:
            fragment = encode_terminal_fragment(
                command.seq, command.method, command.arg, channel=self._gtk_channel
            )
            self._webview.LoadURL(self._gtk_base_url + fragment)
        except Exception:
            self._gtk_screen_snapshot = None
            self._gtk_query_pending = False

    def _start_fragment_ack_timer(self, seq):
        if self._gtk_ack_timer is None:
            return
        self._gtk_ack_timer_seq = seq
        self._gtk_ack_deadline = time.monotonic() + ACK_TIMEOUT_MS / 1000
        self._gtk_ack_timer.Start(ACK_TIMEOUT_MS, oneShot=True)

    def _stop_fragment_ack_timer(self):
        self._gtk_ack_timer_seq = None
        self._gtk_ack_deadline = 0.0
        try:
            if self._gtk_ack_timer and self._gtk_ack_timer.IsRunning():
                self._gtk_ack_timer.Stop()
        except Exception:
            pass

    def _on_fragment_ack_timeout(self, _event=None):
        if self._closed or self._webview is None:
            return
        current = self._gtk_queue.inflight
        if current is None or current.seq != self._gtk_ack_timer_seq:
            return
        remaining = int((self._gtk_ack_deadline - time.monotonic()) * 1000)
        if remaining > 0:
            self._gtk_ack_timer.Start(remaining, oneShot=True)
            return
        retry, exhausted = self._gtk_queue.retry(current.seq)
        if retry is not None:
            self._load_fragment(retry)
            self._start_fragment_ack_timer(retry.seq)
        elif exhausted:
            self._stop_fragment_ack_timer()
            if current.method == "hpcWrite":
                self._gtk_queue.report_output_loss()
            if current.method == "hpcGetScreenState":
                self._gtk_query_pending = False
            self._gtk_screen_snapshot = None
            self._send_next_fragment()

    def _fragment_acknowledged(self, seq):
        if not self._gtk_queue.acknowledge(seq):
            return False
        self._stop_fragment_ack_timer()
        self._send_next_fragment()
        return True

    def _gtk_get_snapshot(self):
        if self._closed or not self._ready:
            return None
        if self._gtk_screen_snapshot is None and not self._gtk_query_pending:
            self._gtk_query_pending = True
            self._fragment_enqueue("hpcGetScreenState")
        return self._gtk_screen_snapshot
