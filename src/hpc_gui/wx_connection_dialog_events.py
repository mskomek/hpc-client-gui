"""ConnectionDialogEventsMixin owns binding and view-state event behavior."""

from __future__ import annotations

from hpc_gui.core.i18n import t

class ConnectionDialogEventsMixin:
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
        for ctrl in (
            self.jump_host_ctrl,
            self.sp_jump_port,
            self.jump_username_ctrl,
            self.jump_key_path_ctrl,
            self.btn_jump_browse,
            self.cb_jump_host_key_policy,
        ):
            ctrl.Enable(enabled)
    def _on_save_password_toggle(self, checked: bool) -> None:
        self.rb_prompt_when_needed.Enable(checked)
        self.rb_prompt_edit_only.Enable(checked)
