"""Source-run-only, toolkit-neutral interaction timing and diagnostics."""
from __future__ import annotations

import sys
import time
from typing import Callable

from hpc_gui.core.logging import get_logger


def is_source_run() -> bool:
    """True for source launches; packaged releases do not collect UI telemetry."""
    return not bool(getattr(sys, "frozen", False))


class TelemetryRecorder:
    """Record structural events only. Never accept user-entered text or labels."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic, logger=None):
        self.clock = clock
        self.log = logger or get_logger("hpc_gui.debug.telemetry")

    def action(self, control_type: str) -> None:
        self.log.info("ui.action clicked control=%s", control_type)

    def key(self, control_type: str, key_code: int, modifiers: int) -> None:
        self.log.info("ui.key widget=%s key=%s modifiers=%s", control_type, key_code, modifiers)

    def tab_changed(self, scope: str, old_index: int, index: int, since: float) -> float:
        now = self.clock()
        self.log.info(
            "ui.tab changed scope=%s from=%d to=%d previous_visible_ms=%d",
            scope, old_index, index, max(0, int((now - since) * 1000)),
        )
        return now

    def tab_ready(self, scope: str, index: int, since: float) -> None:
        self.log.info(
            "ui.tab ready scope=%s tab=%d render_ms=%d",
            scope, index, max(0, int((self.clock() - since) * 1000)),
        )


    def window_shown(self, kind: str) -> None:
        self.log.info("ui.window shown kind=%s", kind)

    def window_ready(self, kind: str, since: float) -> None:
        self.log.info("ui.window ready kind=%s render_ms=%d",
                      kind, max(0, int((self.clock() - since) * 1000)))

    def window_hidden(self, kind: str, since: float) -> None:
        self.log.info("ui.window hidden kind=%s visible_ms=%d",
                      kind, max(0, int((self.clock() - since) * 1000)))
