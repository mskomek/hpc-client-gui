"""wx terminal WebView renderer — xterm.js inside wx.html2.WebView.

Isolated module per Wave 73 architecture. Keeps wx_terminal.py as public
composition layer where practical. Reuses vendored xterm.js / xterm.css /
addon-fit.js; wx-specific page is wx_index.html + wx_bridge.js with a single
structured JSON bridge.

Security: local/offline only, vendored scripts, no CDN, connect-src 'none',
navigation guard, no credential/log leakage.
"""

from __future__ import annotations

import pathlib
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

from hpc_gui.core.i18n import subscribe_language_change, t
from hpc_gui.wx_terminal_webview_io import TerminalIOMixin as _TerminalIOMixin
from hpc_gui.wx_terminal_webview_lifecycle import TerminalLifecycleMixin as _TerminalLifecycleMixin
from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin as _TerminalBridgeMixin
from hpc_gui.wx_terminal_webview_support import (
    DEFAULT_FONT_SIZE,
    MAX_PENDING_PASTE_BYTES as MAX_PENDING_PASTE_BYTES,
    READINESS_TIMEOUT_MS,
    TerminalSize,
    _is_local_file_url as _is_local_file_url,
    _safe_json_dumps as _safe_json_dumps,
    _safe_truncate_index as _safe_truncate_index,
)
from hpc_gui.wx_terminal_fragment_transport import TerminalFragmentTransportMixin

def _assets_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "assets" / "terminal"


def _wx_index_path() -> pathlib.Path:
    return _assets_dir() / "wx_index.html"


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


class WxTerminalWebViewPanel(_TerminalBridgeMixin, _TerminalLifecycleMixin, TerminalFragmentTransportMixin, _TerminalIOMixin, wx.Panel if _WX_AVAILABLE else object):  # type: ignore
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
        # Pre-ready paste queue (W20 TERM-019 lifecycle): user paste issued
        # before the xterm bridge is ready must not be silently lost.
        self._pending_paste: list[str] = []
        self._pending_paste_bytes = 0
        # True while the header shows the transient write-failure diagnostic.
        self._write_failure_shown = False
        self._font_size = DEFAULT_FONT_SIZE
        self._last_resize: tuple[int, int] | None = None
        self._resize_timer = None
        self._readiness_timer = None
        self._webview = None
        self._init_fragment_transport(_wx_index_path().as_uri())
        self._is_parity = False
        self._diagnostic_text = ""
        self._webview_failure_stage = "not-created"
        self._webview_failure_detail = ""
        # REL-046 bounded recreate budget: initial creation + at most 2
        # recreates for transient native aborts (e.g. WebView2 E_ABORT
        # 0x80004004 on cold start). Never unlimited, never after close.
        self._webview_create_attempts = 0
        self._webview_max_attempts = 3
        # Retired never-ready controllers awaiting quiescent destroy (REL-046).
        # A controller that aborted creation asynchronously must never be
        # destroyed while native teardown may still be in flight (observed
        # fastfail 0xC0000409); it is detached, replaced, and destroyed only
        # after its replacement reaches bridge-ready.
        self._retired_webviews: list = []

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
        self._find_ctrl.SetHint(t("login.terminal_find"))
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
            err_label = wx.StaticText(err_panel, label=t("login.terminal_page_failed"))
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

        # WebView path: single-shot creation plus bounded recreate on
        # transient native abort (see _on_readiness_timeout).
        self._mount_webview(root)

    def _mount_webview(self, root):
        """Create the native WebView controller, bind the bridge, load the
        local terminal page and arm the readiness timer. One attempt."""
        self._webview_create_attempts += 1
        self._is_parity = True
        self._webview_failure_stage = "creating"
        try:
            self._webview = wx.html2.WebView.New(self)
        except Exception as exc:
            # Fallback if creation fails despite availability check
            self._webview_failure_stage = "creation"
            self._webview_failure_detail = str(exc)
            self._diagnostic_text = self._build_diagnostic_text(f"WebView creation failed: {exc}")
            err_panel = wx.Panel(self)
            err_sizer = wx.BoxSizer(wx.VERTICAL)
            err_label = wx.StaticText(err_panel, label=t("login.terminal_page_failed"))
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
        self._webview.SetName(t("login.terminal_accessible_name"))
        try:
            self._webview.SetAccessibleName(t("login.terminal_accessible_name"))
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
        self._init_fragment_timer()

        # Load local page
        index_path = _wx_index_path()
        url = index_path.as_uri()
        self._webview_failure_stage = "navigation"
        try:
            self._webview.LoadURL(url)
        except Exception:
            self._webview_failure_stage = "navigation-call"
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
        self._update_accessibility_label()
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

    def _write_failure_text(self) -> str:
        msg = t("login.terminal_write_failed")
        return msg

    def _show_write_failure(self):
        """Surface a failed input write truthfully (W20 TERM-007).

        A write that the transport rejects (False) or that raises must not
        look like success while the header still claims "Connected".
        The connection truth in _status_text is preserved; the diagnostic
        is transient and restored on the next successful write.
        """
        self._write_failure_shown = True
        try:
            self._status_label.SetLabel(self._write_failure_text())
        except Exception:
            pass

    def _clear_write_failure(self):
        if not self._write_failure_shown:
            return
        self._write_failure_shown = False
        try:
            self._status_label.SetLabel(self._status_text)
        except Exception:
            pass



def build_terminal_panel(parent, *, model=None, ssh=None, send_input=None, resize_pty=None, lifecycle=None):
    """Compatibility entry point for WebView terminal composition."""
    from hpc_gui.wx_terminal_webview_composition import build_terminal_panel as compose

    return compose(parent, model=model, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None, lifecycle=None) -> int:
    """Compatibility entry point for the detached WebView terminal window."""
    from hpc_gui.wx_terminal_webview_composition import show_terminal as show

    return show(parent, send_input, resize_pty, ssh=ssh, lifecycle=lifecycle)


__all__ = [
    "WxTerminalWebViewPanel",
    "build_terminal_panel",
    "show_terminal",
    "TerminalSize",
    "READINESS_TIMEOUT_MS",
]
