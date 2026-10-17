"""Terminal input/output and buffer-query operations for the wx WebView panel."""

import json
import sys

from hpc_gui.wx_terminal_url_bridge import parse_terminal_call

from hpc_gui.wx_terminal_webview_support import (
    MAX_PENDING_BYTES,
    MAX_PENDING_ENTRIES,
    MAX_PENDING_PASTE_BYTES,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    _safe_json_dumps,
    _safe_truncate_index,
)


class TerminalIOMixin:
    def _handle_input(self, data: str) -> bool:
        """Forward bridge input to the shell; return True when accepted.

        Returns False (with a visible header diagnostic) when there is no
        usable write path or the transport rejects/raises — the failure
        must never look like a successful send.
        """
        if self._closed or not data:
            return False
        # Production SSH adapter — do not log data
        cb = self._send_input
        if cb is None and self._ssh is not None:
            cb = getattr(self._ssh, "send_shell_input", None)
        if cb is None:
            self._show_write_failure()
            return False
        try:
            accepted = cb(data)
        except Exception:
            self._show_write_failure()
            return False
        # The SSH contract returns False when the shell is unavailable;
        # None (plain callbacks) and True mean accepted.
        if accepted is False:
            self._show_write_failure()
            return False
        self._clear_write_failure()
        return True

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
        if sys.platform.startswith("linux"):
            command = parse_terminal_call(code)
            if command is not None:
                self._fragment_enqueue(*command)
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

    def hpc_paste(self, text: str) -> bool:
        """Paste text into xterm via terminal.paste().

        Paste issued before the bridge is ready is queued (bounded) and
        delivered in order on ready instead of being silently lost
        (W20 TERM-019 lifecycle). Returns True when delivered or queued,
        False when dropped (closed, non-parity fallback, or over-cap).
        """
        if self._closed or not text:
            return False
        if not self._ready or not self._is_parity or self._webview is None:
            if not self._is_parity or self._webview is None:
                return False
            nb = len(text.encode("utf-8", errors="replace"))
            if self._pending_paste_bytes + nb > MAX_PENDING_PASTE_BYTES:
                return False
            self._pending_paste.append(text)
            self._pending_paste_bytes += nb
            return True
        try:
            self._run_js(f"window.hpcPaste && window.hpcPaste({_safe_json_dumps(text)});")
            return True
        except Exception:
            return False

    def _flush_pending_paste(self):
        """Deliver pre-ready queued paste in original order (called on ready)."""
        if self._closed or not self._ready or not self._pending_paste:
            return
        if not self._is_parity or self._webview is None:
            return
        combined = "".join(self._pending_paste)
        self._pending_paste.clear()
        self._pending_paste_bytes = 0
        if combined:
            self.hpc_paste(combined)

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
        if sys.platform.startswith("linux"):
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
        if sys.platform.startswith("linux"):
            state = self._gtk_get_snapshot()
            lines = state.get("lines", []) if state else []
            if 0 <= int(row) < len(lines) and isinstance(lines[int(row)], dict):
                return lines[int(row)].get("text")
            return None
        js = f"window.hpcGetLineText && window.hpcGetLineText({int(row)})"
        return self._run_js_readback(js)

    def hpc_get_buffer_text(self) -> str | None:
        """Read all visible+scrollback lines from xterm buffer."""
        if sys.platform.startswith("linux"):
            state = self._gtk_get_snapshot()
            if state is None:
                return None
            return "\n".join(
                line.get("text", "") for line in state.get("lines", [])
                if isinstance(line, dict)
            )
        js = "window.hpcGetBufferText && window.hpcGetBufferText()"
        return self._run_js_readback(js)

    def hpc_get_screen_state(self) -> dict | None:
        """Read full screen state (cursor, buffer type, lines) from xterm."""
        if sys.platform.startswith("linux"):
            return self._gtk_get_snapshot()
        js = "JSON.stringify(window.hpcGetScreenState && window.hpcGetScreenState())"
        result = self._run_js_readback(js)
        try:
            return json.loads(result) if result else None
        except Exception:
            return None

    # ---------- SSH attach / lifecycle ----------

