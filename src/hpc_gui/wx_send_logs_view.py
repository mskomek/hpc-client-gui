"""wx send-logs view backed by WxLogsModel plus diagnostics/redaction."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.diagnostics import create_diagnostic_bundle
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.core.log_redaction import redact_text
from hpc_gui.core.logging import log_path as default_log_path
from hpc_gui.wx_host import make_host
from hpc_gui.wx_logs import WxLogsModel


def _build_send_logs(parent, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, crash_context: bool = False, crash_summary: str = "", bundle=None, embedded: bool):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    resolved = Path(log_path) if log_path is not None else default_log_path()
    model = model or WxLogsModel(resolved, bundle=bundle or create_diagnostic_bundle)
    if bundle is not None:
        model.bundle = bundle
    host, finish = make_host(parent, title=t("crash.dialog_title_crash") if crash_context else t("crash.dialog_title"), size=(820, 620), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    header = wx.StaticText(panel, label=t("crash.crash_context") if crash_context else t("crash.manual_context"))
    if crash_context and crash_summary:
        header.SetLabel(t("crash.crash_context") + "\n\n" + crash_summary[:1000])
    header.Wrap(780)
    header.SetMinSize(wx.Size(780, -1))

    log_view = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)

    btn_copy = wx.Button(panel, label=t("crash.copy_logs"))
    btn_export = wx.Button(panel, label=t("crash.export_diagnostics"))
    btn_close = wx.Button(panel, label=t("crash.close"))

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_row.AddStretchSpacer(1)
    btn_row.Add(btn_copy, 0, wx.RIGHT, 6)
    btn_row.Add(btn_export, 0, wx.RIGHT, 6)
    btn_row.Add(btn_close, 0)

    root.Add(header, 0, wx.EXPAND | wx.ALL, 8)
    root.Add(log_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(root)

    state = {"closed": False}

    def load_logs():
        def worker():
            try:
                text = model.refresh()
                if not text:
                    if not model.log_path.is_file():
                        text = t("logs.not_created").format(path=str(model.log_path))
                    else:
                        text = ""
                else:
                    text = redact_text(text)
                if state["closed"]:
                    return
                wx.CallAfter(lambda: log_view.SetValue(text) if not state["closed"] else None)
            except Exception as exc:
                if state["closed"]:
                    return
                wx.CallAfter(lambda exc=exc: log_view.SetValue(t("logs.read_failed").format(err=str(exc))) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def copy_logs(_event=None):
        try:
            txt = log_view.GetValue()
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(txt))
                wx.TheClipboard.Close()
        except Exception:
            pass

    def export_diagnostics(_event=None):
        if state["closed"]:
            return
        dlg = wx.DirDialog(host, t("logs.select_output_folder"))
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            dest = dlg.GetPath()
        finally:
            dlg.Destroy()

        if state["closed"]:
            return

        def worker():
            try:
                p = create_diagnostic_bundle(dest)
                if state["closed"]:
                    return
                wx.CallAfter(lambda: wx.MessageBox(t("logs.bundle_created").format(path=str(p)), t("logs.diagnostics_title"), wx.OK | wx.ICON_INFORMATION, host) if not state["closed"] else None)
            except Exception as exc:
                if state["closed"]:
                    return
                wx.CallAfter(lambda exc=exc: wx.MessageBox(t("logs.bundle_failed").format(err=str(exc)), t("logs.diagnostics_title"), wx.OK | wx.ICON_ERROR, host) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def on_close(evt):
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        evt.Skip()

    def refresh_labels(_language=None):
        if state["closed"]:
            return
        try:
            host.set_host_title(t("crash.dialog_title_crash") if crash_context else t("crash.dialog_title"))
            header.SetLabel((t("crash.crash_context") + ("\n\n" + crash_summary[:1000] if crash_summary else "")) if crash_context else t("crash.manual_context"))
            header.Wrap(780)
            btn_copy.SetLabel(t("crash.copy_logs"))
            btn_export.SetLabel(t("crash.export_diagnostics"))
            btn_close.SetLabel(t("crash.close"))
        except Exception:
            pass

    btn_copy.Bind(wx.EVT_BUTTON, copy_logs)
    btn_export.Bind(wx.EVT_BUTTON, export_diagnostics)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())
    subscribe_language_change(refresh_labels)
    host.bind_host_close(on_close)

    host._wx_send_logs_controls = {
        "header": header,
        "log_view": log_view,
        "copy": btn_copy,
        "export": btn_export,
        "close": btn_close,
    }
    host._wx_send_logs_model = model
    host._wx_send_logs_state = state

    # Initial load off GUI thread (user action triggered)
    load_logs()

    finish()
    return host


def build_send_logs_panel(parent, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, crash_context: bool = False, crash_summary: str = "", bundle=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_send_logs(parent, model, log_path=log_path, crash_context=crash_context, crash_summary=crash_summary, bundle=bundle, embedded=True)


def show_send_logs(parent=None, model: WxLogsModel | None = None, *, log_path: str | Path | None = None, crash_context: bool = False, crash_summary: str = "", bundle=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_send_logs(parent, model, log_path=log_path, crash_context=crash_context, crash_summary=crash_summary, bundle=bundle, embedded=False)
    return wx.ID_OK


__all__ = ["build_send_logs_panel", "show_send_logs"]
