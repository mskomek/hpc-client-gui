"""Toolkit-neutral terminal state and PTY sizing contracts."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


class TerminalModel:
    """Keep PTY semantics independent from the toolkit renderer."""

    def __init__(self, send_input=None, resize_pty=None) -> None:
        self._send_input = send_input
        self._resize_pty = resize_pty
        self.text = ""
        self.font_size = 11

    def receive(self, data: str) -> None:
        self.text += str(data or "")
        lines = self.text.splitlines()
        if len(lines) > 5000:
            self.text = "\n".join(lines[-5000:])

    def key_input(self, key: str, *, command: bool = False, shift: bool = False) -> str:
        if key == "C" and not shift and not command:
            payload = "\x03"
        elif key == "D" and not shift and not command:
            payload = "\x04"
        elif key == "Z" and not shift and not command:
            payload = "\x1a"
        elif key in {"C", "V"} and (command or shift):
            return "copy" if key == "C" else "paste"
        else:
            payload = key
        if self._send_input:
            self._send_input(payload)
        return payload

    def resize(self, width: int, height: int, char_width: int = 8, char_height: int = 18) -> TerminalSize:
        size = TerminalSize(max(1, width // max(1, char_width)), max(1, height // max(1, char_height)))
        if self._resize_pty:
            self._resize_pty(size.columns, size.rows)
        return size

    def find(self, query: str) -> int:
        return self.text.find(query) if query else -1

    def clear(self) -> None:
        self.text = ""

    def change_font_size(self, delta: int) -> int:
        self.font_size = max(6, min(32, self.font_size + int(delta)))
        return self.font_size


