"""Opt-in, content-free diagnostics for wx terminal acceptance runs."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()


def record_terminal_event(event: str, **metadata: object) -> None:
    """Append a small allowlisted metadata record when explicitly enabled."""
    target = os.environ.get("HPC_GUI_TERMINAL_DIAGNOSTICS_FILE", "").strip()
    if not target:
        return
    safe: dict[str, object] = {}
    for key, value in metadata.items():
        if key not in {
            "stage", "backend", "created", "ready", "page_loaded", "visible",
            "shown", "width", "height", "callback", "callback_id", "accepted",
            "exception_type", "native_code", "attempt", "pending_native",
            "ssh_id", "same_ssh", "connected", "channel_active", "reader_alive",
            "subscriber_count", "shell_active", "closed", "frozen", "executable",
            "asset_exists", "asset_hash", "url_scheme", "message_type", "elapsed_ms",
            "python_version", "wx_version", "webview_version", "meipass",
            "marker_visible", "is_parity", "webview_present", "script_async",
        }:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "monotonic": time.monotonic(),
        "event": str(event),
        "metadata": safe,
    }
    try:
        path = Path(target).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
        with _LOCK, path.open("a", encoding="utf-8") as stream:
            stream.write(line)
    except (OSError, TypeError, ValueError):
        return
