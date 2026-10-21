"""Find/replace leaf for the wx editor.

Pure operations on explicitly passed editor/find controls; never creates
wx frames or imports the editor facade or document leaves.
"""

from __future__ import annotations


def find_query(find_in, chk_match_case) -> tuple[str, bool]:
    """Current query + case sensitivity."""
    try:
        query = find_in.GetValue()
    except Exception:
        return "", True
    try:
        match_case = bool(chk_match_case.GetValue())
    except Exception:
        match_case = True
    return query or "", match_case


def set_find_status(status, key: str, fallback: str) -> None:
    from hpc_gui.core.i18n import t

    try:
        label = t(key)
        if label == f"[{key}]":
            label = fallback
        status.SetLabel(label)
    except Exception:
        pass


def find_next(editor, find_in, chk_match_case, status) -> bool:
    """Find-next with wrap readback and visible diagnostics."""
    query, match_case = find_query(find_in, chk_match_case)
    if not query:
        set_find_status(status, "editor.find_empty", "Enter text to find.")
        return False
    try:
        text = editor.GetValue()
        _sel_start, sel_end = editor.GetSelection()
        start = sel_end if sel_end is not None else 0
        haystack, needle = (text, query) if match_case else (text.lower(), query.lower())
        idx = haystack.find(needle, start)
        wrapped = False
        if idx < 0:
            idx = haystack.find(needle, 0)
            wrapped = idx >= 0
        if idx < 0:
            set_find_status(status, "editor.find_no_match", "No match found.")
            return False
        editor.SetSelection(idx, idx + len(query))
        editor.ShowPosition(idx)
        try:
            editor.SetFocus()
        except Exception:
            pass
        if wrapped:
            set_find_status(status, "editor.find_wrapped_top", "Wrapped to top.")
        else:
            try:
                status.SetLabel("")
            except Exception:
                pass
        return True
    except Exception:
        return False


def find_previous(editor, find_in, chk_match_case, status) -> bool:
    """Find-previous with wrap readback."""
    query, match_case = find_query(find_in, chk_match_case)
    if not query:
        set_find_status(status, "editor.find_empty", "Enter text to find.")
        return False
    try:
        text = editor.GetValue()
        sel_start, _sel_end = editor.GetSelection()
        start = sel_start if sel_start is not None else len(text)
        haystack, needle = (text, query) if match_case else (text.lower(), query.lower())
        idx = haystack.rfind(needle, 0, start)
        wrapped = False
        if idx < 0:
            idx = haystack.rfind(needle)
            wrapped = idx >= 0
        if idx < 0:
            set_find_status(status, "editor.find_no_match", "No match found.")
            return False
        editor.SetSelection(idx, idx + len(query))
        editor.ShowPosition(idx)
        try:
            editor.SetFocus()
        except Exception:
            pass
        if wrapped:
            set_find_status(status, "editor.find_wrapped_bottom", "Wrapped to bottom.")
        else:
            try:
                status.SetLabel("")
            except Exception:
                pass
        return True
    except Exception:
        return False


def replace_current(editor, model, find_in, replace_in, chk_match_case, status, update_dirty_marker) -> bool:
    """Replace current selection when it matches, else advance first."""
    query, match_case = find_query(find_in, chk_match_case)
    if not query:
        set_find_status(status, "editor.find_empty", "Enter text to find.")
        return False
    try:
        replacement = replace_in.GetValue()
    except Exception:
        replacement = ""
    try:
        sel_start, sel_end = editor.GetSelection()
        selected = editor.GetStringSelection()
        matches = (selected == query) if match_case else (selected.lower() == query.lower())
        if not matches:
            if not find_next(editor, find_in, chk_match_case, status):
                return False
            sel_start, sel_end = editor.GetSelection()
            selected = editor.GetStringSelection()
            matches = (selected == query) if match_case else (selected.lower() == query.lower())
            if not matches:
                return False
        editor.Replace(sel_start, sel_end, replacement)
        try:
            model.controller.update_content(editor.GetValue())
            update_dirty_marker()
        except Exception:
            pass
        return True
    except Exception:
        return False


def replace_all(editor, model, find_in, replace_in, chk_match_case, status, update_dirty_marker) -> int:
    """Replace all occurrences and return the count."""
    query, match_case = find_query(find_in, chk_match_case)
    if not query:
        set_find_status(status, "editor.find_empty", "Enter text to find.")
        return 0
    try:
        replacement = replace_in.GetValue()
    except Exception:
        replacement = ""
    try:
        text = editor.GetValue()
        if match_case:
            count = text.count(query)
            if count <= 0:
                set_find_status(status, "editor.find_no_match", "No match found.")
                return 0
            editor.ChangeValue(text.replace(query, replacement))
        else:
            lowered, needle = text.lower(), query.lower()
            count = lowered.count(needle)
            if count <= 0:
                set_find_status(status, "editor.find_no_match", "No match found.")
                return 0
            parts: list[str] = []
            cursor = 0
            while True:
                idx = lowered.find(needle, cursor)
                if idx < 0:
                    parts.append(text[cursor:])
                    break
                parts.append(text[cursor:idx])
                parts.append(replacement)
                cursor = idx + len(query)
            editor.ChangeValue("".join(parts))
        try:
            model.controller.update_content(editor.GetValue())
            update_dirty_marker()
        except Exception:
            pass
        return count
    except Exception:
        return 0


__all__ = [
    "find_next",
    "find_previous",
    "find_query",
    "replace_all",
    "replace_current",
    "set_find_status",
]
