"""wx logs view backed by WxLogsModel."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.core.logging import log_path as default_log_path
from hpc_gui.wx_host import make_host
from hpc_gui.wx_logs import LogDisplayEntry, WxLogsModel, group_repeated_ssh_commands


def _build_logs(parent, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, bundle=None, embedded):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    # Resolve model and log path
    resolved_log_path = Path(log_path) if log_path is not None else default_log_path()
    model = model or WxLogsModel(resolved_log_path, bundle=bundle) if bundle is not None else (model or WxLogsModel(resolved_log_path))
    # If model was provided but log_path differs, keep model's path; otherwise ensure path
    # For bundle override when model already exists, patch if needed
    if bundle is not None and model is not None:
        model.bundle = bundle

    host, finish = make_host(parent, title=t("tabs.logs"), size=(800, 500), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    # Lifetime guard (LOGS-LIFECYCLE-001): background refresh/export workers
    # must never touch destroyed controls if the tab/app closes first.
    _alive = {"value": True}

    # Top row: title on left, buttons on right
    top = wx.BoxSizer(wx.HORIZONTAL)
    title_label = wx.StaticText(panel, label=t("logs.title"))
    collapse_repeats = wx.CheckBox(panel, label=t("logs.collapse_repeats"))
    top.Add(title_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    top.AddStretchSpacer(1)
    top.Add(collapse_repeats, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    actions = wx.WrapSizer(wx.HORIZONTAL)
    btn_copy = wx.Button(panel, label=t("logs.copy"))
    btn_copy_path = wx.Button(panel, label=t("logs.copy_path"))
    btn_folder = wx.Button(panel, label=t("logs.open_folder"))
    btn_diag = wx.Button(panel, label=t("logs.export_diagnostics"))
    btn_refresh = wx.Button(panel, label=t("logs.refresh"))
    btn_copy_path.SetToolTip(t("logs.copy_path_hint"))
    btn_folder.SetToolTip(t("logs.open_folder_hint"))
    btn_diag.SetToolTip(t("logs.export_diagnostics_hint"))
    for button in (btn_copy, btn_copy_path, btn_folder, btn_diag, btn_refresh):
        button.SetMinSize(wx.Size(-1, 32))
        actions.Add(button, 0, wx.ALL, 3)

    text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    grouped = wx.TreeCtrl(
        panel,
        style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE | wx.TR_HIDE_ROOT | wx.HSCROLL,
    )
    grouped.Hide()

    root.Add(top, 0, wx.EXPAND)
    root.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)
    root.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(grouped, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)

    display_override = {"text": None}

    def _group_identity(entry: LogDisplayEntry, occurrence: int) -> tuple:
        first_line = entry.raw_lines[0] if entry.raw_lines else ""
        return entry.command_family, entry.first_timestamp, first_line, occurrence

    def _expanded_groups() -> set[tuple]:
        expanded: set[tuple] = set()
        tree_root = grouped.GetRootItem()
        if not tree_root.IsOk():
            return expanded
        item, cookie = grouped.GetFirstChild(tree_root)
        while item.IsOk():
            if grouped.ItemHasChildren(item) and grouped.IsExpanded(item):
                data = grouped.GetItemData(item)
                try:
                    key = data.GetData()
                except (AttributeError, RuntimeError):
                    key = data
                if isinstance(key, tuple):
                    expanded.add(key)
            item, cookie = grouped.GetNextChild(tree_root, cookie)
        return expanded

    def _line_label(line: str) -> str:
        return line.rstrip("\r\n") or " "

    def _render_grouped() -> None:
        expanded = _expanded_groups()
        entries = group_repeated_ssh_commands(model.text)
        occurrences: dict[tuple, int] = {}
        grouped.Freeze()
        try:
            grouped.DeleteAllItems()
            tree_root = grouped.AddRoot("")
            for entry in entries:
                if not entry.is_group:
                    for line in entry.raw_lines:
                        grouped.AppendItem(tree_root, _line_label(line))
                    continue

                base = (entry.command_family, entry.first_timestamp, entry.raw_lines[0])
                occurrence = occurrences.get(base, 0)
                occurrences[base] = occurrence + 1
                key = _group_identity(entry, occurrence)
                time_range = ""
                if entry.first_timestamp and entry.last_timestamp:
                    first = entry.first_timestamp[11:19] or entry.first_timestamp
                    last = entry.last_timestamp[11:19] or entry.last_timestamp
                    time_range = f" ({first}–{last})"
                label = t("logs.command_group_summary").format(
                    command=entry.command_family,
                    count=entry.command_count,
                    time_range=time_range,
                )
                parent_item = grouped.AppendItem(tree_root, label)
                grouped.SetItemData(parent_item, key)
                for line in entry.raw_lines:
                    grouped.AppendItem(parent_item, _line_label(line))
                if key in expanded:
                    grouped.Expand(parent_item)
        finally:
            grouped.Thaw()

    def _toggle_group(item) -> None:
        if not item or not item.IsOk() or not grouped.ItemHasChildren(item):
            return
        if grouped.IsExpanded(item):
            grouped.Collapse(item)
        else:
            grouped.Expand(item)

    def _on_group_click(event) -> None:
        item, flags = grouped.HitTest(event.GetPosition())
        disclosure_button = getattr(wx, "TREE_HITTEST_ONITEMBUTTON", 0)
        if item and item.IsOk() and grouped.ItemHasChildren(item) and not (flags & disclosure_button):
            grouped.SelectItem(item)
            _toggle_group(item)
            return
        event.Skip()

    def render_text() -> str:
        override = display_override["text"]
        if override is not None:
            value = override
        else:
            value = model.copy_all()
        if override is None and collapse_repeats.GetValue():
            text.Hide()
            grouped.Show()
            _render_grouped()
        else:
            grouped.Hide()
            text.Show()
            text.SetValue(value)
        root.Layout()
        return value

    def _set_clipboard(value: str) -> None:
        try:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(str(value)))
                wx.TheClipboard.Close()
        except Exception:
            pass

    def _refresh_done(result: str | None, error: Exception | None) -> None:
        if not _alive["value"]:
            return
        if error is not None:
            display_override["text"] = t("logs.read_failed").format(err=str(error))
            render_text()
            return
        display_override["text"] = None
        # model.refresh returns "" for missing file -> show not_created
        if not result:
            # Check if file exists to decide empty vs not_created
            if not model.log_path.is_file():
                display_override["text"] = t("logs.not_created").format(path=str(model.log_path))
            render_text()
            return
        render_text()

    def refresh(_event=None) -> None:
        def worker():
            try:
                result = model.refresh()
                wx.CallAfter(_refresh_done, result, None)
            except Exception as exc:
                wx.CallAfter(_refresh_done, None, exc)
        Thread(target=worker, daemon=True).start()

    def copy_all(_event=None) -> None:
        value = text.GetValue() if display_override["text"] is not None else model.copy_all()
        _set_clipboard(value)

    def copy_path(_event=None) -> None:
        _set_clipboard(str(model.log_path))

    def open_logs_folder(_event=None) -> None:
        """Reveal the actual active log directory (resolved at click time)."""
        try:
            target = model.logs_dir()
        except Exception:
            target = Path(str(model.log_path)).expanduser().parent
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            wx.LaunchDefaultApplication(str(target))
        except Exception as exc:
            try:
                wx.MessageBox(
                    t("logs.folder_open_failed").format(err=str(exc)),
                    t("logs.diagnostics_title"),
                    wx.OK | wx.ICON_ERROR,
                )
            except Exception:
                pass

    def export_diagnostics(_event=None) -> None:
        try:
            import wx as _wx
        except ImportError:
            return
        dlg = _wx.DirDialog(host, t("logs.select_output_folder"))
        try:
            if dlg.ShowModal() != _wx.ID_OK:
                return
            destination = dlg.GetPath()
        finally:
            dlg.Destroy()

        def worker():
            try:
                bundle_path = model.export_bundle(destination)
                wx.CallAfter(_export_done, bundle_path, None)
            except Exception as exc:
                wx.CallAfter(_export_done, None, exc)
        Thread(target=worker, daemon=True).start()

    def _export_done(bundle_path=None, error: Exception | None = None) -> None:
        if not _alive["value"]:
            return
        try:
            if error is None:
                wx.MessageBox(t("logs.bundle_created").format(path=str(bundle_path)), t("logs.diagnostics_title"), wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(t("logs.bundle_failed").format(err=str(error)), t("logs.diagnostics_title"), wx.OK | wx.ICON_ERROR)
        except Exception:
            pass

    btn_refresh.Bind(wx.EVT_BUTTON, refresh)
    btn_copy.Bind(wx.EVT_BUTTON, copy_all)
    btn_copy_path.Bind(wx.EVT_BUTTON, copy_path)
    btn_folder.Bind(wx.EVT_BUTTON, open_logs_folder)
    btn_diag.Bind(wx.EVT_BUTTON, export_diagnostics)
    collapse_repeats.Bind(wx.EVT_CHECKBOX, lambda _event: render_text())
    grouped.Bind(wx.EVT_LEFT_DOWN, _on_group_click)

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.logs"))
        title_label.SetLabel(t("logs.title"))
        btn_copy.SetLabel(t("logs.copy"))
        btn_copy_path.SetLabel(t("logs.copy_path"))
        btn_copy_path.SetToolTip(t("logs.copy_path_hint"))
        btn_folder.SetLabel(t("logs.open_folder"))
        btn_folder.SetToolTip(t("logs.open_folder_hint"))
        btn_diag.SetLabel(t("logs.export_diagnostics"))
        btn_diag.SetToolTip(t("logs.export_diagnostics_hint"))
        btn_refresh.SetLabel(t("logs.refresh"))
        collapse_repeats.SetLabel(t("logs.collapse_repeats"))
        if model.text and collapse_repeats.GetValue():
            render_text()

    def _on_host_close(event):
        _alive["value"] = False
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass
        try:
            event.Skip()
        except Exception:
            pass

    subscribe_language_change(refresh_labels)
    host.bind_host_close(_on_host_close)

    # Expose for tests / shell introspection
    host._wx_logs_controls = {
        "title": title_label,
        "text": text,
        "grouped": grouped,
        "copy": btn_copy,
        "copy_path": btn_copy_path,
        "open_folder": btn_folder,
        "export": btn_diag,
        "refresh": btn_refresh,
        "collapse_repeats": collapse_repeats,
    }
    host._wx_logs_model = model
    host._wx_logs_refresh = refresh
    host._wx_logs_open_folder = open_logs_folder
    host._wx_logs_toggle_group = _toggle_group

    # Initial load off-GUI thread
    refresh()

    finish()
    return host


def build_logs_panel(parent, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, bundle=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_logs(parent, model, log_path=log_path, bundle=bundle, embedded=True)


def show_logs(parent=None, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, bundle=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_logs(parent, model, log_path=log_path, bundle=bundle, embedded=False)
    return wx.ID_OK


__all__ = ["build_logs_panel", "show_logs"]
