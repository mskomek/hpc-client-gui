from __future__ import annotations

from __future__ import annotations
from copy import deepcopy
from typing import Any
from PySide6.QtWidgets import (
    QInputDialog,
    QMenu,
    QMessageBox,
)
from hpc_gui.core.i18n import t
from hpc_gui.config.system_profile import (
    builtin_system_template_groups,
    load_user_system_templates,
    normalize_system_settings,
    save_user_system_template,
)
from hpc_gui.plugins.templates import installed_cluster_template_groups

ProfileData = dict[str, Any]

class _ConnectionDialogTemplatesMixin:
    def _system_form_values(self) -> dict[str, Any]:
        self._sync_structured_editor()
        values: dict[str, Any] = {
            "name": self.system_name.text().strip(),
            "scratch_dir": self.scratch_dir.text().strip(),
            "home_dir": self.home_dir.text().strip(),
            "squeue_command": self.squeue_command.text().strip(),
            "sbatch_command": self.sbatch_command.text().strip(),
            "scancel_command": self.scancel_command.text().strip(),
            "sacct_command": self.sacct_command.text().strip(),
            "scontrol_command": self.scontrol_command.text().strip(),
            "status_command": self.status_command.text().strip(),
            "active_job_ids_command": self.active_job_ids_command.text().strip(),
            "job_state_command": self.job_state_command.text().strip(),
        }
        if self._provider_template is not None:
            values["provider_template"] = {
                key: value for key, value in self._provider_template.items()
            }
        return values


    def _apply_system_template(
        self,
        template: ProfileData,
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
        self.system_name.setText(system["name"])
        self.scratch_dir.setText(system["scratch_dir"])
        self.home_dir.setText(system["home_dir"])
        self._legacy_storage_snapshot = {
            "home_dir": self.home_dir.text().strip(),
            "scratch_dir": self.scratch_dir.text().strip(),
        }
        self.squeue_command.setText(system["squeue_command"])
        self.sbatch_command.setText(system["sbatch_command"])
        self.scancel_command.setText(system["scancel_command"])
        self.sacct_command.setText(system["sacct_command"])
        self.scontrol_command.setText(system["scontrol_command"])
        self.status_command.setText(system["status_command"])
        self.active_job_ids_command.setText(system["active_job_ids_command"])
        self.job_state_command.setText(system["job_state_command"])
        self._update_storage_summary()
        self._load_quota_widgets()


    def _update_storage_summary(self) -> None:
        rows = (self._provider_template or {}).get("storage", [])
        if not isinstance(rows, list):
            rows = []
        visible = [
            f"{row.get('label', row.get('id', ''))}: {row.get('path_template', '').strip()}"
            for row in rows
            if isinstance(row, dict)
            and row.get("path_template", "").strip()
            and row.get("enabled") is not False
        ]
        self.storage_summary.setText("\n".join(visible) or t("connection.storage_areas_empty"))
        self._set_storage_rows(rows)


    def _rebuild_system_template_menu(self) -> None:
        menu = QMenu(self)
        submenus: list[QMenu] = []
        for group_name, templates in builtin_system_template_groups().items():
            submenu = QMenu(group_name, menu)
            menu.addMenu(submenu)
            submenus.append(submenu)
            for template in templates:
                action = submenu.addAction(template["name"])
                action.triggered.connect(
                    lambda _checked=False, selected=dict(template): self._apply_system_template(
                        selected, structured=selected.get("provider_template")
                    )
                )
        plugin_groups = installed_cluster_template_groups()
        if plugin_groups:
            plugin_menu = QMenu(t("connection.plugin_templates"), menu)
            menu.addMenu(plugin_menu)
            submenus.append(plugin_menu)
            for group_name, templates in sorted(plugin_groups.items()):
                group_menu = (
                    plugin_menu
                    if len(templates) == 1
                    else self._add_nested_group(plugin_menu, group_name)
                )
                for template in templates:
                    action = group_menu.addAction(template.settings.get("name", group_name))
                    action.triggered.connect(
                        lambda _checked=False, selected=dict(template.settings), provenance=dict(
                            template.provenance
                        ), structured=dict(template.structured): self._apply_system_template(
                            selected, provenance, structured
                        )
                    )
        user_templates = load_user_system_templates()
        if user_templates:
            user_menu = QMenu(t("connection.user_templates"), menu)
            menu.addMenu(user_menu)
            submenus.append(user_menu)
            for template in user_templates:
                action = user_menu.addAction(template["name"])
                action.triggered.connect(
                    lambda _checked=False, selected=dict(template): self._apply_system_template(selected)
                )
        menu.addSeparator()
        more_action = menu.addAction(t("connection.get_more_plugins"))
        more_action.triggered.connect(self._open_plugin_manager)
        self._system_template_menu = menu
        self._system_template_submenus = submenus
        self.btn_system_templates.setMenu(menu)


    @staticmethod
    def _add_nested_group(parent_menu: QMenu, group_name: str) -> QMenu:
        submenu = QMenu(group_name, parent_menu)
        parent_menu.addMenu(submenu)
        return submenu


    def _open_plugin_manager(self) -> None:
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

            dialog = PluginManagerDialog(self)
            dialog.plugins_changed.connect(self._rebuild_system_template_menu)
            dialog.exec()
            self._rebuild_system_template_menu()
        except Exception:
            pass


    def _save_current_system_template(self) -> None:
        default_name = self.system_name.text().strip() or t("connection.custom_system_template")
        name, ok = QInputDialog.getText(
            self,
            t("connection.save_system_template"),
            t("connection.system_template_name"),
            text=default_name,
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(
                self,
                t("common.error"),
                t("connection.system_template_name_required"),
            )
            return
        try:
            save_user_system_template(name, self._system_form_values())
        except ValueError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        self._rebuild_system_template_menu()

