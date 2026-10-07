"""ConnectionDialogStorageMixin owns the storage portion of the wx connection dialog."""

from __future__ import annotations

from typing import Any

from hpc_gui.core.i18n import t
from hpc_gui.plugins.models import validate_storage_area, validate_storage_policy
from hpc_gui.services.quota_monitor import quota_gate

# Extracted dialog responsibility; behavior stays on the public dialog facade.

def _show_storage_area_dialog(parent, existing: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        import wx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("wxPython is not installed") from exc

    is_edit = existing is not None
    title = t("connection.storage_edit") if is_edit else t("connection.storage_add")
    dlg = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dlg.SetMinSize(wx.Size(520, 480))

    # Controls
    label_ctrl = wx.TextCtrl(dlg, value=str((existing or {}).get("label") or (existing or {}).get("id") or ""))
    label_ctrl.SetHint(t("connection.storage_label"))
    path_ctrl = wx.TextCtrl(dlg, value=str((existing or {}).get("path_template") or ""))
    path_ctrl.SetHint(t("connection.storage_path"))
    kinds = ["home", "scratch", "project", "custom", "node-local"]
    kind_choice = wx.Choice(dlg, choices=kinds)
    cur_kind = str((existing or {}).get("kind") or "custom")
    if cur_kind in kinds:
        kind_choice.SetSelection(kinds.index(cur_kind))
    else:
        kind_choice.SetSelection(3)
    contexts = ["login-node", "shared", "compute-node", "unknown"]
    ctx_choice = wx.Choice(dlg, choices=contexts)
    cur_ctx = str((existing or {}).get("access_context") or "unknown")
    if cur_ctx in contexts:
        ctx_choice.SetSelection(contexts.index(cur_ctx))
    else:
        ctx_choice.SetSelection(3)
    enabled_cb = wx.CheckBox(dlg, label=t("connection.storage_enabled"))
    enabled_cb.SetValue(bool((existing or {}).get("enabled", True)) if isinstance((existing or {}).get("enabled"), bool) else True)
    # Backup policy
    backup_choices = [t("connection.storage_unknown"), t("connection.storage_yes"), t("connection.storage_no")]
    backup_choice = wx.Choice(dlg, choices=backup_choices)
    policy = (existing or {}).get("policy") if isinstance((existing or {}).get("policy"), dict) else {}
    backup_val = policy.get("backup") if isinstance(policy, dict) else None
    if backup_val is True:
        backup_choice.SetSelection(1)
    elif backup_val is False:
        backup_choice.SetSelection(2)
    else:
        backup_choice.SetSelection(0)
    cleanup_ctrl = wx.TextCtrl(dlg, value=str(policy.get("cleanup_note") or "") if isinstance(policy, dict) else "")
    cleanup_ctrl.SetHint(t("connection.storage_cleanup"))
    retention_ctrl = wx.TextCtrl(dlg, value=str(policy.get("retention_days") or "") if isinstance(policy, dict) and policy.get("retention_days") is not None else "")
    retention_ctrl.SetHint(t("connection.storage_retention"))
    url_ctrl = wx.TextCtrl(dlg, value=str(policy.get("documentation_url") or "") if isinstance(policy, dict) else "")
    url_ctrl.SetHint(t("connection.storage_source_url"))

    form = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
    form.AddGrowableCol(1, 1)
    def add_row(label_key, widget):
        lbl = wx.StaticText(dlg, label=t(label_key) if t(label_key) != f"[{label_key}]" else label_key.split(".")[-1])
        form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(widget, 1, wx.EXPAND)

    add_row("connection.storage_label", label_ctrl)
    add_row("connection.storage_path", path_ctrl)
    add_row("connection.storage_kind", kind_choice)
    add_row("connection.storage_access_context", ctx_choice)
    # Enabled row
    enabled_label = wx.StaticText(dlg, label=t("connection.storage_enabled"))
    form.Add(enabled_label, 0, wx.ALIGN_CENTER_VERTICAL)
    form.Add(enabled_cb, 0, wx.ALIGN_CENTER_VERTICAL)
    add_row("connection.storage_backup", backup_choice)
    add_row("connection.storage_cleanup", cleanup_ctrl)
    add_row("connection.storage_retention", retention_ctrl)
    add_row("connection.storage_source_url", url_ctrl)

    btn_sizer = dlg.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)

    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(form, 1, wx.EXPAND | wx.ALL, 12)
    root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 12)
    dlg.SetSizer(root)
    dlg.Fit()
    # Ensure minimal size on DPI scaled displays
    dlg.SetSizeHints(520, 400)

    # Accessibility: first field
    label_ctrl.SetFocus()

    while True:
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            return None
        label = label_ctrl.GetValue().strip()
        path = path_ctrl.GetValue().strip()
        kind = kinds[kind_choice.GetSelection()] if kind_choice.GetSelection() != wx.NOT_FOUND else "custom"
        access_context = contexts[ctx_choice.GetSelection()] if ctx_choice.GetSelection() != wx.NOT_FOUND else "unknown"
        enabled = enabled_cb.GetValue()
        backup_sel = backup_choice.GetSelection()
        backup_map = {1: True, 2: False}
        backup = backup_map.get(backup_sel)
        cleanup = cleanup_ctrl.GetValue().strip()
        retention_raw = retention_ctrl.GetValue().strip()
        doc_url = url_ctrl.GetValue().strip()

        # Validate id/label
        area_id = str((existing or {}).get("id") or "")
        if not area_id:
            area_id = "-".join(label.lower().split()) or "storage"
            # uniqueness will be handled by caller; here just ensure non-empty
        area: dict[str, Any] = {
            "id": area_id,
            "label": label,
            "kind": kind,
            "enabled": bool(enabled),
            "path_template": path,
            "access_context": access_context,
        }
        if validate_storage_area(area):
            wx.MessageBox(validate_storage_area(area) or t("connection.storage_path_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        # Validate retention
        if retention_raw and not retention_raw.isdigit():
            wx.MessageBox(t("connection.storage_retention_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        retention_val = int(retention_raw) if retention_raw else None
        policy_check: dict[str, Any] = {}
        if retention_val is not None:
            policy_check["retention_days"] = retention_val
        if doc_url:
            policy_check["documentation_url"] = doc_url
            if validate_storage_policy(policy_check):
                wx.MessageBox(t("connection.storage_source_url_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
                continue
        # Build final area with existing unknown keys preserved
        base = dict(existing) if isinstance(existing, dict) else {}
        # Preserve unknown top-level keys implicitly via base copy; then override known
        base.update(area)
        # Preserve/merge policy unknown keys
        existing_policy = base.get("policy") if isinstance(base.get("policy"), dict) else {}
        merged_policy: dict[str, Any] = dict(existing_policy) if isinstance(existing_policy, dict) else {}
        merged_policy.update({
            "backup": backup,
            "cleanup_note": cleanup,
            "retention_days": retention_val,
            "documentation_url": doc_url,
        })
        # Remove empty optional keys to keep parity with Qt (None vs absent not critical)
        if validate_storage_policy(merged_policy):
            err = validate_storage_policy(merged_policy)
            wx.MessageBox(err or t("connection.storage_retention_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        base["policy"] = merged_policy
        # Final area validation
        if validate_storage_area(base):
            wx.MessageBox(validate_storage_area(base) or t("connection.storage_path_invalid"), t("common.error"), wx.OK | wx.ICON_WARNING)
            continue
        dlg.Destroy()
        return base


class ConnectionDialogStorageMixin:
    def _refresh_storage_list(self) -> None:
        self.storage_list.Clear()
        for row in getattr(self, "storage_rows", []):
            label = str(row.get("label") or row.get("id") or "Storage")
            path = str(row.get("path_template") or "").strip()
            display = f"{label}: {path}" if path else f"{label} ({t('connection.storage_areas_empty')})"
            self.storage_list.Append(display)
    def _update_storage_summary(self) -> None:
        rows = (self._provider_template or {}).get("storage", [])
        if not isinstance(rows, list):
            rows = []
        # Sync internal rows list
        self.storage_rows: list[dict[str, Any]] = [dict(r) for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        # Update list box
        self._refresh_storage_list()
    def _load_quota_widgets(self) -> None:
        sources = (self._provider_template or {}).get("quota_sources", [])
        source = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else {}
        self._quota_source_declared = bool(source)
        self.quota_enabled_cb.SetValue(source.get("enabled") is True)
        self.quota_consent_cb.SetValue(source.get("consent") is True)
        backend_id = str(source.get("backend_id") or "").strip()
        # Populate backend choices from production registry plus current
        try:
            from hpc_gui.services.quota_monitor import build_production_quota_backend_registry
            registry_ids = sorted(build_production_quota_backend_registry().ids)
        except Exception:
            registry_ids = []
        choices = [t("connection.quota_status_unconfigured")]
        # Build choices list including registry ids and current if unsupported
        for bid in registry_ids:
            if bid not in choices:
                choices.append(bid)
        if backend_id and backend_id not in choices:
            choices.append(f"{backend_id} (unsupported)")
        self.quota_backend_choice.Clear()
        for c in choices:
            self.quota_backend_choice.Append(c)
        # Select
        if backend_id:
            # Find exact or unsupported variant
            idx = self._wx.NOT_FOUND
            for i, c in enumerate(choices):
                if c == backend_id or c.startswith(backend_id + " "):
                    idx = i
                    break
            if idx != self._wx.NOT_FOUND:
                self.quota_backend_choice.SetSelection(idx)
            else:
                self.quota_backend_choice.SetSelection(0)
        else:
            self.quota_backend_choice.SetSelection(0)
        self.quota_command_ctrl.SetValue(str(source.get("command_template") or ""))
        self.quota_scope_ctrl.SetValue(str(source.get("scope") or ""))
        self.quota_subject_ctrl.SetValue(str(source.get("subject_template") or ""))
        local = self._provider_origin == "local"
        supported = self._quota_source_declared
        for ctrl in (
            self.quota_enabled_cb,
            self.quota_consent_cb,
            self.quota_backend_choice,
            self.quota_command_ctrl,
            self.quota_scope_ctrl,
            self.quota_subject_ctrl,
        ):
            ctrl.Enable(supported)
        self.quota_command_label.Enable(supported)
        # Hide quota command/scope/subject when local without backend? Mirror Qt: when local, hide those
        for ctrl in (self.quota_command_label, self.quota_command_ctrl,):
            ctrl.Show(supported and not local)
        # Use 2-col handling: scope/subject labels need to be shown/hidden too
        # For simplicity, disable instead of hide for scope/subject when local
        if local:
            self.quota_command_ctrl.SetValue("")
            self.quota_scope_ctrl.SetValue("")
            self.quota_subject_ctrl.SetValue("")
        self._update_quota_status()
        self.scrolled.Layout()
    def _add_storage_area(self) -> None:
        # Ensure provider template exists for local edits
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
        # Use helper dialog
        existing_ids = {str(row.get("id")) for row in getattr(self, "storage_rows", [])}
        area = self._open_storage_area_editor()
        if area is None:
            return
        # Ensure unique id
        base_id = str(area.get("id") or "storage")
        area_id = base_id
        suffix = 2
        while area_id in existing_ids:
            area_id = f"{base_id}-{suffix}"
            suffix += 1
        area["id"] = area_id
        if validate_storage_area(area):
            self._wx.MessageBox(validate_storage_area(area) or t("connection.storage_path_invalid"), t("common.error"), self._wx.OK | self._wx.ICON_WARNING)
            return
        self.storage_rows.append(area)
        self._sync_structured_editor()
        self._refresh_storage_list()
    def _edit_storage_area(self) -> None:
        sel = self.storage_list.GetSelection()
        if sel == self._wx.NOT_FOUND or sel >= len(getattr(self, "storage_rows", [])):
            return
        current = self.storage_rows[sel]
        updated = self._open_storage_area_editor(current)
        if updated is None:
            return
        if validate_storage_area(updated):
            self._wx.MessageBox(validate_storage_area(updated) or t("connection.storage_path_invalid"), t("common.error"), self._wx.OK | self._wx.ICON_WARNING)
            return
        # Preserve id uniqueness not needed for edit
        self.storage_rows[sel] = updated
        self._sync_structured_editor()
        self._refresh_storage_list()
    def _remove_storage_area(self) -> None:
        sel = self.storage_list.GetSelection()
        if sel != self._wx.NOT_FOUND and sel < len(getattr(self, "storage_rows", [])):
            self.storage_rows.pop(sel)
            self._sync_structured_editor()
            self._refresh_storage_list()
