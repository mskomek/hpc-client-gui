"""Locate the bundled terminal page and inspect the active wx WebView backend."""

from pathlib import Path


def terminal_assets_dir(module_file: str) -> Path:
    return Path(module_file).resolve().parent / "assets" / "terminal"


def terminal_index_path(module_file: str) -> Path:
    return terminal_assets_dir(module_file) / "wx_index.html"


def webview_backend_available(wx_module, wx_imported: bool) -> bool:
    if not wx_imported:
        return False
    try:
        webview = wx_module.html2.WebView
        if hasattr(webview, "IsBackendAvailable"):
            try:
                if not webview.IsBackendAvailable(wx_module.html2.WebViewBackendDefault):
                    return False
            except Exception:
                pass
        return True
    except Exception:
        return False
