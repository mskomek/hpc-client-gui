"""Clipboard reads that tolerate a transiently locked Windows clipboard.

Any other process (an editor, a terminal, a clipboard manager) can hold the
Win32 clipboard for a few milliseconds.  ``wx.TheClipboard.Open()`` then fails
and wx pops a modal "OpenClipboard Failed" dialog that blocks the test run, so
reads retry briefly with wx logging suppressed.
"""

from __future__ import annotations

import time

import wx


def read_clipboard_text(*, attempts: int = 20, delay: float = 0.05) -> str:
    """Return the clipboard text, retrying while the clipboard is locked."""
    last_error = "clipboard never opened"
    for _ in range(attempts):
        suppress = wx.LogNull()
        try:
            if wx.TheClipboard.Open():
                try:
                    data = wx.TextDataObject()
                    if wx.TheClipboard.GetData(data):
                        return data.GetText()
                    last_error = "clipboard held no text data"
                finally:
                    wx.TheClipboard.Close()
        finally:
            del suppress
        time.sleep(delay)
    raise AssertionError(f"could not read the clipboard: {last_error}")
