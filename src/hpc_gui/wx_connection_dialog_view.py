"""ConnectionDialogViewMixin owns the view portion of the wx connection dialog."""

from __future__ import annotations

from hpc_gui.core.i18n import t

# Extracted dialog responsibility; behavior stays on the public dialog facade.

class ConnectionDialogViewMixin:
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
        self.profile_name_ctrl = wx.TextCtrl(profile_box)
        self.profile_name_ctrl.SetHint(t("login.profile_name_label"))
        profile_grid.Add(wx.StaticText(profile_box, label=t("login.profile_name_label")), 0, wx.ALIGN_CENTER_VERTICAL)
        profile_grid.Add(self.profile_name_ctrl, 1, wx.EXPAND)

        # Provider template row: button with menu + save template button
        tmpl_label = wx.StaticText(profile_box, label=t("connection.system_templates_menu") if t("connection.system_templates_menu") != "[connection.system_templates_menu]" else "Provider / System template")
        tmpl_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_system_templates = wx.Button(profile_box, label=t("connection.system_templates_menu"))
        self.btn_save_system_template = wx.Button(profile_box, label=t("connection.save_system_template"))
        tmpl_row.Add(self.btn_system_templates, 0, wx.RIGHT, 8)
        tmpl_row.Add(self.btn_save_system_template, 0)
        profile_grid.Add(tmpl_label, 0, wx.ALIGN_CENTER_VERTICAL)
        profile_grid.Add(tmpl_row, 1, wx.EXPAND)
        # Provider info line
        self.provider_info = wx.StaticText(profile_box, label="")
        self.provider_info.SetForegroundColour(wx.Colour(90, 90, 90))
        profile_grid.Add(wx.StaticText(profile_box, label=""), 0)
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
        self.host_ctrl = wx.TextCtrl(conn_box)
        self.host_ctrl.SetHint(t("login.host"))
        self.port_ctrl = wx.TextCtrl(conn_box, value="22")
        self.port_ctrl.SetHint("22")
        self.username_ctrl = wx.TextCtrl(conn_box)
        self.username_ctrl.SetHint(t("login.username"))
        self.project_label = wx.StaticText(conn_box, label=t("connection.project"))
        self.project_ctrl = wx.TextCtrl(conn_box)
        self.project_ctrl.SetHint(t("connection.project"))
        self.account_label = wx.StaticText(conn_box, label=t("connection.account"))
        self.account_ctrl = wx.TextCtrl(conn_box)
        self.account_ctrl.SetHint(t("connection.account"))

        def add_conn_row(label_widget, ctrl):
            # label_widget may be StaticText already
            if isinstance(label_widget, str):
                lbl = wx.StaticText(conn_box, label=label_widget)
            else:
                lbl = label_widget
            conn_grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            conn_grid.Add(ctrl, 1, wx.EXPAND)

        add_conn_row(wx.StaticText(conn_box, label=t("login.host")), self.host_ctrl)
        add_conn_row(wx.StaticText(conn_box, label=t("login.port")), self.port_ctrl)
        add_conn_row(wx.StaticText(conn_box, label=t("login.username")), self.username_ctrl)
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
        self.password_ctrl = wx.TextCtrl(auth_box, style=wx.TE_PASSWORD)
        self.password_ctrl.SetHint(t("login.password"))
        auth_grid.Add(wx.StaticText(auth_box, label=t("login.password")), 0, wx.ALIGN_CENTER_VERTICAL)
        auth_grid.Add(self.password_ctrl, 1, wx.EXPAND)
        self.cb_save_password = wx.CheckBox(auth_box, label=t("login.save_password"))
        auth_grid.Add(wx.StaticText(auth_box, label=""), 0)
        auth_grid.Add(self.cb_save_password, 0, wx.ALIGN_CENTER_VERTICAL)
        # Prompt policy radios
        self.rb_prompt_when_needed = wx.RadioButton(auth_box, label=t("connection.password_prompt_when_needed"), style=wx.RB_GROUP)
        # Qt uses two checkboxes: save password enables edit-only; we'll use radios similarly
        # Actually map: rb.when-needed = Ask when needed (default), rb.edit-only = Do not ask while connecting if secure system storage is available
        self.rb_prompt_edit_only = wx.RadioButton(auth_box, label=t("connection.password_no_prompt"))
        # Layout radios vertically
        radio_sizer = wx.BoxSizer(wx.VERTICAL)
        radio_sizer.Add(self.rb_prompt_when_needed, 0, wx.BOTTOM, 4)
        radio_sizer.Add(self.rb_prompt_edit_only, 0)
        auth_grid.Add(wx.StaticText(auth_box, label=t("connection.password_prompt_policy") if t("connection.password_prompt_policy") != "[connection.password_prompt_policy]" else "Password prompt"), 0, wx.ALIGN_CENTER_VERTICAL)
        auth_grid.Add(radio_sizer, 1, wx.EXPAND)
        # SSH key row
        self.key_path_ctrl = wx.TextCtrl(auth_box)
        self.key_path_ctrl.SetHint(t("login.ssh_key"))
        browse_key_btn = wx.Button(auth_box, label=t("login.browse"))
        key_row = wx.BoxSizer(wx.HORIZONTAL)
        key_row.Add(self.key_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        key_row.Add(browse_key_btn, 0)
        auth_grid.Add(wx.StaticText(auth_box, label=t("login.ssh_key")), 0, wx.ALIGN_CENTER_VERTICAL)
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
        # Add quota group
        quota_box = wx.StaticBox(self.cluster_panel, label=t("connection.quota_settings"))
        if quota_box.GetLabel().startswith("["):
            quota_box.SetLabelText("Quota Settings")
        quota_sizer = wx.StaticBoxSizer(quota_box, wx.VERTICAL)
        self.quota_enabled_cb = wx.CheckBox(quota_box, label=t("connection.quota_enable"))
        self.quota_consent_cb = wx.CheckBox(quota_box, label=t("connection.quota_consent"))
        self.quota_backend_choice = wx.Choice(quota_box, choices=[t("connection.quota_status_unconfigured") if t("connection.quota_status_unconfigured") != "[connection.quota_status_unconfigured]" else "Unconfigured"])
        self.quota_backend_choice.SetSelection(0)
        self.quota_command_ctrl = wx.TextCtrl(quota_box)
        self.quota_command_ctrl.SetHint(t("connection.quota_command"))
        self.quota_scope_ctrl = wx.TextCtrl(quota_box)
        self.quota_scope_ctrl.SetHint(t("connection.quota_scope"))
        self.quota_subject_ctrl = wx.TextCtrl(quota_box)
        self.quota_subject_ctrl.SetHint(t("connection.quota_subject"))
        self.quota_status_label = wx.StaticText(quota_box, label=t("connection.quota_status_off") if t("connection.quota_status_off") != "[connection.quota_status_off]" else "Quota monitoring is off.")
        self.quota_status_label.Wrap(500)
        # Quota grid
        quota_grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=12)
        quota_grid.AddGrowableCol(1, 1)
        quota_grid.Add(self.quota_enabled_cb, 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_consent_cb, 0, wx.ALIGN_CENTER_VERTICAL)
        # Backend row
        quota_grid.Add(wx.StaticText(quota_box, label=t("connection.quota_backend")), 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_backend_choice, 1, wx.EXPAND)
        self.quota_command_label = wx.StaticText(quota_box, label=t("connection.quota_command"))
        quota_grid.Add(self.quota_command_label, 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_command_ctrl, 1, wx.EXPAND)
        quota_grid.Add(wx.StaticText(quota_box, label=t("connection.quota_scope")), 0, wx.ALIGN_CENTER_VERTICAL)
        quota_grid.Add(self.quota_scope_ctrl, 1, wx.EXPAND)
        quota_grid.Add(wx.StaticText(quota_box, label=t("connection.quota_subject")), 0, wx.ALIGN_CENTER_VERTICAL)
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
        self.cb_host_key_policy = wx.Choice(ssh_box, choices=[t("connection.host_key_accept_new"), t("connection.host_key_strict")])
        self.cb_host_key_policy.SetSelection(0)
        self.cb_host_key_policy.SetToolTip(t("connection.host_key_verification_tip"))
        self.sp_keepalive = wx.SpinCtrl(ssh_box, min=0, max=3600, initial=30)
        self.sp_keepalive.SetToolTip(t("connection.ssh_keepalive_tip"))
        self.sp_ssh_timeout = wx.SpinCtrlDouble(ssh_box, min=0, max=600, initial=0, inc=0.5)
        self.sp_ssh_timeout.SetDigits(1)
        self.sp_ssh_timeout.SetToolTip(t("connection.ssh_timeout_override_tip"))
        # Jump host
        self.cb_jump_enabled = wx.CheckBox(ssh_box, label=t("connection.jump_enable"))
        self.jump_host_ctrl = wx.TextCtrl(ssh_box)
        self.jump_host_ctrl.SetHint(t("connection.jump_host_label"))
        self.sp_jump_port = wx.SpinCtrl(ssh_box, min=1, max=65535, initial=22)
        self.jump_username_ctrl = wx.TextCtrl(ssh_box)
        self.jump_username_ctrl.SetHint(t("connection.jump_username"))
        self.jump_key_path_ctrl = wx.TextCtrl(ssh_box)
        self.jump_key_path_ctrl.SetHint(t("connection.jump_ssh_key"))
        btn_jump_browse = wx.Button(ssh_box, label=t("login.browse"))
        self.btn_jump_browse = btn_jump_browse
        jump_key_row = wx.BoxSizer(wx.HORIZONTAL)
        jump_key_row.Add(self.jump_key_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        jump_key_row.Add(btn_jump_browse, 0)
        self.cb_jump_host_key_policy = wx.Choice(ssh_box, choices=[t("connection.host_key_accept_new"), t("connection.host_key_strict")])
        self.cb_jump_host_key_policy.SetSelection(0)

        # Add to grid
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.host_key_verification")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.cb_host_key_policy, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.ssh_keepalive_interval")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_keepalive, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.ssh_timeout_override")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_ssh_timeout, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=""), 0)
        ssh_grid.Add(self.cb_jump_enabled, 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.jump_host_label")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.jump_host_ctrl, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.jump_port")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.sp_jump_port, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.jump_username")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(self.jump_username_ctrl, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.jump_ssh_key")), 0, wx.ALIGN_CENTER_VERTICAL)
        ssh_grid.Add(jump_key_row, 1, wx.EXPAND)
        ssh_grid.Add(wx.StaticText(ssh_box, label=t("connection.jump_host_key_verification")), 0, wx.ALIGN_CENTER_VERTICAL)
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
        self.sp_transfer_parallelism = wx.SpinCtrl(transfers_box, min=1, max=10, initial=1)
        self.sp_transfer_parallelism.SetToolTip(t("connection.max_simultaneous_transfers_tip"))
        transfers_grid.Add(wx.StaticText(transfers_box, label=t("connection.max_simultaneous_transfers")), 0, wx.ALIGN_CENTER_VERTICAL)
        transfers_grid.Add(self.sp_transfer_parallelism, 1, wx.EXPAND)
        transfers_sizer.Add(transfers_grid, 0, wx.EXPAND | wx.ALL, 8)
        adv_sizer.Add(transfers_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Other group
        other_box = wx.StaticBox(self.advanced_panel, label=t("connection.other_group"))
        if other_box.GetLabel().startswith("["):
            other_box.SetLabelText("Other")
        other_sizer = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        self.cb_x11 = wx.CheckBox(other_box, label=t("login.x11_enable"))
        self.cb_cli_allowed = wx.CheckBox(other_box, label=t("connection.cli_allowed"))
        self.default_local_dir_ctrl = wx.TextCtrl(other_box)
        self.default_local_dir_ctrl.SetHint(t("connection.default_local_dir"))
        btn_local_browse = wx.Button(other_box, label=t("connection.browse_default_local_folder") if t("connection.browse_default_local_folder") != "[connection.browse_default_local_folder]" else t("login.browse"))
        local_row = wx.BoxSizer(wx.HORIZONTAL)
        local_row.Add(self.default_local_dir_ctrl, 1, wx.EXPAND | wx.RIGHT, 8)
        local_row.Add(btn_local_browse, 0)
        other_sizer.Add(self.cb_x11, 0, wx.BOTTOM, 4)
        other_sizer.Add(self.cb_cli_allowed, 0, wx.BOTTOM, 8)
        other_sizer.Add(wx.StaticText(other_box, label=t("connection.default_local_dir")), 0, wx.BOTTOM, 4)
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
