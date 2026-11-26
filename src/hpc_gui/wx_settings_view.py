"""wx settings view backed by WxSettingsModel."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_host import make_host
from hpc_gui.wx_settings import WxSettingsModel
from hpc_gui.services.transfer_speed_test import run_transfer_speed_test
from hpc_gui.wx_settings_speed import resolve_transfer_speed_target, transfer_speed_target_is_current


def _build_settings(parent, model: WxSettingsModel | None = None, *, settings=None, apply=None, embedded: bool, session_state=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    model = model or WxSettingsModel(settings, apply=apply)
    state = {"closed": False, "speed_test_running": False}
    if apply is not None and getattr(model, "apply_callback", None) is None:
        # SETTINGS-PERSIST-001: a caller-supplied persistence callback must
        # not be silently dropped when a prebuilt model is injected.
        model.apply_callback = apply
    # Spec §96: Settings 840×620 resizable, §4 dialog body 16px, §98 label width 180-240px
    host, finish = make_host(parent, title=t("settings.dialog_title"), size=(840, 620), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    title = wx.StaticText(panel, label=t("settings.dialog_title"))
    title.SetFont(title.GetFont().Bold())

    # Global settings
    cb_remote_cache = wx.CheckBox(panel, label=t("settings.remote_directory_cache_label"))
    cb_remote_cache.SetValue(bool(model.global_settings.get("remote_directory_cache", True)))
    cb_checksum = wx.CheckBox(panel, label=t("settings.transfer_checksum_verification_label"))
    cb_checksum.SetValue(bool(model.global_settings.get("transfer_checksum", False)))
    cb_preflight = wx.CheckBox(panel, label=t("settings.upload_preflight_confirmation_label"))
    cb_preflight.SetValue(bool(model.global_settings.get("upload_preflight_confirmation", True)))
    btn_reset_smart_open = wx.Button(panel, label=t("settings.smart_open_reset"))
    association_title = wx.StaticText(panel, label=t("settings.file_associations_section"))
    association_list = wx.ListBox(panel)
    association_change = wx.Button(panel, label=t("settings.file_association_change"))
    association_clear = wx.Button(panel, label=t("settings.file_association_clear"))
    speed_label = wx.StaticText(panel, label=t("settings.transfer_speed_test_size_label"))
    speed_size = wx.Choice(panel, choices=["8 MiB", "32 MiB", "100 MiB"])
    speed_size.SetSelection(0)
    speed_button = wx.Button(panel, label=t("settings.transfer_speed_test"))
    speed_state = {"running": False}
    state["speed_test_running"] = False

    from hpc_gui.config.storage import clear_file_association, get_file_associations, set_file_association
    file_associations = get_file_associations()

    def refresh_associations():
        association_list.Clear()
        for extension, program in sorted(file_associations.items()):
            association_list.Append(f"{extension} -> {program}", clientData=extension)
        selected = association_list.GetSelection() != wx.NOT_FOUND
        has_items = association_list.GetCount() > 0
        association_change.Enable(has_items)
        association_clear.Enable(selected)

    def change_association(_event=None):
        index = association_list.GetSelection()
        if index == wx.NOT_FOUND:
            wx.MessageBox(t("settings.file_association_none_selected"), t("common.info"), wx.OK | wx.ICON_INFORMATION, host)
            return
        extension = association_list.GetClientData(index)
        dialog = wx.FileDialog(
            host, t("files.open_with_select_program"),
            defaultFile=file_associations.get(extension, ""),
            wildcard=t("files.open_with_program_filter"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            file_associations.update(set_file_association(extension, dialog.GetPath()))
            refresh_associations()
        finally:
            dialog.Destroy()

    def clear_association(_event=None):
        index = association_list.GetSelection()
        if index == wx.NOT_FOUND:
            wx.MessageBox(t("settings.file_association_none_selected"), t("common.info"), wx.OK | wx.ICON_INFORMATION, host)
            return
        extension = association_list.GetClientData(index)
        file_associations.clear()
        file_associations.update(clear_file_association(extension))
        refresh_associations()

    association_list.Bind(wx.EVT_LISTBOX, lambda _event: association_clear.Enable(association_list.GetSelection() != wx.NOT_FOUND))
    association_change.Bind(wx.EVT_BUTTON, change_association)
    association_clear.Bind(wx.EVT_BUTTON, clear_association)
    refresh_associations()
    try:
        resolve_transfer_speed_target(session_state)
        speed_button.Enable(True)
    except RuntimeError:
        speed_button.Enable(False)

    # Profile settings
    lbl_parallel = wx.StaticText(panel, label=t("connection.transfer_parallelism"))
    sp_parallel = wx.SpinCtrl(panel, min=1, max=16, initial=int(model.profile_settings.get("transfer_parallelism", 1) or 1))
    lbl_timeout = wx.StaticText(panel, label=t("connection.ssh_timeout"))
    sp_timeout = wx.SpinCtrl(panel, min=0, max=300, initial=int(model.profile_settings.get("ssh_timeout", 0) or 0))
    lbl_attempts = wx.StaticText(panel, label=t("settings.ssh_connection_attempts"))
    sp_attempts = wx.SpinCtrl(panel, min=1, max=5, initial=int(model.global_settings.get("ssh_connection_attempts", 5) or 5))

    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_apply = wx.Button(panel, label=t("settings.apply"))
    btn_close = wx.Button(panel, label=t("common.close"))
    btn_sizer.AddStretchSpacer(1)
    btn_sizer.Add(btn_apply, 0, wx.RIGHT, 6)
    btn_sizer.Add(btn_close, 0)

    # layout — §4 spacing scale 4/8/12/16, §16 dialog body 16px, footer 12-16px
    root.Add(title, 0, wx.ALL, 16)
    root.Add(cb_remote_cache, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    root.Add(cb_checksum, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    root.Add(cb_preflight, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    root.Add(btn_reset_smart_open, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    root.Add(association_title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    root.Add(association_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
    association_buttons = wx.BoxSizer(wx.HORIZONTAL)
    association_buttons.Add(association_change, 0, wx.RIGHT, 6)
    association_buttons.Add(association_clear, 0)
    root.Add(association_buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    speed_row = wx.BoxSizer(wx.HORIZONTAL)
    speed_row.Add(speed_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    speed_row.Add(speed_size, 0, wx.RIGHT, 8)
    speed_row.Add(speed_button, 0)
    root.Add(speed_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    row1 = wx.BoxSizer(wx.HORIZONTAL)
    row1.Add(lbl_parallel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    row1.Add(sp_parallel, 0)
    root.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    row2 = wx.BoxSizer(wx.HORIZONTAL)
    row2.Add(lbl_timeout, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    row2.Add(sp_timeout, 0)
    root.Add(row2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    row3 = wx.BoxSizer(wx.HORIZONTAL)
    row3.Add(lbl_attempts, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    row3.Add(sp_attempts, 0)
    root.Add(row3, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 16)

    panel.SetSizer(root)

    def apply_settings(_event=None):
        # W02 error governance (HPC-W01-TODO-018 / HPC-W01-TODO-020): staging
        # failures must not be swallowed and must never end in an "OK" dialog.
        set_errors: list[tuple[str, Exception]] = []
        try:
            model.set_global("remote_directory_cache", bool(cb_remote_cache.GetValue()))
        except Exception as exc:
            set_errors.append(("remote_directory_cache", exc))
        try:
            model.set_global("transfer_checksum", bool(cb_checksum.GetValue()))
        except Exception as exc:
            set_errors.append(("transfer_checksum", exc))
        try:
            model.set_global("upload_preflight_confirmation", bool(cb_preflight.GetValue()))
        except Exception as exc:
            set_errors.append(("upload_preflight_confirmation", exc))
        try:
            model.set_profile("transfer_parallelism", int(sp_parallel.GetValue()))
        except Exception as exc:
            set_errors.append(("transfer_parallelism", exc))
        try:
            model.set_profile("ssh_timeout", int(sp_timeout.GetValue()))
        except Exception as exc:
            set_errors.append(("ssh_timeout", exc))
        try:
            model.set_global("ssh_connection_attempts", int(sp_attempts.GetValue()))
        except Exception as exc:
            set_errors.append(("ssh_connection_attempts", exc))

        def worker(pending=set_errors):
            try:
                if pending:
                    names = ", ".join(name for name, _exc in pending)
                    raise RuntimeError(f"settings rejected ({names}): {pending[0][1]}") from pending[0][1]
                snapshot = model.apply()
                # W37 SETTINGS-PERSIST-002: Apply reports success only after
                # the underlying config write succeeds. When the model
                # carries a real persistence callback (shell-injected) the
                # callback already persisted; otherwise persist the snapshot
                # here so Apply-without-persistence is impossible.
                try:
                    if getattr(model, "apply_callback", None) is None:
                        from hpc_gui.wx_settings import persist_model_snapshot
                        persist_model_snapshot(snapshot)
                    else:
                        # Callback path already persisted; keep the legacy
                        # checksum bridge as a second write only when it was
                        # not covered (persist_model_snapshot covers it, a
                        # minimal custom callback may not).
                        try:
                            from hpc_gui.wx_settings import persist_transfer_checksum_to_storage
                            persist_transfer_checksum_to_storage(model)
                        except Exception:
                            from hpc_gui.wx_settings import persist_model_snapshot as _persist
                            _persist(snapshot)
                except Exception as exc:
                    raise RuntimeError(f"settings persist rejected: {exc}") from exc
                wx.CallAfter(lambda: wx.MessageBox(t("common.ok"), t("settings.dialog_title"), wx.OK | wx.ICON_INFORMATION, host) if not state["closed"] else None)
            except Exception as exc:
                # Visible, diagnosable error with a stable code; "OK" is only
                # shown on the success path above, never after a failure.
                from hpc_gui.core.wx_errors import report_wx_action_error
                wx.CallAfter(lambda exc=exc: report_wx_action_error(host, area="SETTINGS", message_key="settings.apply_failed", exc=exc) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def start_speed_test(_event=None):
        if speed_state["running"] or state["closed"]:
            return
        try:
            target = resolve_transfer_speed_target(session_state)
        except Exception as exc:
            from hpc_gui.core.wx_errors import report_wx_action_error
            report_wx_action_error(host, area="SETTINGS", message_key="settings.apply_failed", exc=exc)
            return
        selected = speed_size.GetStringSelection().split()[0]
        try:
            size_mib = int(selected)
        except ValueError:
            size_mib = 8
        speed_state["running"] = True
        state["speed_test_running"] = True
        speed_button.Enable(False)

        def worker():
            result = None
            error = None
            try:
                result = run_transfer_speed_test(target.files, remote_dir=target.remote_dir, size_mib=size_mib)
            except Exception as exc:
                error = exc

            def finish_speed_test():
                speed_state["running"] = False
                state["speed_test_running"] = False
                if state["closed"] or not transfer_speed_target_is_current(session_state, target):
                    return
                speed_button.Enable(True)
                if error is not None:
                    from hpc_gui.core.wx_errors import report_wx_action_error
                    report_wx_action_error(host, area="SETTINGS", message_key="settings.apply_failed", exc=error)
                    return
                wx.MessageBox(
                    t("settings.transfer_speed_test_result").format(
                        size=result["size_mib"], upload=result["upload_mib_s"], download=result["download_mib_s"]
                    ),
                    t("settings.dialog_title"), wx.OK | wx.ICON_INFORMATION, host,
                )

            wx.CallAfter(finish_speed_test)

        Thread(target=worker, daemon=True).start()

    def reset_smart_open(_event=None):
        answer = wx.MessageBox(
            t("settings.smart_open_reset_confirm"), t("settings.dialog_title"),
            wx.YES_NO | wx.ICON_QUESTION, host,
        )
        if answer != wx.YES:
            return
        try:
            from hpc_gui.services.file_open import reset_smart_open_preferences
            reset_smart_open_preferences()
            wx.MessageBox(t("common.ok"), t("settings.dialog_title"), wx.OK | wx.ICON_INFORMATION, host)
        except Exception as exc:
            from hpc_gui.core.wx_errors import report_wx_action_error
            report_wx_action_error(host, area="SETTINGS", message_key="settings.apply_failed", exc=exc)

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

    def on_destroy(evt):
        if evt.GetEventObject() is host:
            state["closed"] = True
            unsubscribe_language_change(refresh_labels)
        evt.Skip()

    def refresh_labels(_language=None):
        if state["closed"]:
            return
        try:
            host.set_host_title(t("settings.dialog_title"))
            title.SetLabel(t("settings.dialog_title"))
            cb_remote_cache.SetLabel(t("settings.remote_directory_cache_label"))
            cb_checksum.SetLabel(t("settings.transfer_checksum_verification_label"))
            cb_preflight.SetLabel(t("settings.upload_preflight_confirmation_label"))
            btn_reset_smart_open.SetLabel(t("settings.smart_open_reset"))
            association_title.SetLabel(t("settings.file_associations_section"))
            association_change.SetLabel(t("settings.file_association_change"))
            association_clear.SetLabel(t("settings.file_association_clear"))
            speed_label.SetLabel(t("settings.transfer_speed_test_size_label"))
            speed_button.SetLabel(t("settings.transfer_speed_test"))
            lbl_parallel.SetLabel(t("connection.transfer_parallelism"))
            lbl_timeout.SetLabel(t("connection.ssh_timeout"))
            btn_apply.SetLabel(t("settings.apply"))
            btn_close.SetLabel(t("common.close"))
        except Exception:
            pass

    btn_apply.Bind(wx.EVT_BUTTON, apply_settings)
    btn_reset_smart_open.Bind(wx.EVT_BUTTON, reset_smart_open)
    speed_button.Bind(wx.EVT_BUTTON, start_speed_test)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())
    subscribe_language_change(refresh_labels)
    host.bind_host_close(on_close)
    host.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)

    host._wx_settings_controls = {
        "title": title,
        "remote_cache": cb_remote_cache,
        "checksum": cb_checksum,
        "upload_preflight": cb_preflight,
        "reset_smart_open": btn_reset_smart_open,
        "file_associations": association_list,
        "file_association_change": association_change,
        "file_association_clear": association_clear,
        "speed_test_size": speed_size,
        "speed_test": speed_button,
        "parallelism": sp_parallel,
        "timeout": sp_timeout,
        "apply": btn_apply,
        "close": btn_close,
    }
    host._wx_settings_model = model
    host._wx_settings_state = state

    finish()
    return host


def build_settings_panel(parent, model: WxSettingsModel | None = None, *, settings=None, apply=None, session_state=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_settings(parent, model, settings=settings, apply=apply, embedded=True, session_state=session_state)


def show_settings(parent=None, model: WxSettingsModel | None = None, *, settings=None, apply=None, session_state=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_settings(parent, model, settings=settings, apply=apply, embedded=False, session_state=session_state)
    return wx.ID_OK


__all__ = ["build_settings_panel", "show_settings"]
