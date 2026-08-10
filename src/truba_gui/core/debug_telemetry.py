from __future__ import annotations

"""Source-run-only, privacy-safe UI telemetry for debugging responsiveness."""

import sys
import time
from typing import Any

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QAbstractButton, QDialog, QLineEdit, QTabWidget, QTextEdit, QWidget

from truba_gui.core.logging import get_logger


def is_source_run() -> bool:
    """True for Python/source launches and false for packaged releases."""
    return not bool(getattr(sys, "frozen", False))


def _widget_name(widget: QWidget | None) -> str:
    if widget is None:
        return "unknown"
    name = widget.objectName().strip()
    return name or widget.__class__.__name__


class DebugTelemetry(QObject):
    """Logs intentional UI activity without recording user-entered content.

    The event filter intentionally ignores mouse movement and typed characters:
    they generate excessive logs and may expose sensitive input.  Clicks,
    non-text shortcuts, dialog visibility, and tab changes are sufficient to
    reconstruct a user flow and diagnose slow screens.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._log = get_logger("truba_gui.debug.telemetry")
        self._visible_since: dict[int, float] = {}

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (Qt API)
        if not isinstance(watched, QWidget):
            return False
        event_type = event.type()
        if event_type == QEvent.Type.Show:
            started = time.monotonic()
            self._visible_since[id(watched)] = started
            if isinstance(watched, QDialog):
                self._log.info("ui.dialog shown dialog=%s", _widget_name(watched))
                QTimer.singleShot(0, lambda w=watched, s=started: self._log_screen_ready(w, s))
        elif event_type == QEvent.Type.Hide:
            started = self._visible_since.pop(id(watched), None)
            if isinstance(watched, QDialog) and started is not None:
                self._log.info(
                    "ui.dialog hidden dialog=%s visible_ms=%d",
                    _widget_name(watched), (time.monotonic() - started) * 1000,
                )
        elif event_type == QEvent.Type.MouseButtonRelease:
            self._log_click(watched)
        elif event_type == QEvent.Type.KeyPress:
            self._log_key_action(watched, event)
        return False

    def _log_screen_ready(self, widget: QWidget, started: float) -> None:
        if widget.isVisible():
            self._log.info(
                "ui.screen ready screen=%s render_ms=%d",
                _widget_name(widget), (time.monotonic() - started) * 1000,
            )

    def _log_click(self, widget: QWidget) -> None:
        if isinstance(widget, (QLineEdit, QTextEdit)):
            # Do not turn text-entry interactions into a detailed audit trail.
            self._log.info("ui.input clicked widget=%s", _widget_name(widget))
            return
        if isinstance(widget, QAbstractButton):
            self._log.info("ui.action clicked control=%s text=%r", _widget_name(widget), widget.text())
            return
        self._log.info("ui.click widget=%s", _widget_name(widget))

    def _log_key_action(self, widget: QWidget, event: Any) -> None:
        if isinstance(widget, (QLineEdit, QTextEdit)):
            return
        # Log only the physical key code, never event.text().
        modifiers = event.modifiers()
        # PySide6 exposes Qt flag values as enum objects rather than values
        # accepted by int() on every version.
        modifier_value = getattr(modifiers, "value", modifiers)
        self._log.info(
            "ui.key widget=%s key=%s modifiers=%s",
            _widget_name(widget),
            event.key(),
            modifier_value,
        )

    def observe_tab_widget(self, tabs: QTabWidget, scope: str) -> None:
        """Record tab switches, time spent on the previous tab, and render time."""
        state = {"index": tabs.currentIndex(), "started": time.monotonic()}

        def on_changed(index: int) -> None:
            now = time.monotonic()
            old_index = state["index"]
            old_name = tabs.tabText(old_index) if old_index >= 0 else "none"
            new_name = tabs.tabText(index) if index >= 0 else "none"
            self._log.info(
                "ui.tab changed scope=%s from=%r to=%r previous_visible_ms=%d",
                scope, old_name, new_name, (now - state["started"]) * 1000,
            )
            state["index"] = index
            state["started"] = now
            QTimer.singleShot(0, lambda i=index, s=now: self._log_tab_ready(tabs, scope, i, s))

        tabs.currentChanged.connect(on_changed)

    def _log_tab_ready(self, tabs: QTabWidget, scope: str, index: int, started: float) -> None:
        if tabs.currentIndex() == index:
            self._log.info(
                "ui.tab ready scope=%s tab=%r render_ms=%d",
                scope, tabs.tabText(index), (time.monotonic() - started) * 1000,
            )
