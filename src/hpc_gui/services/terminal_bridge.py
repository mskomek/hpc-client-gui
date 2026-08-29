from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class TerminalBridge(QObject):
    """Small Qt bridge around the already-owned interactive SSH channel."""

    output = Signal(str)
    state_changed = Signal(str)
    error = Signal(str)
    ready = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ssh: Any | None = None

    def attach(self, ssh: Any) -> None:
        self.detach()
        self._ssh = ssh
        self.state_changed.emit("open")

    def receive_output(self, text: str) -> None:
        if text:
            self.output.emit(text)

    @Slot()
    def terminal_ready(self) -> None:
        """Called only after the page has created xterm and its channel."""
        self.ready.emit()

    def detach(self) -> None:
        if self._ssh is None:
            return
        self._ssh = None
        self.state_changed.emit("closed")

    @Slot(str)
    def send_input(self, text: str) -> None:
        ssh = self._ssh
        if ssh is None:
            return
        try:
            if not ssh.send_shell_input(text):
                self.error.emit("interactive shell unavailable")
        except Exception as exc:
            self.error.emit(str(exc))

    @Slot(int, int, int, int)
    def resize(self, columns: int, rows: int, pixel_width: int = 0, pixel_height: int = 0) -> None:
        del pixel_width, pixel_height
        ssh = self._ssh
        if ssh is None:
            return
        try:
            ssh.resize_shell_pty(max(1, columns), max(1, rows))
        except Exception as exc:
            self.error.emit(str(exc))
