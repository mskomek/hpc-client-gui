"""Conflict and overwrite prompts used by the wx editor save flow."""

from __future__ import annotations

import os

from hpc_gui.wx_editor_file_safety import disk_baseline


class EditorSavePrompts:
    def __init__(self, wx, host, translate, baseline_by_path):
        self.wx = wx
        self.host = host
        self.t = translate
        self.baseline_by_path = baseline_by_path

    def _ask_overwrite(self, title_key: str, message: str) -> bool:
        try:
            title = self.t(title_key)
            if title == f"[{title_key}]":
                title = title_key
            return self.wx.MessageBox(
                message, title, self.wx.YES_NO | self.wx.ICON_WARNING, self.host
            ) == self.wx.ID_YES
        except Exception:
            return False

    def confirm_save_as(self, target: str, is_local: bool, target_exists) -> bool:
        """Ask before replacing an existing Save As target."""
        exists = False
        if is_local:
            try:
                exists = os.path.exists(target)
            except Exception:
                exists = False
        elif callable(target_exists):
            try:
                exists = bool(target_exists(target))
            except Exception:
                exists = False
        if not exists:
            return True
        message = self.t("editor.save_as_exists").format(path=target)
        return self._ask_overwrite("editor.save_as_title", message)

    def confirm_external_change(self, path: str, saved_content: str, new_content: str) -> bool:
        """Detect local edits/deletion since open and confirm any overwrite."""
        baseline = self.baseline_by_path.get(path, disk_baseline(path))
        if path not in self.baseline_by_path:
            self.baseline_by_path[path] = baseline
            return True
        current = disk_baseline(path)
        if current == baseline:
            return True
        if current is None:
            if baseline is not None and saved_content:
                message = self.t("editor.external_deleted_message").format(path=path)
                return self._ask_overwrite("editor.external_change_title", message)
            return True
        if baseline is None:
            message = self.t("editor.save_as_exists").format(path=path)
            return self._ask_overwrite("editor.save_as_title", message)
        try:
            if os.path.getsize(path) > 10 * 1024 * 1024:
                return True
            disk = open(path, encoding="utf-8").read()
        except (OSError, UnicodeError, ValueError):
            return True
        if disk in (saved_content, new_content):
            return True
        message = self.t("editor.external_change_message").format(path=path)
        return self._ask_overwrite("editor.external_change_title", message)
