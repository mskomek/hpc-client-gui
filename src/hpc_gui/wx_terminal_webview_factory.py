"""Create Windows Edge terminal controllers with an explicit, writable profile.

wxPython 4.3+ creates WebView2 asynchronously.  Callers must bind CREATED
before Create and load the page only after native controller initialization.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from hpc_gui.core.paths import app_data_dir

_WINDOWS = sys.platform == "win32"
_EDGE_CONFIG = None


def _edge_configuration(webview_class):
    """Reuse a single WebView2 environment for the lifetime of the process."""
    global _EDGE_CONFIG
    if _EDGE_CONFIG is not None:
        return _EDGE_CONFIG
    path_override = os.environ.get("WEBVIEW2_USER_DATA_FOLDER", "").strip()
    data_dir = Path(path_override).expanduser() if path_override else app_data_dir() / "webview2"
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    config = webview_class.NewConfiguration()
    config.SetDataPath(str(data_dir))
    _EDGE_CONFIG = config
    return config


def new_terminal_webview(parent, html2, on_created):
    """Return (view, pending_native_creation).

    The caller binds its navigation/error handlers and calls Create(parent)
    when pending_native_creation is true. Never fall back to IE on Windows.
    """
    cls = html2.WebView
    created_event = getattr(html2, "EVT_WEBVIEW_CREATED", None)
    if _WINDOWS and callable(getattr(cls, "NewConfiguration", None)) and created_event:
        config = _edge_configuration(cls)
        view = cls.New(config)
        if view is None:
            raise RuntimeError("WebView2 factory returned no controller")
        view.Bind(created_event, on_created)
        return view, True
    return cls.New(parent), False
