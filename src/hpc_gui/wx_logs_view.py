"""wx logs view backed by WxLogsModel."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.core.logging import log_path as default_log_path
from hpc_gui.wx_host import make_host
from hpc_gui.wx_logs import WxLogsModel


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

    # Top row: title on left, buttons on right
    top = wx.BoxSizer(wx.HORIZONTAL)
    title_label = wx.StaticText(panel, label=t("logs.title"))
    btn_copy = wx.Button(panel, label=t("logs.copy"))
    btn_copy_path = wx.Button(panel, label=t("logs.copy_path"))
    btn_diag = wx.Button(panel, label=t("logs.export_diagnostics"))
    btn_refresh = wx.Button(panel, label=t("logs.refresh"))
    top.Add(title_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    top.AddStretchSpacer(1)
    top.Add(btn_copy, 0, wx.ALL, 4)
    top.Add(btn_copy_path, 0, wx.ALL, 4)
    top.Add(btn_diag, 0, wx.ALL, 4)
    top.Add(btn_refresh, 0, wx.ALL, 4)

    text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)

    root.Add(top, 0, wx.EXPAND)
    root.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)

    def _set_clipboard(value: str) -> None:
        try:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(str(value)))
                wx.TheClipboard.Close()
        except Exception:
            pass

    def _refresh_done(result: str | None, error: Exception | None) -> None:
        if error is not None:
            text.SetValue(t("logs.read_failed").format(err=str(error)))
            return
        # model.refresh returns "" for missing file -> show not_created
        if not result:
            # Check if file exists to decide empty vs not_created
            if not model.log_path.is_file():
                text.SetValue(t("logs.not_created").format(path=str(model.log_path)))
            else:
                text.SetValue(result)
            return
        text.SetValue(result)

    def refresh(_event=None) -> None:
        def worker():
            try:
                result = model.refresh()
                wx.CallAfter(_refresh_done, result, None)
            except Exception as exc:
                wx.CallAfter(_refresh_done, None, exc)
        Thread(target=worker, daemon=True).start()

    def copy_all(_event=None) -> None:
        try:
            value = model.copy_all()
        except Exception:
            value = text.GetValue()
        # Fallback to displayed text if model empty yet file exists? keep model value
        _set_clipboard(value)

    def copy_path(_event=None) -> None:
        _set_clipboard(str(model.log_path))

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
                wx.CallAfter(lambda: wx.MessageBox(t("logs.bundle_created").format(path=str(bundle_path)), t("logs.diagnostics_title"), wx.OK | wx.ICON_INFORMATION))
            except Exception as exc:
                wx.CallAfter(lambda: wx.MessageBox(t("logs.bundle_failed").format(err=str(exc)), t("logs.diagnostics_title"), wx.OK | wx.ICON_ERROR))
        Thread(target=worker, daemon=True).start()

    btn_refresh.Bind(wx.EVT_BUTTON, refresh)
    btn_copy.Bind(wx.EVT_BUTTON, copy_all)
    btn_copy_path.Bind(wx.EVT_BUTTON, copy_path)
    btn_diag.Bind(wx.EVT_BUTTON, export_diagnostics)

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.logs"))
        title_label.SetLabel(t("logs.title"))
        btn_copy.SetLabel(t("logs.copy"))
        btn_copy_path.SetLabel(t("logs.copy_path"))
        btn_diag.SetLabel(t("logs.export_diagnostics"))
        btn_refresh.SetLabel(t("logs.refresh"))

    subscribe_language_change(refresh_labels)
    host.bind_host_close(lambda event: (unsubscribe_language_change(refresh_labels), event.Skip()))

    # Expose for tests / shell introspection
    host._wx_logs_controls = {
        "title": title_label,
        "text": text,
        "copy": btn_copy,
        "copy_path": btn_copy_path,
        "export": btn_diag,
        "refresh": btn_refresh,
    }
    host._wx_logs_model = model
    host._wx_logs_refresh = refresh

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
