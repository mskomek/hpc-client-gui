"""Read individual keys from an interactive local terminal."""

from __future__ import annotations

import os
import select
import sys
import time
from contextlib import contextmanager
from typing import Callable, Iterator


_WINDOWS_EXTENDED_KEYS = {
    "H": "\x1b[A",
    "P": "\x1b[B",
    "M": "\x1b[C",
    "K": "\x1b[D",
    "G": "\x1b[H",
    "O": "\x1b[F",
    "R": "\x1b[2~",
    "S": "\x1b[3~",
    "I": "\x1b[5~",
    "Q": "\x1b[6~",
}


def normalize_terminal_key(key: str) -> str:
    """Translate local console Enter and Backspace to terminal key bytes."""
    if key in ("\r", "\n"):
        return "\r"
    if key in ("\b", "\x7f"):
        return "\x7f"
    return key


def _read_windows_key() -> str | None:
    import msvcrt

    while True:
        if not msvcrt.kbhit():
            time.sleep(0.05)
            return None
        try:
            key = msvcrt.getwch()
        except KeyboardInterrupt:
            return "\x03"
        if key in ("\x00", "\xe0"):
            key = _WINDOWS_EXTENDED_KEYS.get(msvcrt.getwch(), "")
            if not key:
                continue
            return key
        if 0xD800 <= ord(key) <= 0xDBFF:
            low = msvcrt.getwch()
            if low and 0xDC00 <= ord(low) <= 0xDFFF:
                codepoint = 0x10000 + ((ord(key) - 0xD800) << 10) + ord(low) - 0xDC00
                key = chr(codepoint)
        return normalize_terminal_key(key)


@contextmanager
def terminal_key_reader() -> Iterator[Callable[[], str | None]]:
    """Yield a nonblocking one-key reader, enabling raw mode on POSIX."""
    if os.name == "nt":
        yield _read_windows_key
        return

    import termios
    import tty

    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    tty.setraw(descriptor)
    try:
        def read_key() -> str | None:
            ready, _, _ = select.select([descriptor], [], [], 0.1)
            if not ready:
                return None
            return normalize_terminal_key(sys.stdin.read(1))

        yield read_key
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
