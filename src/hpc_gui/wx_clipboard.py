"""Small retrying helpers for native wx clipboard operations."""

from __future__ import annotations

import time


def write_text(wx_module, value: str, *, attempts: int = 8, delay: float = 0.015) -> bool:
    """Write text while tolerating short native clipboard locks."""
    for attempt in range(max(1, attempts)):
        opened = False
        suppress = wx_module.LogNull()
        try:
            opened = bool(wx_module.TheClipboard.Open())
            if opened and wx_module.TheClipboard.SetData(wx_module.TextDataObject(value)):
                return True
        except Exception:
            pass
        finally:
            if opened:
                try:
                    wx_module.TheClipboard.Close()
                except Exception:
                    pass
            del suppress
        if attempt + 1 < max(1, attempts):
            time.sleep(max(0.0, delay))
    return False
