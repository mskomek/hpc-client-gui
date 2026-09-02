"""Toolkit-neutral window geometry recovery helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def intersects(self, other: "Rect") -> bool:
        return self.x < other.x + other.width and other.x < self.x + self.width and self.y < other.y + other.height and other.y < self.y + self.height


def recover_geometry(saved: Rect | None, work_areas: tuple[Rect, ...], *, default_size: tuple[int, int] = (900, 650)) -> Rect:
    """Keep a saved window visible on one of the current display work areas."""
    if not work_areas:
        return Rect(0, 0, *default_size)
    valid = saved if saved and saved.width > 0 and saved.height > 0 else Rect(0, 0, *default_size)
    area = next((item for item in work_areas if valid.intersects(item)), work_areas[0])
    width = min(valid.width, area.width)
    height = min(valid.height, area.height)
    x = min(max(valid.x, area.x), area.x + area.width - width)
    y = min(max(valid.y, area.y), area.y + area.height - height)
    return Rect(x, y, width, height)


LAYOUT_ACCEPTANCE_MATRIX = (
    (1280, 720, 100), (1366, 768, 100), (1920, 1080, 150),
    (2560, 1440, 200), (3840, 2160, 200),
)
