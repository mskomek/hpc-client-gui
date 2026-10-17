"""Bounded, retryable command queue for the local WebKit terminal bridge."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterator


MAX_QUEUE_BYTES = 2 * 1024 * 1024
MAX_QUEUE_ENTRIES = 4096
FRAGMENT_WRITE_CHARS = 2048
MAX_ACK_RETRIES = 2
RETRYABLE_METHODS = frozenset({
    "hpcClear", "hpcFocus", "hpcSetFontSize", "hpcFit", "hpcFind",
    "hpcGetScreenState",
})
OUTPUT_LIMIT_NOTICE = "\r\n[Terminal output paused: local bridge queue limit reached]\r\n"
_COMMAND_OVERHEAD_BYTES = 128


@dataclass(frozen=True)
class TerminalCommand:
    seq: int
    method: str
    arg: object

    @property
    def size_bytes(self) -> int:
        payload = self.arg if isinstance(self.arg, str) else ""
        return len(payload.encode("utf-8", errors="replace")) + _COMMAND_OVERHEAD_BYTES


class TerminalFragmentQueue:
    """Keep fragment IPC memory bounded and retry one command at a time."""

    def __init__(self) -> None:
        self._next_seq = 0
        self._queued: deque[TerminalCommand] = deque()
        self._inflight: TerminalCommand | None = None
        self._inflight_retries = 0
        self._bytes = 0
        self._overflow_notice_queued = False

    @property
    def inflight(self) -> TerminalCommand | None:
        return self._inflight

    @property
    def queued_entries(self) -> int:
        return len(self._queued) + int(self._inflight is not None)

    @property
    def queued_bytes(self) -> int:
        return self._bytes

    def enqueue(self, method: str, arg: object = None) -> bool:
        accepted = True
        for value in self._values(method, arg):
            command = self._new_command(method, value)
            if (self.queued_entries >= MAX_QUEUE_ENTRIES
                    or self._bytes + command.size_bytes > MAX_QUEUE_BYTES):
                if method == "hpcWrite":
                    self.report_output_loss()
                accepted = False
                break
            self._queued.append(command)
            self._bytes += command.size_bytes
        return accepted

    def start_next(self) -> TerminalCommand | None:
        if self._inflight is None and self._queued:
            first = self._queued.popleft()
            if first.method == "hpcWrite" and isinstance(first.arg, str):
                chunks = [first.arg]
                seq = first.seq
                byte_count = first.size_bytes
                char_count = len(first.arg)
                while self._queued:
                    following = self._queued[0]
                    if (following.method != "hpcWrite"
                            or not isinstance(following.arg, str)
                            or char_count + len(following.arg) > FRAGMENT_WRITE_CHARS):
                        break
                    following = self._queued.popleft()
                    chunks.append(following.arg)
                    seq = following.seq
                    char_count += len(following.arg)
                    byte_count += following.size_bytes
                combined = "".join(chunks)
                self._inflight = TerminalCommand(seq, "hpcWrite", combined)
                self._bytes += self._inflight.size_bytes - byte_count
            else:
                self._inflight = first
            self._inflight_retries = 0
        return self._inflight

    def acknowledge(self, seq: object) -> bool:
        if self._inflight is None or type(seq) is not int or seq != self._inflight.seq:
            return False
        was_notice = self._inflight.arg == OUTPUT_LIMIT_NOTICE
        self._bytes -= self._inflight.size_bytes
        self._inflight = None
        self._inflight_retries = 0
        if was_notice:
            self._overflow_notice_queued = False
        return True

    def retry(self, seq: object) -> tuple[TerminalCommand | None, bool]:
        """Return (same command to resend, exhausted) for an ACK timeout."""
        if self._inflight is None or seq != self._inflight.seq:
            return None, False
        if (self._inflight.method in RETRYABLE_METHODS
                and self._inflight_retries < MAX_ACK_RETRIES):
            self._inflight_retries += 1
            return self._inflight, False
        self._bytes -= self._inflight.size_bytes
        self._inflight = None
        self._inflight_retries = 0
        return None, True

    def reset(self) -> None:
        self._queued.clear()
        self._inflight = None
        self._inflight_retries = 0
        self._bytes = 0
        self._overflow_notice_queued = False

    def report_output_loss(self) -> None:
        """Replace stale queued output with one visible loss notice."""
        if self._overflow_notice_queued:
            return
        while self._queued:
            self._bytes -= self._queued.pop().size_bytes
        notice = self._new_command("hpcWrite", OUTPUT_LIMIT_NOTICE)
        if (self.queued_entries < MAX_QUEUE_ENTRIES
                and self._bytes + notice.size_bytes <= MAX_QUEUE_BYTES):
            self._queued.append(notice)
            self._bytes += notice.size_bytes
            self._overflow_notice_queued = True

    def _new_command(self, method: str, arg: object) -> TerminalCommand:
        self._next_seq += 1
        return TerminalCommand(self._next_seq, method, arg)

    @staticmethod
    def _values(method: str, arg: object) -> Iterator[object]:
        if method == "hpcWrite" and isinstance(arg, str):
            for offset in range(0, len(arg), FRAGMENT_WRITE_CHARS):
                yield arg[offset:offset + FRAGMENT_WRITE_CHARS]
            return
        yield arg

