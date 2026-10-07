"""ConnectionDialogProfileMixin owns the profile portion of the wx connection dialog."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from hpc_gui.config.file_manager_profile import normalize_file_manager_settings, patch_file_manager_settings
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings, patch_jump_host_settings
from hpc_gui.config.storage import coerce_profile_ssh_timeout, coerce_profile_transfer_parallelism
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core.i18n import t
from hpc_gui.ssh.client import coerce_keepalive_interval

# Extracted dialog responsibility; behavior stays on the public dialog facade.

class ConnectionDialogProfileMixin:
    def _system_form_values(self) -> dict[str, Any]:
        self._sync_structured_editor()
        values: dict[str, Any] = deepcopy(
            self._initial_profile.get("system")
            if isinstance(self._initial_profile.get("system"), dict)
            else {}
        )
        values.update({
            "name": self.system_name_ctrl.GetValue().strip(),
            "scratch_dir": self.scratch_dir_ctrl.GetValue().strip(),
            "home_dir": self.home_dir_ctrl.GetValue().strip(),
            "squeue_command": self.squeue_ctrl.GetValue().strip(),
            "sbatch_command": self.sbatch_ctrl.GetValue().strip(),
            "scancel_command": self.scancel_ctrl.GetValue().strip(),
            "sacct_command": self.sacct_ctrl.GetValue().strip(),
            "scontrol_command": self.scontrol_ctrl.GetValue().strip(),
            "status_command": self.status_cmd_ctrl.GetValue().strip(),
            "active_job_ids_command": self.active_job_ids_ctrl.GetValue().strip(),
            "job_state_command": self.job_state_ctrl.GetValue().strip(),
        })
        if self._provider_template is not None:
            values["provider_template"] = {k: v for k, v in self._provider_template.items()}
        return values
    def _sync_legacy_storage_paths(self) -> None:
        for key, kind in (("home_dir", "home"), ("scratch_dir", "scratch")):
            ctrl = getattr(self, f"{key}_ctrl")
            current = ctrl.GetValue().strip()
            previous = self._legacy_storage_snapshot.get(key, current)
            rows = [row for row in getattr(self, "storage_rows", []) if row.get("kind") == kind or row.get("id") == kind]
            if current != previous:
                for row in rows:
                    row["path_template"] = current
            elif rows and rows[0].get("path_template"):
                current = str(rows[0]["path_template"]).strip()
                ctrl.SetValue(current)
            self._legacy_storage_snapshot[key] = current
    def _sync_structured_editor(self) -> None:
        feature_used = bool(getattr(self, "storage_rows", []))
        quota_used = self._quota_source_declared and (
            self.quota_enabled_cb.GetValue()
            or bool(self.quota_scope_ctrl.GetValue().strip())
            or bool(self.quota_subject_ctrl.GetValue().strip())
        )
        feature_used = feature_used or quota_used
        # Check backend selection non-empty
        sel = self.quota_backend_choice.GetStringSelection() if self.quota_backend_choice.GetSelection() != self._wx.NOT_FOUND else ""
        if self._quota_source_declared and sel and sel != t("connection.quota_status_unconfigured"):
            feature_used = True
        if self._provider_template is None and not feature_used:
            return
        if self._provider_template is None:
            self._provider_template = {
                "schema_version": 2,
                "profile_id": "local",
                "name": self.system_name_ctrl.GetValue().strip() or "Custom HPC",
                "scheduler": "slurm",
                "storage": [],
                "quota_sources": [],
            }
            self._provider_origin = "local"
        self._sync_legacy_storage_paths()
        # Sync storage
        self._provider_template["storage"] = [dict(row) for row in getattr(self, "storage_rows", [])]
        sources = self._provider_template.get("quota_sources")
        preserved = [dict(item) for item in sources if isinstance(item, dict)] if isinstance(sources, list) else []
        if not self._quota_source_declared:
            return
        source = dict(preserved[0])
        backend_sel = self.quota_backend_choice.GetStringSelection() if self.quota_backend_choice.GetSelection() != self._wx.NOT_FOUND else ""
        if backend_sel == t("connection.quota_status_unconfigured"):
            backend_sel = ""
        # Strip unsupported suffix
        if " (unsupported)" in backend_sel:
            backend_sel = backend_sel.split(" ")[0]
        source.update({
            "enabled": self.quota_enabled_cb.GetValue(),
            "consent": self.quota_consent_cb.GetValue(),
            "backend_id": backend_sel.strip(),
            "command_template": "" if self._provider_origin == "local" else self.quota_command_ctrl.GetValue().strip(),
            "scope": self.quota_scope_ctrl.GetValue().strip(),
            "subject_template": self.quota_subject_ctrl.GetValue().strip(),
        })
        self._provider_template["quota_sources"] = [source, *preserved[1:]]
    def _load_profile(self, profile: dict[str, Any]) -> None:
        self.profile_name_ctrl.SetValue(str(profile.get("name", "")))
        self.host_ctrl.SetValue(str(profile.get("host", "")))
        self.port_ctrl.SetValue(str(profile.get("port", 22)))
        self.username_ctrl.SetValue(str(profile.get("username", "")))
        self.project_ctrl.SetValue(str(profile.get("project", "")))
        self.account_ctrl.SetValue(str(profile.get("account", "")))
        self.key_path_ctrl.SetValue(str(profile.get("key_path", "") or profile.get("ssh_key", "")))
        # Do not auto-populate password for security; keep empty unless legacy plaintext present for Add? Follow Qt: only show if save_password and password plaintext exists
        # For edit, never auto-fill saved encrypted
        if profile.get("save_password") and isinstance(profile.get("password"), str) and profile.get("password"):
            self.password_ctrl.SetValue(str(profile.get("password")))
        else:
            self.password_ctrl.SetValue("")
        self.cb_save_password.SetValue(bool(profile.get("save_password", False)))
        prompt_policy = str(profile.get("password_prompt_policy") or "when-needed")
        if prompt_policy == "edit-only":
            self.rb_prompt_edit_only.SetValue(True)
        else:
            self.rb_prompt_when_needed.SetValue(True)
        # Host key policy
        host_key_policy = str(profile.get("host_key_policy") or "accept-new").strip()
        if host_key_policy not in {"accept-new", "strict"}:
            host_key_policy = "accept-new"
        self.cb_host_key_policy.SetSelection(0 if host_key_policy == "accept-new" else 1)
        # Keepalive
        self.sp_keepalive.SetValue(coerce_keepalive_interval(profile.get("keepalive_interval_seconds", 30)))
        self.sp_transfer_parallelism.SetValue(coerce_profile_transfer_parallelism(profile.get("transfer_parallelism", 1)))
        self.sp_ssh_timeout.SetValue(coerce_profile_ssh_timeout(profile.get("ssh_timeout")) or 0)
        self.cb_x11.SetValue(bool(profile.get("x11_forwarding", False)))
        self.cb_cli_allowed.SetValue(bool(profile.get("cli_allowed", False)))
        # File manager
        fm = normalize_file_manager_settings(profile.get("file_manager"))
        self.default_local_dir_ctrl.SetValue(fm["local_start_dir"])
        # Jump host
        jump = normalize_jump_host_settings(profile.get("jump_host"))
        self.cb_jump_enabled.SetValue(bool(jump["enabled"]))
        self.jump_host_ctrl.SetValue(jump["host"])
        self.sp_jump_port.SetValue(int(jump["port"]))
        self.jump_username_ctrl.SetValue(jump["username"])
        self.jump_key_path_ctrl.SetValue(jump["key_path"])
        jump_policy = str(jump["host_key_policy"] or "accept-new").strip()
        self.cb_jump_host_key_policy.SetSelection(0 if jump_policy != "strict" else 1)
        # System
        system = normalize_system_settings(profile.get("system"))
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
    def _collect_profile(self) -> dict[str, Any] | None:
        wx = self._wx
        try:
            port = int(self.port_ctrl.GetValue().strip() or "22")
        except ValueError:
            wx.MessageBox(t("login.err_port_numeric"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.port_ctrl.SetFocus()
            return None
        if not (1 <= port <= 65535):
            wx.MessageBox(t("login.err_port_numeric"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.port_ctrl.SetFocus()
            return None
        host = self.host_ctrl.GetValue().strip()
        if not host:
            wx.MessageBox(t("login.err_host_required"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            self.host_ctrl.SetFocus()
            return None
        # Provider-required validation before assembling?
        # We validate after building provider context
        is_edit = bool(self._initial_profile)
        profile: dict[str, Any] = dict(self._initial_profile) if is_edit else {}
        # Basic patch
        profile.update({
            "name": self.profile_name_ctrl.GetValue().strip(),
            "host": host,
            "port": port,
            "username": self.username_ctrl.GetValue().strip(),
            "project": self.project_ctrl.GetValue().strip(),
            "account": self.account_ctrl.GetValue().strip(),
            "password": self.password_ctrl.GetValue(),
            "key_path": self.key_path_ctrl.GetValue().strip(),
            "host_key_policy": "strict" if self.cb_host_key_policy.GetSelection() == 1 else "accept-new",
            "x11_forwarding": self.cb_x11.GetValue(),
            "cli_allowed": self.cb_cli_allowed.GetValue(),
            "keepalive_interval_seconds": int(self.sp_keepalive.GetValue()),
            "transfer_parallelism": int(self.sp_transfer_parallelism.GetValue()),
            "ssh_timeout": float(self.sp_ssh_timeout.GetValue()) or None,
            "save_password": self.cb_save_password.GetValue(),
            "password_prompt_policy": "edit-only" if self.rb_prompt_edit_only.GetValue() else "when-needed",
            "system": {**self._system_form_values()},
        })
        # Clear secret material not to ride through; will be handled by shared service
        for sk in ("password_dpapi", "password_enc", "password_salt"):
            profile.pop(sk, None)
        # Provider template preservation logic mirrors Qt's _collect_profile
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
            {"local_start_dir": self.default_local_dir_ctrl.GetValue().strip()},
        )
        if self.cb_jump_enabled.GetValue() and not self.jump_host_ctrl.GetValue().strip():
            wx.MessageBox(t("connection.jump_host_required"), t("common.error"), wx.OK | wx.ICON_WARNING)
            self.jump_host_ctrl.SetFocus()
            return None
        profile["jump_host"] = patch_jump_host_settings(
            (self._initial_profile or {}).get("jump_host"),
            {
                "enabled": self.cb_jump_enabled.GetValue(),
                "host": self.jump_host_ctrl.GetValue().strip(),
                "port": int(self.sp_jump_port.GetValue()),
                "username": self.jump_username_ctrl.GetValue().strip(),
                "key_path": self.jump_key_path_ctrl.GetValue().strip(),
                "host_key_policy": "strict" if self.cb_jump_host_key_policy.GetSelection() == 1 else "accept-new",
            },
        )
        # Provider-required project/account validation comes only from the
        # declarative template selected for this profile.
        provider_meta = self._provider_template
        if isinstance(provider_meta, dict):
            requirements = provider_meta.get("requirements", {}) if isinstance(provider_meta.get("requirements"), dict) else {}
            for key, ctrl, label in (("project", self.project_ctrl, self.project_label), ("account", self.account_ctrl, self.account_label)):
                rule = requirements.get(key) if isinstance(requirements, dict) else None
                if isinstance(rule, dict) and rule.get("required") and not ctrl.GetValue().strip():
                    wx.MessageBox(
                        t("connection.required_field").format(field=label.GetLabel().rstrip(" *")),
                        t("login.err_title"),
                        wx.OK | wx.ICON_WARNING,
                    )
                    ctrl.SetFocus()
                    return None
        # Fallback name handling
        if not profile.get("name"):
            username = profile.get("username", "").strip()
            host_val = profile.get("host", "").strip()
            fallback = f"{username}@{host_val}" if username else host_val
            if not fallback:
                wx.MessageBox(t("login.err_host_required"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
                return None
            profile["name"] = fallback
        return profile
    def _save_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        if self._on_save is not None and not self._on_save(profile):
            return
        self.dlg.EndModal(self._wx.ID_OK)
    def _save_and_connect_clicked(self) -> None:
        profile = self._collect_profile()
        if profile is None:
            return
        callback = self._on_save_and_connect or self._on_save
        if callback is not None and not callback(profile):
            return
        self.dlg.EndModal(self._wx.ID_OK)
