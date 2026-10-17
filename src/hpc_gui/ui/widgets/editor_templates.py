"""Editor templates mixin behavior."""

from __future__ import annotations


from PySide6.QtWidgets import (
    QMessageBox
)

from hpc_gui.core.i18n import t




class EditorTemplatesMixin:
    def _load_templates_filtered(self, plugin_id: str | None = None):
        from hpc_gui.plugins.job_templates import load_job_templates
        try:
            return load_job_templates(plugin_id=plugin_id)
        except TypeError:
            try:
                templates = load_job_templates()
            except Exception:
                return []
            if plugin_id:
                return [t for t in templates if t.plugin_id == plugin_id]
            return templates
        except Exception:
            return []
    def new_from_template_for_plugin(self, plugin_id: str):
        """Scoped template flow filtered to one plugin (host-owned)."""
        templates = self._load_templates_filtered(plugin_id)
        if not templates:
            QMessageBox.information(self, t("common.info"), t("templates.none_installed"))
            return
        from PySide6.QtWidgets import QDialog
        from hpc_gui.ui.dialogs.template_browser_dialog import TemplateBrowserDialog
        provider_template = {}
        if isinstance(self.session, dict):
            cfg = self.session.get("cfg")
            provider_template = getattr(cfg, "provider_template", {}) or {}
            if isinstance(provider_template, dict):
                provider_template = dict(provider_template)
                provider_template["account"] = getattr(cfg, "account", "")
        dialog = TemplateBrowserDialog(self, templates, provider_template=provider_template)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        template, values = dialog.result_template, dialog.result_values
        if template is None:
            return
        from hpc_gui.plugins.job_templates import render_template
        try:
            rendered = render_template(template, values)
        except Exception as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        suggested = template.file_name or f"{template.id}.txt"
        self.open_file("", rendered)
        index = self.document_tabs.currentIndex()
        if index >= 0:
            self.document_tabs.setTabText(index, self._tab_title(suggested))
        document = self._current_document()
        if document is not None:
            document.path = ""
    def new_from_template(self):
        """Open the plugin-template browser; rendered text opens in a NEW
        document tab for review/editing. Nothing is saved or submitted
        automatically."""
        from hpc_gui.plugins.job_templates import load_job_templates

        try:
            templates = load_job_templates()
        except Exception:
            templates = []
        if not templates:
            QMessageBox.information(
                self,
                t("common.info"),
                t("templates.none_installed"),
            )
            return
        from PySide6.QtWidgets import QDialog
        from hpc_gui.ui.dialogs.template_browser_dialog import TemplateBrowserDialog

        provider_template = {}
        if isinstance(self.session, dict):
            cfg = self.session.get("cfg")
            provider_template = getattr(cfg, "provider_template", {}) or {}
            if isinstance(provider_template, dict):
                provider_template = dict(provider_template)
                provider_template["account"] = getattr(cfg, "account", "")
        dialog = TemplateBrowserDialog(self, templates, provider_template=provider_template)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        template, values = dialog.result_template, dialog.result_values
        if template is None:
            return
        from hpc_gui.plugins.job_templates import render_template

        try:
            rendered = render_template(template, values)
        except Exception as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        # Preview requirement: content lands in an unsaved editor tab.
        suggested = template.file_name or f"{template.id}.txt"
        self.open_file("", rendered)
        index = self.document_tabs.currentIndex()
        if index >= 0:
            self.document_tabs.setTabText(index, self._tab_title(suggested))
        document = self._current_document()
        if document is not None:
            document.path = ""
