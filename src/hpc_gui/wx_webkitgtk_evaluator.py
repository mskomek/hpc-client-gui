"""CSP-safe JavaScript evaluation for wxGTK's WebKitGTK WebView."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable


class WebKitGtkUnavailable(RuntimeError):
    """Raised when the wx WebView does not expose a supported WebKitGTK widget."""


class _GList(ctypes.Structure):
    pass


_GList._fields_ = [
    ("data", ctypes.c_void_p),
    ("next", ctypes.POINTER(_GList)),
    ("prev", ctypes.POINTER(_GList)),
]


class _GError(ctypes.Structure):
    _fields_ = [("domain", ctypes.c_uint), ("code", ctypes.c_int), ("message", ctypes.c_char_p)]


@dataclass
class _PendingEvaluation:
    callback: object
    script: ctypes.Array
    on_complete: Callable[[str | None, str | None], None] | None


class WebKitGtkEvaluator:
    """Use WebKitGTK's native async API without weakening the page CSP.

    wxGTK's GetGtkWidget() returns a scrolled-window wrapper. This class
    discovers its WebKitWebView child and keeps each native request alive until
    its completion callback runs.
    """

    def __init__(self, wx_webview) -> None:
        if not sys.platform.startswith("linux"):
            raise WebKitGtkUnavailable("wx WebView is not running on Linux")
        getter = getattr(wx_webview, "GetGtkWidget", None)
        if not callable(getter):
            raise WebKitGtkUnavailable("wx WebView has no GTK widget accessor")

        self._gobject = ctypes.CDLL("libgobject-2.0.so.0")
        self._gtk = ctypes.CDLL("libgtk-3.so.0")
        self._glib = ctypes.CDLL("libglib-2.0.so.0")
        self._webkit = self._load_webkit()
        self._configure_apis()
        self._webview_ptr = self._find_webkit_view(int(getter()))
        if not self._webview_ptr:
            raise WebKitGtkUnavailable("GTK widget tree contains no WebKitWebView")
        self._owner_thread = threading.get_ident()
        self._pending: dict[int, _PendingEvaluation] = {}
        self._next_id = 0
        self._closed = False

    @staticmethod
    def _load_webkit():
        for name in ("libwebkit2gtk-4.1.so.0", "libwebkit2gtk-4.0.so.37"):
            try:
                return ctypes.CDLL(name)
            except OSError:
                continue
        raise WebKitGtkUnavailable("WebKitGTK shared library is unavailable")

    def _configure_apis(self) -> None:
        gobject = self._gobject
        gobject.g_type_from_name.argtypes = [ctypes.c_char_p]
        gobject.g_type_from_name.restype = ctypes.c_size_t
        gobject.g_type_check_instance_is_a.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        gobject.g_type_check_instance_is_a.restype = ctypes.c_int
        gobject.g_object_ref.argtypes = [ctypes.c_void_p]
        gobject.g_object_unref.argtypes = [ctypes.c_void_p]
        gobject.g_list_free.argtypes = [ctypes.c_void_p]
        gtk = self._gtk
        gtk.gtk_container_get_type.restype = ctypes.c_size_t
        gtk.gtk_container_get_children.argtypes = [ctypes.c_void_p]
        gtk.gtk_container_get_children.restype = ctypes.c_void_p
        glib = self._glib
        glib.g_free.argtypes = [ctypes.c_void_p]
        glib.g_error_free.argtypes = [ctypes.POINTER(_GError)]
        glib.g_main_context_iteration.argtypes = [ctypes.c_void_p, ctypes.c_int]
        webkit = self._webkit
        try:
            evaluate = webkit.webkit_web_view_evaluate_javascript
            finish = webkit.webkit_web_view_evaluate_javascript_finish
            to_string = webkit.jsc_value_to_string
        except AttributeError as exc:
            raise WebKitGtkUnavailable("WebKitGTK evaluate_javascript API is unavailable") from exc
        evaluate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_ssize_t,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        evaluate.restype = None
        finish.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(_GError))]
        finish.restype = ctypes.c_void_p
        to_string.argtypes = [ctypes.c_void_p]
        to_string.restype = ctypes.c_void_p

    def _find_webkit_view(self, root: int) -> int:
        gobject = self._gobject
        webview_type = gobject.g_type_from_name(b"WebKitWebView")
        container_type = self._gtk.gtk_container_get_type()
        stack = [root]
        visited: set[int] = set()
        while stack and len(visited) < 256:
            pointer = stack.pop()
            if not pointer or pointer in visited:
                continue
            visited.add(pointer)
            if webview_type and gobject.g_type_check_instance_is_a(pointer, webview_type):
                return pointer
            if not gobject.g_type_check_instance_is_a(pointer, container_type):
                continue
            children = self._gtk.gtk_container_get_children(pointer)
            node = ctypes.cast(children, ctypes.POINTER(_GList))
            while node:
                child = node.contents.data
                if child:
                    stack.append(int(child))
                node = node.contents.next
            if children:
                gobject.g_list_free(children)
        return 0

    def _dispatch(self, script: str, on_complete=None) -> int:
        if self._closed or not self._webview_ptr:
            raise WebKitGtkUnavailable("WebKitGTK evaluator is closed")
        self._next_id += 1
        request_id = self._next_id
        encoded = ctypes.create_string_buffer(script.encode("utf-8"))
        request = _PendingEvaluation(callback=None, script=encoded, on_complete=on_complete)
        self._pending[request_id] = request
        self._gobject.g_object_ref(self._webview_ptr)

        @ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        def finished(webview_ptr, result_ptr, _user_data):
            current = self._pending.pop(request_id, None)
            value_text = None
            error_text = None
            try:
                error = ctypes.POINTER(_GError)()
                value = self._webkit.webkit_web_view_evaluate_javascript_finish(
                    webview_ptr, result_ptr, ctypes.byref(error)
                )
                if error:
                    error_text = error.contents.message.decode("utf-8", errors="replace")
                    self._glib.g_error_free(error)
                elif value:
                    text = self._webkit.jsc_value_to_string(value)
                    if text:
                        value_text = ctypes.string_at(text).decode("utf-8", errors="replace")
                        self._glib.g_free(text)
                    self._gobject.g_object_unref(value)
            except Exception as exc:  # callbacks must not leak Python errors into C
                error_text = str(exc)
            finally:
                self._gobject.g_object_unref(webview_ptr)
            if current and current.on_complete:
                try:
                    current.on_complete(value_text, error_text)
                except Exception:
                    pass

        request.callback = finished
        self._webkit.webkit_web_view_evaluate_javascript(
            self._webview_ptr,
            ctypes.cast(encoded, ctypes.c_char_p),
            -1,
            None,
            None,
            None,
            ctypes.cast(finished, ctypes.c_void_p),
            None,
        )
        return request_id

    def run_async(self, script: str) -> bool:
        """Queue a no-result terminal command on WebKit's main context."""
        if threading.get_ident() != self._owner_thread:
            return False
        try:
            self._dispatch(script)
            return True
        except Exception:
            return False

    def evaluate_sync(self, script: str, timeout_seconds: float = 2.0) -> str | None:
        """Evaluate a bounded readback expression while pumping wx/GLib events."""
        if threading.get_ident() != self._owner_thread or self._closed:
            return None
        state: dict[str, str | None | bool] = {"done": False, "value": None, "error": None}

        def complete(value, error):
            state.update(done=True, value=value, error=error)

        try:
            self._dispatch(script, complete)
        except Exception:
            return None
        try:
            import wx

            deadline = time.monotonic() + max(0.05, min(timeout_seconds, 3.0))
            while not state["done"] and time.monotonic() < deadline:
                wx.YieldIfNeeded()
                self._glib.g_main_context_iteration(None, 0)
                time.sleep(0.005)
        except Exception:
            return None
        return state["value"] if state["done"] and not state["error"] else None

    def close(self) -> None:
        """Prevent new work; outstanding native requests retain their widget."""
        self._closed = True
        self._webview_ptr = 0
