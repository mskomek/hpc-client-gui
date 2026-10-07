"""ConnectionDialogTemplateMixin owns the templates portion of the wx connection dialog."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from hpc_gui.config.system_profile import (
    builtin_system_template_groups,
    load_user_system_templates,
    normalize_system_settings,
    save_user_system_template,
)
from hpc_gui.core.i18n import t
from hpc_gui.plugins.models import validate_storage_area
from hpc_gui.plugins.templates import installed_cluster_template_groups

# Extracted dialog responsibility; behavior stays on the public dialog facade.

class ConnectionDialogTemplateMixin:
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
            try:
                from hpc_gui.wx_plugins_view import show_plugins

                show_plugins(parent=self.dlg)
            except (ImportError, RuntimeError) as exc:
                wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR)
        self.dlg.Bind(wx.EVT_MENU, _more_handler, more)

        # Popup
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
