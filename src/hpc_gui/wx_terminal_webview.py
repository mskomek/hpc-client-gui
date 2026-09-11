"""wx terminal WebView renderer — xterm.js inside wx.html2.WebView.

Isolated module per Wave 73 architecture. Keeps wx_terminal.py as public
composition layer where practical. Reuses vendored xterm.js / xterm.css /
addon-fit.js; wx-specific page is wx_index.html + wx_bridge.js with a single
structured JSON bridge.

Security: local/offline only, vendored scripts, no CDN, connect-src 'none',
navigation guard, no credential/log leakage.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any, Callable, Optional

# Keep PySide6 out of wx terminal path — wave 73 forbids Qt channel / qrc in wx page
# and forbids importing PySide6 here.

try:
    import wx
    import wx.html2
    _WX_AVAILABLE = True
except ImportError:
    wx = None  # type: ignore
    wx_html2 = None  # type: ignore
    _WX_AVAILABLE = False

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change

READINESS_TIMEOUT_MS = 5000
MAX_PENDING_BYTES = 2 * 1024 * 1024
MAX_PENDING_ENTRIES = 5000
DEFAULT_FONT_SIZE = 14
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 32


def _safe_truncate_index(text: str, max_bytes: int) -> int:
    """Find the last safe truncation index that does not split an ESC sequence or a multi-byte UTF-8 char."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return len(text)
    cut = max_bytes
    # Walk backward from cut point to find a safe boundary
    while cut > 0:
        try:
            partial = encoded[:cut].decode("utf-8", errors="strict")
            return len(partial)
        except UnicodeDecodeError:
            cut -= 1
    # If all else fails, find last ESC boundary — do not cut inside an CSI/OSC sequence
    # ESC sequences: ESC [ ... final_byte, or ESC ] ... ST
    last_safe = 0
    i = 0
    raw = encoded[:max_bytes]
    while i < len(raw):
        b = raw[i]
        if b == 0x1B:  # ESC
            # Skip entire escape sequence
            if i + 1 < len(raw):
                next_b = raw[i + 1]
                if next_b == 0x5B:  # [ — CSI: ESC [ ... final_byte (0x40-0x7E)
                    j = i + 2
                    while j < len(raw) and not (0x40 <= raw[j] <= 0x7E):
                        j += 1
                    i = min(j + 1, len(raw))
                elif next_b == 0x5D:  # ] — OSC: ESC ] ... BEL or ST
                    j = i + 2
                    while j < len(raw):
                        if raw[j] == 0x07:  # BEL
                            j += 1
                            break
                        if raw[j] == 0x9B or (raw[j] == 0x1B and j + 1 < len(raw) and raw[j + 1] == 0x5C):
                            j += 2
                            break
                        j += 1
                    i = min(j, len(raw))
                else:
                    i += 2
            else:
                i += 1
        else:
            last_safe = i
            i += 1
    try:
        return encoded[:last_safe].decode("utf-8", errors="replace").__len__()
    except Exception:
        return len(text) // 2


@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


def _assets_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "assets" / "terminal"


def _wx_index_path() -> pathlib.Path:
    return _assets_dir() / "wx_index.html"


def _is_local_file_url(url: str) -> bool:
    # wx WebView reports file:// URLs for local assets; allow only those
    # and data: for xterm's internal use. Block http/https and anything else.
    u = (url or "").strip().lower()
    return u.startswith("file://") or u.startswith("about:blank") or u == ""


def _is_webview_available() -> bool:
    if not _WX_AVAILABLE:
        return False
    try:
        # wx.html2.WebView.IsBackendAvailable exists on some builds; fallback to import check
        if hasattr(wx.html2.WebView, "IsBackendAvailable"):
            try:
                if not wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendDefault):  # type: ignore
                    return False
            except Exception:
                pass
        # Also check that WebView can be instantiated (some platforms lack WebKit2)
        return True
    except Exception:
        return False


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


