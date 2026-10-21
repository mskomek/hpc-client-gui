from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
)

from hpc_gui.core.i18n import t
from hpc_gui.config.system_profile import (
    normalize_system_settings,
)
from hpc_gui.plugins.models import (
    validate_storage_area,
    validate_storage_policy,
)

ProfileData = dict[str, Any]


class _ConnectionDialogStorageMixin:
    def _set_storage_rows(self, rows: Any) -> None:
        self.storage_rows = (
            [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        )
        self.storage_list.clear()
        for row in self.storage_rows:
            label = str(row.get("label") or row.get("id") or "Storage")
            path = str(row.get("path_template") or "").strip()
            self.storage_list.addItem(
                f"{label}: {path}" if path else f"{label} ({t('connection.storage_areas_empty')})"
            )

    def _add_storage_area(self) -> None:
        label, ok = QInputDialog.getText(
            self, t("connection.storage_add"), t("connection.storage_label")
        )
        if not ok or not label.strip():
            return
        path, ok = QInputDialog.getText(
            self, t("connection.storage_add"), t("connection.storage_path")
        )
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
            self,
            t("connection.storage_add"),
            t("connection.storage_access_context"),
            contexts,
            3,
            False,
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
            self,
            t("connection.storage_edit"),
            t("connection.storage_label"),
            text=str(current.get("label") or current.get("id") or ""),
        )
        if not ok or not label.strip():
            return
        path, ok = QInputDialog.getText(
            self,
            t("connection.storage_edit"),
            t("connection.storage_path"),
            text=str(current.get("path_template") or ""),
        )
        if not ok:
            return
        kind_values = ["home", "scratch", "project", "custom", "node-local"]
        kind, ok = QInputDialog.getItem(
            self,
            t("connection.storage_edit"),
            t("connection.storage_kind"),
            kind_values,
            max(0, kind_values.index(str(current.get("kind") or "custom")))
            if current.get("kind") in kind_values
            else 3,
            False,
        )
        if not ok:
            return
        contexts = ["login-node", "shared", "compute-node", "unknown"]
        access_context, ok = QInputDialog.getItem(
            self,
            t("connection.storage_edit"),
            t("connection.storage_access_context"),
            contexts,
            max(0, contexts.index(str(current.get("access_context") or "unknown")))
            if current.get("access_context") in contexts
            else 3,
            False,
        )
        if not ok:
            return
        backup, ok = QInputDialog.getItem(
            self,
            t("connection.storage_edit"),
            t("connection.storage_backup"),
            [
                t("connection.storage_unknown"),
                t("connection.storage_yes"),
                t("connection.storage_no"),
            ],
            0,
            False,
        )
        if not ok:
            return
        cleanup, ok = QInputDialog.getText(
            self,
            t("connection.storage_edit"),
            t("connection.storage_cleanup"),
            text=str((current.get("policy") or {}).get("cleanup_note") or ""),
        )
        if not ok:
            return
        retention, ok = QInputDialog.getText(
            self,
            t("connection.storage_edit"),
            t("connection.storage_retention"),
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
            self,
            t("connection.storage_edit"),
            t("connection.storage_source_url"),
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
            "backup": {t("connection.storage_yes"): True, t("connection.storage_no"): False}.get(
                backup
            ),
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
        preserved = (
            [dict(item) for item in sources if isinstance(item, dict)]
            if isinstance(sources, list)
            else []
        )
        source = dict(preserved[0]) if preserved else {"id": "local-quota"}
        source.update(
            {
                "enabled": self.quota_enabled.isChecked(),
                "consent": self.quota_consent.isChecked(),
                "backend_id": str(self.quota_backend.currentData() or "").strip(),
                "command_template": ""
                if self._provider_origin == "local"
                else self.quota_command.text().strip(),
                "scope": self.quota_scope.text().strip(),
                "subject_template": self.quota_subject.text().strip(),
            }
        )
        provider["quota_sources"] = [source, *preserved[1:]]

    def _sync_legacy_storage_paths(self) -> None:
        """Keep legacy Home/Scratch fields and structured rows aligned."""
        for key, kind in (("home_dir", "home"), ("scratch_dir", "scratch")):
            value = getattr(self, key)
            current = value.text().strip()
            previous = self._legacy_storage_snapshot.get(key, current)
            rows = [
                row for row in self.storage_rows if row.get("kind") == kind or row.get("id") == kind
            ]
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
        self._provider_origin = (
            "plugin" if provenance and structured else ("local" if structured else None)
        )
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
