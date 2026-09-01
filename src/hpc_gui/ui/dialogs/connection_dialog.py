from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QInputDialog,
    QLabel,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
)

from hpc_gui.core.i18n import t
from hpc_gui.config.file_manager_profile import (
    normalize_file_manager_settings,
    patch_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import (
    normalize_jump_host_settings,
    patch_jump_host_settings,
)
from hpc_gui.config.system_profile import (
    builtin_system_template_groups,
    load_user_system_templates,
    normalize_system_settings,
    save_user_system_template,
)
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.plugins.models import (
    validate_storage_area,
    validate_storage_policy,
)
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.ui.dialogs.cluster_self_test_dialog import ClusterSelfTestDialog
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
        self._provider_template: dict[str, Any] | None = (
            deepcopy((initial_profile or {}).get("provider_template"))
            if isinstance((initial_profile or {}).get("provider_template"), dict)
            else None
        )
        self._provider_origin = "plugin" if self._provider_template is not None else None
        self._legacy_storage_snapshot: dict[str, str] = {}
        self._template_action_taken = False
        self._profile_keepalive = 30
        self._profile_transfer_parallelism = 1
        self._profile_ssh_timeout = None
        source = (initial_profile or {}).get("system_template_source")
        self._system_template_source = (
            {str(k): str(v) for k, v in source.items()}
            if isinstance(source, dict)
            else None
        )
        if self._provider_template is not None:
            self._provider_origin = (
                "plugin"
                if self._system_template_source and self._system_template_source.get("kind") == "plugin"
                else "local"
            )

        self.setModal(True)
        self.setWindowTitle(t("connection.dialog_title"))
        self.setMinimumWidth(720)

        self.profile_name = QLineEdit()
        self.host = QLineEdit()
        self.port = QLineEdit("22")
        self.username = QLineEdit()
        self.project = QLineEdit()
        self.account = QLineEdit()
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
        self.cb_host_key_policy = QComboBox()
        self.cb_host_key_policy.addItem(t("connection.host_key_accept_new"), "accept-new")
        self.cb_host_key_policy.addItem(t("connection.host_key_strict"), "strict")
        self.cb_host_key_policy.setToolTip(
            t("connection.host_key_verification_tip")
        )
        self.cb_cli_allowed = QCheckBox(t("connection.cli_allowed"))

        self.sp_keepalive = QSpinBox()
        self.sp_keepalive.setRange(0, 3600)
        self.sp_keepalive.setValue(30)
        self.sp_keepalive.setSuffix(" s")
        self.sp_keepalive.setToolTip(
            t("connection.ssh_keepalive_tip")
        )

        # ---- jump host (one-hop bastion) ---------------------------------
        self.cb_jump_enabled = QCheckBox(t("connection.jump_enable"))
        self.jump_host = QLineEdit()
        self.sp_jump_port = QSpinBox()
        self.sp_jump_port.setRange(1, 65535)
        self.sp_jump_port.setValue(22)
        self.jump_username = QLineEdit()
        self.jump_key_path = QLineEdit()
        self.btn_browse_jump_key = QPushButton(t("login.browse"))
        self.btn_browse_jump_key.clicked.connect(self.pick_jump_key)
        self.cb_jump_host_key_policy = QComboBox()
        self.cb_jump_host_key_policy.addItem(
            t("connection.host_key_accept_new"), "accept-new"
        )
        self.cb_jump_host_key_policy.addItem(
            t("connection.host_key_strict"), "strict"
        )
        jump_row = QHBoxLayout()
        jump_row.addWidget(self.jump_key_path)
        jump_row.addWidget(self.btn_browse_jump_key)
        self._jump_child_widgets = [
            self.jump_host,
            self.sp_jump_port,
            self.jump_username,
            self.jump_key_path,
            self.btn_browse_jump_key,
            self.cb_jump_host_key_policy,
        ]
        for widget in self._jump_child_widgets:
            widget.setEnabled(False)
        self.cb_jump_enabled.toggled.connect(self._set_jump_children_enabled)
        self.cb_jump_enabled.setToolTip(t("connection.jump_auth_tip"))

        self.default_local_dir = QLineEdit()
        self.btn_browse_default_local = QPushButton(t("connection.browse_default_local_folder"))
        self.btn_browse_default_local.clicked.connect(self.pick_default_local_dir)
        self.default_local_dir.setToolTip(
            t("connection.default_local_dir_tooltip")
        )

        form = QFormLayout()
        form.addRow(t("login.profile_name_label"), self.profile_name)
        form.addRow(t("login.host"), self.host)
        form.addRow(t("login.port"), self.port)
        form.addRow(t("login.username"), self.username)
        form.addRow(t("connection.project"), self.project)
        form.addRow(t("connection.account"), self.account)
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
        self.storage_summary = QLabel()
        self.storage_summary.setWordWrap(True)
        self.storage_rows: list[dict[str, Any]] = []
        self.storage_list = QListWidget()
        self.storage_list.setMaximumHeight(90)
        self.btn_storage_add = QPushButton(t("connection.storage_add"))
        self.btn_storage_edit = QPushButton(t("connection.storage_edit"))
        self.btn_storage_remove = QPushButton(t("connection.storage_remove"))
        self.btn_storage_add.clicked.connect(self._add_storage_area)
        self.btn_storage_edit.clicked.connect(self._edit_storage_area)
        self.btn_storage_remove.clicked.connect(self._remove_storage_area)
        self.quota_enabled = QCheckBox(t("connection.quota_enable"))
        self.quota_consent = QCheckBox(t("connection.quota_consent"))
        self.quota_backend = QComboBox()
        self.quota_backend.addItem(t("connection.quota_status_unconfigured"), "")
        self.quota_command = QLineEdit()
        self.quota_scope = QLineEdit()
        self.quota_subject = QLineEdit()
        self.quota_status = QLabel()
        self.quota_command.setPlaceholderText(t("connection.quota_command_placeholder"))

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
        storage_controls = QVBoxLayout()
        storage_controls.addWidget(self.storage_list)
        storage_buttons = QHBoxLayout()
        storage_buttons.addWidget(self.btn_storage_add)
        storage_buttons.addWidget(self.btn_storage_edit)
        storage_buttons.addWidget(self.btn_storage_remove)
        storage_controls.addLayout(storage_buttons)
        system_form.addRow(t("connection.storage_areas"), storage_controls)
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
        quota_form = QFormLayout()
        quota_form.addRow("", self.quota_enabled)
        quota_form.addRow("", self.quota_consent)
        quota_form.addRow(t("connection.quota_backend"), self.quota_backend)
        self.quota_command_label = QLabel(t("connection.quota_command"))
        quota_form.addRow(self.quota_command_label, self.quota_command)
        quota_form.addRow(t("connection.quota_scope"), self.quota_scope)
        quota_form.addRow(t("connection.quota_subject"), self.quota_subject)
        quota_form.addRow(t("connection.quota_status"), self.quota_status)
        quota_group = QGroupBox(t("connection.quota_settings"))
        quota_group.setLayout(quota_form)
        self.quota_enabled.toggled.connect(self.quota_backend.setEnabled)
        self.quota_enabled.toggled.connect(self.quota_command.setEnabled)
        self.quota_enabled.toggled.connect(self._update_quota_status)
        self.quota_command.textChanged.connect(self._update_quota_status)
        self.quota_backend.currentTextChanged.connect(self._update_quota_status)
        self.quota_scope.textChanged.connect(self._update_quota_status)
        self.quota_consent.toggled.connect(self._update_quota_status)
        quota_group.setToolTip(t("connection.quota_disabled_tip"))

        self.advanced_button = QToolButton()
        self.advanced_button.setText(t("connection.advanced_settings"))
        self.advanced_button.setCheckable(True)
        self.advanced_button.setChecked(False)
        self.advanced_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_body = QGroupBox()
        advanced_layout = QVBoxLayout(self.advanced_body)

        ssh_group = QGroupBox(t("connection.ssh_group"))
        ssh_form = QFormLayout(ssh_group)
        ssh_form.addRow(t("connection.host_key_verification"), self.cb_host_key_policy)
        ssh_form.addRow(t("connection.ssh_keepalive_interval"), self.sp_keepalive)
        self.sp_ssh_timeout.setToolTip(
            t("connection.ssh_timeout_override_tip")
        )
        ssh_form.addRow(t("connection.ssh_timeout_override"), self.sp_ssh_timeout)
        ssh_form.addRow("", self.cb_jump_enabled)
        ssh_form.addRow(t("connection.jump_host_label"), self.jump_host)
        ssh_form.addRow(t("connection.jump_port"), self.sp_jump_port)
        ssh_form.addRow(t("connection.jump_username"), self.jump_username)
        ssh_form.addRow(t("connection.jump_ssh_key"), jump_row)
        ssh_form.addRow(
            t("connection.jump_host_key_verification"),
            self.cb_jump_host_key_policy,
        )

        transfers_group = QGroupBox(t("connection.transfers_group"))
        transfers_form = QFormLayout(transfers_group)
        self.sp_transfer_parallelism.setToolTip(
            t("connection.max_simultaneous_transfers_tip")
        )
        transfers_form.addRow(
            t("connection.max_simultaneous_transfers"),
            self.sp_transfer_parallelism,
        )

        other_group = QGroupBox(t("connection.other_group"))
        other_form = QFormLayout(other_group)
        other_form.addRow("", self.cb_x11)
        other_form.addRow("", self.cb_cli_allowed)
        file_browser_group = QGroupBox(t("connection.file_browser_group"))
        browser_form = QFormLayout(file_browser_group)
        local_dir_row = QHBoxLayout()
        local_dir_row.addWidget(self.default_local_dir)
        local_dir_row.addWidget(self.btn_browse_default_local)
        browser_form.addRow(t("connection.default_local_dir"), local_dir_row)
        other_form.addRow("", file_browser_group)

        advanced_layout.addWidget(ssh_group)
        advanced_layout.addWidget(transfers_group)
        advanced_layout.addWidget(other_group)
        self.advanced_body.setVisible(False)
        self.advanced_button.toggled.connect(self._set_advanced_visible)

        self.btn_save = QPushButton(t("connection.save"))
        self.btn_save.clicked.connect(self._save_clicked)

        self.btn_save_connect = QPushButton(t("connection.save_and_connect"))
        self.btn_save_connect.clicked.connect(self._save_and_connect_clicked)

        self.btn_test_cluster = QPushButton(t("connection.test_cluster"))
        self.btn_test_cluster.clicked.connect(self._test_cluster)

        self.btn_cancel = QPushButton(t("common.cancel"))
        self.btn_cancel.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.btn_test_cluster)
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_save_connect)
        button_row.addWidget(self.btn_cancel)

        root = QVBoxLayout()
        root.addLayout(form)
        # Ready-made system settings (templates + site fields) stay visible at
        # the top instead of hiding inside the advanced section.
        root.addWidget(system_group)
        root.addWidget(quota_group)
        root.addWidget(self.advanced_button)
        root.addWidget(self.advanced_body)

        # The advanced section is tall; keep the dialog within the screen by
        # scrolling the content while the action row stays fixed at the bottom.
        content = QWidget()
        content.setLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.addWidget(scroll, 1)
        dialog_layout.addLayout(button_row)

        self._load_profile(self._initial_profile)
        self._rebuild_system_template_menu()

    def _clamp_dialog_to_screen(self) -> None:
        screen = self.screen() or self.windowHandle().screen()
        if screen is None:
            return
        available = screen.availableGeometry().adjusted(16, 16, -16, -16)
        if self.height() > available.height():
            self.resize(self.width(), available.height())
        if self.width() > available.width():
            self.resize(available.width(), self.height())

    def _set_jump_children_enabled(self, enabled: bool) -> None:
        for widget in self._jump_child_widgets:
            widget.setEnabled(enabled)

    def showEvent(self, event) -> None:
        # Keep the dialog inside the screen from the start; the scroll area
        # absorbs any overflow instead of growing past the desktop.
        super().showEvent(event)
        self._clamp_dialog_to_screen()

    def _set_advanced_visible(self, visible: bool) -> None:
        self.advanced_body.setVisible(visible)
        self.advanced_button.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )
        if visible:
            self._clamp_dialog_to_screen()

    def _load_profile(self, profile: ProfileData) -> None:
        self.profile_name.setText(str(profile.get("name", "")))
        self.host.setText(str(profile.get("host", "")))
        self.port.setText(str(profile.get("port", 22)))
        self.username.setText(str(profile.get("username", "")))
        self.project.setText(str(profile.get("project", "")))
        self.account.setText(str(profile.get("account", "")))
        self.key_path.setText(str(profile.get("key_path", "")))
        self.cb_x11.setChecked(bool(profile.get("x11_forwarding", False)))
        host_key_policy = str(profile.get("host_key_policy") or "accept-new").strip()
        if host_key_policy not in {"accept-new", "strict"}:
            host_key_policy = "accept-new"
        policy_index = self.cb_host_key_policy.findData(host_key_policy)
        self.cb_host_key_policy.setCurrentIndex(max(0, policy_index))
        self.sp_keepalive.setValue(
            coerce_keepalive_interval(profile.get("keepalive_interval_seconds", 30))
        )
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
        file_manager = normalize_file_manager_settings(profile.get("file_manager"))
        self.default_local_dir.setText(file_manager["local_start_dir"])
        jump = normalize_jump_host_settings(profile.get("jump_host"))
        was_blocked = self.cb_jump_enabled.blockSignals(True)
        try:
            self.cb_jump_enabled.setChecked(bool(jump["enabled"]))
        finally:
            self.cb_jump_enabled.blockSignals(was_blocked)
        self.jump_host.setText(jump["host"])
        self.sp_jump_port.setValue(int(jump["port"]))
        self.jump_username.setText(jump["username"])
        self.jump_key_path.setText(jump["key_path"])
        jump_policy_index = self.cb_jump_host_key_policy.findData(
            jump["host_key_policy"]
        )
        self.cb_jump_host_key_policy.setCurrentIndex(max(0, jump_policy_index))
        self._set_jump_children_enabled(bool(jump["enabled"]))

        system = normalize_system_settings(profile.get("system"))
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

        if profile.get("save_password") and isinstance(profile.get("password"), str) and profile.get("password"):
            self.password.setText(str(profile.get("password", "")))
        else:
            self.password.setText("")
        self._update_storage_summary()
        self._load_quota_widgets()

    def _load_quota_widgets(self) -> None:
        sources = (self._provider_template or {}).get("quota_sources", [])
        source = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else {}
        self.quota_enabled.setChecked(source.get("enabled") is True)
        self.quota_consent.setChecked(source.get("consent") is True)
        backend_id = str(source.get("backend_id") or "").strip()
        if backend_id and self.quota_backend.findData(backend_id) < 0:
            self.quota_backend.addItem(f"{backend_id} (unsupported)", backend_id)
        self.quota_backend.setCurrentIndex(max(0, self.quota_backend.findData(backend_id)))
        self.quota_command.setText(str(source.get("command_template") or ""))
        self.quota_scope.setText(str(source.get("scope") or ""))
        self.quota_subject.setText(str(source.get("subject_template") or ""))
        local = self._provider_origin == "local"
        if local:
            self.quota_backend.clear()
            self.quota_backend.addItem(t("connection.quota_status_unconfigured"), "")
        for widget in (self.quota_command_label, self.quota_command, self.quota_scope, self.quota_subject):
            widget.setVisible(not local)
        if local:
            self.quota_command.clear()
            self.quota_scope.clear()
            self.quota_subject.clear()
        self._update_quota_status()

    def _ensure_local_provider_template(self) -> dict[str, Any]:
        if self._provider_template is None:
            self._provider_origin = "local"
            self._provider_template = {
                "schema_version": 2,
                "profile_id": "local",
                "name": self.system_name.text().strip() or "Custom HPC",
                "scheduler": "slurm",
                "storage": [],
                "quota_sources": [],
            }
        return self._provider_template

    def _update_quota_status(self) -> None:
        state = quota_gate(
            {
                "enabled": self.quota_enabled.isChecked(),
                "consent": self.quota_consent.isChecked(),
                "backend_id": str(self.quota_backend.currentData() or "").strip(),
                "command_template": self.quota_command.text().strip(),
                "scope": self.quota_scope.text().strip(),
            },
            backend_ids=(),
        )
        if state == "disabled":
            self.quota_status.setText(t("connection.quota_status_off"))
        elif state == "not_configured":
            self.quota_status.setText(t("connection.quota_status_unconfigured"))
        elif state == "invalid_configuration":
            self.quota_status.setText(t("connection.quota_status_invalid"))
        else:
            self.quota_status.setText(t("connection.quota_status_backend_required"))

    def _set_storage_rows(self, rows: Any) -> None:
        self.storage_rows = [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        self.storage_list.clear()
        for row in self.storage_rows:
            label = str(row.get("label") or row.get("id") or "Storage")
            path = str(row.get("path_template") or "").strip()
            self.storage_list.addItem(f"{label}: {path}" if path else f"{label} ({t('connection.storage_areas_empty')})")

    def _add_storage_area(self) -> None:
        label, ok = QInputDialog.getText(self, t("connection.storage_add"), t("connection.storage_label"))
        if not ok or not label.strip():
            return
        path, ok = QInputDialog.getText(self, t("connection.storage_add"), t("connection.storage_path"))
        if not ok:
            return
        kind_values = ["home", "scratch", "project", "custom", "node-local"]
        kind, ok = QInputDialog.getItem(
            self, t("connection.storage_add"), t("connection.storage_kind"), kind_values, 3, False
        )
        if not ok:
            return
        contexts = ["login-node", "shared", "compute-node", "unknown"]
        access_context, ok = QInputDialog.getItem(
            self, t("connection.storage_add"), t("connection.storage_access_context"), contexts, 3, False
        )
        if not ok:
            return
        path = path.strip()
        area_id = "-".join(label.strip().lower().split()) or "storage"
        used_ids = {str(row.get("id")) for row in self.storage_rows}
        base_id = area_id
        suffix = 2
        while area_id in used_ids:
            area_id = f"{base_id}-{suffix}"
            suffix += 1
        area = {
            "id": area_id,
            "label": label.strip(),
            "kind": kind,
            "enabled": True,
            "path_template": path,
            "access_context": access_context,
            "policy": {"backup": None, "retention_days": None},
        }
        if validate_storage_area(area):
            QMessageBox.warning(self, t("common.error"), t("connection.storage_path_invalid"))
            return
        self._ensure_local_provider_template()
        self.storage_rows.append(area)
        self._set_storage_rows(self.storage_rows)

    def _remove_storage_area(self) -> None:
        row = self.storage_list.currentRow()
        if row >= 0:
            self.storage_rows.pop(row)
            self._set_storage_rows(self.storage_rows)

    def _edit_storage_area(self) -> None:
        row = self.storage_list.currentRow()
        if row < 0 or row >= len(self.storage_rows):
            return
        current = self.storage_rows[row]
        label, ok = QInputDialog.getText(
            self, t("connection.storage_edit"), t("connection.storage_label"),
            text=str(current.get("label") or current.get("id") or ""),
        )
        if not ok or not label.strip():
            return
        path, ok = QInputDialog.getText(
            self, t("connection.storage_edit"), t("connection.storage_path"),
            text=str(current.get("path_template") or ""),
        )
        if not ok:
            return
        kind_values = ["home", "scratch", "project", "custom", "node-local"]
        kind, ok = QInputDialog.getItem(
            self, t("connection.storage_edit"), t("connection.storage_kind"), kind_values,
            max(0, kind_values.index(str(current.get("kind") or "custom")))
            if current.get("kind") in kind_values else 3, False,
        )
        if not ok:
            return
        contexts = ["login-node", "shared", "compute-node", "unknown"]
        access_context, ok = QInputDialog.getItem(
            self, t("connection.storage_edit"), t("connection.storage_access_context"), contexts,
            max(0, contexts.index(str(current.get("access_context") or "unknown")))
            if current.get("access_context") in contexts else 3, False,
        )
        if not ok:
            return
        backup, ok = QInputDialog.getItem(
            self, t("connection.storage_edit"), t("connection.storage_backup"),
            [t("connection.storage_unknown"), t("connection.storage_yes"), t("connection.storage_no")],
            0, False,
        )
        if not ok:
            return
        cleanup, ok = QInputDialog.getText(
            self, t("connection.storage_edit"), t("connection.storage_cleanup"),
            text=str((current.get("policy") or {}).get("cleanup_note") or ""),
        )
        if not ok:
            return
        retention, ok = QInputDialog.getText(
            self, t("connection.storage_edit"), t("connection.storage_retention"),
            text=str((current.get("policy") or {}).get("retention_days") or ""),
        )
        if not ok:
            return
        retention_value = retention.strip()
        policy_check = {"retention_days": int(retention_value) if retention_value else None}
        if retention_value and not retention_value.isdigit():
            policy_check["retention_days"] = retention_value
        if validate_storage_policy(policy_check):
            QMessageBox.warning(self, t("common.error"), t("connection.storage_retention_invalid"))
            return
        source_url, ok = QInputDialog.getText(
            self, t("connection.storage_edit"), t("connection.storage_source_url"),
            text=str((current.get("policy") or {}).get("documentation_url") or ""),
        )
        if not ok:
            return
        source_url = source_url.strip()
        if validate_storage_policy({"documentation_url": source_url}):
            QMessageBox.warning(self, t("common.error"), t("connection.storage_source_url_invalid"))
            return
        current["kind"] = kind
        current["access_context"] = access_context
        current["enabled"] = current.get("enabled") is not False
        current["id"] = str(current.get("id") or "custom")
        candidate = dict(current, label=label.strip(), path_template=path.strip())
        if validate_storage_area(candidate):
            QMessageBox.warning(self, t("common.error"), t("connection.storage_path_invalid"))
            return
        self._ensure_local_provider_template()
        current["label"] = label.strip()
        current["path_template"] = path.strip()
        current["policy"] = {
            **(current.get("policy") if isinstance(current.get("policy"), dict) else {}),
            "backup": {t("connection.storage_yes"): True, t("connection.storage_no"): False}.get(backup),
            "cleanup_note": cleanup.strip(),
            "retention_days": int(retention_value) if retention_value else None,
            "documentation_url": source_url,
        }
        self._set_storage_rows(self.storage_rows)

    def _sync_structured_editor(self) -> None:
        feature_used = bool(self.storage_rows) or self.quota_enabled.isChecked()
        feature_used = feature_used or bool(self.quota_scope.text().strip())
        feature_used = feature_used or bool(self.quota_subject.text().strip())
        feature_used = feature_used or bool(self.quota_backend.currentData())
        if self._provider_template is None and not feature_used:
            return
        provider = self._ensure_local_provider_template()
        self._sync_legacy_storage_paths()
        provider["storage"] = [dict(row) for row in self.storage_rows]
        sources = provider.get("quota_sources")
        preserved = [dict(item) for item in sources if isinstance(item, dict)] if isinstance(sources, list) else []
        source = dict(preserved[0]) if preserved else {"id": "local-quota"}
        source.update({
            "enabled": self.quota_enabled.isChecked(),
            "consent": self.quota_consent.isChecked(),
            "backend_id": str(self.quota_backend.currentData() or "").strip(),
            "command_template": "" if self._provider_origin == "local" else self.quota_command.text().strip(),
            "scope": self.quota_scope.text().strip(),
            "subject_template": self.quota_subject.text().strip(),
        })
        provider["quota_sources"] = [source, *preserved[1:]]

    def _sync_legacy_storage_paths(self) -> None:
        """Keep legacy Home/Scratch fields and structured rows aligned."""
        for key, kind in (("home_dir", "home"), ("scratch_dir", "scratch")):
            value = getattr(self, key)
            current = value.text().strip()
            previous = self._legacy_storage_snapshot.get(key, current)
            rows = [row for row in self.storage_rows if row.get("kind") == kind or row.get("id") == kind]
            if current != previous:
                for row in rows:
                    row["path_template"] = current
            elif rows and rows[0].get("path_template"):
                current = str(rows[0]["path_template"]).strip()
                value.setText(current)
            self._legacy_storage_snapshot[key] = current

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

    def pick_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("login.ssh_key"))
        if path:
            self.key_path.setText(path)

    def pick_default_local_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            t("connection.browse_default_local_folder"),
            self.default_local_dir.text().strip() or "",
        )
        if path:
            self.default_local_dir.setText(path)

    def pick_jump_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("connection.jump_ssh_key"))
        if path:
            self.jump_key_path.setText(path)

    def _collect_profile(self) -> ProfileData | None:
        try:
            port = int(self.port.text().strip() or "22")
        except ValueError:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_port_numeric"))
            return None

        # Editing starts from the stored profile so unknown/future keys
        # (plugin provenance, file_manager, jump_host, ...) survive.
        is_edit = bool(self._initial_profile)
        profile: ProfileData = dict(self._initial_profile) if is_edit else {}

        profile.update(
            {
                "name": self.profile_name.text().strip(),
                "host": self.host.text().strip(),
                "port": port,
                "username": self.username.text().strip(),
                "project": self.project.text().strip(),
                "account": self.account.text().strip(),
                "password": self.password.text(),
                "key_path": self.key_path.text().strip(),
                "host_key_policy": str(
                    self.cb_host_key_policy.currentData() or "accept-new"
                ),
                "x11_forwarding": self.cb_x11.isChecked(),
                "cli_allowed": self.cb_cli_allowed.isChecked(),
                "keepalive_interval_seconds": int(self.sp_keepalive.value()),
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
        )
        # Secret storage stays authoritative in LoginWidget; never carry
        # stored secret material through the dialog result.
        for secret_key in ("password_dpapi", "password_enc", "password_salt"):
            profile.pop(secret_key, None)

        # Structured provider data is part of the saved connection state, not
        # an ephemeral UI action.  Keep every source and update only the source
        # represented by the current quota editor.
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
            {"local_start_dir": self.default_local_dir.text().strip()},
        )
        if (
            self.cb_jump_enabled.isChecked()
            and not self.jump_host.text().strip()
        ):
            QMessageBox.warning(
                self,
                t("common.error"),
                t("connection.jump_host_required"),
            )
            return None
        profile["jump_host"] = patch_jump_host_settings(
            (self._initial_profile or {}).get("jump_host"),
            {
                "enabled": self.cb_jump_enabled.isChecked(),
                "host": self.jump_host.text().strip(),
                "port": int(self.sp_jump_port.value()),
                "username": self.jump_username.text().strip(),
                "key_path": self.jump_key_path.text().strip(),
                "host_key_policy": str(
                    self.cb_jump_host_key_policy.currentData() or "accept-new"
                ),
            },
        )
        return profile

    def _save_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        self.accept()

    def _test_cluster(self) -> None:
        profile = self._collect_profile()
        if profile is not None:
            ClusterSelfTestDialog(self, profile).exec()

    def _save_and_connect_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        if self._on_connect is not None and not self._on_connect(profile):
            return
        self.accept()
