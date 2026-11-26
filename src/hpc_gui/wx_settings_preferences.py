"""Global settings controls outside the transfer and profile model."""

from __future__ import annotations

from typing import Any

from hpc_gui.core.i18n import t


FOLLOW_MODES = (
    ("none", "settings.sbatch_follow_mode_none"),
    ("outputs_tab", "settings.sbatch_follow_mode_outputs_tab"),
    ("new_tabs_split", "settings.sbatch_follow_mode_tabs"),
    ("new_window_combined", "settings.sbatch_follow_mode_window_combined"),
    ("new_windows_split", "settings.sbatch_follow_mode_windows_split"),
)
GRAPHICS_MODES = (
    ("auto", "settings.terminal_graphics_mode_auto"),
    ("compatibility", "settings.terminal_graphics_mode_compatibility"),
    ("accelerated", "settings.terminal_graphics_mode_accelerated"),
)
TRANSFER_MODES = (("auto", "ftp.mode_auto"), ("binary", "ftp.mode_binary"), ("ascii", "ftp.mode_ascii"))


def build_settings_preferences(
    wx,
    parent,
    settings: dict[str, Any],
    profiles: list[dict[str, Any]],
    session_state: dict[str, Any] | None = None,
):
    """Build scrollable-ready preference groups and retain storage keys."""
    jobs = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.jobs_outputs_section"))
    transfers = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.ftp_section"))
    connection = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.connection_section"))
    graphics = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.terminal_graphics_section"))
    remote_paths = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.ftp_section"))
    controls: dict[str, Any] = {}
    labels: dict[str, tuple[str, tuple[str, ...] | None]] = {}
    label_controls: dict[str, Any] = {}
    group_labels = {
        jobs: "settings.jobs_outputs_section",
        transfers: "settings.ftp_section",
        connection: "settings.connection_section",
        graphics: "settings.terminal_graphics_section",
        remote_paths: "settings.ftp_section",
    }

    def translated(value: str) -> str:
        result = t(value)
        return value if result == f"[{value}]" else result

    def add_spin(group, key, label_key, low, high, default):
        owner = group.GetStaticBox()
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(owner, label=t(label_key))
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        control = wx.SpinCtrl(owner, min=low, max=high, initial=int(settings.get(key, default)))
        row.Add(control, 0)
        group.Add(row, 0, wx.ALL, 4)
        controls[key] = control
        labels[key] = (label_key, None)
        label_controls[key] = label

    def add_check(group, key, label_key, default):
        control = wx.CheckBox(group.GetStaticBox(), label=t(label_key))
        control.SetValue(settings.get(key, default) if isinstance(settings.get(key, default), bool) else default)
        group.Add(control, 0, wx.ALL, 4)
        controls[key] = control
        labels[key] = (label_key, None)

    def add_choice(group, key, label_key, options, default):
        owner = group.GetStaticBox()
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(owner, label=t(label_key))
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        values = [value for value, _text in options]
        label_keys = tuple(text for _value, text in options)
        choice = wx.Choice(owner, choices=[t(text) for text in label_keys])
        current = settings.get(key, default)
        choice.SetSelection(values.index(current) if current in values else 0)
        row.Add(choice, 0)
        group.Add(row, 0, wx.ALL, 4)
        controls[key] = (choice, tuple(values))
        labels[key] = (label_key, label_keys)
        label_controls[key] = label

    add_spin(jobs, "jobs_outputs_refresh_interval_seconds", "settings.jobs_outputs_refresh_interval_label", 1, 3600, 15)
    add_spin(jobs, "live_tracking_warning_interval_seconds", "settings.live_tracking_warning_interval_label", 0, 3600, 60)
    for key, label_key, default in (
        ("pause_live_follow_when_minimized_enabled", "settings.pause_live_follow_when_minimized_label", True),
        ("follow_window_open_minimized_enabled", "settings.follow_window_open_minimized_label", True),
        ("squeue_auto_refresh_enabled", "settings.squeue_auto_refresh_label", True),
        ("sacct_auto_refresh_enabled", "settings.sacct_auto_refresh_label", True),
        ("lssrv_auto_refresh_enabled", "settings.lssrv_auto_refresh_label", False),
    ):
        add_check(jobs, key, label_key, default)

    add_choice(transfers, "ftp_transfer_type", "settings.ftp_transfer_type_label", TRANSFER_MODES, "auto")
    add_choice(transfers, "sbatch_follow_mode", "settings.sbatch_follow_mode_label", FOLLOW_MODES, "outputs_tab")
    for key, label_key, default in (
        ("x11_autodeps", "login.x11_autodeps_label", True),
        ("close_vcxsrv_on_exit", "login.close_vcxsrv_label", True),
        ("close_x11_procs_on_exit", "login.close_x11_procs_label", True),
        ("cli_external_access_enabled", "settings.cli_external_access_label", False),
    ):
        add_check(connection, key, label_key, default)
    profile_names = sorted({str(p.get("name") or "").strip() for p in profiles if str(p.get("name") or "").strip()}, key=str.casefold)
    add_choice(connection, "cli_default_profile", "settings.cli_default_profile_label", (("", "settings.cli_default_profile_none"), *((name, name) for name in profile_names)), "")
    add_choice(graphics, "terminal_graphics_mode", "settings.terminal_graphics_mode_label", GRAPHICS_MODES, "auto")
    reset_graphics = wx.Button(graphics.GetStaticBox(), label=t("settings.terminal_graphics_reset"))
    graphics.Add(reset_graphics, 0, wx.ALL, 4)

    session = (session_state or {}).get("session") or {}
    active_profile = session.get("profile") or {}
    active_name = str(session.get("profile_name") or active_profile.get("name") or "").strip()
    system = active_profile.get("system")
    if not isinstance(system, dict):
        system = active_profile.get("system_settings")
    if not isinstance(system, dict):
        system = {}
    paths_enabled = bool(session.get("connected") and active_name)
    remote_controls: dict[str, Any] = {}
    for key, label_key in (
        ("profile_scratch_dir", "settings.ftp_scratch_default"),
        ("profile_home_dir", "settings.ftp_home_default"),
    ):
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(remote_paths.GetStaticBox(), label=t(label_key))
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        text = wx.TextCtrl(remote_paths.GetStaticBox(), value=str(system.get(key.removeprefix("profile_"), "")))
        text.Enable(paths_enabled)
        row.Add(text, 1, wx.EXPAND)
        remote_paths.Add(row, 0, wx.EXPAND | wx.ALL, 4)
        controls[key] = text
        remote_controls[key] = text
        labels[key] = (label_key, None)
        label_controls[key] = label
    reset_remote = wx.Button(remote_paths.GetStaticBox(), label=t("settings.ftp_reset_defaults"))
    reset_remote.Enable(paths_enabled)
    remote_paths.Add(reset_remote, 0, wx.ALL, 4)

    def reset_remote_defaults(_event=None):
        remote_controls["profile_scratch_dir"].SetValue("")
        remote_controls["profile_home_dir"].SetValue("")

    reset_remote.Bind(wx.EVT_BUTTON, reset_remote_defaults)

    def refresh_labels():
        for group, label_key in group_labels.items():
            group.GetStaticBox().SetLabel(t(label_key))
        for key, control in controls.items():
            label_key, option_keys = labels[key]
            if key in label_controls:
                label_controls[key].SetLabel(t(label_key))
            if isinstance(control, tuple):
                choice, _values = control
                if option_keys:
                    for index, option_key in enumerate(option_keys):
                        choice.SetString(index, translated(option_key))
            elif control.GetClassName() == "wxCheckBox":
                control.SetLabel(t(label_key))
        reset_graphics.SetLabel(t("settings.terminal_graphics_reset"))
        reset_remote.SetLabel(t("settings.ftp_reset_defaults"))

    return (jobs, transfers, connection, graphics, remote_paths), controls, reset_graphics, reset_remote, refresh_labels


def collect_settings_preferences(controls: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, control in controls.items():
        if isinstance(control, bool):
            values[key] = control
        elif isinstance(control, tuple):
            choice, options = control
            selected = choice.GetSelection()
            values[key] = options[selected] if selected >= 0 else options[0]
        elif control.GetClassName() == "wxSpinCtrl":
            values[key] = int(control.GetValue())
        elif control.GetClassName() == "wxTextCtrl":
            values[key] = control.GetValue().strip()
        else:
            values[key] = bool(control.GetValue())
    return values


__all__ = ["build_settings_preferences", "collect_settings_preferences"]
