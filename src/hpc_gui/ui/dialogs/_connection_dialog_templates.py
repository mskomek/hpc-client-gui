from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
)

from hpc_gui.core.i18n import t

ProfileData = dict[str, Any]


class _ConnectionDialogTemplatesMixin:
    def _rebuild_system_template_menu(
        self, builtin_groups, plugin_groups_loader, user_templates_loader
    ) -> None:
        menu = QMenu(self)
        submenus: list[QMenu] = []
        for group_name, templates in builtin_groups().items():
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
        plugin_groups = plugin_groups_loader()
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
                        lambda _checked=False, selected=dict(template.settings), provenance=dict(template.provenance), structured=dict(template.structured): (
                            self._apply_system_template(selected, provenance, structured)
                        )
                    )
        user_templates = user_templates_loader()
        if user_templates:
            user_menu = QMenu(t("connection.user_templates"), menu)
            menu.addMenu(user_menu)
            submenus.append(user_menu)
            for template in user_templates:
                action = user_menu.addAction(template["name"])
                action.triggered.connect(
                    lambda _checked=False, selected=dict(template): self._apply_system_template(
                        selected
                    )
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

    def _save_current_system_template(self, prompt, save_template) -> None:
        default_name = self.system_name.text().strip() or t("connection.custom_system_template")
        name, ok = prompt(
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
            save_template(name, self._system_form_values())
        except ValueError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        self._rebuild_system_template_menu()
