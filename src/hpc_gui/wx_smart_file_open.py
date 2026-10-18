"""Shared Smart Open chooser used by local and TRUBA wx file panels."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tempfile
import time
from pathlib import Path

from hpc_gui.core.i18n import t
from hpc_gui.services.file_open import (
    LARGE_REMOTE_THRESHOLD,
    detect_file_type,
    remember_smart_open,
    smart_open_preferences,
)

_TEMP_ROOT: tempfile.TemporaryDirectory | None = None


def _labels(file_type, has_editor: bool) -> list[str]:
    labels = [t("file_open.windows_default")]
    if has_editor and file_type.editable:
        labels.append(t("file_open.internal_editor"))
    return labels


def choose_smart_open(wx, parent, *, name: str, size: int, prefix: bytes = b"", has_editor: bool = False):
    """Return selected action, or None when the user cancels."""
    file_type = detect_file_type(name, prefix)
    choices = _labels(file_type, has_editor)
    dlg = wx.Dialog(parent, title=t("file_open.title"))
    root = wx.BoxSizer(wx.VERTICAL)
    info = wx.StaticText(
        dlg,
        label=t("file_open.file_details").format(name=Path(name).name, size=f"{size:,}", kind=file_type.category.upper()),
    )
    root.Add(info, 0, wx.ALL | wx.EXPAND, 12)
    radio = wx.RadioBox(dlg, label=t("file_open.choose"), choices=choices, majorDimension=1)
    radio.SetSelection(0)
    root.Add(radio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)
    remember = wx.CheckBox(dlg, label=t("file_open.remember"))
    root.Add(remember, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    buttons = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
    dlg.SetSizerAndFit(root)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        index = radio.GetSelection()
        action = "system" if index == 0 else "editor" if choices[index] == t("file_open.internal_editor") else None
        if action and remember.GetValue() and file_type.extension:
            remember_smart_open(file_type.extension, action)
        return action
    finally:
        dlg.Destroy()


def open_local_file(wx, parent, path: str | Path, open_editor=None) -> None:
    target = Path(path).expanduser().resolve()
    if target.is_dir():
        return
    try:
        size = target.stat().st_size
        prefix = _read_prefix(target)
    except OSError as error:
        wx.MessageBox(str(error), t("file_open.title"), wx.OK | wx.ICON_ERROR, parent)
        return
    file_type = detect_file_type(target.name, prefix)
    preference = smart_open_preferences().get(file_type.extension)
    if file_type.category == "text" and open_editor:
        open_editor(str(target))
        return
    if preference == "system" and not file_type.executable:
        _open_system(wx, parent, target)
        return
    if preference == "editor" and file_type.editable and open_editor:
        open_editor(str(target))
        return
    action = choose_smart_open(
        wx, parent, name=target.name, size=size,
        prefix=prefix, has_editor=bool(open_editor),
    )
    if action == "editor" and open_editor:
        open_editor(str(target))
    elif action == "system":
        if file_type.executable and wx.MessageBox(
            t("file_open.executable_confirm"), t("file_open.title"),
            wx.YES_NO | wx.ICON_WARNING, parent,
        ) != wx.YES:
            return
        _open_system(wx, parent, target)


def _open_system(wx, parent, target: Path) -> None:
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(target))
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(target)])
    except (OSError, AttributeError) as error:
        wx.MessageBox(t("file_open.default_failed").format(error=error), t("file_open.title"), wx.OK | wx.ICON_ERROR, parent)


def _read_prefix(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read(8192)


def remote_temp_path(name: str) -> Path:
    """Create a unique, app-managed file for an explicitly requested external open."""
    global _TEMP_ROOT
    if _TEMP_ROOT is None:
        _TEMP_ROOT = tempfile.TemporaryDirectory(prefix="hpc-smart-open-")
    suffix = Path(name).suffix[:20]
    fd, target = tempfile.mkstemp(prefix="open-", suffix=suffix, dir=_TEMP_ROOT.name)
    os.close(fd)
    return Path(target)


def needs_large_file_confirmation(size: int) -> bool:
    return int(size or 0) >= LARGE_REMOTE_THRESHOLD


def open_remote_with_system(wx, parent, remote_path: str, size: int, download) -> None:
    """Download an explicitly selected remote file to a unique temp file."""
    if needs_large_file_confirmation(size):
        answer = wx.MessageBox(
            t("file_open.large_confirm").format(size=f"{size:,}"),
            t("file_open.title"), wx.YES_NO | wx.ICON_QUESTION, parent,
        )
        if answer != wx.YES:
            return
    target = remote_temp_path(remote_path)
    progress = wx.ProgressDialog(
        t("file_open.title"), t("file_open.preparing"), maximum=100,
        parent=parent, style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE,
    )
    state = {"bytes": 0, "total": max(0, int(size or 0)), "error": None, "done": False}
    cancelled = threading.Event()

    def report(done: int, total: int) -> bool:
        state["bytes"] = int(done)
        state["total"] = max(0, int(total or 0))
        return not cancelled.is_set()

    def worker() -> None:
        try:
            download(remote_path, str(target), report)
        except Exception as error:
            state["error"] = error
        finally:
            state["done"] = True

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        while not state["done"]:
            total = state["total"]
            done = state["bytes"]
            percent = min(99, int(done * 100 / total)) if total else 0
            keep_going, _skip = progress.Update(percent, t("file_open.progress").format(done=f"{done:,}", total=f"{total:,}"))
            if not keep_going:
                cancelled.set()
            wx.YieldIfNeeded()
            time.sleep(0.04)
        thread.join()
    finally:
        progress.Destroy()
    if cancelled.is_set():
        target.unlink(missing_ok=True)
        wx.MessageBox(t("file_open.cancelled"), t("file_open.title"), wx.OK | wx.ICON_INFORMATION, parent)
        return
    if state["error"]:
        target.unlink(missing_ok=True)
        wx.MessageBox(t("file_open.download_failed").format(error=state['error']), t("file_open.title"), wx.OK | wx.ICON_ERROR, parent)
        return
    try:
        actual_size = target.stat().st_size
    except OSError as error:
        target.unlink(missing_ok=True)
        wx.MessageBox(t("file_open.download_failed").format(error=error), t("file_open.title"), wx.OK | wx.ICON_ERROR, parent)
        return
    if actual_size != int(size or 0):
        target.unlink(missing_ok=True)
        wx.MessageBox(
            t("file_open.size_mismatch").format(expected=f"{size:,}", actual=f"{actual_size:,}"),
            t("file_open.title"), wx.OK | wx.ICON_ERROR, parent,
        )
        return
    if detect_file_type(remote_path).executable and wx.MessageBox(
        t("file_open.executable_confirm"), t("file_open.title"),
        wx.YES_NO | wx.ICON_WARNING, parent,
    ) != wx.YES:
        target.unlink(missing_ok=True)
        return
    _open_system(wx, parent, target)
