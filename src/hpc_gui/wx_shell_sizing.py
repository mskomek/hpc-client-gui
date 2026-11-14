"""Window sizing helpers for the wx shell.

The shell asks for 1440x900 and a 1280x760 minimum, but a 1024x768 desktop
(the Kole Ubuntu guest, small laptops) cannot honour either, and the window is
then clipped: the status bar falls off the screen and the layout squeezes the
chrome. These helpers fit both numbers into the display work area while keeping
a usability floor whenever the display is large enough.
"""

from __future__ import annotations

from typing import Tuple

PREFERRED_SIZE: Tuple[int, int] = (1440, 900)
MINIMUM_SIZE: Tuple[int, int] = (1280, 760)
FLOOR_SIZE: Tuple[int, int] = (900, 600)


def clamp_size(
    preferred: Tuple[int, int],
    available: Tuple[int, int],
    floor: Tuple[int, int] = FLOOR_SIZE,
) -> Tuple[int, int]:
    """Fit the window to the work area; use the floor only when it fits."""
    preferred_w, preferred_h = preferred
    available_w, available_h = available
    floor_w, floor_h = floor
    # The usability floor applies only when there is enough display space.
    # Never request a window wider or taller than the available work area.
    width = min(max(floor_w, int(preferred_w)), max(1, int(available_w)))
    height = min(max(floor_h, int(preferred_h)), max(1, int(available_h)))
    return width, height


def display_available(wx) -> Tuple[int, int]:
    """Client area of the primary display, or the preferred size as fallback."""
    try:
        area = wx.Display(0).GetClientArea()
        width, height = int(area.width), int(area.height)
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass
    return PREFERRED_SIZE


def shell_sizes(wx) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Return (default_size, minimum_size) fitted to this display."""
    available = display_available(wx)
    return clamp_size(PREFERRED_SIZE, available), clamp_size(MINIMUM_SIZE, available)


__all__ = [
    "FLOOR_SIZE",
    "MINIMUM_SIZE",
    "PREFERRED_SIZE",
    "clamp_size",
    "display_available",
    "shell_sizes",
]
