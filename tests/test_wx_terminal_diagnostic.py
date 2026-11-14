"""Regression coverage for the extracted wx WebView diagnostic builder."""

from types import SimpleNamespace

from hpc_gui.wx_terminal_webview_support import build_terminal_diagnostic_text


def test_diagnostic_reports_terminal_runtime_and_backend() -> None:
    class WebView:
        @staticmethod
        def GetBackendVersionInfo() -> str:
            return "test-backend"

    wx_module = SimpleNamespace(
        version=lambda: "wx-test",
        html2=SimpleNamespace(WebView=WebView),
    )

    text = build_terminal_diagnostic_text("WebView unavailable", wx_module)

    assert text.startswith("WebView unavailable\n")
    assert "wxPython: wx-test\n" in text
    assert "WebView backend: test-backend\n" in text
    assert "Python:" in text
    assert "Assets expected: wx_index.html" in text
    assert "WebView2/Edge on Windows" in text


def test_diagnostic_keeps_fallback_when_backend_probe_fails() -> None:
    def unavailable_version() -> str:
        raise RuntimeError("probe unavailable")

    wx_module = SimpleNamespace(
        version=unavailable_version,
        html2=SimpleNamespace(WebView=object),
    )

    text = build_terminal_diagnostic_text("Failure", wx_module)

    assert "wxPython: unknown\n" in text
    assert "WebView backend: unknown\n" in text
