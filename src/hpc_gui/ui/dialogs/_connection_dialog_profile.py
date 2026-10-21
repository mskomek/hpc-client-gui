from __future__ import annotations

from typing import Any


from hpc_gui.core.i18n import t
from hpc_gui.config.file_manager_profile import (
    normalize_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import (
    normalize_jump_host_settings,
)
from hpc_gui.config.system_profile import (
    normalize_system_settings,
)
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.ssh.client import coerce_keepalive_interval
from hpc_gui.config.storage import coerce_profile_transfer_parallelism, coerce_profile_ssh_timeout

ProfileData = dict[str, Any]


class _ConnectionDialogProfileMixin:
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
        self._profile_transfer_parallelism = coerce_profile_transfer_parallelism(
            profile.get("transfer_parallelism", 1)
        )
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
        jump_policy_index = self.cb_jump_host_key_policy.findData(jump["host_key_policy"])
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

        if (
            profile.get("save_password")
            and isinstance(profile.get("password"), str)
            and profile.get("password")
        ):
            self.password.setText(str(profile.get("password", "")))
        else:
            self.password.setText("")
        self._update_storage_summary()
        self._load_quota_widgets()

    def _load_quota_widgets(self) -> None:
        sources = (self._provider_template or {}).get("quota_sources", [])
        source = (
            sources[0]
            if isinstance(sources, list) and sources and isinstance(sources[0], dict)
            else {}
        )
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
        for widget in (
            self.quota_command_label,
            self.quota_command,
            self.quota_scope,
            self.quota_subject,
        ):
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
