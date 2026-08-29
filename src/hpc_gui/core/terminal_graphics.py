"""Qt-free terminal graphics policy and GBM warning detection."""

from __future__ import annotations

import os
import shlex
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

DISABLE_GPU = "--disable-gpu"
MODES = {"auto", "compatibility", "accelerated"}
GBM_WARNING = "Failed to create GBM buffer for EGL"
GBM_THRESHOLD = 3
GBM_WINDOW_SECONDS = 30.0

_initial_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
_application_added_flag = False


@dataclass(frozen=True)
class GraphicsBootstrap:
    mode: str
    remembered_auto_compatibility: bool
    applied_disable_gpu: bool
    flag_origin: str


def _flag_tokens(value: str) -> list[str]:
    try:
        return shlex.split(value, posix=True)
    except ValueError:
        return value.split()


def has_flag(value: str, flag: str = DISABLE_GPU) -> bool:
    return flag in _flag_tokens(value)


def normalize_settings(settings: dict | None) -> tuple[str, bool]:
    settings = settings if isinstance(settings, dict) else {}
    mode = settings.get("terminal_graphics_mode", "auto")
    mode = mode if isinstance(mode, str) and mode in MODES else "auto"
    remembered = settings.get("terminal_graphics_auto_compatibility", False)
    return mode, remembered if isinstance(remembered, bool) else False


def apply_bootstrap(settings: dict | None = None) -> GraphicsBootstrap:
    """Apply the saved policy before QApplication/WebEngine imports."""
    global _application_added_flag
    mode, remembered = normalize_settings(settings)
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    external_disable = has_flag(_initial_flags)
    should_disable = mode == "compatibility" or (mode == "auto" and remembered)
    if should_disable and not has_flag(flags):
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (flags + " " + DISABLE_GPU).strip()
        _application_added_flag = True
    elif flags:
        _application_added_flag = False
    return GraphicsBootstrap(
        mode=mode,
        remembered_auto_compatibility=remembered,
        applied_disable_gpu=has_flag(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")),
        flag_origin="external" if external_disable else ("application" if _application_added_flag else "none"),
    )


def restart_environment() -> dict[str, str]:
    """Return a child environment without inheriting an app-added flag."""
    env = dict(os.environ)
    if _application_added_flag and not has_flag(_initial_flags):
        if _initial_flags:
            env["QTWEBENGINE_CHROMIUM_FLAGS"] = _initial_flags
        else:
            env.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
    return env


def restart_command(argv: list[str] | None = None) -> list[str]:
    """Build a safe argv for both PyInstaller and source/console-script runs."""
    current = list(sys.argv if argv is None else argv)
    if getattr(sys, "frozen", False):
        return [sys.executable, *current[1:]]
    return [sys.executable, *current]


class GbmWarningTracker:
    def __init__(self, threshold: int = GBM_THRESHOLD, window_seconds: float = GBM_WINDOW_SECONDS) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds
        self._events: deque[float] = deque()
        self._lock = threading.Lock()
        self._suggested = False

    def record(self, message: str, now: float | None = None) -> bool:
        if GBM_WARNING not in message or sys.platform != "linux":
            return False
        current = time.monotonic() if now is None else now
        with self._lock:
            self._events.append(current)
            while self._events and current - self._events[0] > self.window_seconds:
                self._events.popleft()
            if len(self._events) < self.threshold or self._suggested:
                return False
            self._suggested = True
            return True

    def reset_session(self) -> None:
        with self._lock:
            self._events.clear()
            self._suggested = False
