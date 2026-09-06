"""wx-native connection/profile editor for V2.

Single dialog implementation for Add / Edit / Duplicate. The layout keeps
basic sections visible (Profile / Connection / Authentication) while advanced
Cluster and SSH settings stay collapsed until requested. The dialog never
stores plaintext passwords and preserves unknown profile keys via patch-based
persistence handled by the shared connection_profile service.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hpc_gui.config.file_manager_profile import normalize_file_manager_settings, patch_file_manager_settings
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings, patch_jump_host_settings
from hpc_gui.config.storage import coerce_profile_ssh_timeout, coerce_profile_transfer_parallelism
from hpc_gui.config.system_profile import (
    builtin_system_template_groups,
    load_user_system_templates,
    normalize_system_settings,
    save_user_system_template,
)
from hpc_gui.core.i18n import t
from hpc_gui.plugins.models import validate_storage_area, validate_storage_policy
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.ssh.client import coerce_keepalive_interval


# ---------------------------------------------------------------------------
# Compact storage-area editor
# ---------------------------------------------------------------------------

def _show_storage_area_dialog(parent, existing: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        import wx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("wxPython is not installed") from exc

    is_edit = existing is not None
    title = t("connection.storage_edit") if is_edit else t("connection.storage_add")
    dlg = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dlg.SetMinSize(wx.Size(520, 480))

    # Controls
    label_ctrl = wx.TextCtrl(dlg, value=str((existing or {}).get("label") or (existing or {}).get("id") or ""))
    label_ctrl.SetHint(t("connection.storage_label"))
    path_ctrl = wx.TextCtrl(dlg, value=str((existing or {}).get("path_template") or ""))
    path_ctrl.SetHint(t("connection.storage_path"))
    kinds = ["home", "scratch", "project", "custom", "node-local"]
    kind_choice = wx.Choice(dlg, choices=kinds)
    cur_kind = str((existing or {}).get("kind") or "custom")
    if cur_kind in kinds:
        kind_choice.SetSelection(kinds.index(cur_kind))
    else:
        kind_choice.SetSelection(3)
    contexts = ["login-node", "shared", "compute-node", "unknown"]
    ctx_choice = wx.Choice(dlg, choices=contexts)
    cur_ctx = str((existing or {}).get("access_context") or "unknown")
    if cur_ctx in contexts:
        ctx_choice.SetSelection(contexts.index(cur_ctx))
    else:
        ctx_choice.SetSelection(3)
    enabled_cb = wx.CheckBox(dlg, label=t("common.ok") if t("common.ok") != "[common.ok]" else "Enabled")
    # Use explicit label for enabled; fallback to English if key missing
    enabled_cb.SetLabel("Enabled" if t("common.ok") == "[common.ok]" or True else t("common.ok"))
    enabled_cb.SetValue(bool((existing or {}).get("enabled", True)) if isinstance((existing or {}).get("enabled"), bool) else True)
    # Backup policy
    backup_choices = [t("connection.storage_unknown"), t("connection.storage_yes"), t("connection.storage_no")]
    backup_choice = wx.Choice(dlg, choices=backup_choices)
    policy = (existing or {}).get("policy") if isinstance((existing or {}).get("policy"), dict) else {}
    backup_val = policy.get("backup") if isinstance(policy, dict) else None
    if backup_val is True:
        backup_choice.SetSelection(1)
    elif backup_val is False:
        backup_choice.SetSelection(2)
    else:
        backup_choice.SetSelection(0)
    cleanup_ctrl = wx.TextCtrl(dlg, value=str(policy.get("cleanup_note") or "") if isinstance(policy, dict) else "")
    cleanup_ctrl.SetHint(t("connection.storage_cleanup"))
    retention_ctrl = wx.TextCtrl(dlg, value=str(policy.get("retention_days") or "") if isinstance(policy, dict) and policy.get("retention_days") is not None else "")
    retention_ctrl.SetHint(t("connection.storage_retention"))
    url_ctrl = wx.TextCtrl(dlg, value=str(policy.get("documentation_url") or "") if isinstance(policy, dict) else "")
    url_ctrl.SetHint(t("connection.storage_source_url"))

    form = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
    form.AddGrowableCol(1, 1)
    def add_row(label_key, widget):
        lbl = wx.StaticText(dlg, label=t(label_key) if t(label_key) != f"[{label_key}]" else label_key.split(".")[-1])
        form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(widget, 1, wx.EXPAND)

    add_row("connection.storage_label", label_ctrl)
    add_row("connection.storage_path", path_ctrl)
    add_row("connection.storage_kind", kind_choice)
    add_row("connection.storage_access_context", ctx_choice)
    # Enabled row
    enabled_label = wx.StaticText(dlg, label="Enabled")
    form.Add(enabled_label, 0, wx.ALIGN_CENTER_VERTICAL)
    form.Add(enabled_cb, 0, wx.ALIGN_CENTER_VERTICAL)
    add_row("connection.storage_backup", backup_choice)
    add_row("connection.storage_cleanup", cleanup_ctrl)
    add_row("connection.storage_retention", retention_ctrl)
    add_row("connection.storage_source_url", url_ctrl)

    btn_sizer = dlg.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)

    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(form, 1, wx.EXPAND | wx.ALL, 12)
    root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 12)
    dlg.SetSizer(root)
    dlg.Fit()
    # Ensure minimal size on DPI scaled displays
    dlg.SetSizeHints(520, 400)

    # Accessibility: first field
    label_ctrl.SetFocus()

    while True:
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            return None
        label = label_ctrl.GetValue().strip()
        path = path_ctrl.GetValue().strip()
        kind = kinds[kind_choice.GetSelection()] if kind_choice.GetSelection() != wx.NOT_FOUND else "custom"
        access_context = contexts[ctx_choice.GetSelection()] if ctx_choice.GetSelection() != wx.NOT_FOUND else "unknown"
        enabled = enabled_cb.GetValue()
        backup_sel = backup_choice.GetSelection()
        backup_map = {1: True, 2: False}
        backup = backup_map.get(backup_sel)
        cleanup = cleanup_ctrl.GetValue().strip()
        retention_raw = retention_ctrl.GetValue().strip()
        doc_url = url_ctrl.GetValue().strip()

        # Validate id/label
        area_id = str((existing or {}).get("id") or "")
        if not area_id:
            area_id = "-".join(label.lower().split()) or "storage"
            # uniqueness will be handled by caller; here just ensure non-empty
        area: dict[str, Any] = {
            "id": area_id,
            "label": label,
            "kind": kind,
            "enabled": bool(enabled),
            "path_template": path,
            "access_context": access_context,
        }
        if validate_storage_area(area):
            wx.MessageBox(validate_storage_area(area) or t("connection.storage_path_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        # Validate retention
        if retention_raw and not retention_raw.isdigit():
            wx.MessageBox(t("connection.storage_retention_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        retention_val = int(retention_raw) if retention_raw else None
        policy_check: dict[str, Any] = {}
        if retention_val is not None:
            policy_check["retention_days"] = retention_val
        if doc_url:
            policy_check["documentation_url"] = doc_url
            if validate_storage_policy(policy_check):
                wx.MessageBox(t("connection.storage_source_url_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
                continue
        # Build final area with existing unknown keys preserved
        base = dict(existing) if isinstance(existing, dict) else {}
        # Preserve unknown top-level keys implicitly via base copy; then override known
        base.update(area)
        # Preserve/merge policy unknown keys
        existing_policy = base.get("policy") if isinstance(base.get("policy"), dict) else {}
        merged_policy: dict[str, Any] = dict(existing_policy) if isinstance(existing_policy, dict) else {}
        merged_policy.update({
            "backup": backup,
            "cleanup_note": cleanup,
            "retention_days": retention_val,
            "documentation_url": doc_url,
        })
        # Remove empty optional keys to keep parity with Qt (None vs absent not critical)
        if validate_storage_policy(merged_policy):
            err = validate_storage_policy(merged_policy)
            wx.MessageBox(err or t("connection.storage_retention_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        base["policy"] = merged_policy
        # Final area validation
        if validate_storage_area(base):
            wx.MessageBox(validate_storage_area(base) or t("connection.storage_path_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        dlg.Destroy()
        return base


# ---------------------------------------------------------------------------
# Main connection dialog
# ---------------------------------------------------------------------------

class WxConnectionDialog:
    """wx-native profile editor.

    Usage:
        dlg = WxConnectionDialog(parent, initial_profile=None, mode="add",
                                 on_save=callable, on_save_and_connect=callable)
        result = dlg.ShowModal()
    For testability the dialog logic is separated from wx top-level handling
    where possible.
    """

    def __init__(
        self,
        parent,
        *,
        initial_profile: dict[str, Any] | None = None,
        mode: str = "add",
        on_save: Callable[[dict[str, Any]], bool] | None = None,
        on_save_and_connect: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        try:
            import wx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("wxPython is not installed") from exc
        self._wx = wx
        self.parent = parent
        self.mode = mode if mode in ("add", "edit", "duplicate") else "add"
        self._initial_profile: dict[str, Any] = dict(initial_profile or {})
        self._on_save = on_save
        self._on_save_and_connect = on_save_and_connect
        self._provider_template: dict[str, Any] | None = (
            deepcopy(self._initial_profile.get("provider_template"))
            if isinstance(self._initial_profile.get("provider_template"), dict)
            else None
        )
        source = self._initial_profile.get("system_template_source")
        self._system_template_source: dict[str, str] | None = (
            {str(k): str(v) for k, v in source.items()} if isinstance(source, dict) else None
        )
        self._provider_origin = "plugin" if self._provider_template is not None and self._system_template_source and self._system_template_source.get("kind") == "plugin" else ("local" if self._provider_template is not None else None)
        if self._provider_template is not None and self._provider_origin is None:
            self._provider_origin = "local"
        self._template_action_taken = False
        self._legacy_storage_snapshot: dict[str, str] = {}
        self._keepalive_default = coerce_keepalive_interval(self._initial_profile.get("keepalive_interval_seconds", 30))
        self._transfer_parallelism_default = coerce_profile_transfer_parallelism(self._initial_profile.get("transfer_parallelism", 1))
        self._ssh_timeout_default = coerce_profile_ssh_timeout(self._initial_profile.get("ssh_timeout"))

        self._build_dialog()

    # -- UI construction -----------------------------------------------------

    def _build_dialog(self) -> None:
        wx = self._wx
        parent = self.parent
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        dlg_title = {
            "add": t("connection.dialog_title"),
            "edit": t("connection.edit_dialog_title"),
            "duplicate": t("login.duplicate"),
        }.get(self.mode, t("connection.dialog_title"))
        self.dlg = wx.Dialog(parent, title=dlg_title, style=style)
        self.dlg.SetMinSize(wx.Size(720, 560))
        # Content scrolled window
        scrolled = wx.ScrolledWindow(self.dlg, style=wx.VSCROLL)
        scrolled.SetScrollRate(5, 5)
        content = wx.BoxSizer(wx.VERTICAL)

        # Profile section
        profile_box = wx.StaticBox(scrolled, label=t("connection.profile_section") if t("connection.profile_section") != "[connection.profile_section]" else "Profile")
        profile_sizer = wx.StaticBoxSizer(profile_box, wx.VERTICAL)
        profile_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        profile_grid.AddGrowableCol(1, 1)
        self.profile_name_ctrl = wx.TextCtrl(scrolled)
        self.profile_name_ctrl.SetHint(t("login.profile_name_label"))
        profile_grid.Add(wx.StaticText(scrolled, label=t("login.profile_name_label")), 0, wx.ALIGN_CENTER_VERTICAL)
        profile_grid.Add(self.profile_name_ctrl, 1, wx.EXPAND)

        # Provider template row: button with menu + save template button
        tmpl_label = wx.StaticText(scrolled, label=t("connection.system_templates_menu") if t("connection.system_templates_menu") != "[connection.system_templates_menu]" else "Provider / System template")
        tmpl_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_system_templates = wx.Button(scrolled, label=t("connection.system_templates_menu"))
        self.btn_save_system_template = wx.Button(scrolled, label=t("connection.save_system_template"))
        tmpl_row.Add(self.btn_system_templates, 0, wx.RIGHT, 8)
        tmpl_row.Add(self.btn_save_system_template, 0)
        profile_grid.Add(tmpl_label, 0, wx.ALIGN_CENTER_VERTICAL)
        profile_grid.Add(tmpl_row, 1, wx.EXPAND)
        # Provider info line
        self.provider_info = wx.StaticText(scrolled, label="")
        self.provider_info.SetForegroundColour(wx.Colour(90, 90, 90))
        profile_grid.Add(wx.StaticText(scrolled, label=""), 0)
        profile_grid.Add(self.provider_info, 0, wx.TOP, 2)

        profile_sizer.Add(profile_grid, 0, wx.EXPAND | wx.ALL, 8)
        content.Add(profile_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Connection section
        conn_box = wx.StaticBox(scrolled, label=t("connection.connection_section") if t("connection.connection_section") != "[connection.connection_section]" else "Connection")
        # Fallback label if key missing
        if conn_box.GetLabel() in ("[connection.connection_section]", "connection.connection_section"):
            conn_box.SetLabelText("Connection")
        conn_sizer = wx.StaticBoxSizer(conn_box, wx.VERTICAL)
        conn_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        conn_grid.AddGrowableCol(1, 1)
        self.host_ctrl = wx.TextCtrl(scrolled)
        self.host_ctrl.SetHint(t("login.host"))
        self.port_ctrl = wx.TextCtrl(scrolled, value="22")
        self.port_ctrl.SetHint("22")
        self.username_ctrl = wx.TextCtrl(scrolled)
        self.username_ctrl.SetHint(t("login.username"))
        self.project_label = wx.StaticText(scrolled, label=t("connection.project"))
        self.project_ctrl = wx.TextCtrl(scrolled)
        self.project_ctrl.SetHint(t("connection.project"))
        self.account_label = wx.StaticText(scrolled, label=t("connection.account"))
        self.account_ctrl = wx.TextCtrl(scrolled)
        self.account_ctrl.SetHint(t("connection.account"))

        def add_conn_row(label_widget, ctrl):
            # label_widget may be StaticText already
            if isinstance(label_widget, str):
                lbl = wx.StaticText(scrolled, label=label_widget)
            else:
                lbl = label_widget
            conn_grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            conn_grid.Add(ctrl, 1, wx.EXPAND)

        add_conn_row(wx.StaticText(scrolled, label=t("login.host")), self.host_ctrl)
        add_conn_row(wx.StaticText(scrolled, label=t("login.port")), self.port_ctrl)
        add_conn_row(wx.StaticText(scrolled, label=t("login.username")), self.username_ctrl)
        add_conn_row(self.project_label, self.project_ctrl)
        add_conn_row(self.account_label, self.account_ctrl)
        conn_sizer.Add(conn_grid, 0, wx.EXPAND | wx.ALL, 8)
        content.Add(conn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Authentication section
        auth_box = wx.StaticBox(scrolled, label=t("connection.auth_section") if t("connection.auth_section") != "[connection.auth_section]" else "Authentication")
        if auth_box.GetLabel().startswith("["):
            auth_box.SetLabelText("Authentication")
        auth_sizer = wx.StaticBoxSizer(auth_box, wx.VERTICAL)
        auth_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        auth_grid.AddGrowableCol(1, 1)
        self.password_ctrl = wx.TextCtrl(scrolled, style=wx.TE_PASSWORD)
        self.password_ctrl.SetHint(t("login.password"))
        auth_grid.Add(wx.StaticText(scrolled, label=t("login.password")), 0, wx.ALIGN_CENTER_VERTICAL)
        auth_grid.Add(self.password_ctrl, 1, wx.EXPAND)
        self.cb_save_password = wx.CheckBox(scrolled, label=t("login.save_password"))
        auth_grid.Add(wx.StaticText(scrolled, label=""), 0)
        auth_grid.Add(self.cb_save_password, 0, wx.ALIGN_CENTER_VERTICAL)
        # Prompt policy radios
        self.rb_prompt_when_needed = wx.RadioButton(scrolled, label=t("connection.password_no_prompt") if False else "Ask when needed", style=wx.RB_GROUP)
        # Qt uses two checkboxes: save password enables edit-only; we'll use radios similarly
        # Actually map: rb.when-needed = Ask when needed (default), rb.edit-only = Do not ask while connecting if secure system storage is available
        self.rb_prompt_when_needed.SetLabel("Ask when needed")
        # Try i18n for those; fallback to explicit English for now plus TR keys exist for edit-only
        # We'll set labels via t()
        try:
            # Use existing keys: connection.password_edit_only_tip etc but radio labels should be short
            # We'll use connection.password_no_prompt for edit-only variant text
            # Provide readable labels
            self.rb_prompt_when_needed.SetLabel(t("connection.password_prompt_when_needed") if t("connection.password_prompt_when_needed") != "[connection.password_prompt_when_needed]" else "Ask when needed")
        except Exception:
            pass
        self.rb_prompt_edit_only = wx.RadioButton(scrolled, label=t("connection.password_no_prompt") if t("connection.password_no_prompt") != "[connection.password_no_prompt]" else "Do not ask while connecting if secure system storage is available")
        # Layout radios vertically
        radio_sizer = wx.BoxSizer(wx.VERTICAL)
        radio_sizer.Add(self.rb_prompt_when_needed, 0, wx.BOTTOM, 4)
        radio_sizer.Add(self.rb_prompt_edit_only, 0)
        auth_grid.Add(wx.StaticText(scrolled, label=t("connection.password_prompt_policy") if t("connection.password_prompt_policy") != "[connection.password_prompt_policy]" else "Password prompt"), 0, wx.ALIGN_CENTER_VERTICAL)
        auth_grid.Add(radio_sizer, 1, wx.EXPAND)
        # SSH key row
        self.key_path_ctrl = wx.TextCtrl(scrolled)
        self.key_path_ctrl.SetHint(t("login.ssh_key"))
        browse_key_btn = wx.Button(scrolled, label=t("login.browse"))
        key_row = wx.BoxSizer(wx.HORIZONTAL)
        key_row.Add(self.key_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        key_row.Add(browse_key_btn, 0)
        auth_grid.Add(wx.StaticText(scrolled, label=t("login.ssh_key")), 0, wx.ALIGN_CENTER_VERTICAL)
        auth_grid.Add(key_row, 1, wx.EXPAND)

        auth_sizer.Add(auth_grid, 0, wx.EXPAND | wx.ALL, 8)
        content.Add(auth_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Cluster Settings collapsible
        self.cluster_toggle = wx.ToggleButton(scrolled, label=(t("connection.system_settings") if t("connection.system_settings") != "[connection.system_settings]" else "Cluster Settings") + "  ▶")
        content.Add(self.cluster_toggle, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.cluster_panel = wx.Panel(scrolled)
        cluster_sizer = wx.BoxSizer(wx.VERTICAL)
        # System name / home / scratch
        sys_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        sys_grid.AddGrowableCol(1, 1)
        self.system_name_ctrl = wx.TextCtrl(self.cluster_panel)
        self.system_name_ctrl.SetHint(t("connection.system_name"))
        self.home_dir_ctrl = wx.TextCtrl(self.cluster_panel)
        self.home_dir_ctrl.SetHint(t("connection.home_dir"))
        self.scratch_dir_ctrl = wx.TextCtrl(self.cluster_panel)
        self.scratch_dir_ctrl.SetHint(t("connection.scratch_dir"))
        for lbl_key, ctrl in (
            ("connection.system_name", self.system_name_ctrl),
            ("connection.home_dir", self.home_dir_ctrl),
            ("connection.scratch_dir", self.scratch_dir_ctrl),
        ):
            lbl = wx.StaticText(self.cluster_panel, label=t(lbl_key))
            sys_grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            sys_grid.Add(ctrl, 1, wx.EXPAND)
        cluster_sizer.Add(sys_grid, 0, wx.EXPAND | wx.ALL, 8)
        # Storage areas
        storage_label = wx.StaticText(self.cluster_panel, label=t("connection.storage_areas"))
        cluster_sizer.Add(storage_label, 0, wx.LEFT | wx.TOP, 8)
        self.storage_list = wx.ListBox(self.cluster_panel, style=wx.LB_SINGLE)
        self.storage_list.SetMinSize(wx.Size(-1, 90))
        cluster_sizer.Add(self.storage_list, 0, wx.EXPAND | wx.ALL, 8)
        storage_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_storage_add = wx.Button(self.cluster_panel, label=t("connection.storage_add"))
        self.btn_storage_edit = wx.Button(self.cluster_panel, label=t("connection.storage_edit"))
        self.btn_storage_remove = wx.Button(self.cluster_panel, label=t("connection.storage_remove"))
        storage_btn_row.Add(self.btn_storage_add, 0, wx.RIGHT, 8)
        storage_btn_row.Add(self.btn_storage_edit, 0, wx.RIGHT, 8)
        storage_btn_row.Add(self.btn_storage_remove, 0)
        cluster_sizer.Add(storage_btn_row, 0, wx.LEFT | wx.BOTTOM, 8)
        # Scheduler commands
        self.squeue_ctrl = wx.TextCtrl(self.cluster_panel)
        self.sbatch_ctrl = wx.TextCtrl(self.cluster_panel)
        self.scancel_ctrl = wx.TextCtrl(self.cluster_panel)
        self.sacct_ctrl = wx.TextCtrl(self.cluster_panel)
        self.scontrol_ctrl = wx.TextCtrl(self.cluster_panel)
        self.status_cmd_ctrl = wx.TextCtrl(self.cluster_panel)
        self.active_job_ids_ctrl = wx.TextCtrl(self.cluster_panel)
        self.job_state_ctrl = wx.TextCtrl(self.cluster_panel)
        sched_grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=12)
        sched_grid.AddGrowableCol(1, 1)
        for lbl_key, ctrl in (
            ("connection.squeue_command", self.squeue_ctrl),
            ("connection.sbatch_command", self.sbatch_ctrl),
            ("connection.scancel_command", self.scancel_ctrl),
            ("connection.sacct_command", self.sacct_ctrl),
            ("connection.scontrol_command", self.scontrol_ctrl),
            ("connection.status_command", self.status_cmd_ctrl),
            ("connection.active_job_ids_command", self.active_job_ids_ctrl),
            ("connection.job_state_command", self.job_state_ctrl),
        ):
            lbl = wx.StaticText(self.cluster_panel, label=t(lbl_key))
            lbl.Wrap(360)
            sched_grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            sched_grid.Add(ctrl, 1, wx.EXPAND)
        cluster_sizer.Add(sched_grid, 0, wx.EXPAND | wx.ALL, 8)
        # Save template row inside cluster
        save_tmpl_row = wx.BoxSizer(wx.HORIZONTAL)
        # Reuse save template button already in profile? Keep separate add template here
        # The button added in profile sizer also does save; keep only one – we already have save in profile
        # Add quota group
        quota_box = wx.StaticBox(self.cluster_panel, label=t("connection.quota_settings"))
        if quota_box.GetLabel().startswith("["):
            quota_box.SetLabelText("Quota Settings")
        quota_sizer = wx.StaticBoxSizer(quota_box, wx.VERTICAL)
        self.quota_enabled_cb = wx.CheckBox(self.cluster_panel, label=t("connection.quota_enable"))
        self.quota_consent_cb = wx.CheckBox(self.cluster_panel, label=t("connection.quota_consent"))
        self.quota_backend_choice = wx.Choice(self.cluster_panel, choices=[t("connection.quota_status_unconfigured") if t("connection.quota_status_unconfigured") != "[connection.quota_status_unconfigured]" else "Unconfigured"])
        self.quota_backend_choice.SetSelection(0)
        self.quota_command_ctrl = wx.TextCtrl(self.cluster_panel)
        self.quota_command_ctrl.SetHint(t("connection.quota_command"))
        self.quota_scope_ctrl = wx.TextCtrl(self.cluster_panel)
        self.quota_scope_ctrl.SetHint(t("connection.quota_scope"))
        self.quota_subject_ctrl = wx.TextCtrl(self.cluster_panel)
        self.quota_subject_ctrl.SetHint(t("connection.quota_subject"))
        self.quota_status_label = wx.StaticText(self.cluster_panel, label=t("connection.quota_status_off") if t("connection.quota_status_off") != "[connection.quota_status_off]" else "Quota monitoring is off.")
        self.quota_status_label.Wrap(500)
        # Quota grid
        quota_grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=12)
        quota_grid.AddGrowableCol(1, 1)
        quota_grid.Add(self.quota_enabled_cb, 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_consent_cb, 0, wx.ALIGN_CENTER_VERTICAL)
        # Backend row
        quota_grid.Add(wx.StaticText(self.cluster_panel, label=t("connection.quota_backend")), 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_backend_choice, 1, wx.EXPAND)
        self.quota_command_label = wx.StaticText(self.cluster_panel, label=t("connection.quota_command"))
        quota_grid.Add(self.quota_command_label, 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_command_ctrl, 1, wx.EXPAND)
        quota_grid.Add(wx.StaticText(self.cluster_panel, label=t("connection.quota_scope")), 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_scope_ctrl, 1, wx.EXPAND)
        quota_grid.Add(wx.StaticText(self.cluster_panel, label=t("connection.quota_subject")), 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_subject_ctrl, 1, wx.EXPAND)
        quota_sizer.Add(quota_grid, 0, wx.EXPAND | wx.ALL, 8)
        quota_sizer.Add(self.quota_status_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        cluster_sizer.Add(quota_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.cluster_panel.SetSizer(cluster_sizer)
        self.cluster_panel.Hide()
        content.Add(self.cluster_panel, 0, wx.EXPAND | wx.ALL, 8)

        # Advanced SSH / Client Settings collapsible
        self.advanced_toggle = wx.ToggleButton(scrolled, label=(t("connection.advanced_settings") if t("connection.advanced_settings") != "[connection.advanced_settings]" else "Advanced Settings") + "  ▶")
        content.Add(self.advanced_toggle, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.advanced_panel = wx.Panel(scrolled)
        adv_sizer = wx.BoxSizer(wx.VERTICAL)

        # SSH group
        ssh_box = wx.StaticBox(self.advanced_panel, label=t("connection.ssh_group"))
        if ssh_box.GetLabel().startswith("["):
            ssh_box.SetLabelText("SSH")
        ssh_sizer = wx.StaticBoxSizer(ssh_box, wx.VERTICAL)
        ssh_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        ssh_grid.AddGrowableCol(1, 1)
        self.cb_host_key_policy = wx.Choice(self.advanced_panel, choices=[t("connection.host_key_accept_new"), t("connection.host_key_strict")])
        self.cb_host_key_policy.SetSelection(0)
        self.cb_host_key_policy.SetToolTip(t("connection.host_key_verification_tip"))
        self.sp_keepalive = wx.SpinCtrl(self.advanced_panel, min=0, max=3600, initial=30)
        self.sp_keepalive.SetToolTip(t("connection.ssh_keepalive_tip"))
        self.sp_ssh_timeout = wx.SpinCtrlDouble(self.advanced_panel, min=0, max=600, initial=0, inc=0.5)
        self.sp_ssh_timeout.SetDigits(1)
        self.sp_ssh_timeout.SetToolTip(t("connection.ssh_timeout_override_tip"))
        # Jump host
        self.cb_jump_enabled = wx.CheckBox(self.advanced_panel, label=t("connection.jump_enable"))
        self.jump_host_ctrl = wx.TextCtrl(self.advanced_panel)
        self.jump_host_ctrl.SetHint(t("connection.jump_host_label"))
        self.sp_jump_port = wx.SpinCtrl(self.advanced_panel, min=1, max=65535, initial=22)
        self.jump_username_ctrl = wx.TextCtrl(self.advanced_panel)
        self.jump_username_ctrl.SetHint(t("connection.jump_username"))
        self.jump_key_path_ctrl = wx.TextCtrl(self.advanced_panel)
        self.jump_key_path_ctrl.SetHint(t("connection.jump_ssh_key"))
        btn_jump_browse = wx.Button(self.advanced_panel, label=t("login.browse"))
        jump_key_row = wx.BoxSizer(wx.HORIZONTAL)
        jump_key_row.Add(self.jump_key_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        jump_key_row.Add(btn_jump_browse, 0)
        self.cb_jump_host_key_policy = wx.Choice(self.advanced_panel, choices=[t("connection.host_key_accept_new"), t("connection.host_key_strict")])
        self.cb_jump_host_key_policy.SetSelection(0)

        # Add to grid
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.host_key_verification")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.cb_host_key_policy, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.ssh_keepalive_interval")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_keepalive, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.ssh_timeout_override")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_ssh_timeout, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=""), 0)
        ssh_grid.Add(self.cb_jump_enabled, 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.jump_host_label")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.jump_host_ctrl, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.jump_port")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_jump_port, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.jump_username")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.jump_username_ctrl, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.jump_ssh_key")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(jump_key_row, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.jump_host_key_verification")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.cb_jump_host_key_policy, 1, wx.EXPAND)
        ssh_sizer.Add(ssh_grid, 0, wx.EXPAND | wx.ALL, 8)
        adv_sizer.Add(ssh_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Transfers group
        transfers_box = wx.StaticBox(self.advanced_panel, label=t("connection.transfers_group"))
        if transfers_box.GetLabel().startswith("["):
            transfers_box.SetLabelText("Transfers")
        transfers_sizer = wx.StaticBoxSizer(transfers_box, wx.VERTICAL)
        transfers_grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        transfers_grid.AddGrowableCol(1, 1)
        self.sp_transfer_parallelism = wx.SpinCtrl(self.advanced_panel, min=1, max=10, initial=1)
        self.sp_transfer_parallelism.SetToolTip(t("connection.max_simultaneous_transfers_tip"))
        transfers_grid.Add(wx.StaticText(self.advanced_panel, label=t("connection.max_simultaneous_transfers")), 0, wx.ALIGN_CENTER_VERTICAL)
        transfers_grid.Add(self.sp_transfer_parallelism, 1, wx.EXPAND)
        transfers_sizer.Add(transfers_grid, 0, wx.EXPAND | wx.ALL, 8)
        adv_sizer.Add(transfers_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Other group
        other_box = wx.StaticBox(self.advanced_panel, label=t("connection.other_group"))
        if other_box.GetLabel().startswith("["):
            other_box.SetLabelText("Other")
        other_sizer = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        self.cb_x11 = wx.CheckBox(self.advanced_panel, label=t("login.x11_enable"))
        self.cb_cli_allowed = wx.CheckBox(self.advanced_panel, label=t("connection.cli_allowed"))
        self.default_local_dir_ctrl = wx.TextCtrl(self.advanced_panel)
        self.default_local_dir_ctrl.SetHint(t("connection.default_local_dir"))
        btn_local_browse = wx.Button(self.advanced_panel, label=t("connection.browse_default_local_folder") if t("connection.browse_default_local_folder") != "[connection.browse_default_local_folder]" else t("login.browse"))
        local_row = wx.BoxSizer(wx.HORIZONTAL)
        local_row.Add(self.default_local_dir_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        local_row.Add(btn_local_browse, 0)
        other_sizer.Add(self.cb_x11, 0, wx.BOTTOM, 4)
        other_sizer.Add(self.cb_cli_allowed, 0, wx.BOTTOM, 8)
        other_sizer.Add(wx.StaticText(self.advanced_panel, label=t("connection.default_local_dir")), 0, wx.BOTTOM, 4)
        other_sizer.Add(local_row, 0, wx.EXPAND)
        adv_sizer.Add(other_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.advanced_panel.SetSizer(adv_sizer)
        self.advanced_panel.Hide()
        content.Add(self.advanced_panel, 0, wx.EXPAND | wx.ALL, 8)

        scrolled.SetSizer(content)
        # Layout scrolled content before adding action row
        # Root sizer for dialog: scrolled on top, action row fixed at bottom
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(scrolled, 1, wx.EXPAND | wx.ALL, 8)
        # Action row
        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_test_cluster = wx.Button(self.dlg, label=t("connection.test_cluster"))
        self.btn_cancel = wx.Button(self.dlg, label=t("common.cancel"))
        self.btn_save = wx.Button(self.dlg, label=t("connection.save"))
        self.btn_save.SetDefault()
        self.btn_save_connect = wx.Button(self.dlg, label=t("connection.save_and_connect"))
        action_row.Add(self.btn_test_cluster, 0, wx.RIGHT, 8)
        action_row.AddStretchSpacer(1)
        action_row.Add(self.btn_cancel, 0, wx.RIGHT, 8)
        action_row.Add(self.btn_save, 0, wx.RIGHT, 8)
        action_row.Add(self.btn_save_connect, 0)
        root.Add(action_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.dlg.SetSizer(root)
        self.dlg.Fit()
        # Clamp to screen for DPI safety
        self.dlg.SetSizeHints(720, 520)
        # Ensure dialog not larger than display at high DPI
        try:
            display = wx.Display(0)
            area = display.GetClientArea()
            sz = self.dlg.GetSize()
            if sz.GetHeight() > area.GetHeight() - 40:
                self.dlg.SetSize(wx.Size(sz.GetWidth(), area.GetHeight() - 40))
            if sz.GetWidth() > area.GetWidth() - 40:
                self.dlg.SetSize(wx.Size(area.GetWidth() - 40, sz.GetHeight()))
        except Exception:
            pass

        self.scrolled = scrolled
        self.content = content
        # Bind events
        self._bind_events(browse_key_btn, btn_jump_browse, btn_local_browse)
        self._load_profile(self._initial_profile)
        self._rebuild_system_template_menu()
        self._update_provider_labels()
        self._update_quota_status()
        self._set_jump_children_enabled(self.cb_jump_enabled.GetValue())
        # Auth enable logic
        self.cb_save_password.Bind(wx.EVT_CHECKBOX, lambda e: self._on_save_password_toggle(e.IsChecked()))
        self._on_save_password_toggle(self.cb_save_password.GetValue())
        # Tab order is natural via creation order; ensure focus on first invalid after validation

    def _bind_events(self, browse_key_btn, btn_jump_browse, btn_local_browse) -> None:
        wx = self._wx
        self.cluster_toggle.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_cluster_visible(e.IsChecked()))
        self.advanced_toggle.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_advanced_visible(e.IsChecked()))
        self.btn_system_templates.Bind(wx.EVT_BUTTON, self._on_show_templates_menu)
        self.btn_save_system_template.Bind(wx.EVT_BUTTON, lambda e: self._save_current_system_template())
        browse_key_btn.Bind(wx.EVT_BUTTON, lambda e: self._pick_key(self.key_path_ctrl))
        btn_jump_browse.Bind(wx.EVT_BUTTON, lambda e: self._pick_key(self.jump_key_path_ctrl))
        btn_local_browse.Bind(wx.EVT_BUTTON, lambda e: self._pick_local_dir())
        self.btn_storage_add.Bind(wx.EVT_BUTTON, lambda e: self._add_storage_area())
        self.btn_storage_edit.Bind(wx.EVT_BUTTON, lambda e: self._edit_storage_area())
        self.btn_storage_remove.Bind(wx.EVT_BUTTON, lambda e: self._remove_storage_area())
        self.btn_test_cluster.Bind(wx.EVT_BUTTON, lambda e: self._test_cluster())
        self.btn_cancel.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        self.btn_save.Bind(wx.EVT_BUTTON, lambda e: self._save_clicked())
        self.btn_save_connect.Bind(wx.EVT_BUTTON, lambda e: self._save_and_connect_clicked())
        self.cb_jump_enabled.Bind(wx.EVT_CHECKBOX, lambda e: self._set_jump_children_enabled(e.IsChecked()))
        self.quota_enabled_cb.Bind(wx.EVT_CHECKBOX, lambda e: self._update_quota_status())
        self.quota_consent_cb.Bind(wx.EVT_CHECKBOX, lambda e: self._update_quota_status())
        self.quota_backend_choice.Bind(wx.EVT_CHOICE, lambda e: self._update_quota_status())
        self.quota_command_ctrl.Bind(wx.EVT_TEXT, lambda e: self._update_quota_status())
        self.quota_scope_ctrl.Bind(wx.EVT_TEXT, lambda e: self._update_quota_status())
        # Make Edit disabled until selection logic elsewhere

    # -- Helpers -------------------------------------------------------------

    def _set_cluster_visible(self, visible: bool) -> None:
        label_base = t("connection.system_settings") if t("connection.system_settings") != "[connection.system_settings]" else "Cluster Settings"
        self.cluster_toggle.SetLabel(f"{label_base}  {'▼' if visible else '▶'}")
        self.cluster_panel.Show(visible)
        self._relayout()

    def _set_advanced_visible(self, visible: bool) -> None:
        label_base = t("connection.advanced_settings") if t("connection.advanced_settings") != "[connection.advanced_settings]" else "Advanced Settings"
        self.advanced_toggle.SetLabel(f"{label_base}  {'▼' if visible else '▶'}")
        self.advanced_panel.Show(visible)
        self._relayout()

    def _relayout(self) -> None:
        self.scrolled.Layout()
        self.scrolled.FitInside()
        self.dlg.Layout()
        # Keep dialog within screen after expanding
        try:
            import wx as _wx
            display = _wx.Display(0)
            area = display.GetClientArea()
            sz = self.dlg.GetSize()
            if sz.GetHeight() > area.GetHeight() - 20:
                self.dlg.SetSize(_wx.Size(sz.GetWidth(), area.GetHeight() - 20))
        except Exception:
            pass

    def _set_jump_children_enabled(self, enabled: bool) -> None:
        for ctrl in (self.jump_host_ctrl, self.sp_jump_port, self.jump_username_ctrl, self.jump_key_path_ctrl, self.cb_jump_host_key_policy):
            ctrl.Enable(enabled)
        # Also browse button is inside sizer but we handle via its parent row; disabling key_path implies browse disabled logically but keep enabled for UI consistency
        # Find browse button via parent traversal not needed; we keep key path disable sufficient

    def _on_save_password_toggle(self, checked: bool) -> None:
        self.rb_prompt_when_needed.Enable(checked)
        self.rb_prompt_edit_only.Enable(checked)

    def _pick_key(self, target: Any) -> None:
        dlg = self._wx.FileDialog(self.dlg, t("login.ssh_key"), style=self._wx.FD_OPEN | self._wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == self._wx.ID_OK:
            target.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _pick_local_dir(self) -> None:
        dlg = self._wx.DirDialog(self.dlg, t("connection.browse_default_local_folder"), style=self._wx.DD_DEFAULT_STYLE | self._wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == self._wx.ID_OK:
            self.default_local_dir_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _update_provider_labels(self) -> None:
        provider = self._provider_template or {}
        requirements = provider.get("requirements", {}) if isinstance(provider, dict) else {}
        for key, label in (("project", self.project_label), ("account", self.account_label)):
            rule = requirements.get(key) if isinstance(requirements, dict) else None
            name = ""
            required = False
            help_text = ""
            if isinstance(rule, dict):
                name = str(rule.get("label") or t(f"connection.{key}"))
                required = bool(rule.get("required"))
                help_text = str(rule.get("help") or "")
            else:
                name = t(f"connection.{key}")
            display = name + (" *" if required else "")
            label.SetLabel(display)
            if help_text:
                label.SetToolTip(help_text)
            else:
                label.SetToolTip("")
        # Also update provider info line
        prov_name = ""
        if isinstance(self._provider_template, dict):
            prov_name = str(self._provider_template.get("name") or self._provider_template.get("profile_id") or "")
            if not prov_name and isinstance(self._provider_template.get("site"), dict):
                prov_name = str(self._provider_template.get("site").get("name") or "")
        if prov_name:
            self.provider_info.SetLabel(f"{t('connection.system_templates_menu')}: {prov_name}" if t("connection.system_templates_menu") != "[connection.system_templates_menu]" else f"Provider: {prov_name}")
        else:
            self.provider_info.SetLabel("")

    def _update_quota_status(self) -> None:
        state = quota_gate(
            {
                "enabled": self.quota_enabled_cb.GetValue(),
                "consent": self.quota_consent_cb.GetValue(),
                "backend_id": str(self.quota_backend_choice.GetStringSelection() or "").strip() if self.quota_backend_choice.GetStringSelection() != t("connection.quota_status_unconfigured") else "",
                "command_template": self.quota_command_ctrl.GetValue().strip(),
                "scope": self.quota_scope_ctrl.GetValue().strip(),
            },
            backend_ids=(),
        )
        # Map to label; avoid color-only signal
        if state == "disabled":
            self.quota_status_label.SetLabel(t("connection.quota_status_off"))
        elif state == "not_configured":
            self.quota_status_label.SetLabel(t("connection.quota_status_unconfigured"))
        elif state == "invalid_configuration":
            self.quota_status_label.SetLabel(t("connection.quota_status_invalid"))
        else:
            self.quota_status_label.SetLabel(t("connection.quota_status_backend_required"))
        self.quota_status_label.Wrap(500)
        self.scrolled.Layout()

    # -- Template handling ---------------------------------------------------

    def _rebuild_system_template_menu(self) -> None:
        # Build menu structure for provider selection; called at init and after save template
        # We keep menu data for popup; actual menu built on demand in _on_show_templates_menu
        pass

    def _on_show_templates_menu(self, event) -> None:
        wx = self._wx
        menu = wx.Menu()
        # Builtin
        for group_name, templates in builtin_system_template_groups().items():
            submenu = wx.Menu()
            for tmpl in templates:
                item = submenu.Append(wx.ID_ANY, tmpl["name"])
                # Capture template copy
                def _handler(evt, selected=dict(tmpl)):
                    self._apply_system_template(selected, structured=selected.get("provider_template"))
                self.dlg.Bind(wx.EVT_MENU, _handler, item)
            menu.AppendSubMenu(submenu, group_name)
        # Plugin templates
        plugin_groups = installed_cluster_template_groups()
        if plugin_groups:
            plugin_menu = wx.Menu()
            for group_name, templates in sorted(plugin_groups.items()):
                if len(templates) == 1:
                    target_menu = plugin_menu
                    for tmpl in templates:
                        item = target_menu.Append(wx.ID_ANY, tmpl.settings.get("name", group_name))
                        def _handler2(evt, selected=dict(tmpl.settings), provenance=dict(tmpl.provenance), structured=dict(tmpl.structured)):
                            self._apply_system_template(selected, provenance, structured)
                        self.dlg.Bind(wx.EVT_MENU, _handler2, item)
                else:
                    sub = wx.Menu()
                    for tmpl in templates:
                        item = sub.Append(wx.ID_ANY, tmpl.settings.get("name", group_name))
                        def _handler3(evt, selected=dict(tmpl.settings), provenance=dict(tmpl.provenance), structured=dict(tmpl.structured)):
                            self._apply_system_template(selected, provenance, structured)
                        self.dlg.Bind(wx.EVT_MENU, _handler3, item)
                    plugin_menu.AppendSubMenu(sub, group_name)
            menu.AppendSubMenu(plugin_menu, t("connection.plugin_templates"))
        # User templates
        user_templates = load_user_system_templates()
        if user_templates:
            user_menu = wx.Menu()
            for tmpl in user_templates:
                item = user_menu.Append(wx.ID_ANY, tmpl["name"])
                def _handler4(evt, selected=dict(tmpl)):
                    self._apply_system_template(selected)
                self.dlg.Bind(wx.EVT_MENU, _handler4, item)
            menu.AppendSubMenu(user_menu, t("connection.user_templates"))
        menu.AppendSeparator()
        more = menu.Append(wx.ID_ANY, t("connection.get_more_plugins"))
        def _more_handler(evt):
            # Route to plugin manager via callback if parent has shell; otherwise just show info
            try:
                # Try to dispatch through parent frame if it exposes plugin browse
                # For tests, this is a no-op but must not raise.
                pass
            except Exception:
                pass
            wx.MessageBox(t("connection.get_more_plugins"), t("common.info"), wx.OK | wx.ICON_INFORMATION)
        self.dlg.Bind(wx.EVT_MENU, _more_handler, more)

        # Popup
        pos = self.btn_system_templates.GetPosition()
        # Need screen position: convert button position to screen
        btn_pos = self.btn_system_templates.ClientToScreen(wx.Point(0, self.btn_system_templates.GetSize().GetHeight()))
        self.dlg.PopupMenu(menu, self.dlg.ScreenToClient(btn_pos))
        menu.Destroy()

    def _apply_system_template(
        self,
        template: dict[str, Any],
        provenance: dict[str, str] | None = None,
        structured: dict[str, Any] | None = None,
    ) -> None:
        if structured is None and isinstance(template.get("provider_template"), dict):
            structured = template["provider_template"]
        self._system_template_source = dict(provenance) if provenance else None
        self._provider_template = deepcopy(structured) if structured else None
        self._provider_origin = "plugin" if provenance and structured else ("local" if structured else None)
        self._template_action_taken = True
        system = normalize_system_settings(template)
        self.system_name_ctrl.SetValue(system["name"])
        self.scratch_dir_ctrl.SetValue(system["scratch_dir"])
        self.home_dir_ctrl.SetValue(system["home_dir"])
        self._legacy_storage_snapshot = {
            "home_dir": self.home_dir_ctrl.GetValue().strip(),
            "scratch_dir": self.scratch_dir_ctrl.GetValue().strip(),
        }
        self.squeue_ctrl.SetValue(system["squeue_command"])
        self.sbatch_ctrl.SetValue(system["sbatch_command"])
        self.scancel_ctrl.SetValue(system["scancel_command"])
        self.sacct_ctrl.SetValue(system["sacct_command"])
        self.scontrol_ctrl.SetValue(system["scontrol_command"])
        self.status_cmd_ctrl.SetValue(system["status_command"])
        self.active_job_ids_ctrl.SetValue(system["active_job_ids_command"])
        self.job_state_ctrl.SetValue(system["job_state_command"])
        self._update_storage_summary()
        self._load_quota_widgets()
        self._update_provider_labels()

    def _refresh_storage_list(self) -> None:
        self.storage_list.Clear()
        for row in getattr(self, "storage_rows", []):
            label = str(row.get("label") or row.get("id") or "Storage")
            path = str(row.get("path_template") or "").strip()
            display = f"{label}: {path}" if path else f"{label} ({t('connection.storage_areas_empty')})"
            self.storage_list.Append(display)

    def _update_storage_summary(self) -> None:
        rows = (self._provider_template or {}).get("storage", [])
        if not isinstance(rows, list):
            rows = []
        # Sync internal rows list
        self.storage_rows: list[dict[str, Any]] = [dict(r) for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        # Update list box
        self._refresh_storage_list()

    def _load_quota_widgets(self) -> None:
        sources = (self._provider_template or {}).get("quota_sources", [])
        source = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else {}
        self.quota_enabled_cb.SetValue(source.get("enabled") is True)
        self.quota_consent_cb.SetValue(source.get("consent") is True)
        backend_id = str(source.get("backend_id") or "").strip()
        # Populate backend choices from production registry plus current
        try:
            from hpc_gui.services.quota_monitor import build_production_quota_backend_registry
            registry_ids = sorted(build_production_quota_backend_registry().ids)
        except Exception:
            registry_ids = []
        choices = [t("connection.quota_status_unconfigured")]
        # Build choices list including registry ids and current if unsupported
        for bid in registry_ids:
            if bid not in choices:
                choices.append(bid)
        if backend_id and backend_id not in choices:
            choices.append(f"{backend_id} (unsupported)")
        self.quota_backend_choice.Clear()
        for c in choices:
            self.quota_backend_choice.Append(c)
        # Select
        if backend_id:
            # Find exact or unsupported variant
            idx = self._wx.NOT_FOUND
            for i, c in enumerate(choices):
                if c == backend_id or c.startswith(backend_id + " "):
                    idx = i
                    break
            if idx != self._wx.NOT_FOUND:
                self.quota_backend_choice.SetSelection(idx)
            else:
                self.quota_backend_choice.SetSelection(0)
        else:
            self.quota_backend_choice.SetSelection(0)
        self.quota_command_ctrl.SetValue(str(source.get("command_template") or ""))
        self.quota_scope_ctrl.SetValue(str(source.get("scope") or ""))
        self.quota_subject_ctrl.SetValue(str(source.get("subject_template") or ""))
        local = self._provider_origin == "local"
        # Hide quota command/scope/subject when local without backend? Mirror Qt: when local, hide those
        for ctrl in (self.quota_command_label, self.quota_command_ctrl,):
            ctrl.Show(not local)
        # Use 2-col handling: scope/subject labels need to be shown/hidden too
        # For simplicity, disable instead of hide for scope/subject when local
        if local:
            self.quota_command_ctrl.SetValue("")
            self.quota_scope_ctrl.SetValue("")
            self.quota_subject_ctrl.SetValue("")
        self._update_quota_status()
        self.scrolled.Layout()

    def _save_current_system_template(self) -> None:
        wx = self._wx
        default_name = self.system_name_ctrl.GetValue().strip() or t("connection.custom_system_template")
        dlg = wx.TextEntryDialog(self.dlg, t("connection.system_template_name"), t("connection.save_system_template"), value=default_name)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        name = dlg.GetValue().strip()
        dlg.Destroy()
        if not name:
            wx.MessageBox(t("connection.system_template_name_required"), t("common.error"), wx.OK | wx.ICON_WARNING)
            return
        try:
            save_user_system_template(name, self._system_form_values())
        except ValueError as exc:
            wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_WARNING)
            return
        self._rebuild_system_template_menu()

    def _system_form_values(self) -> dict[str, Any]:
        self._sync_structured_editor()
        values: dict[str, Any] = {
            "name": self.system_name_ctrl.GetValue().strip(),
            "scratch_dir": self.scratch_dir_ctrl.GetValue().strip(),
            "home_dir": self.home_dir_ctrl.GetValue().strip(),
            "squeue_command": self.squeue_ctrl.GetValue().strip(),
            "sbatch_command": self.sbatch_ctrl.GetValue().strip(),
            "scancel_command": self.scancel_ctrl.GetValue().strip(),
            "sacct_command": self.sacct_ctrl.GetValue().strip(),
            "scontrol_command": self.scontrol_ctrl.GetValue().strip(),
            "status_command": self.status_cmd_ctrl.GetValue().strip(),
            "active_job_ids_command": self.active_job_ids_ctrl.GetValue().strip(),
            "job_state_command": self.job_state_ctrl.GetValue().strip(),
        }
        if self._provider_template is not None:
            values["provider_template"] = {k: v for k, v in self._provider_template.items()}
        return values

    def _sync_legacy_storage_paths(self) -> None:
        for key, kind in (("home_dir", "home"), ("scratch_dir", "scratch")):
            ctrl = getattr(self, f"{key}_ctrl")
            current = ctrl.GetValue().strip()
            previous = self._legacy_storage_snapshot.get(key, current)
            rows = [row for row in getattr(self, "storage_rows", []) if row.get("kind") == kind or row.get("id") == kind]
            if current != previous:
                for row in rows:
                    row["path_template"] = current
            elif rows and rows[0].get("path_template"):
                current = str(rows[0]["path_template"]).strip()
                ctrl.SetValue(current)
            self._legacy_storage_snapshot[key] = current

    def _sync_structured_editor(self) -> None:
        feature_used = bool(getattr(self, "storage_rows", [])) or self.quota_enabled_cb.GetValue()
        feature_used = feature_used or bool(self.quota_scope_ctrl.GetValue().strip())
        feature_used = feature_used or bool(self.quota_subject_ctrl.GetValue().strip())
        # Check backend selection non-empty
        sel = self.quota_backend_choice.GetStringSelection() if self.quota_backend_choice.GetSelection() != self._wx.NOT_FOUND else ""
        if sel and sel != t("connection.quota_status_unconfigured"):
            feature_used = True
        if self._provider_template is None and not feature_used:
            return
        if self._provider_template is None:
            self._provider_template = {
                "schema_version": 2,
                "profile_id": "local",
                "name": self.system_name_ctrl.GetValue().strip() or "Custom HPC",
                "scheduler": "slurm",
                "storage": [],
                "quota_sources": [],
            }
            self._provider_origin = "local"
        self._sync_legacy_storage_paths()
        # Sync storage
        self._provider_template["storage"] = [dict(row) for row in getattr(self, "storage_rows", [])]
        sources = self._provider_template.get("quota_sources")
        preserved = [dict(item) for item in sources if isinstance(item, dict)] if isinstance(sources, list) else []
        source = dict(preserved[0]) if preserved else {"id": "local-quota"}
        backend_sel = self.quota_backend_choice.GetStringSelection() if self.quota_backend_choice.GetSelection() != self._wx.NOT_FOUND else ""
        if backend_sel == t("connection.quota_status_unconfigured"):
            backend_sel = ""
        # Strip unsupported suffix
        if " (unsupported)" in backend_sel:
            backend_sel = backend_sel.split(" ")[0]
        source.update({
            "enabled": self.quota_enabled_cb.GetValue(),
            "consent": self.quota_consent_cb.GetValue(),
            "backend_id": backend_sel.strip(),
            "command_template": "" if self._provider_origin == "local" else self.quota_command_ctrl.GetValue().strip(),
            "scope": self.quota_scope_ctrl.GetValue().strip(),
            "subject_template": self.quota_subject_ctrl.GetValue().strip(),
        })
        self._provider_template["quota_sources"] = [source, *preserved[1:]]

    # -- Storage add/edit/remove -------------------------------------------

    def _add_storage_area(self) -> None:
        # Ensure provider template exists for local edits
        if self._provider_template is None:
            self._provider_template = {
                "schema_version": 2,
                "profile_id": "local",
                "name": self.system_name_ctrl.GetValue().strip() or "Custom HPC",
                "scheduler": "slurm",
                "storage": [],
                "quota_sources": [],
            }
            self._provider_origin = "local"
        # Use helper dialog
        existing_ids = {str(row.get("id")) for row in getattr(self, "storage_rows", [])}
        area = _show_storage_area_dialog(self.dlg, None)
        if area is None:
            return
        # Ensure unique id
        base_id = str(area.get("id") or "storage")
        area_id = base_id
        suffix = 2
        while area_id in existing_ids:
            area_id = f"{base_id}-{suffix}"
            suffix += 1
        area["id"] = area_id
        if validate_storage_area(area):
            self._wx.MessageBox(validate_storage_area(area) or t("connection.storage_path_invalid"), t("common.error"), self._wx.OK | self._wx.ICON_WARNING)
            return
        self.storage_rows.append(area)
        self._sync_structured_editor()
        self._refresh_storage_list()

    def _edit_storage_area(self) -> None:
        sel = self.storage_list.GetSelection()
        if sel == self._wx.NOT_FOUND or sel >= len(getattr(self, "storage_rows", [])):
            return
        current = self.storage_rows[sel]
        updated = _show_storage_area_dialog(self.dlg, current)
        if updated is None:
            return
        if validate_storage_area(updated):
            self._wx.MessageBox(validate_storage_area(updated) or t("connection.storage_path_invalid"), t("common.error"), self._wx.OK | self._wx.ICON_WARNING)
            return
        # Preserve id uniqueness not needed for edit
        self.storage_rows[sel] = updated
        self._sync_structured_editor()
        self._refresh_storage_list()

    def _remove_storage_area(self) -> None:
        sel = self.storage_list.GetSelection()
        if sel != self._wx.NOT_FOUND and sel < len(getattr(self, "storage_rows", [])):
            self.storage_rows.pop(sel)
            self._sync_structured_editor()
            self._refresh_storage_list()

    # -- Load / collect ----------------------------------------------------

    def _load_profile(self, profile: dict[str, Any]) -> None:
        self.profile_name_ctrl.SetValue(str(profile.get("name", "")))
        self.host_ctrl.SetValue(str(profile.get("host", "")))
        self.port_ctrl.SetValue(str(profile.get("port", 22)))
        self.username_ctrl.SetValue(str(profile.get("username", "")))
        self.project_ctrl.SetValue(str(profile.get("project", "")))
        self.account_ctrl.SetValue(str(profile.get("account", "")))
        self.key_path_ctrl.SetValue(str(profile.get("key_path", "") or profile.get("ssh_key", "")))
        # Do not auto-populate password for security; keep empty unless legacy plaintext present for Add? Follow Qt: only show if save_password and password plaintext exists
        # For edit, never auto-fill saved encrypted
        if profile.get("save_password") and isinstance(profile.get("password"), str) and profile.get("password"):
            self.password_ctrl.SetValue(str(profile.get("password")))
        else:
            self.password_ctrl.SetValue("")
        self.cb_save_password.SetValue(bool(profile.get("save_password", False)))
        prompt_policy = str(profile.get("password_prompt_policy") or "when-needed")
        if prompt_policy == "edit-only":
            self.rb_prompt_edit_only.SetValue(True)
        else:
            self.rb_prompt_when_needed.SetValue(True)
        # Host key policy
        host_key_policy = str(profile.get("host_key_policy") or "accept-new").strip()
        if host_key_policy not in {"accept-new", "strict"}:
            host_key_policy = "accept-new"
        self.cb_host_key_policy.SetSelection(0 if host_key_policy == "accept-new" else 1)
        # Keepalive
        self.sp_keepalive.SetValue(coerce_keepalive_interval(profile.get("keepalive_interval_seconds", 30)))
        self.sp_transfer_parallelism.SetValue(coerce_profile_transfer_parallelism(profile.get("transfer_parallelism", 1)))
        self.sp_ssh_timeout.SetValue(coerce_profile_ssh_timeout(profile.get("ssh_timeout")) or 0)
        self.cb_x11.SetValue(bool(profile.get("x11_forwarding", False)))
        self.cb_cli_allowed.SetValue(bool(profile.get("cli_allowed", False)))
        # File manager
        fm = normalize_file_manager_settings(profile.get("file_manager"))
        self.default_local_dir_ctrl.SetValue(fm["local_start_dir"])
        # Jump host
        jump = normalize_jump_host_settings(profile.get("jump_host"))
        self.cb_jump_enabled.SetValue(bool(jump["enabled"]))
        self.jump_host_ctrl.SetValue(jump["host"])
        self.sp_jump_port.SetValue(int(jump["port"]))
        self.jump_username_ctrl.SetValue(jump["username"])
        self.jump_key_path_ctrl.SetValue(jump["key_path"])
        jump_policy = str(jump["host_key_policy"] or "accept-new").strip()
        self.cb_jump_host_key_policy.SetSelection(0 if jump_policy != "strict" else 1)
        # System
        system = normalize_system_settings(profile.get("system"))
        self.system_name_ctrl.SetValue(system["name"])
        self.scratch_dir_ctrl.SetValue(system["scratch_dir"])
        self.home_dir_ctrl.SetValue(system["home_dir"])
        self._legacy_storage_snapshot = {
            "home_dir": self.home_dir_ctrl.GetValue().strip(),
            "scratch_dir": self.scratch_dir_ctrl.GetValue().strip(),
        }
        self.squeue_ctrl.SetValue(system["squeue_command"])
        self.sbatch_ctrl.SetValue(system["sbatch_command"])
        self.scancel_ctrl.SetValue(system["scancel_command"])
        self.sacct_ctrl.SetValue(system["sacct_command"])
        self.scontrol_ctrl.SetValue(system["scontrol_command"])
        self.status_cmd_ctrl.SetValue(system["status_command"])
        self.active_job_ids_ctrl.SetValue(system["active_job_ids_command"])
        self.job_state_ctrl.SetValue(system["job_state_command"])
        self._update_storage_summary()
        self._load_quota_widgets()

    def _collect_profile(self) -> dict[str, Any] | None:
        wx = self._wx
        try:
            port = int(self.port_ctrl.GetValue().strip() or "22")
        except ValueError:
            wx.MessageBox(t("login.err_port_numeric"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.port_ctrl.SetFocus()
            return None
        if not (1 <= port <= 65535):
            wx.MessageBox(t("login.err_port_numeric"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.port_ctrl.SetFocus()
            return None
        host = self.host_ctrl.GetValue().strip()
        if not host:
            wx.MessageBox(t("login.err_host_required"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.host_ctrl.SetFocus()
            return None
        # Provider-required validation before assembling?
        # We validate after building provider context
        is_edit = bool(self._initial_profile)
        profile: dict[str, Any] = dict(self._initial_profile) if is_edit else {}
        # Basic patch
        profile.update({
            "name": self.profile_name_ctrl.GetValue().strip(),
            "host": host,
            "port": port,
            "username": self.username_ctrl.GetValue().strip(),
            "project": self.project_ctrl.GetValue().strip(),
            "account": self.account_ctrl.GetValue().strip(),
            "password": self.password_ctrl.GetValue(),
            "key_path": self.key_path_ctrl.GetValue().strip(),
            "host_key_policy": "strict" if self.cb_host_key_policy.GetSelection() == 1 else "accept-new",
            "x11_forwarding": self.cb_x11.GetValue(),
            "cli_allowed": self.cb_cli_allowed.GetValue(),
            "keepalive_interval_seconds": int(self.sp_keepalive.GetValue()),
            "transfer_parallelism": int(self.sp_transfer_parallelism.GetValue()),
            "ssh_timeout": float(self.sp_ssh_timeout.GetValue()) or None,
            "save_password": self.cb_save_password.GetValue(),
            "password_prompt_policy": "edit-only" if self.rb_prompt_edit_only.GetValue() else "when-needed",
            "system": {**self._system_form_values()},
        })
        # Clear secret material not to ride through; will be handled by shared service
        for sk in ("password_dpapi", "password_enc", "password_salt"):
            profile.pop(sk, None)
        # Provider template preservation logic mirrors Qt's _collect_profile
        if self._provider_template is not None:
            profile["provider_template"] = deepcopy(self._provider_template)
            if self._system_template_source:
                profile["system_template_source"] = dict(self._system_template_source)
        elif self._template_action_taken:
            if self._system_template_source:
                profile["system_template_source"] = dict(self._system_template_source)
            else:
                profile.pop("system_template_source", None)
            profile.pop("provider_template", None)
        elif not is_edit:
            profile.pop("system_template_source", None)

        profile["file_manager"] = patch_file_manager_settings(
            (self._initial_profile or {}).get("file_manager"),
            {"local_start_dir": self.default_local_dir_ctrl.GetValue().strip()},
        )
        if self.cb_jump_enabled.GetValue() and not self.jump_host_ctrl.GetValue().strip():
            wx.MessageBox(t("connection.jump_host_required"), t("common.error"), wx.OK | wx.ICON_WARNING)
            self.jump_host_ctrl.SetFocus()
            return None
        profile["jump_host"] = patch_jump_host_settings(
            (self._initial_profile or {}).get("jump_host"),
            {
                "enabled": self.cb_jump_enabled.GetValue(),
                "host": self.jump_host_ctrl.GetValue().strip(),
                "port": int(self.sp_jump_port.GetValue()),
                "username": self.jump_username_ctrl.GetValue().strip(),
                "key_path": self.jump_key_path_ctrl.GetValue().strip(),
                "host_key_policy": "strict" if self.cb_jump_host_key_policy.GetSelection() == 1 else "accept-new",
            },
        )
        # Provider-required project/account validation decoratively via provider metadata
        provider_meta = profile.get("system", {}).get("provider_template") if isinstance(profile.get("system"), dict) else profile.get("provider_template")
        if provider_meta is None:
            provider_meta = self._provider_template
        if isinstance(provider_meta, dict):
            requirements = provider_meta.get("requirements", {}) if isinstance(provider_meta.get("requirements"), dict) else {}
            for key, ctrl, label in (("project", self.project_ctrl, self.project_label), ("account", self.account_ctrl, self.account_label)):
                rule = requirements.get(key) if isinstance(requirements, dict) else None
                if isinstance(rule, dict) and rule.get("required") and not ctrl.GetValue().strip():
                    wx.MessageBox(f"{label.GetLabel().rstrip(' *')} is required for this provider.", t("login.err_title"), wx.OK | wx.ICON_WARNING)
                    ctrl.SetFocus()
                    return None
        # Fallback name handling
        if not profile.get("name"):
            username = profile.get("username", "").strip()
            host_val = profile.get("host", "").strip()
            fallback = f"{username}@{host_val}" if username else host_val
            if not fallback:
                wx.MessageBox(t("login.err_host_required"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
                return None
            profile["name"] = fallback
        return profile

    def _save_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        self.dlg.EndModal(wx.ID_OK)

    def _save_and_connect_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        if self._on_save_and_connect is not None and not self._on_save_and_connect(profile):
            return
        self.dlg.EndModal(wx.ID_OK)

    def _test_cluster(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        # wx-native adapter for shared self-test; keep async to not freeze GUI
        try:
            from hpc_gui.services.cluster_self_test import run_cluster_self_test
            from hpc_gui.ssh.client import SSHConnInfo
            from hpc_gui.config.storage import load_settings
            # Build minimal SSHConnInfo from profile; password not needed for dry probe
            info = SSHConnInfo(
                host=str(profile.get("host", "")),
                port=int(profile.get("port", 22)),
                username=str(profile.get("username", "")),
                password=str(profile.get("password", "")),
                key_path=str(profile.get("key_path", "")),
                host_key_policy=str(profile.get("host_key_policy", "accept-new")),
                x11_forwarding=bool(profile.get("x11_forwarding", False)),
                timeout=coerce_profile_ssh_timeout(profile.get("ssh_timeout")),
                keepalive_interval_seconds=coerce_keepalive_interval(profile.get("keepalive_interval_seconds", 30)),
            )
            provider = profile.get("provider_template") or profile.get("system", {}).get("provider_template") if isinstance(profile.get("system"), dict) else None
            # Show simple running dialog then execute sync for now (bounded)
            # For real implementation this would be threaded; here we run directly with mocked factories in tests
            result = run_cluster_self_test(info, provider=provider, project=str(profile.get("project", "")), account=str(profile.get("account", "")))
            # Present results in a wx dialog
            self._show_self_test_result(result)
        except Exception as exc:
            self._wx.MessageBox(str(exc), t("common.error"), self._wx.OK | self._wx.ICON_ERROR)

    def _show_self_test_result(self, result) -> None:
        wx = self._wx
        dlg = wx.Dialog(self.dlg, title=t("cluster_self_test.title") if t("cluster_self_test.title") != "[cluster_self_test.title]" else "Cluster Self-Test", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetMinSize(wx.Size(500, 400))
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Summary
        status_label = wx.StaticText(dlg, label=t("cluster_self_test.summary").format(status=result.status) if t("cluster_self_test.summary") != "[cluster_self_test.summary]" else f"Result: {result.status}")
        status_label.Wrap(480)
        sizer.Add(status_label, 0, wx.EXPAND | wx.ALL, 12)
        # Sections
        text = wx.TextCtrl(dlg, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        lines = []
        for sec in getattr(result, "sections", []):
            lines.append(f"[{sec.id}]")
            for item in sec.items:
                lines.append(f"  {item.id}: {item.status} {item.detail}")
        text.SetValue("\n".join(lines))
        sizer.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        btns = dlg.CreateStdDialogButtonSizer(wx.OK)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.ShowModal()
        dlg.Destroy()

    # -- Public API ----------------------------------------------------------

    def ShowModal(self) -> int:
        return self.dlg.ShowModal()

    def Destroy(self) -> None:
        self.dlg.Destroy()

    def GetDialog(self):
        return self.dlg


def show_connection_dialog(
    parent,
    *,
    initial_profile: dict[str, Any] | None = None,
    mode: str = "add",
    on_save: Callable[[dict[str, Any]], bool] | None = None,
    on_save_and_connect: Callable[[dict[str, Any]], bool] | None = None,
) -> int:
    """Convenience wrapper returning wx.ID_OK / wx.ID_CANCEL."""
    dlg = WxConnectionDialog(parent, initial_profile=initial_profile, mode=mode, on_save=on_save, on_save_and_connect=on_save_and_connect)
    try:
        return dlg.ShowModal()
    finally:
        dlg.Destroy()


__all__ = ["WxConnectionDialog", "show_connection_dialog"]
