from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
)

from hpc_gui.core.i18n import t
from hpc_gui.config.system_profile import (
    builtin_system_template_groups,
    load_user_system_templates,
    normalize_system_settings,
    save_user_system_template,
)
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.ssh.client import coerce_keepalive_interval
from hpc_gui.config.storage import coerce_profile_transfer_parallelism, coerce_profile_ssh_timeout

ProfileData = dict[str, Any]


class ConnectionDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        initial_profile: ProfileData | None = None,
        on_save: Callable[[ProfileData], bool] | None = None,
        on_connect: Callable[[ProfileData], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._initial_profile = dict(initial_profile or {})
        self._on_save = on_save
        self._on_connect = on_connect
        self._system_template_menu: QMenu | None = None
        self._system_template_submenus: list[QMenu] = []
        self._system_template_source: dict[str, str] | None = None
        self._profile_keepalive = 30
        self._profile_transfer_parallelism = 1
        self._profile_ssh_timeout = None
        source = (initial_profile or {}).get("system_template_source")
        self._system_template_source = (
            {str(k): str(v) for k, v in source.items()}
            if isinstance(source, dict)
            else None
        )

        self.setModal(True)
        self.setWindowTitle(t("connection.dialog_title"))
        self.setMinimumWidth(720)

        self.profile_name = QLineEdit()
        self.host = QLineEdit()
        self.port = QLineEdit("22")
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.cb_save_password = QCheckBox(t("login.save_password"))
        self.cb_edit_only_password = QCheckBox(
            t("connection.password_no_prompt")
        )
        self.cb_edit_only_password.setToolTip(
            t("connection.password_edit_only_tip")
        )
        self.cb_save_password.toggled.connect(
            self.cb_edit_only_password.setEnabled
        )
        self.key_path = QLineEdit()
        self.btn_browse_key = QPushButton(t("login.browse"))
        self.btn_browse_key.clicked.connect(self.pick_key)

        self.sp_transfer_parallelism = QSpinBox()
        self.sp_transfer_parallelism.setRange(1, 10)
        self.sp_ssh_timeout = QDoubleSpinBox()
        self.sp_ssh_timeout.setRange(0, 600)
        self.sp_ssh_timeout.setDecimals(1)
        self.sp_ssh_timeout.setSuffix(" s")

        self.cb_x11 = QCheckBox(t("login.x11_enable"))
        self.cb_strict_hostkey = QCheckBox(t("login.strict_host_key"))
        self.cb_cli_allowed = QCheckBox(t("connection.cli_allowed"))

        form = QFormLayout()
        form.addRow(t("login.profile_name_label"), self.profile_name)
        form.addRow(t("login.host"), self.host)
        form.addRow(t("login.port"), self.port)
        form.addRow(t("login.username"), self.username)
        form.addRow(t("login.password"), self.password)
        form.addRow("", self.cb_save_password)
        form.addRow("", self.cb_edit_only_password)

        key_row = QHBoxLayout()
        key_row.addWidget(self.key_path)
        key_row.addWidget(self.btn_browse_key)
        form.addRow(t("login.ssh_key"), key_row)

        self.system_name = QLineEdit()
        self.scratch_dir = QLineEdit()
        self.home_dir = QLineEdit()
        self.squeue_command = QLineEdit()
        self.sbatch_command = QLineEdit()
        self.scancel_command = QLineEdit()
        self.sacct_command = QLineEdit()
        self.scontrol_command = QLineEdit()
        self.status_command = QLineEdit()
        self.active_job_ids_command = QLineEdit()
        self.job_state_command = QLineEdit()

        self.btn_system_templates = QToolButton()
        self.btn_system_templates.setText(t("connection.system_templates_menu"))
        self.btn_system_templates.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_save_system_template = QPushButton(t("connection.save_system_template"))
        self.btn_save_system_template.clicked.connect(self._save_current_system_template)

        system_actions = QHBoxLayout()
        system_actions.addWidget(self.btn_system_templates)
        system_actions.addWidget(self.btn_save_system_template)
        system_actions.addStretch(1)

        system_form = QFormLayout()
        system_form.addRow(t("connection.system_name"), self.system_name)
        system_form.addRow(t("connection.system_templates"), system_actions)
        system_form.addRow(t("connection.scratch_dir"), self.scratch_dir)
        system_form.addRow(t("connection.home_dir"), self.home_dir)
        system_form.addRow(t("connection.squeue_command"), self.squeue_command)
        system_form.addRow(t("connection.sbatch_command"), self.sbatch_command)
        system_form.addRow(t("connection.scancel_command"), self.scancel_command)
        system_form.addRow(t("connection.sacct_command"), self.sacct_command)
        system_form.addRow(t("connection.scontrol_command"), self.scontrol_command)
        system_form.addRow(t("connection.status_command"), self.status_command)
        system_form.addRow(
            t("connection.active_job_ids_command"),
            self.active_job_ids_command,
        )
        system_form.addRow(
            t("connection.job_state_command"),
            self.job_state_command,
        )
        system_group = QGroupBox(t("connection.system_settings"))
        system_group.setLayout(system_form)

        self.advanced_button = QToolButton()
        self.advanced_button.setText(t("connection.advanced_settings"))
        self.advanced_button.setCheckable(True)
        self.advanced_button.setChecked(False)
        self.advanced_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_body = QGroupBox()
        advanced_form = QFormLayout(self.advanced_body)
        advanced_form.addRow("", self.cb_x11)
        advanced_form.addRow(t("connection.transfer_parallelism"), self.sp_transfer_parallelism)
        advanced_form.addRow(t("connection.ssh_timeout"), self.sp_ssh_timeout)
        advanced_form.addRow("", self.cb_strict_hostkey)
        advanced_form.addRow("", self.cb_cli_allowed)
        advanced_form.addRow(system_group)
        self.advanced_body.setVisible(False)
        self.advanced_button.toggled.connect(self._set_advanced_visible)

        self.btn_save = QPushButton(t("connection.save"))
        self.btn_save.clicked.connect(self._save_clicked)

        self.btn_save_connect = QPushButton(t("connection.save_and_connect"))
        self.btn_save_connect.clicked.connect(self._save_and_connect_clicked)

        self.btn_cancel = QPushButton(t("common.cancel"))
        self.btn_cancel.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_save_connect)
        button_row.addWidget(self.btn_cancel)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.advanced_button)
        root.addWidget(self.advanced_body)
        root.addLayout(button_row)

        self._load_profile(self._initial_profile)
        self._rebuild_system_template_menu()

    def _set_advanced_visible(self, visible: bool) -> None:
        self.advanced_body.setVisible(visible)
        self.advanced_button.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )

    def _load_profile(self, profile: ProfileData) -> None:
        self.profile_name.setText(str(profile.get("name", "")))
        self.host.setText(str(profile.get("host", "")))
        self.port.setText(str(profile.get("port", 22)))
        self.username.setText(str(profile.get("username", "")))
        self.key_path.setText(str(profile.get("key_path", "")))
        self.cb_x11.setChecked(bool(profile.get("x11_forwarding", False)))
        self.cb_strict_hostkey.setChecked((profile.get("host_key_policy") or "accept-new") == "strict")
        self.cb_cli_allowed.setChecked(bool(profile.get("cli_allowed", False)))
        self._profile_keepalive = coerce_keepalive_interval(
            profile.get("keepalive_interval_seconds", 30)
        )
        self._profile_transfer_parallelism = coerce_profile_transfer_parallelism(profile.get("transfer_parallelism", 1))
        self._profile_ssh_timeout = coerce_profile_ssh_timeout(profile.get("ssh_timeout"))
        self.sp_transfer_parallelism.setValue(self._profile_transfer_parallelism)
        self.sp_ssh_timeout.setValue(self._profile_ssh_timeout or 0)
        self.cb_save_password.setChecked(bool(profile.get("save_password", False)))
        self.cb_edit_only_password.setEnabled(self.cb_save_password.isChecked())
        self.cb_edit_only_password.setChecked(
            (profile.get("password_prompt_policy") or "when-needed") == "edit-only"
        )

        system = normalize_system_settings(profile.get("system"))
        self.system_name.setText(system["name"])
        self.scratch_dir.setText(system["scratch_dir"])
        self.home_dir.setText(system["home_dir"])
        self.squeue_command.setText(system["squeue_command"])
        self.sbatch_command.setText(system["sbatch_command"])
        self.scancel_command.setText(system["scancel_command"])
        self.sacct_command.setText(system["sacct_command"])
        self.scontrol_command.setText(system["scontrol_command"])
        self.status_command.setText(system["status_command"])
        self.active_job_ids_command.setText(system["active_job_ids_command"])
        self.job_state_command.setText(system["job_state_command"])

        if profile.get("save_password") and isinstance(profile.get("password"), str) and profile.get("password"):
            self.password.setText(str(profile.get("password", "")))
        else:
            self.password.setText("")

    def _system_form_values(self) -> dict[str, str]:
        return {
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

    def _apply_system_template(
        self, template: ProfileData, provenance: dict[str, str] | None = None
    ) -> None:
        self._system_template_source = dict(provenance) if provenance else None
        system = normalize_system_settings(template)
        self.system_name.setText(system["name"])
        self.scratch_dir.setText(system["scratch_dir"])
        self.home_dir.setText(system["home_dir"])
        self.squeue_command.setText(system["squeue_command"])
        self.sbatch_command.setText(system["sbatch_command"])
        self.scancel_command.setText(system["scancel_command"])
        self.sacct_command.setText(system["sacct_command"])
        self.scontrol_command.setText(system["scontrol_command"])
        self.status_command.setText(system["status_command"])
        self.active_job_ids_command.setText(system["active_job_ids_command"])
        self.job_state_command.setText(system["job_state_command"])

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
                    lambda _checked=False, selected=dict(template): self._apply_system_template(selected)
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
                        ): self._apply_system_template(selected, provenance)
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

    def pick_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("login.ssh_key"))
        if path:
            self.key_path.setText(path)

    def _collect_profile(self) -> ProfileData | None:
        try:
            port = int(self.port.text().strip() or "22")
        except ValueError:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_port_numeric"))
            return None

        profile: ProfileData = {
            "name": self.profile_name.text().strip(),
            "host": self.host.text().strip(),
            "port": port,
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "key_path": self.key_path.text().strip(),
            "host_key_policy": "strict" if self.cb_strict_hostkey.isChecked() else "accept-new",
            "x11_forwarding": self.cb_x11.isChecked(),
            "cli_allowed": self.cb_cli_allowed.isChecked(),
            "keepalive_interval_seconds": self._profile_keepalive,
            "transfer_parallelism": int(self.sp_transfer_parallelism.value()),
            "ssh_timeout": float(self.sp_ssh_timeout.value()) or None,
            "save_password": self.cb_save_password.isChecked(),
            "password_prompt_policy": (
                "edit-only"
                if self.cb_edit_only_password.isChecked()
                else "when-needed"
            ),
            "system": {
                **self._system_form_values(),
            },
        }
        if self._system_template_source:
            profile["system_template_source"] = dict(self._system_template_source)
        return profile

    def _save_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        self.accept()

    def _save_and_connect_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        if self._on_connect is not None and not self._on_connect(profile):
            return
        self.accept()
