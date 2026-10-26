"""Persist the resizable Journal Studio panel and result-tab state."""

from __future__ import annotations

from math import isfinite

from hpc_gui.config.storage import load_config, save_config


_LAYOUT_KEY = "journal_studio_layout"
_RESULT_TAB_COUNT = 4


def _valid_ratio(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        ratio = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return ratio if isfinite(ratio) and 0.05 <= ratio <= 0.95 else None


def _valid_tab(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        tab = int(value)
    except (TypeError, ValueError):
        return None
    return tab if 0 <= tab < _RESULT_TAB_COUNT else None


def load_journal_studio_layout() -> dict[str, float | int]:
    """Load only sane, version-neutral split ratios and result-tab indexes."""
    try:
        config = load_config()
    except Exception:
        return {}
    if not isinstance(config, dict):
        return {}
    ui = config.get("ui", {})
    if not isinstance(ui, dict):
        return {}
    raw = ui.get(_LAYOUT_KEY)
    if not isinstance(raw, dict):
        return {}
    state: dict[str, float | int] = {}
    for key in ("structure_ratio", "library_ratio"):
        ratio = _valid_ratio(raw.get(key))
        if ratio is not None:
            state[key] = ratio
    tab = _valid_tab(raw.get("results_tab"))
    if tab is not None:
        state["results_tab"] = tab
    return state


def save_journal_studio_layout(state: dict[str, object]) -> bool:
    """Store sanitized layout state without replacing unrelated preferences."""
    clean: dict[str, float | int] = {}
    for key in ("structure_ratio", "library_ratio"):
        ratio = _valid_ratio(state.get(key))
        if ratio is not None:
            clean[key] = ratio
    tab = _valid_tab(state.get("results_tab"))
    if tab is not None:
        clean["results_tab"] = tab
    if not clean:
        return False
    try:
        config = load_config()
        if not isinstance(config, dict):
            return False
        ui = config.get("ui", {})
        if not isinstance(ui, dict):
            ui = {}
        ui[_LAYOUT_KEY] = clean
        config["ui"] = ui
        save_config(config)
    except Exception:
        return False
    return True


def bind_journal_studio_layout(editor, work_split, results, structure_split=None) -> None:
    """Restore and save splitter proportions and selected diagnostics tab."""
    wx = editor.wx
    state = load_journal_studio_layout()
    restored = False
    restore_attempts = 0

    def set_sash_ratio(splitter, key: str, minimum_left: int, minimum_right: int) -> bool:
        ratio = state.get(key)
        width = int(splitter.GetClientSize().width)
        if ratio is None or width <= minimum_left + minimum_right:
            return False
        position = max(minimum_left, min(width - minimum_right, round(width * ratio)))
        splitter.SetSashPosition(position)
        return True

    def restore() -> None:
        nonlocal restored, restore_attempts
        if restored:
            return
        width = int(work_split.GetClientSize().width)
        if width <= 0:
            restore_attempts += 1
            if restore_attempts < 10:
                wx.CallLater(100, restore)
            return
        if structure_split is not None:
            set_sash_ratio(structure_split, "structure_ratio", 140, 300)
        set_sash_ratio(work_split, "library_ratio", 300, 220)
        tab = state.get("results_tab")
        if isinstance(tab, int) and tab < results.GetPageCount():
            results.SetSelection(tab)
        restored = True

    def ratio_for(splitter) -> float | None:
        width = int(splitter.GetClientSize().width)
        if width <= 0:
            return None
        position = int(splitter.GetSashPosition())
        if position < 0:
            position = width + position
        return position / width

    def persist(_event=None) -> None:
        current = load_journal_studio_layout()
        if structure_split is not None:
            ratio = ratio_for(structure_split)
            if ratio is not None:
                current["structure_ratio"] = ratio
        ratio = ratio_for(work_split)
        if ratio is not None:
            current["library_ratio"] = ratio
        tab = results.GetSelection()
        if tab >= 0:
            current["results_tab"] = tab
        save_journal_studio_layout(current)
        if _event is not None:
            _event.Skip()

    def on_size(event) -> None:
        restore()
        event.Skip()

    work_split.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, persist)
    if structure_split is not None:
        structure_split.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, persist)
    results.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, persist)
    editor.page.Bind(wx.EVT_SIZE, on_size)
    wx.CallAfter(restore)


__all__ = ["bind_journal_studio_layout", "load_journal_studio_layout", "save_journal_studio_layout"]