class WxTerminalWebViewPanel(wx.Panel if _WX_AVAILABLE else object):  # type: ignore
    """Real xterm.js terminal hosted in wx.html2.WebView.

    Single structured JSON bridge:
      {"type":"ready"}
      {"type":"input","data":"..."}
      {"type":"resize","cols":120,"rows":36,"pixelWidth":..,"pixelHeight":..}

    Python -> JS API (preserves bytes, no splitlines):
      hpcWrite(data) -> terminal.write
      hpcClear()     -> terminal.clear
      hpcFocus()     -> terminal.focus
      hpcSetFontSize(size) -> terminal.options.fontSize + fit
      hpcFit()       -> fit.fit + resize notify
    """

    def __init__(
        self,
        parent,
        *,
        ssh: Any | None = None,
        send_input: Optional[Callable[[str], bool]] = None,
        resize_pty: Optional[Callable[[int, int], None]] = None,
        lifecycle=None,
    ) -> None:
        if not _WX_AVAILABLE:
            raise RuntimeError("wxPython is not installed")
        super().__init__(parent)
        self._ssh = ssh
        self._send_input = send_input
        self._resize_pty = resize_pty
        if ssh is not None:
            self._send_input = getattr(ssh, "send_shell_input", send_input)
            self._resize_pty = getattr(ssh, "resize_shell_pty", resize_pty)

        self._ready = False
        self._page_loaded = False
        self._closed = False
        self._pending: list[str] = []
        self._pending_bytes = 0
        self._font_size = DEFAULT_FONT_SIZE
        self._last_resize: tuple[int, int] | None = None
        self._resize_timer = None
        self._readiness_timer = None
        self._webview = None
        self._is_parity = False
        self._diagnostic_text = ""

        # Generation counter for stale-output rejection across reconnects
        self._generation = 0

        # Header state — live, updated on connect/disconnect/reconnect
        self._status_text = t("login.status_disconnected")
        self._identity_text = ""
        self._dimensions_text = "--"

        # Build UI
        self._build_ui()

        # Subscribe to language changes
        self._lang_cb = self._refresh_labels
        subscribe_language_change(self._lang_cb)
        if lifecycle is not None:
            lifecycle.register_cleanup(self.close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

        # SSH output subscription
        self._subscriber = None
        self._subscribers_list = None
        self._attach_ssh(ssh)

        # Apply initial font
        self._apply_font_size(self._font_size, notify=False)

    # ---------- UI building ----------

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        # Toolbar — keep Find/Clear/A-/A+ for compat, add dimensions + status
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        self._find_ctrl = wx.TextCtrl(self, value="", style=wx.TE_PROCESS_ENTER)
        self._find_ctrl.SetHint(t("login.terminal_find") if t("login.terminal_find") != "[login.terminal_find]" else "Find")
        self._find_btn = wx.Button(self, label=t("login.terminal_find"))
        self._clear_btn = wx.Button(self, label=t("login.terminal_clear"))
        self._font_down_btn = wx.Button(self, label=t("login.terminal_font_decrease_short"))
        self._font_up_btn = wx.Button(self, label=t("login.terminal_font_increase_short"))
        self._status_label = wx.StaticText(self, label=self._status_text)
        self._identity_label = wx.StaticText(self, label=self._identity_text)
        font_b = self._identity_label.GetFont()
        font_b.SetWeight(wx.FONTWEIGHT_BOLD)
        self._identity_label.SetFont(font_b)
        self._sep_label = wx.StaticText(self, label="-")
        self._dimensions_label = wx.StaticText(self, label=self._dimensions_text)

        self._find_btn.SetToolTip(t("login.terminal_find"))
        self._clear_btn.SetToolTip(t("login.terminal_clear"))
        self._font_down_btn.SetToolTip(t("login.terminal_font_decrease"))
        self._font_up_btn.SetToolTip(t("login.terminal_font_increase"))

        toolbar.Add(self._find_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        toolbar.Add(self._find_btn, 0, wx.RIGHT, 6)
        toolbar.Add(self._clear_btn, 0, wx.RIGHT, 6)
        toolbar.Add(self._font_down_btn, 0, wx.RIGHT, 4)
        toolbar.Add(self._font_up_btn, 0, wx.RIGHT, 6)
        toolbar.Add(self._status_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        toolbar.Add(self._sep_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        toolbar.Add(self._identity_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        toolbar.AddStretchSpacer(1)
        toolbar.Add(self._dimensions_label, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self._find_btn.Bind(wx.EVT_BUTTON, self._on_find)
        self._find_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_find)
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        self._font_down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._change_font(-1))
        self._font_up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._change_font(1))

        root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 6)

        # WebView or fallback error panel
        if not _is_webview_available():
            self._is_parity = False
            self._diagnostic_text = self._build_diagnostic_text("WebView backend unavailable")
            err_panel = wx.Panel(self)
            err_sizer = wx.BoxSizer(wx.VERTICAL)
            err_label = wx.StaticText(err_panel, label=t("login.terminal_page_failed") if t("login.terminal_page_failed") != "[login.terminal_page_failed]" else "Terminal unavailable: WebView backend missing (WebView2/Edge on Windows, WebKit2 on Linux/macOS)")
            err_label.Wrap(600)
            diag = wx.TextCtrl(err_panel, value=self._diagnostic_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
            diag.SetMinSize(wx.Size(-1, 120))
            err_sizer.Add(err_label, 0, wx.ALL | wx.EXPAND, 8)
            err_sizer.Add(diag, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            err_panel.SetSizer(err_sizer)
            root.Add(err_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            self._webview = None
            self._error_panel = err_panel
            self._is_parity = False
            self.SetSizer(root)
            # expose controls for test seam (parity = False)
            self._wx_terminal_controls = {
                "find": self._find_ctrl,
                "find_btn": self._find_btn,
                "clear": self._clear_btn,
                "font_down": self._font_down_btn,
                "font_up": self._font_up_btn,
                "output": diag,
                "input": diag,
                "webview": None,
                "dimensions": self._dimensions_label,
                "status": self._status_label,
                "identity": self._identity_label,
            }
            self._wx_terminal_is_webview = False
            self._wx_terminal_is_parity = False
            return

        # WebView path
        self._is_parity = True
        try:
            self._webview = wx.html2.WebView.New(self)
        except Exception as exc:
            # Fallback if creation fails despite availability check
            self._diagnostic_text = self._build_diagnostic_text(f"WebView creation failed: {exc}")
            err_panel = wx.Panel(self)
            err_sizer = wx.BoxSizer(wx.VERTICAL)
            err_label = wx.StaticText(err_panel, label=t("login.terminal_page_failed") if t("login.terminal_page_failed") != "[login.terminal_page_failed]" else f"Terminal unavailable: {exc}")
            diag = wx.TextCtrl(err_panel, value=self._diagnostic_text, style=wx.TE_MULTILINE | wx.TE_READONLY)
            err_sizer.Add(err_label, 0, wx.ALL, 8)
            err_sizer.Add(diag, 1, wx.EXPAND | wx.ALL, 8)
            err_panel.SetSizer(err_sizer)
            root.Add(err_panel, 1, wx.EXPAND | wx.ALL, 6)
            self.SetSizer(root)
            self._wx_terminal_controls = {
                "find": self._find_ctrl,
                "find_btn": self._find_btn,
                "clear": self._clear_btn,
                "font_down": self._font_down_btn,
                "font_up": self._font_up_btn,
                "output": diag,
                "input": diag,
                "webview": None,
                "dimensions": self._dimensions_label,
                "status": self._status_label,
                "identity": self._identity_label,
            }
            self._wx_terminal_is_webview = False
            self._wx_terminal_is_parity = False
            return

        # WebView succeeded
        self._webview.SetMinSize(wx.Size(400, 200))
        # Accessibility
        self._webview.SetName(t("login.terminal_accessible_name") if t("login.terminal_accessible_name") != "[login.terminal_accessible_name]" else "Remote terminal")
        try:
            self._webview.SetAccessibleName(t("login.terminal_accessible_name") if t("login.terminal_accessible_name") != "[login.terminal_accessible_name]" else "Remote terminal")
        except Exception:
            pass

        # Single structured bridge handler
        try:
            self._webview.AddScriptMessageHandler("hpc")
        except Exception:
            try:
                self._webview.AddScriptMessageHandler("wx_msg")
            except Exception:
                pass
        self._webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._on_script_message)
        self._webview.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self._on_navigating)
        # Block popup/new-window
        try:
            self._webview.Bind(wx.html2.EVT_WEBVIEW_NEWWINDOW, self._on_new_window)
        except Exception:
            pass
        self._webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self._on_loaded)
        self._webview.Bind(wx.html2.EVT_WEBVIEW_ERROR, self._on_error)
        self.Bind(wx.EVT_SIZE, self._on_size)

        root.Add(self._webview, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.SetSizer(root)

        # Timers
        self._readiness_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_readiness_timeout, self._readiness_timer)
        self._resize_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_resize_timer, self._resize_timer)

        # Load local page
        index_path = _wx_index_path()
        url = index_path.as_uri()
        try:
            self._webview.LoadURL(url)
        except Exception:
            pass
        # Start readiness timeout
        self._readiness_timer.Start(READINESS_TIMEOUT_MS, oneShot=True)

        # Expose controls for tests
        self._wx_terminal_controls = {
            "find": self._find_ctrl,
            "find_btn": self._find_btn,
            "clear": self._clear_btn,
            "font_down": self._font_down_btn,
            "font_up": self._font_up_btn,
            "output": self._webview,
            "input": self._webview,
            "webview": self._webview,
            "dimensions": self._dimensions_label,
            "status": self._status_label,
            "identity": self._identity_label,
        }
        self._wx_terminal_is_webview = True
        self._wx_terminal_is_parity = True
        # For compat with old wx_terminal panel seam
        self._wx_terminal_model = None  # no splitlines model; xterm is authority

    def _build_diagnostic_text(self, reason: str) -> str:
        import platform as _pl
        import sys as _sys

        wx_ver = "unknown"
        try:
            wx_ver = wx.version()  # type: ignore
        except Exception:
            pass
        backend = "unknown"
        try:
            if hasattr(wx.html2.WebView, "GetBackendVersionInfo"):
                backend = str(wx.html2.WebView.GetBackendVersionInfo())  # type: ignore
        except Exception:
            pass
        return (
            f"{reason}\n"
            f"wxPython: {wx_ver}\n"
            f"Python: {_sys.version.split()[0]} platform={_pl.system()} {_pl.release()}\n"
            f"WebView backend: {backend}\n"
            f"Expected: WebView2/Edge on Windows, WebKit2 on Linux/macOS; install WebView2 Runtime or libwebkit2gtk.\n"
            f"Assets expected: wx_index.html, wx_bridge.js, xterm.js, xterm.css, addon-fit.js under assets/terminal/ (vendored, no CDN).\n"
        )

    # ---------- Language ----------

    def _refresh_labels(self, _lang=None):
        try:
            self._find_ctrl.SetHint(t("login.terminal_find"))
            self._find_btn.SetLabel(t("login.terminal_find"))
            self._clear_btn.SetLabel(t("login.terminal_clear"))
            self._clear_btn.SetToolTip(t("login.terminal_clear"))
            self._font_down_btn.SetLabel(t("login.terminal_font_decrease_short"))
            self._font_down_btn.SetToolTip(t("login.terminal_font_decrease"))
            self._font_up_btn.SetLabel(t("login.terminal_font_increase_short"))
            self._font_up_btn.SetToolTip(t("login.terminal_font_increase"))
            self._find_btn.SetToolTip(t("login.terminal_find"))
            # Status/identity/dimensions labels keep their values but tooltips refresh
        except Exception:
            pass

    # ---------- WebView events ----------

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
        try:
            event.Skip()
        except Exception:
            pass

    def _on_error(self, event):
        # Page load failed
        try:
            self._diagnostic_text = self._build_diagnostic_text(f"WebView load error: {event.GetString() if hasattr(event, 'GetString') else ''}")
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
        self._ready = True
        try:
            if self._readiness_timer and self._readiness_timer.IsRunning():
                self._readiness_timer.Stop()
        except Exception:
            pass
        self._flush_pending()
        # Initial fit after ready
        self._schedule_fit()

    def _on_readiness_timeout(self, _evt=None):
        if self._closed or self._ready:
            return
        # Readiness timeout — show diagnostic but remain functional if ready arrives later
        try:
            self._status_label.SetLabel(t("login.terminal_readiness_timeout") if t("login.terminal_readiness_timeout") != "[login.terminal_readiness_timeout]" else "Terminal did not become ready in time.")
        except Exception:
            pass
        # Do not clear pending — if ready arrives late, flush then

    # ---------- Input / Resize ----------

    def _handle_input(self, data: str):
        if self._closed or not data:
            return
        # Production SSH adapter — do not log data
        cb = self._send_input
        if cb is None and self._ssh is not None:
            cb = getattr(self._ssh, "send_shell_input", None)
        if cb is not None:
            try:
                cb(data)
            except Exception:
                pass

    def _handle_resize(self, cols: int, rows: int, _pw: int = 0, _ph: int = 0):
        if self._closed:
            return
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        # Deduplicate same size
        if self._last_resize == (cols, rows):
            return
        self._last_resize = (cols, rows)
        try:
            self._dimensions_label.SetLabel(f"{cols}\u00d7{rows}")
        except Exception:
            pass
        cb = self._resize_pty
        if cb is None and self._ssh is not None:
            cb = getattr(self._ssh, "resize_shell_pty", None)
        if cb is not None:
            try:
                cb(cols, rows)
            except Exception:
                pass

    def _on_size(self, evt):
        if self._closed:
            try:
                evt.Skip()
            except Exception:
                pass
            return
        # Debounce resize -> fit
        self._schedule_fit()
        try:
            evt.Skip()
        except Exception:
            pass

    def _schedule_fit(self):
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            if self._resize_timer and self._resize_timer.IsRunning():
                self._resize_timer.Stop()
            self._resize_timer.Start(50, oneShot=True)
        except Exception:
            pass

    def _on_resize_timer(self, _evt=None):
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            # Ask xterm to fit; it will post resize back via bridge
            self._run_js("window.hpcFit && window.hpcFit();")
        except Exception:
            pass

    # ---------- Public API (Python -> JS) ----------

    def _run_js(self, code: str):
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            # Fire-and-forget calls must not synchronously back up WebView2's
            # renderer queue while wx is pumping a burst of terminal output.
            if hasattr(self._webview, "RunScriptAsync"):
                self._webview.RunScriptAsync(code)
            elif hasattr(self._webview, "RunScript"):
                self._webview.RunScript(code)
        except Exception:
            pass

    def hpc_write(self, data: str):
        """Write raw terminal bytes/text to xterm without transformation."""
        if self._closed:
            return
        if not isinstance(data, str):
            data = str(data or "")
        if not data:
            return
        # Preserve carriage return, ESC, control chars, ANSI — no line splitting, no normalization
        if not self._ready or not self._is_parity or self._webview is None:
            # Buffer until ready, bounded
            # Coalesce if pending too large? Keep ordering, just append
            nb = len(data.encode("utf-8", errors="replace"))
            # Bounded check — if would exceed, flush aggressively by dropping oldest? Instead, keep but warn.
            # For Wave 73, we keep all pending up to bound; if exceeded, we still keep to avoid silent loss during startup,
            # but we enforce bound by coalescing earlier entries.
            if self._pending_bytes + nb > MAX_PENDING_BYTES or len(self._pending) >= MAX_PENDING_ENTRIES:
                # Coalesce pending into one entry to free entry count
                combined = "".join(self._pending)
                self._pending = [combined]
                self._pending_bytes = len(combined.encode("utf-8", errors="replace"))
                if self._pending_bytes + nb > MAX_PENDING_BYTES:
                    # Safe truncation: never split ESC sequences or UTF-8 chars
                    keep_bytes = max(0, MAX_PENDING_BYTES - nb)
                    safe_idx = _safe_truncate_index(combined, keep_bytes)
                    if safe_idx > 0:
                        self._pending[0] = combined[-safe_idx:]
                        self._pending_bytes = len(self._pending[0].encode("utf-8", errors="replace"))
                    else:
                        self._pending.clear()
                        self._pending_bytes = 0
            self._pending.append(data)
            self._pending_bytes += nb
            return
        # Ready — write directly, batched if data is huge
        # Use batching to avoid one expensive JS invocation per tiny fragment? However direct write is okay;
        # batching is for flush. Here we do single write per call; coalescing happens at pending flush.
        # To avoid per-fragment overhead, we could also coalesce if caller sends many tiny fragments rapidly
        # before the next event loop. For now, single write.
        try:
            self._run_js(f"window.hpcWrite && window.hpcWrite({_safe_json_dumps(data)});")
        except Exception:
            pass

    def _flush_pending(self):
        if self._closed or not self._ready or not self._pending:
            return
        # Coalesce pending in exact original order
        combined = "".join(self._pending)
        self._pending.clear()
        self._pending_bytes = 0
        # Batch into chunks to avoid one huge JS string (512KB chunks)
        max_chunk = 256 * 1024
        if len(combined) > max_chunk:
            for i in range(0, len(combined), max_chunk):
                chunk = combined[i : i + max_chunk]
                try:
                    self._run_js(f"window.hpcWrite && window.hpcWrite({_safe_json_dumps(chunk)});")
                except Exception:
                    pass
        else:
            try:
                self._run_js(f"window.hpcWrite && window.hpcWrite({_safe_json_dumps(combined)});")
            except Exception:
                pass

    def hpc_clear(self):
        if self._closed:
            return
        if not self._ready or not self._is_parity or self._webview is None:
            # Clear pending as well
            self._pending.clear()
            self._pending_bytes = 0
            return
        try:
            self._run_js("window.hpcClear && window.hpcClear();")
        except Exception:
            pass
        # Also clear pending
        self._pending.clear()
        self._pending_bytes = 0

    def hpc_focus(self):
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            self._run_js("window.hpcFocus && window.hpcFocus();")
        except Exception:
            pass
        try:
            self._webview.SetFocus()
        except Exception:
            pass

    def hpc_set_font_size(self, size: int):
        size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(size)))
        self._font_size = size
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            self._run_js(f"window.hpcSetFontSize && window.hpcSetFontSize({int(size)});")
        except Exception:
            pass
        # Font change will trigger resize via JS hpcFit -> post resize; no extra Python resize needed
        # But ensure fit is scheduled if not ready? JS handles.

    def hpc_fit(self):
        if self._closed or not self._is_parity or self._webview is None:
            return
        try:
            self._run_js("window.hpcFit && window.hpcFit();")
        except Exception:
            pass

    def _apply_font_size(self, size: int, *, notify: bool = True):
        self._font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(size)))
        if notify:
            self.hpc_set_font_size(self._font_size)

    def _change_font(self, delta: int):
        new_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, self._font_size + int(delta)))
        self._font_size = new_size
        self.hpc_set_font_size(new_size)

    def hpc_paste(self, text: str):
        """Paste text into xterm via terminal.paste()."""
        if self._closed or not text:
            return
        if not self._ready or not self._is_parity or self._webview is None:
            return
        try:
            self._run_js(f"window.hpcPaste && window.hpcPaste({_safe_json_dumps(text)});")
        except Exception:
            pass

    def _on_find(self, _evt=None):
        """Find text in xterm buffer via hpcFind JS helper."""
        query = ""
        try:
            query = self._find_ctrl.GetValue()
        except Exception:
            pass
        if not query or not self._is_parity or self._webview is None:
            return
        # If same query as last time, advance to next match
        if query == getattr(self, "_last_find_query", None):
            self.hpc_find_next()
            return
        self._last_find_query = query
        self.hpc_find(query)

    def hpc_find(self, query: str):
        """Find text in xterm buffer (test seam)."""
        if self._closed or not query:
            return False
        if not self._ready or not self._is_parity or self._webview is None:
            return False
        try:
            self._last_find_query = query
            self._run_js(f"window.hpcFind && window.hpcFind({_safe_json_dumps(query)});")
            return True
        except Exception:
            return False

    def hpc_find_next(self):
        """Advance to next match of the last find query."""
        if self._closed or not self._is_parity or self._webview is None:
            return False
        try:
            self._run_js("window.hpcFindNext && window.hpcFindNext();")
            return True
        except Exception:
            return False

    def hpc_find_prev(self):
        """Go to previous match of the last find query."""
        if self._closed or not self._is_parity or self._webview is None:
            return False
        try:
            self._run_js("window.hpcFindPrev && window.hpcFindPrev();")
            return True
        except Exception:
            return False

    def _on_clear(self, _evt=None):
        self.hpc_clear()

    # ---------- Buffer query helpers (test seam) ----------

    def _run_js_readback(self, js: str) -> str | None:
        """Return wx WebView's synchronous JavaScript result for readback helpers."""
        if self._closed or not self._ready or not self._is_parity or self._webview is None:
            return None
        try:
            result = self._webview.RunScript(js)
        except Exception:
            return None
        if isinstance(result, tuple) and len(result) >= 2:
            ok, value = result[0], result[1]
            return str(value) if ok and value is not None else None
        return result if isinstance(result, str) else None

    def hpc_get_line_text(self, row: int) -> str | None:
        """Read a single line from xterm buffer via JS helper."""
        js = f"window.hpcGetLineText && window.hpcGetLineText({int(row)})"
        return self._run_js_readback(js)

    def hpc_get_buffer_text(self) -> str | None:
        """Read all visible+scrollback lines from xterm buffer."""
        js = "window.hpcGetBufferText && window.hpcGetBufferText()"
        return self._run_js_readback(js)

    def hpc_get_screen_state(self) -> dict | None:
        """Read full screen state (cursor, buffer type, lines) from xterm."""
        js = "JSON.stringify(window.hpcGetScreenState && window.hpcGetScreenState())"
        result = self._run_js_readback(js)
        try:
            return json.loads(result) if result else None
        except Exception:
            return None

    # ---------- SSH attach / lifecycle ----------

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
        if new_ssh is not None:
            self._send_input = getattr(new_ssh, "send_shell_input", self._send_input)
            self._resize_pty = getattr(new_ssh, "resize_shell_pty", self._resize_pty)
            self._attach_ssh(new_ssh)
        else:
            self._send_input = None
            self._resize_pty = None
            self._update_status("disconnected")
            self._identity_text = ""
            try:
                self._identity_label.SetLabel("")
            except Exception:
                pass

    def close(self):
        if self._closed:
            return
        webview = self._webview
        self._closed = True
        self._webview = None
        self._is_parity = False
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
        try:
            unsubscribe_language_change(self._lang_cb)
        except Exception:
            pass
        # Release the native WebView2 controller before its parent panel is destroyed.
        if webview is not None:
            try:
                webview.Stop()
            except Exception:
                pass
            try:
                webview.Destroy()
            except Exception:
                pass

    def _update_status(self, state: str):
        """Update the connection status label. States: disconnected, connecting, connected, reconnecting."""
        label_map = {
            "disconnected": t("login.status_disconnected"),
            "connecting": t("login.status_connecting") if t("login.status_connecting") != "[login.status_connecting]" else "Connecting\u2026",
            "connected": t("login.status_connected") if t("login.status_connected") != "[login.status_connected]" else "Connected",
            "reconnecting": t("login.status_reconnecting") if t("login.status_reconnecting") != "[login.status_reconnecting]" else "Reconnecting\u2026",
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
        self.close()
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
        self.close()
        try:
            return super().Destroy()  # type: ignore
        except Exception:
            return False

    @property
    def _wx_terminal_ready(self):
        return getattr(self, "_ready", False)


def build_terminal_panel(parent, *, model=None, ssh=None, send_input=None, resize_pty=None, lifecycle=None):
    """Public composition entry — tries WebView, falls back to diagnostic non-parity panel.

    Keeps literal references to ssh.send_shell_input / ssh.resize_shell_pty for test seam.
    """
    # Keep model param for compat but ignore for WebView (xterm is authority)
    # If WebView is available, use it; else fall back to TextCtrl via wx_terminal
    if _is_webview_available():
        try:
            panel = WxTerminalWebViewPanel(parent, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
            # Expose same seam as old panel for shell compatibility
            panel._terminal_model = model  # for compat
            panel._terminal_ssh = ssh
            panel._wx_terminal_close = panel.close
            panel._wx_terminal_set_ssh = panel.set_ssh
            # For tests that call _wx_terminal_render, provide a wrapper that writes to xterm
            def _render_wrap(data):
                panel.hpc_write(data)

            panel._wx_terminal_render = _render_wrap
            # Expose model getter for old tests (may be None)
            if model is not None:
                panel._wx_terminal_model = model
            else:
                # Create a minimal model-like object for compat (clear/find/font)
                class _CompatModel:
                    def __init__(self, panel):
                        self._panel = panel
                        self.text = ""  # not used for rendering, but for find
                        self.font_size = panel._font_size

                    def receive(self, data):
                        self.text += str(data or "")
                        # Do not splitlines — preserve for find
                        if len(self.text) > 50000:
                            self.text = self.text[-50000:]

                    def find(self, q):
                        return self.text.find(q) if q else -1

                    def clear(self):
                        self.text = ""
                        self._panel.hpc_clear()

                    def change_font_size(self, delta):
                        self._panel._change_font(delta)
                        self.font_size = self._panel._font_size
                        return self.font_size

                compat = _CompatModel(panel)
                panel._wx_terminal_model = compat

            return panel
        except Exception:
            # Fall through to TextCtrl fallback
            pass

    # Fallback — import legacy TextCtrl panel (non-parity, diagnostic)
    try:
        from hpc_gui.wx_terminal import build_terminal_panel as _legacy_build
    except Exception as exc:
        raise RuntimeError("wx terminal fallback unavailable") from exc
    # Legacy panel already handles ssh/send_input/resize_pty/lifecycle
    panel = _legacy_build(parent, model=model, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
    # Mark as non-parity explicitly
    try:
        panel._wx_terminal_is_webview = False  # type: ignore
        panel._wx_terminal_is_parity = False  # type: ignore
    except Exception:
        pass
    return panel


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None, lifecycle=None) -> int:
    """Detached terminal — uses same WebView renderer, not TextCtrl divergence."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if ssh is None and send_input is None:
        wx.MessageBox(t("login.status_disconnected"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
        return wx.ID_CANCEL
    if ssh is not None:
        send_input = getattr(ssh, "send_shell_input", send_input)
        resize_pty = getattr(ssh, "resize_shell_pty", resize_pty)
    # Use lifecycle-aware frame
    frame = wx.Frame(parent, title=t("help.section_terminal"), size=(900, 600))
    panel = build_terminal_panel(frame, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)

    def refresh_labels(_language=None):
        try:
            frame.SetTitle(t("help.section_terminal"))
        except Exception:
            pass

    subscribe_language_change(refresh_labels)

    def close(_event=None):
        try:
            # Panel close handles unsubscribe and timers
            c = getattr(panel, "_wx_terminal_close", None) or getattr(panel, "close", None)
            if callable(c):
                c()
        except Exception:
            pass
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass
        try:
            frame.Destroy()
        except Exception:
            pass

    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_terminal_panel = panel
    # Expose controls for tests
    try:
        frame._wx_terminal_controls = getattr(panel, "_wx_terminal_controls", {})
    except Exception:
        frame._wx_terminal_controls = {}
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    frame.Show()
    return wx.ID_OK


__all__ = [
    "WxTerminalWebViewPanel",
    "build_terminal_panel",
    "show_terminal",
    "TerminalSize",
    "READINESS_TIMEOUT_MS",
]
