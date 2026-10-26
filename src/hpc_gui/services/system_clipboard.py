"""Small adapter for writing text to a desktop clipboard safely."""

from __future__ import annotations

import time
from collections.abc import Callable


def set_text(
    clipboard,
    data_factory: Callable[[str], object],
    value: str,
    *,
    attempts: int = 20,
    retry_delay: float = 0.025,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Write text while tolerating a clipboard briefly held by another app."""
    retry_count = max(1, int(attempts))
    for attempt in range(retry_count):
        opened = False
        try:
            opened = bool(clipboard.Open())
            if opened and clipboard.SetData(data_factory(str(value))):
                return True
        except Exception:
            pass
        finally:
            if opened:
                try:
                    clipboard.Close()
                except Exception:
                    pass
        if attempt + 1 < retry_count:
            sleep(max(0.0, float(retry_delay)))
    return False


def get_text(
    clipboard,
    data_factory: Callable[[], object],
    *,
    attempts: int = 20,
    retry_delay: float = 0.025,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Read clipboard text while tolerating a clipboard briefly held by another app."""
    retry_count = max(1, int(attempts))
    for attempt in range(retry_count):
        opened = False
        try:
            opened = bool(clipboard.Open())
            if opened:
                data = data_factory()
                if clipboard.GetData(data):
                    return str(data.GetText())
        except Exception:
            pass
        finally:
            if opened:
                try:
                    clipboard.Close()
                except Exception:
                    pass
        if attempt + 1 < retry_count:
            sleep(max(0.0, float(retry_delay)))
    return None


__all__ = ["get_text", "set_text"]
