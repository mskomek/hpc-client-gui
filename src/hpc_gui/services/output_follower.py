"""Shared bounded remote-file follow state."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

MAX_VISIBLE_LINES = 5000


def retain_last_lines(text: str, max_lines: int = MAX_VISIBLE_LINES) -> str:
    lines = str(text or "").splitlines()[-max(1, int(max_lines)):]
    return "".join(f"{line}\n" for line in lines)


@dataclass
class OutputFollowerState:
    tracking_id: str
    channel_id: str | None
    job_id: str
    generation: int
    label: str
    path: str
    origin: str
    roles: tuple[str, ...] = ()
    offset: int = 0
    paused: bool = False
    auto_scroll: bool = True
    in_flight: bool = False
    waiting_state: int = 0
    closed: bool = False


class OutputFollower:
    """Poll one resolved remote path and retain only visible bounded history."""

    def __init__(self, state: OutputFollowerState, *, max_lines: int = MAX_VISIBLE_LINES) -> None:
        self.state = state
        self.max_lines = max(1, int(max_lines))
        self.text = ""
        self._retry_at = 0.0
        self._poll_token = 0

    def assign(
        self,
        *,
        channel_id: str | None,
        job_id: str,
        generation: int,
        label: str,
        path: str,
        origin: str,
        roles: tuple[str, ...] = (),
    ) -> None:
        changed = (
            self.state.job_id != str(job_id)
            or self.state.path != str(path)
            or self.state.origin != str(origin)
        )
        self.state.channel_id = channel_id
        self.state.job_id = str(job_id)
        self.state.generation = int(generation)
        self.state.label = str(label)
        self.state.path = str(path)
        self.state.origin = str(origin)
        self.state.roles = tuple(roles)
        self.state.closed = False
        if changed:
            self._poll_token += 1
            self.state.offset = 0
            self.state.waiting_state = 0
            self.state.in_flight = False
            self.text = ""
            self._retry_at = 0.0

    def replace_snapshot(self, text: str) -> str:
        self._poll_token += 1
        self.text = retain_last_lines(text, self.max_lines)
        self.state.offset = len(str(text or ""))
        self.state.waiting_state = 0
        self._retry_at = 0.0
        return self.text

    def poll(
        self,
        read_path: Callable[[str], str],
        stat_path: Callable[[str], object] | None = None,
        force: bool = False,
    ) -> tuple[str, str, bool]:
        """Return ``(new_chunk, retained_text, waiting)`` for this path."""
        if self.state.closed or self.state.paused:
            return "", self.text, False
        if self.state.in_flight:
            return "", self.text, self.state.waiting_state > 0
        if not force and self._retry_at and time.monotonic() < self._retry_at:
            return "", self.text, True
        self._poll_token += 1
        token = self._poll_token
        path = self.state.path
        self.state.in_flight = True
        try:
            if stat_path is not None:
                stat_path(path)
            full_text = str(read_path(path) or "")
            if token != self._poll_token or path != self.state.path:
                return "", self.text, False
            if len(full_text) < self.state.offset:
                self.state.offset = 0
                self.text = ""
            new_text = full_text[self.state.offset:]
            self.state.offset = len(full_text)
            self.state.waiting_state = 0
            self._retry_at = 0.0
            self.text = retain_last_lines(self.text + new_text, self.max_lines)
            return new_text, self.text, False
        except (FileNotFoundError, OSError):
            # A missing/rotated file is retried by the caller; reset the offset
            # so a recreated file is not silently skipped.
            self.state.offset = 0
            self.state.waiting_state = min(self.state.waiting_state + 1, 5)
            self._retry_at = time.monotonic() + min(5.0, float(2 ** (self.state.waiting_state - 1)))
            return "", self.text, True
        finally:
            if token == self._poll_token:
                self.state.in_flight = False

    def close(self) -> None:
        self._poll_token += 1
        self.state.closed = True
        self.state.in_flight = False


__all__ = ["MAX_VISIBLE_LINES", "OutputFollower", "OutputFollowerState", "retain_last_lines"]
