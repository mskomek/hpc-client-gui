"""Toolkit-neutral interactive shell bridge; renderers own event dispatch."""
from __future__ import annotations

from typing import Any, Callable


class TerminalBridge:
    """Attach to an already-owned SSH channel without assuming a GUI toolkit."""

    def __init__(
        self, *, on_output: Callable[[str], None] | None = None,
        on_state: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        self._ssh: Any | None = None
        self._on_output = on_output
        self._on_state = on_state
        self._on_error = on_error
        self._on_ready = on_ready

    def attach(self, ssh: Any) -> None:
        self.detach()
        self._ssh = ssh
        if self._on_state:
            self._on_state("open")

    def receive_output(self, text: str) -> None:
        if text and self._on_output:
            self._on_output(text)

    def terminal_ready(self) -> None:
        if self._on_ready:
            self._on_ready()

    def detach(self) -> None:
        if self._ssh is None:
            return
        self._ssh = None
        if self._on_state:
            self._on_state("closed")

    def send_input(self, text: str) -> None:
        ssh = self._ssh
        if ssh is None:
            return
        try:
            if not ssh.send_shell_input(text) and self._on_error:
                self._on_error("interactive shell unavailable")
        except Exception as exc:
            if self._on_error:
                self._on_error(str(exc))

    def resize(self, columns: int, rows: int, pixel_width: int = 0, pixel_height: int = 0) -> None:
        del pixel_width, pixel_height
        ssh = self._ssh
        if ssh is None:
            return
        try:
            ssh.resize_shell_pty(max(1, columns), max(1, rows))
        except Exception as exc:
            if self._on_error:
                self._on_error(str(exc))
