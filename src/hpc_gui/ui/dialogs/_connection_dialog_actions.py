from __future__ import annotations

from __future__ import annotations
from copy import deepcopy
from typing import Any
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)
from hpc_gui.core.i18n import t
from hpc_gui.config.file_manager_profile import (
    patch_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import (
    patch_jump_host_settings,
)
from hpc_gui.ui.dialogs.cluster_self_test_dialog import ClusterSelfTestDialog

ProfileData = dict[str, Any]

class _ConnectionDialogActionsMixin:
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
        # One logical Save & Connect action performs exactly one save. The
        # connect handler owns persistence (so the transient typed password is
        # used for this connection attempt); calling the plain save callback as
        # well would persist the profile twice and duplicate the saved event.
        handler = self._on_connect or self._on_save
        if handler is not None and not handler(profile):
            return
        self.accept()

