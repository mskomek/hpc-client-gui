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


def resolve_main_window_state(
    raw: object,
    work_areas: tuple[Rect, ...],
    *,
    default_size: tuple[int, int] = (1440, 900),
    tab_count: int | None = None,
) -> dict:
    """Resolve a persisted main-window record to a safe runtime state.

    Contract (HPC-W09-UISTATE-009..014):

    - ``None``/corrupt/foreign records (including legacy Qt geometry blobs,
      which never carry ``x/y/width/height`` ints) resolve to fresh defaults
      with ``maximized=False`` and ``selected_tab=None``.
    - Saved geometry is clamped into a visible work area via
      :func:`recover_geometry` (corrupt/out-of-range/off-screen recovery).
    - ``selected_tab`` is kept only when it names an existing notebook page;
      dialog geometry, column widths/order and splitter positions are
      intentionally **not** persisted by the wx shell (fresh defaults every
      launch) and therefore never appear here.
    """
    if not isinstance(raw, dict):
        return {
            "rect": Rect(0, 0, *default_size),
            "maximized": False,
            "selected_tab": None,
        }
    try:
        saved = Rect(int(raw["x"]), int(raw["y"]), int(raw["width"]), int(raw["height"]))
    except (KeyError, TypeError, ValueError):
        return {
            "rect": Rect(0, 0, *default_size),
            "maximized": False,
            "selected_tab": None,
        }
    if saved.width <= 0 or saved.height <= 0:
        saved = Rect(0, 0, *default_size)
    rect = recover_geometry(saved, work_areas, default_size=default_size)
    selected = raw.get("selected_tab", None)
    try:
        selected = int(selected) if selected is not None else None
    except (TypeError, ValueError):
        selected = None
    if selected is not None and tab_count is not None and not 0 <= selected < tab_count:
        selected = None
    return {"rect": rect, "maximized": bool(raw.get("maximized", False)), "selected_tab": selected}


def dispose_legacy_qt_geometry_blob(blob: object) -> str:
    """Disposition for legacy Qt geometry/state blobs (HPC-W09-UISTATE-015).

    Qt ``saveGeometry``/``saveState`` payloads (``QByteArray``, base64 text or
    Qt-keyed dicts) use a different binary format from wx geometry and must
    never be applied to wx windows. There is no Qt-blob ingestion path in the
    wx shell; any such blob resolves to this explicit ``ignored`` disposition
    and the caller falls back to fresh defaults.
    """
    kind = type(blob).__name__
    return (
        "ignored: legacy Qt geometry/state blob "
        f"(type={kind}) is not applied to wx windows; fresh defaults apply"
    )
