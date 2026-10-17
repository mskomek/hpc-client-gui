from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
)

from hpc_gui.core.i18n import t
from PySide6.QtWidgets import QInputDialog  # noqa: F401

from hpc_gui.ui.dialogs._connection_dialog_profile import _ConnectionDialogProfileMixin
from hpc_gui.ui.dialogs._connection_dialog_templates import _ConnectionDialogTemplatesMixin
from hpc_gui.ui.dialogs._connection_dialog_actions import _ConnectionDialogActionsMixin

ProfileData = dict[str, Any]



class ConnectionDialog(_ConnectionDialogProfileMixin, _ConnectionDialogTemplatesMixin, _ConnectionDialogActionsMixin, QDialog):
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





























