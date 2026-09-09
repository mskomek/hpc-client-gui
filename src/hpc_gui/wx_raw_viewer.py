"""Reusable wx Raw Command Viewer dialog for displaying raw scheduler output."""

from __future__ import annotations

from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.raw_command_result import RawCommandResult


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

    root = wx.BoxSizer(wx.VERTICAL)

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

    # STDOUT section
    stdout_label = wx.StaticText(dialog, label=t("raw_viewer.stdout"))
    root.Add(stdout_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    stdout_text = wx.TextCtrl(
        dialog,
        value=result.stdout or "",
        style=wx.TE_READONLY | wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2,
    )
    stdout_text.SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
    root.Add(stdout_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    # STDERR section (only shown if non-empty)
    _stderr_state = {"ctrl": None}
    if result.stderr:
        stderr_label = wx.StaticText(dialog, label=t("raw_viewer.stderr"))
        root.Add(stderr_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        _stderr_state["ctrl"] = wx.TextCtrl(
            dialog,
            value=result.stderr,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2,
        )
        _stderr_state["ctrl"].SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
        root.Add(_stderr_state["ctrl"], 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

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
        stdout_text.SetSelection(-1, -1)
        if _stderr_state["ctrl"] is not None:
            _stderr_state["ctrl"].SetSelection(-1, -1)

    def _on_refresh(_event=None):
        if refresh_callback is None:
            return
        try:
            new_result = refresh_callback()
        except Exception:
            return
        if new_result is None or not isinstance(new_result, RawCommandResult):
            return
        cmd_text.SetValue(new_result.display_command)
        exit_label.SetLabel(f"{t('raw_viewer.exit_code')}: {new_result.exit_code}")
        stdout_text.SetValue(new_result.stdout or "")
        if new_result.stderr:
            if _stderr_state["ctrl"] is None:
                stderr_label_new = wx.StaticText(dialog, label=t("raw_viewer.stderr"))
                root.Insert(root.GetItemCount() - 2, stderr_label_new, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
                _stderr_state["ctrl"] = wx.TextCtrl(
                    dialog,
                    value=new_result.stderr,
                    style=wx.TE_READONLY | wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2,
                )
                _stderr_state["ctrl"].SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
                root.Insert(root.GetItemCount() - 2, _stderr_state["ctrl"], 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
            else:
                _stderr_state["ctrl"].SetValue(new_result.stderr)
        dialog.Layout()

    def _on_close(_event=None):
        dialog.Close()

    btn_copy.Bind(wx.EVT_BUTTON, _on_copy)
    btn_select_all.Bind(wx.EVT_BUTTON, _on_select_all)
    btn_refresh.Bind(wx.EVT_BUTTON, _on_refresh)
    btn_close.Bind(wx.EVT_BUTTON, _on_close)
    dialog.Bind(wx.EVT_CLOSE, lambda _e: dialog.Close())

    if lifecycle is not None:
        lifecycle.register_cleanup(lambda: dialog.Close() if dialog else None)

    dialog.ShowModal()
    dialog.Destroy()
    return wx.ID_CLOSE


__all__ = ["show_raw_viewer"]
