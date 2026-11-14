"""Find and replace controls and behavior for the wx editor."""

from __future__ import annotations


class WxEditorSearch:
    """Own the find/replace bar, matching, replacement, and its status text."""

    def __init__(self, panel, root, wx, translate):
        self.wx = wx
        self.t = translate
        self.editor = None
        self.status = None
        self.model = None
        self.update_dirty = None

        self.find_bar = wx.WrapSizer(wx.HORIZONTAL)
        self.find_label = wx.StaticText(panel, label=translate("editor.find_label"))
        self.find_in = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._set_hint(self.find_in, "editor.find_placeholder")
        self.replace_label = wx.StaticText(panel, label=translate("editor.replace_label"))
        self.replace_in = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._set_hint(self.replace_in, "editor.replace_placeholder")
        self.btn_find_next = wx.Button(panel, label=translate("editor.find_next"))
        self.btn_find_prev = wx.Button(panel, label=translate("editor.find_previous"))
        self.chk_match_case = wx.CheckBox(panel, label=translate("editor.match_case"))
        self.btn_replace = wx.Button(panel, label=translate("editor.replace"))
        self.btn_replace_all = wx.Button(panel, label=translate("editor.replace_all"))
        for item in self.widgets:
            try:
                self.find_bar.Add(item, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
            except Exception:
                pass
        try:
            self.find_in.SetMinSize(wx.Size(140, -1))
            self.replace_in.SetMinSize(wx.Size(140, -1))
        except Exception:
            pass
        root.Add(self.find_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)

    @property
    def widgets(self):
        return (
            self.find_label, self.find_in, self.replace_label, self.replace_in,
            self.btn_find_next, self.btn_find_prev, self.chk_match_case,
            self.btn_replace, self.btn_replace_all,
        )

    def _set_hint(self, widget, key):
        try:
            widget.SetHint(self.t(key))
        except Exception:
            pass

    def bind(self, editor, status, model, update_dirty):
        self.editor = editor
        self.status = status
        self.model = model
        self.update_dirty = update_dirty
        self.btn_find_next.Bind(self.wx.EVT_BUTTON, lambda _event: self.find_next())
        self.btn_find_prev.Bind(self.wx.EVT_BUTTON, lambda _event: self.find_previous())
        self.btn_replace.Bind(self.wx.EVT_BUTTON, lambda _event: self.replace_current())
        self.btn_replace_all.Bind(self.wx.EVT_BUTTON, lambda _event: self.replace_all())
        self.find_in.Bind(self.wx.EVT_TEXT_ENTER, lambda _event: self.find_next())
        self.replace_in.Bind(self.wx.EVT_TEXT_ENTER, lambda _event: self.replace_current())

    def control_map(self):
        return {
            "find_in": self.find_in, "replace_in": self.replace_in,
            "find_next": self.btn_find_next, "find_prev": self.btn_find_prev,
            "match_case": self.chk_match_case, "replace": self.btn_replace,
            "replace_all": self.btn_replace_all, "find_label": self.find_label,
            "replace_label": self.replace_label,
        }

    def _query(self):
        try:
            query = self.find_in.GetValue()
        except Exception:
            return "", True
        try:
            match_case = bool(self.chk_match_case.GetValue())
        except Exception:
            match_case = True
        return query or "", match_case

    def set_status(self, key: str, fallback: str) -> None:
        try:
            label = self.t(key)
            if label == f"[{key}]":
                label = fallback
            self.status.SetLabel(label)
        except Exception:
            pass

    def find_next(self) -> bool:
        """Find next with wrap readback and optional case-insensitive match."""
        query, match_case = self._query()
        if not query:
            self.set_status("editor.find_empty", "Enter text to find.")
            return False
        try:
            text = self.editor.GetValue()
            _sel_start, sel_end = self.editor.GetSelection()
            start = sel_end if sel_end is not None else 0
            haystack, needle = (text, query) if match_case else (text.lower(), query.lower())
            idx = haystack.find(needle, start)
            wrapped = False
            if idx < 0:
                idx = haystack.find(needle, 0)
                wrapped = idx >= 0
            if idx < 0:
                self.set_status("editor.find_no_match", "No match found.")
                return False
            self.editor.SetSelection(idx, idx + len(query))
            self.editor.ShowPosition(idx)
            try:
                self.editor.SetFocus()
            except Exception:
                pass
            if wrapped:
                self.set_status("editor.find_wrapped_top", "Wrapped to top.")
            else:
                self.status.SetLabel("")
            return True
        except Exception:
            return False

    def find_previous(self) -> bool:
        """Find previous with wrap readback and optional case-insensitive match."""
        query, match_case = self._query()
        if not query:
            self.set_status("editor.find_empty", "Enter text to find.")
            return False
        try:
            text = self.editor.GetValue()
            sel_start, _sel_end = self.editor.GetSelection()
            start = sel_start if sel_start is not None else len(text)
            haystack, needle = (text, query) if match_case else (text.lower(), query.lower())
            idx = haystack.rfind(needle, 0, start)
            wrapped = False
            if idx < 0:
                idx = haystack.rfind(needle)
                wrapped = idx >= 0
            if idx < 0:
                self.set_status("editor.find_no_match", "No match found.")
                return False
            self.editor.SetSelection(idx, idx + len(query))
            self.editor.ShowPosition(idx)
            try:
                self.editor.SetFocus()
            except Exception:
                pass
            if wrapped:
                self.set_status("editor.find_wrapped_bottom", "Wrapped to bottom.")
            else:
                self.status.SetLabel("")
            return True
        except Exception:
            return False

    def replace_current(self) -> bool:
        """Replace the selected match or first advance to the next match."""
        query, match_case = self._query()
        if not query:
            self.set_status("editor.find_empty", "Enter text to find.")
            return False
        try:
            replacement = self.replace_in.GetValue()
        except Exception:
            replacement = ""
        try:
            sel_start, sel_end = self.editor.GetSelection()
            selected = self.editor.GetStringSelection()
            matches = selected == query if match_case else selected.lower() == query.lower()
            if not matches:
                if not self.find_next():
                    return False
                sel_start, sel_end = self.editor.GetSelection()
                selected = self.editor.GetStringSelection()
                matches = selected == query if match_case else selected.lower() == query.lower()
                if not matches:
                    return False
            self.editor.Replace(sel_start, sel_end, replacement)
            self._update_model_content()
            return True
        except Exception:
            return False

    def replace_all(self) -> int:
        """Replace every occurrence and return the replacement count."""
        query, match_case = self._query()
        if not query:
            self.set_status("editor.find_empty", "Enter text to find.")
            return 0
        try:
            replacement = self.replace_in.GetValue()
        except Exception:
            replacement = ""
        try:
            text = self.editor.GetValue()
            if match_case:
                count = text.count(query)
                if count <= 0:
                    self.set_status("editor.find_no_match", "No match found.")
                    return 0
                self.editor.ChangeValue(text.replace(query, replacement))
            else:
                lowered, needle = text.lower(), query.lower()
                count = lowered.count(needle)
                if count <= 0:
                    self.set_status("editor.find_no_match", "No match found.")
                    return 0
                parts: list[str] = []
                cursor = 0
                while True:
                    idx = lowered.find(needle, cursor)
                    if idx < 0:
                        parts.append(text[cursor:])
                        break
                    parts.extend((text[cursor:idx], replacement))
                    cursor = idx + len(query)
                self.editor.ChangeValue("".join(parts))
            self._update_model_content()
            return count
        except Exception:
            return 0

    def _update_model_content(self):
        try:
            self.model.controller.update_content(self.editor.GetValue())
            self.update_dirty()
        except Exception:
            pass
