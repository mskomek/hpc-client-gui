"""Reusable wx Raw Command Viewer dialog for displaying raw scheduler output."""

from __future__ import annotations

from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.raw_command_result import RawCommandResult


_SOURCE_LABELS = {
    "scontrol": "Slurm Job Details",
    "sacct": "Slurm Accounting",
    "lssrv": "Cluster Server Status",
}


def show_raw_viewer(
    parent: Any,
    result: RawCommandResult,
    *,
    title: str = "",
    refresh_callback: Callable[[], RawCommandResult | None] | None = None,
    lifecycle: Any = None,
) -> Any:
    """Show a read-only raw command viewer dialog.

    The viewer is monospace, scrollable, and provides Copy, Select All,
    Refresh, and Close.  The command text is displayed but never executed.

    Parameters
    ----------
    parent : wx window
        Parent window for the dialog.
    result : RawCommandResult
        The raw command result to display.
    title : str
        Optional override for the dialog title.
    refresh_callback : callable, optional
        If provided, a Refresh button re-invokes this callback and updates
        the display with the new RawCommandResult.
    lifecycle : optional
        Application lifecycle manager for cleanup.
    """
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    dialog = wx.Dialog(
        parent,
        title=title or t("raw_viewer.title"),
        size=(720, 520),
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )

    closed = {"value": False}
    _refresh_in_flight = [False]

    root = wx.BoxSizer(wx.VERTICAL)

    # Source display
    source_label_text = _SOURCE_LABELS.get(result.source_id, result.source_id)
    if source_label_text:
        src_label = wx.StaticText(dialog, label=f"{t('raw_viewer.source')}: {source_label_text}")
        root.Add(src_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    # Command display
    cmd_label = wx.StaticText(dialog, label=f"{t('raw_viewer.command')}:")
    cmd_text = wx.TextCtrl(
        dialog,
        value=result.display_command,
        style=wx.TE_READONLY | wx.TE_MULTILINE,
    )
    cmd_text.SetMinSize(wx.Size(-1, 32))
    cmd_text.SetMaxSize(wx.Size(-1, 48))

    root.Add(cmd_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    root.Add(cmd_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # Exit code
    exit_label = wx.StaticText(
        dialog,
        label=f"{t('raw_viewer.exit_code')}: {result.exit_code}",
    )
    root.Add(exit_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # STDERR section (dynamically managed)
    _stderr_state = {"ctrl": None, "label": None}

    def _ensure_stderr(shown: bool = True):
        """Create or destroy the stderr section dynamically."""
        if shown and _stderr_state["ctrl"] is None:
            _stderr_state["label"] = wx.StaticText(dialog, label=t("raw_viewer.stderr"))
            _stderr_state["ctrl"] = wx.TextCtrl(
                dialog,
                value="",
                style=wx.TE_READONLY | wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2,
            )
            _stderr_state["ctrl"].SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
            # Insert before the button bar (last item)
            root.Insert(root.GetItemCount() - 1, _stderr_state["label"], 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
            root.Insert(root.GetItemCount() - 1, _stderr_state["ctrl"], 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        elif not shown and _stderr_state["ctrl"] is not None:
            try:
                idx_label = root.GetItemIndex(_stderr_state["label"])
                idx_ctrl = root.GetItemIndex(_stderr_state["ctrl"])
                if idx_ctrl >= 0:
                    root.Remove(idx_ctrl)
                if idx_label >= 0:
                    root.Remove(idx_label)
            except Exception:
                pass
            _stderr_state["ctrl"] = None
            _stderr_state["label"] = None

    # STDOUT section (always present)
    stdout_label = wx.StaticText(dialog, label=t("raw_viewer.stdout"))
    root.Add(stdout_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    stdout_text = wx.TextCtrl(
        dialog,
        value=result.stdout or "",
        style=wx.TE_READONLY | wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2,
    )
    stdout_text.SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
    root.Add(stdout_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    # Initialize stderr if needed
    if result.stderr:
        _ensure_stderr(True)
        _stderr_state["ctrl"].SetValue(result.stderr)

    # Button bar
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

    btn_copy = wx.Button(dialog, label=t("raw_viewer.copy"))
    btn_select_all = wx.Button(dialog, label=t("raw_viewer.select_all"))
    btn_refresh = wx.Button(dialog, label=t("raw_viewer.refresh"))
    btn_close = wx.Button(dialog, wx.ID_CLOSE, label=t("raw_viewer.close"))

    btn_sizer.Add(btn_copy, 0, wx.RIGHT, 4)
    btn_sizer.Add(btn_select_all, 0, wx.RIGHT, 4)
    if refresh_callback is not None:
        btn_sizer.Add(btn_refresh, 0, wx.RIGHT, 4)
    else:
        btn_refresh.Hide()
    btn_sizer.AddStretchSpacer(1)
    btn_sizer.Add(btn_close, 0)

    root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

    dialog.SetSizer(root)

    # --- Event handlers -------------------------------------------------------
    def _on_copy(_event=None):
        if closed["value"]:
            return
        parts = [stdout_text.GetValue()]
        if _stderr_state["ctrl"] is not None:
            parts.append(f"\n--- STDERR ---\n{_stderr_state['ctrl'].GetValue()}")
        data = wx.TextDataObject("\n".join(parts))
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(data)
            finally:
                wx.TheClipboard.Close()

    def _on_select_all(_event=None):
        if closed["value"]:
            return
        stdout_text.SetSelection(-1, -1)
        if _stderr_state["ctrl"] is not None:
            _stderr_state["ctrl"].SetSelection(-1, -1)

    def _on_refresh(_event=None):
        if closed["value"] or refresh_callback is None or _refresh_in_flight[0]:
            return
        btn_refresh.Enable(False)
        _refresh_in_flight[0] = True

        def _worker():
            try:
                new_result = refresh_callback()
            except Exception:
                new_result = None
            wx.CallAfter(_apply_result, new_result)

        def _apply_result(new_result):
            if closed["value"]:
                return
            _refresh_in_flight[0] = False
            btn_refresh.Enable(True)
            if new_result is None or not isinstance(new_result, RawCommandResult):
                return
            # Update source label
            new_source = _SOURCE_LABELS.get(new_result.source_id, new_result.source_id)
            if new_source:
                src_label.SetLabel(f"{t('raw_viewer.source')}: {new_source}")
            cmd_text.SetValue(new_result.display_command)
            exit_label.SetLabel(f"{t('raw_viewer.exit_code')}: {new_result.exit_code}")
            stdout_text.SetValue(new_result.stdout or "")
            # Handle stderr dynamically
            if new_result.stderr:
                _ensure_stderr(True)
                _stderr_state["ctrl"].SetValue(new_result.stderr)
            else:
                _ensure_stderr(False)
            dialog.Layout()

        Thread(target=_worker, daemon=True).start()

    def _on_close(_event=None):
        if closed["value"]:
            return
        closed["value"] = True
        dialog.EndModal(wx.ID_CLOSE)

    btn_copy.Bind(wx.EVT_BUTTON, _on_copy)
    btn_select_all.Bind(wx.EVT_BUTTON, _on_select_all)
    btn_refresh.Bind(wx.EVT_BUTTON, _on_refresh)
    btn_close.Bind(wx.EVT_BUTTON, _on_close)
    dialog.Bind(wx.EVT_CLOSE, _on_close)

    if lifecycle is not None:
        lifecycle.register_cleanup(lambda: _on_close() if not closed["value"] else None)

    dialog.ShowModal()
    dialog.Destroy()
    return wx.ID_CLOSE


__all__ = ["show_raw_viewer"]
