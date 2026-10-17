from __future__ import annotations

from __future__ import annotations
from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
)
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
from hpc_gui.plugins.models import (
    validate_storage_area,
    validate_storage_policy,
)
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.ssh.client import coerce_keepalive_interval
from hpc_gui.config.storage import coerce_profile_transfer_parallelism, coerce_profile_ssh_timeout

ProfileData = dict[str, Any]

class _ConnectionDialogProfileMixin:
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

