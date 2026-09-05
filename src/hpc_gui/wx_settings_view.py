"""wx settings view backed by WxSettingsModel."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_host import make_host
from hpc_gui.wx_settings import WxSettingsModel


def _build_settings(parent, model: WxSettingsModel | None = None, *, settings=None, apply=None, embedded: bool):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    model = model or WxSettingsModel(settings, apply=apply)
    host, finish = make_host(parent, title=t("settings.dialog_title"), size=(640, 560), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    title = wx.StaticText(panel, label=t("settings.dialog_title"))
    title.SetFont(title.GetFont().Bold())

    # Global settings
    cb_remote_cache = wx.CheckBox(panel, label=t("settings.remote_directory_cache_label") if t("settings.remote_directory_cache_label") != "[settings.remote_directory_cache_label]" else "Cache remote directory listings")
    cb_remote_cache.SetValue(bool(model.global_settings.get("remote_directory_cache", True)))
    cb_checksum = wx.CheckBox(panel, label=t("settings.transfer_checksum_verification_label") if t("settings.transfer_checksum_verification_label") != "[settings.transfer_checksum_verification_label]" else "Verify transfers with SHA-256")
    cb_checksum.SetValue(bool(model.global_settings.get("transfer_checksum", False)))

    # Profile settings
    lbl_parallel = wx.StaticText(panel, label=t("connection.transfer_parallelism") if t("connection.transfer_parallelism") != "[connection.transfer_parallelism]" else "Profile transfer parallelism")
    sp_parallel = wx.SpinCtrl(panel, min=1, max=16, initial=int(model.profile_settings.get("transfer_parallelism", 1) or 1))
    lbl_timeout = wx.StaticText(panel, label=t("connection.ssh_timeout") if t("connection.ssh_timeout") != "[connection.ssh_timeout]" else "SSH timeout (0 = default)")
    sp_timeout = wx.SpinCtrl(panel, min=0, max=300, initial=int(model.profile_settings.get("ssh_timeout", 0) or 0))

    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_apply = wx.Button(panel, label=t("settings.apply"))
    btn_close = wx.Button(panel, label=t("common.close"))
    btn_sizer.AddStretchSpacer(1)
    btn_sizer.Add(btn_apply, 0, wx.RIGHT, 6)
    btn_sizer.Add(btn_close, 0)

    # layout
    root.Add(title, 0, wx.ALL, 8)
    root.Add(cb_remote_cache, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(cb_checksum, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    row1 = wx.BoxSizer(wx.HORIZONTAL)
    row1.Add(lbl_parallel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    row1.Add(sp_parallel, 0)
    root.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    row2 = wx.BoxSizer(wx.HORIZONTAL)
    row2.Add(lbl_timeout, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    row2.Add(sp_timeout, 0)
    root.Add(row2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

    panel.SetSizer(root)

    state = {"closed": False}

    def apply_settings(_event=None):
        try:
            model.set_global("remote_directory_cache", bool(cb_remote_cache.GetValue()))
        except Exception:
            pass
        try:
            model.set_global("transfer_checksum", bool(cb_checksum.GetValue()))
        except Exception:
            pass
        try:
            model.set_profile("transfer_parallelism", int(sp_parallel.GetValue()))
        except Exception:
            pass
        try:
            model.set_profile("ssh_timeout", int(sp_timeout.GetValue()))
        except Exception:
            pass

        def worker():
            try:
                snapshot = model.apply()
                wx.CallAfter(lambda: wx.MessageBox(t("common.ok"), t("settings.dialog_title"), wx.OK | wx.ICON_INFORMATION, host) if not state["closed"] else None)
            except Exception as exc:
                wx.CallAfter(lambda: wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR, host) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def close_host(_event=None):
        if state["closed"]:
            return
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        # host will be destroyed via EVT_CLOSE; this is for embedded cleanup
        try:
            host.Hide()
            host.Destroy()
        except Exception:
            pass

    def on_close(evt):
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        evt.Skip()

    def refresh_labels(_language=None):
        if state["closed"]:
            return
        try:
            host.set_host_title(t("settings.dialog_title"))
            title.SetLabel(t("settings.dialog_title"))
            cb_remote_cache.SetLabel(t("settings.remote_directory_cache_label") if t("settings.remote_directory_cache_label") != "[settings.remote_directory_cache_label]" else "Cache remote directory listings")
            cb_checksum.SetLabel(t("settings.transfer_checksum_verification_label") if t("settings.transfer_checksum_verification_label") != "[settings.transfer_checksum_verification_label]" else "Verify transfers with SHA-256")
            lbl_parallel.SetLabel(t("connection.transfer_parallelism") if t("connection.transfer_parallelism") != "[connection.transfer_parallelism]" else "Profile transfer parallelism")
            lbl_timeout.SetLabel(t("connection.ssh_timeout") if t("connection.ssh_timeout") != "[connection.ssh_timeout]" else "SSH timeout (0 = default)")
            btn_apply.SetLabel(t("settings.apply"))
            btn_close.SetLabel(t("common.close"))
        except Exception:
            pass

    btn_apply.Bind(wx.EVT_BUTTON, apply_settings)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())
    subscribe_language_change(refresh_labels)
    host.bind_host_close(on_close)

    host._wx_settings_controls = {
        "title": title,
        "remote_cache": cb_remote_cache,
        "checksum": cb_checksum,
        "parallelism": sp_parallel,
        "timeout": sp_timeout,
        "apply": btn_apply,
        "close": btn_close,
    }
    host._wx_settings_model = model
    host._wx_settings_state = state

    finish()
    return host


def build_settings_panel(parent, model: WxSettingsModel | None = None, *, settings=None, apply=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_settings(parent, model, settings=settings, apply=apply, embedded=True)


def show_settings(parent=None, model: WxSettingsModel | None = None, *, settings=None, apply=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_settings(parent, model, settings=settings, apply=apply, embedded=False)
    return wx.ID_OK


__all__ = ["build_settings_panel", "show_settings"]
