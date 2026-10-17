from __future__ import annotations

from typing import Any, Dict, Optional

from hpc_gui.config._storage_core import load_config, save_config

MAIN_WINDOW_STATE_KEY = "main_window"

def get_ui_pref_bool(key: str, default: bool = True) -> bool:
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    v = ui.get(key)
    if isinstance(v, bool):
        return v
    return default

def set_ui_pref_bool(key: str, value: bool) -> None:
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    ui[key] = bool(value)
    cfg["ui"] = ui
    save_config(cfg)

def get_main_window_state() -> Optional[Dict[str, Any]]:
    """Return the raw persisted wx main-window record, or ``None``.

    ``None`` covers absent state (fresh defaults), corrupt records (wrong
    types, non-positive sizes, non-dict ``ui`` section) and foreign blobs
    such as legacy Qt geometry payloads, which never drive wx geometry
    (HPC-W09-UISTATE-015). Never raises for malformed user data.
    """
    try:
        cfg = load_config()
    except Exception:
        return None
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        return None
    raw = ui.get(MAIN_WINDOW_STATE_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        x = int(raw["x"])
        y = int(raw["y"])
        width = int(raw["width"])
        height = int(raw["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    selected = raw.get("selected_tab", None)
    if selected is not None:
        try:
            selected = int(selected)
        except (TypeError, ValueError):
            selected = None
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "maximized": bool(raw.get("maximized", False)),
        "selected_tab": selected,
    }

def save_main_window_state(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    maximized: bool = False,
    selected_tab: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist the wx main-window layout record (HPC-W09-UISTATE-009..014).

    Raises ``ValueError`` for non-positive sizes or non-integer geometry so
    corrupt values can never be written; the shutdown hook treats this as
    best-effort and keeps the previous record on failure.
    """
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError(f"Refusing to persist non-positive window size {(width, height)}")
    record: Dict[str, Any] = {
        "x": int(x),
        "y": int(y),
        "width": width,
        "height": height,
        "maximized": bool(maximized),
    }
    if selected_tab is not None:
        record["selected_tab"] = int(selected_tab)
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    ui[MAIN_WINDOW_STATE_KEY] = record
    cfg["ui"] = ui
    save_config(cfg)
    return record

def clear_main_window_state() -> None:
    """Remove the persisted wx main-window record (fresh-defaults path)."""
    try:
        cfg = load_config()
    except Exception:
        return
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        return
    if MAIN_WINDOW_STATE_KEY in ui:
        del ui[MAIN_WINDOW_STATE_KEY]
        cfg["ui"] = ui
        try:
            save_config(cfg)
        except Exception:
            pass
