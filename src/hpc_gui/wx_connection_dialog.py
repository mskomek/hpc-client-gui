"""Public wx connection/profile dialog facade for Add / Edit / Duplicate."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hpc_gui.config.storage import coerce_profile_ssh_timeout, coerce_profile_transfer_parallelism
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.ssh.client import coerce_keepalive_interval
from hpc_gui.wx_connection_dialog_view import ConnectionDialogViewMixin
from hpc_gui.wx_connection_dialog_events import ConnectionDialogEventsMixin
from hpc_gui.wx_connection_dialog_profile import ConnectionDialogProfileMixin
from hpc_gui.wx_connection_dialog_templates import ConnectionDialogTemplateMixin
from hpc_gui.wx_connection_dialog_storage import ConnectionDialogStorageMixin, _show_storage_area_dialog
from hpc_gui.wx_connection_dialog_self_test import ConnectionDialogSelfTestMixin


class WxConnectionDialog(
    ConnectionDialogViewMixin,
    ConnectionDialogEventsMixin,
    ConnectionDialogProfileMixin,
    ConnectionDialogTemplateMixin,
    ConnectionDialogStorageMixin,
    ConnectionDialogSelfTestMixin,
):
    """wx-native profile editor.

    Usage:
        dlg = WxConnectionDialog(parent, initial_profile=None, mode="add",
                                 on_save=callable, on_save_and_connect=callable)
        result = dlg.ShowModal()
    For testability the dialog logic is separated from wx top-level handling
    where possible.
    """

    def __init__(
        self,
        parent,
        *,
        initial_profile: dict[str, Any] | None = None,
        mode: str = "add",
        on_save: Callable[[dict[str, Any]], bool] | None = None,
        on_save_and_connect: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        try:
            import wx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("wxPython is not installed") from exc
        self._wx = wx
        self.parent = parent
        self.mode = mode if mode in ("add", "edit", "duplicate") else "add"
        self._initial_profile: dict[str, Any] = dict(initial_profile or {})
        self._on_save = on_save
        self._on_save_and_connect = on_save_and_connect
        provider_template = self._initial_profile.get("provider_template")
        if not isinstance(provider_template, dict):
            system = self._initial_profile.get("system")
            provider_template = system.get("provider_template") if isinstance(system, dict) else None
        self._provider_template: dict[str, Any] | None = (
            deepcopy(provider_template) if isinstance(provider_template, dict) else None
        )
        source = self._initial_profile.get("system_template_source")
        self._system_template_source: dict[str, str] | None = (
            {str(k): str(v) for k, v in source.items()} if isinstance(source, dict) else None
        )
        self._provider_origin = "plugin" if self._provider_template is not None and self._system_template_source and self._system_template_source.get("kind") == "plugin" else ("local" if self._provider_template is not None else None)
        if self._provider_template is not None and self._provider_origin is None:
            self._provider_origin = "local"
        self._template_action_taken = False
        self._quota_source_declared = False
        self._legacy_storage_snapshot: dict[str, str] = {}
        self._keepalive_default = coerce_keepalive_interval(self._initial_profile.get("keepalive_interval_seconds", 30))
        self._transfer_parallelism_default = coerce_profile_transfer_parallelism(self._initial_profile.get("transfer_parallelism", 1))
        self._ssh_timeout_default = coerce_profile_ssh_timeout(self._initial_profile.get("ssh_timeout"))

        self._destroyed = False
        self._build_dialog()
        self._language_callback = self.retranslate_ui
        subscribe_language_change(self._language_callback)

    # -- UI construction -----------------------------------------------------

        # Tab order is natural via creation order; ensure focus on first invalid after validation

        # Make Edit disabled until selection logic elsewhere

    # -- Helpers -------------------------------------------------------------






    def retranslate_ui(self, _language: str | None = None) -> None:
        """Refresh labels that can change while this modal is open."""
        self.dlg.SetTitle({
            "add": t("connection.dialog_title"),
            "edit": t("connection.edit_dialog_title"),
            "duplicate": t("login.duplicate"),
        }.get(self.mode, t("connection.dialog_title")))
        self.btn_system_templates.SetLabel(t("connection.system_templates_menu"))
        self.btn_save_system_template.SetLabel(t("connection.save_system_template"))
        self.rb_prompt_when_needed.SetLabel(t("connection.password_prompt_when_needed"))
        self.rb_prompt_edit_only.SetLabel(t("connection.password_no_prompt"))
        self.cb_save_password.SetLabel(t("login.save_password"))
        self.cluster_toggle.SetLabel(
            f"{t('connection.system_settings')}  {'▼' if self.cluster_toggle.GetValue() else '▶'}"
        )
        self.advanced_toggle.SetLabel(
            f"{t('connection.advanced_settings')}  {'▼' if self.advanced_toggle.GetValue() else '▶'}"
        )
        for button, key in (
            (self.btn_storage_add, "connection.storage_add"),
            (self.btn_storage_edit, "connection.storage_edit"),
            (self.btn_storage_remove, "connection.storage_remove"),
            (self.btn_test_cluster, "connection.test_cluster"),
            (self.btn_cancel, "common.cancel"),
            (self.btn_save, "connection.save"),
            (self.btn_save_connect, "connection.save_and_connect"),
        ):
            button.SetLabel(t(key))
        self.quota_enabled_cb.SetLabel(t("connection.quota_enable"))
        self.quota_consent_cb.SetLabel(t("connection.quota_consent"))
        self.quota_command_ctrl.SetHint(t("connection.quota_command"))
        self.quota_scope_ctrl.SetHint(t("connection.quota_scope"))
        self.quota_subject_ctrl.SetHint(t("connection.quota_subject"))
        self._update_provider_labels()
        self._update_quota_status()
        self.dlg.Layout()

    def _pick_key(self, target: Any) -> None:
        dlg = self._wx.FileDialog(self.dlg, t("login.ssh_key"), style=self._wx.FD_OPEN | self._wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == self._wx.ID_OK:
            target.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _pick_local_dir(self) -> None:
        dlg = self._wx.DirDialog(self.dlg, t("connection.browse_default_local_folder"), style=self._wx.DD_DEFAULT_STYLE | self._wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == self._wx.ID_OK:
            self.default_local_dir_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _update_provider_labels(self) -> None:
        provider = self._provider_template or {}
        requirements = provider.get("requirements", {}) if isinstance(provider, dict) else {}
        for key, label in (("project", self.project_label), ("account", self.account_label)):
            rule = requirements.get(key) if isinstance(requirements, dict) else None
            name = ""
            required = False
            help_text = ""
            if isinstance(rule, dict):
                name = str(rule.get("label") or t(f"connection.{key}"))
                required = bool(rule.get("required"))
                help_text = str(rule.get("help") or "")
            else:
                name = t(f"connection.{key}")
            display = name + (" *" if required else "")
            label.SetLabel(display)
            if help_text:
                label.SetToolTip(help_text)
            else:
                label.SetToolTip("")
        # Also update provider info line
        prov_name = ""
        if isinstance(self._provider_template, dict):
            prov_name = str(self._provider_template.get("name") or self._provider_template.get("profile_id") or "")
            if not prov_name and isinstance(self._provider_template.get("site"), dict):
                prov_name = str(self._provider_template.get("site").get("name") or "")
        if prov_name:
            self.provider_info.SetLabel(f"{t('connection.system_templates_menu')}: {prov_name}" if t("connection.system_templates_menu") != "[connection.system_templates_menu]" else f"Provider: {prov_name}")
        else:
            self.provider_info.SetLabel("")

    def _update_quota_status(self) -> None:
        if not self._quota_source_declared:
            self.quota_status_label.SetLabel(t("connection.quota_status_unconfigured"))
            self.quota_status_label.Wrap(500)
            return
        state = quota_gate(
            {
                "enabled": self.quota_enabled_cb.GetValue(),
                "consent": self.quota_consent_cb.GetValue(),
                "backend_id": str(self.quota_backend_choice.GetStringSelection() or "").strip() if self.quota_backend_choice.GetStringSelection() != t("connection.quota_status_unconfigured") else "",
                "command_template": self.quota_command_ctrl.GetValue().strip(),
                "scope": self.quota_scope_ctrl.GetValue().strip(),
            },
            backend_ids=(),
        )
        # Map to label; avoid color-only signal
        if state == "disabled":
            self.quota_status_label.SetLabel(t("connection.quota_status_off"))
        elif state == "not_configured":
            self.quota_status_label.SetLabel(t("connection.quota_status_unconfigured"))
        elif state == "invalid_configuration":
            self.quota_status_label.SetLabel(t("connection.quota_status_invalid"))
        else:
            self.quota_status_label.SetLabel(t("connection.quota_status_backend_required"))
        self.quota_status_label.Wrap(500)
        self.scrolled.Layout()
























    # -- Public API ----------------------------------------------------------

    def ShowModal(self) -> int:
        return self.dlg.ShowModal()

    def Destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        unsubscribe_language_change(self._language_callback)
        self.dlg.Destroy()

    def _open_storage_area_editor(self, existing=None):
        return _show_storage_area_dialog(self.dlg, existing)

    def GetDialog(self):
        return self.dlg


def show_connection_dialog(
    parent,
    *,
    initial_profile: dict[str, Any] | None = None,
    mode: str = "add",
    on_save: Callable[[dict[str, Any]], bool] | None = None,
    on_save_and_connect: Callable[[dict[str, Any]], bool] | None = None,
) -> int:
    """Convenience wrapper returning wx.ID_OK / wx.ID_CANCEL."""
    dlg = WxConnectionDialog(parent, initial_profile=initial_profile, mode=mode, on_save=on_save, on_save_and_connect=on_save_and_connect)
    try:
        return dlg.ShowModal()
    finally:
        dlg.Destroy()


__all__ = ["WxConnectionDialog", "show_connection_dialog"]
