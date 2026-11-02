"""Editor remote io mixin behavior."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QMessageBox
)

from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.core.history import append_event




class EditorRemoteIoMixin:
    def load_path(self):
        document = self._current_document()
        if document is not None and document.is_local:
            path = document.path
            try:
                content = Path(path).read_text(encoding="utf-8")
                document.text.setPlainText(content)
                append_event({"type": "editor_load", "path": path})
            except (OSError, UnicodeError) as e:
                show_exception(self, title=t("common.error"), user_message=t("editor.open_failed").format(err=e), exc=e, area="EDITOR")
            return
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        path = self.path_in.text().strip()
        if not path:
            return
        try:
            files = self.session["files"]
            reader = getattr(files, "read_text_for_edit", files.read_text)
            content = reader(path)
            self.open_file(path, content)
            append_event({"type": "editor_load", "path": path})
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.open_failed").format(err=e), exc=e, area="EDITOR")
    def save_path(self, force_submit: bool = False, run_in_terminal: bool = False):
        document = self._current_document()
        path = self.path_in.text().strip()
        if document is not None and document.is_local:
            if not path:
                return
            text = self.text.toPlainText()
            if not self._validate_before_save(path, text):
                return
            try:
                Path(path).write_text(text, encoding="utf-8", newline="")
                self._set_active_document_path(path)
                document.saved_text = text
                document.text.document().setModified(False)
                append_event({"type": "editor_save", "path": path})
                if run_in_terminal and path.lower().endswith(".sh"):
                    self.run_in_terminal_requested.emit(path)
                    return
                QMessageBox.information(self, t("common.info"), t("editor.saved"))
            except OSError as e:
                show_exception(self, title=t("common.error"), user_message=t("editor.save_failed").format(err=e), exc=e, area="EDITOR")
            return
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if not path:
            return
        text = self.text.toPlainText()
        if not self._validate_before_save(path, text):
            return
        try:
            self.session["files"].write_text(path, text)
            self._set_active_document_path(path)
            document.saved_text = text
            document.text.document().setModified(False)
            append_event({"type": "editor_save", "path": path})
            if run_in_terminal:
                if path.lower().endswith(".sh"):
                    self.run_in_terminal_requested.emit(path)
                return
            self._offer_submit_after_save(path, force_submit=force_submit)
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.save_failed").format(err=e), exc=e, area="EDITOR")
    def _validate_before_save(self, path: str, text: str) -> bool:
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            return True

        warnings = self._collect_lint_issues(path, text)

        if not warnings:
            return True

        message = (t("editor.validation_title")) + "\n\n" + "\n".join(warnings)
        answer = QMessageBox.question(
            self,
            t("common.warning"),
            message + "\n\n" + (t("editor.validation_continue")),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes
    def _offer_submit_after_save(self, path: str, *, force_submit: bool = False):
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            QMessageBox.information(self, t("common.info"), t("editor.saved"))
            return

        if not force_submit:
            answer = QMessageBox.question(
                self,
                t("editor.submit"),
                t("editor.ask_submit_after_save"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, t("common.info"), t("editor.saved"))
                return

        slurm = (self.session or {}).get("slurm")
        if not slurm:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        try:
            out = slurm.sbatch(path)
            append_event({"type": "editor_submit", "path": path, "result": out})
            job_id = self._extract_job_id(out)
            if job_id:
                self.script_submitted.emit(job_id, path)
                msg = (t("editor.submitted_job")).format(jobid=job_id)
                QMessageBox.information(self, t("common.info"), msg + "\n" + (out or ""))
            else:
                # sbatch can fail and still return output text. Show actionable error.
                details = out or ""
                hint = self._diagnose_submit_output(details)
                QMessageBox.critical(
                    self,
                    t("common.error"),
                    (t("editor.submit_failed")) + "\n\n" + hint + ("\n\n" + details if details else ""),
                )
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.submit_error").format(err=e), exc=e, area="SLURM")
    @staticmethod
    def _extract_job_id(sbatch_output: str) -> str:
        txt = sbatch_output or ""
        m = re.search(r"Submitted batch job\s+(\d+)", txt, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        return ""
