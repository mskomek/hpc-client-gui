"""Asynchronous Slurm submit and script-run lifecycle for directories UI."""

from __future__ import annotations

import posixpath
import re
import shlex

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QMessageBox,
    QDialog, QPlainTextEdit, QDialogButtonBox,
    QProgressDialog
)

from hpc_gui.core.i18n import t
from hpc_gui.core.history import append_event




def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class _SubmitSignals(QObject):
    finished = Signal(object, str, str)  # worker, script path, sbatch output
    failed = Signal(object, str, str)  # worker, script path, error
class _SubmitWorker(QRunnable):
    def __init__(self, slurm, script_path: str):
        super().__init__()
        self._slurm = slurm
        self._script_path = script_path
        self.signals = _SubmitSignals()

    @Slot()
    def run(self) -> None:
        try:
            output = self._slurm.sbatch(self._script_path)
        except Exception as exc:
            self.signals.failed.emit(self, self._script_path, str(exc))
            return
        self.signals.finished.emit(self, self._script_path, output or "")
class _BatchSubmitSignals(QObject):
    progress = Signal(object, int, int, str)
    file_finished = Signal(object, str, str)  # worker, script path, sbatch output
    file_failed = Signal(object, str, str)  # worker, script path, error
    finished = Signal(object)  # worker, all paths processed
class _BatchSubmitWorker(QRunnable):
    def __init__(self, slurm, script_paths):
        super().__init__()
        self._slurm = slurm
        self._script_paths = list(script_paths)
        self.signals = _BatchSubmitSignals()

    @Slot()
    def run(self) -> None:
        total = len(self._script_paths)
        for index, script_path in enumerate(self._script_paths, 1):
            self.signals.progress.emit(self, index - 1, total, script_path)
            try:
                output = self._slurm.sbatch(script_path)
            except Exception as exc:
                self.signals.file_failed.emit(self, script_path, str(exc))
                continue
            self.signals.file_finished.emit(self, script_path, output or "")
        self.signals.finished.emit(self)
class _ShellRunSignals(QObject):
    finished = Signal(object, str, str)  # worker, script path, command output
    failed = Signal(object, str, str)  # worker, script path, error
class _ShellRunWorker(QRunnable):
    def __init__(self, ssh, script_path: str):
        super().__init__()
        self._ssh = ssh
        self._script_path = script_path
        self.signals = _ShellRunSignals()

    @staticmethod
    def command_for(script_path: str) -> str:
        script_dir = posixpath.dirname(script_path) or "."
        script_name = posixpath.basename(script_path)
        return (
            f"cd {shlex.quote(script_dir)} && "
            f"bash {shlex.quote('./' + script_name)}"
        )

    @Slot()
    def run(self) -> None:
        try:
            command = self.command_for(self._script_path)
            code, out, err = self._ssh.run(command, log_output=False)
            output = out if out.strip() else err
            if code != 0:
                message = output.strip() or f"script failed [exit={code}]"
                self.signals.failed.emit(self, self._script_path, message)
                return
        except Exception as exc:
            self.signals.failed.emit(self, self._script_path, str(exc))
            return
        self.signals.finished.emit(self, self._script_path, output or "")


class DirectoriesSubmissionMixin:
    def submit_script(self, script_path: str) -> None:
        slurm = (self.session or {}).get("slurm")
        if not slurm:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            append_event(
                {
                    "type": "directories_submit",
                    "path": script_path,
                    "status": "failed",
                    "error": "no Slurm session",
                }
            )
            return

        worker = _SubmitWorker(slurm, script_path)
        self._submit_workers.add(worker)
        worker.signals.finished.connect(self._on_submit_finished)
        worker.signals.failed.connect(self._on_submit_failed)
        QThreadPool.globalInstance().start(worker)
    def submit_scripts_batch(self, script_paths) -> None:
        slurm = (self.session or {}).get("slurm")
        if not slurm:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            append_event(
                {
                    "type": "directories_batch_submit",
                    "status": "failed",
                    "error": "no Slurm session",
                }
            )
            return

        # Defensive case-insensitive ordering, mirroring the panel emission.
        paths = sorted(
            (str(path) for path in (script_paths or []) if path),
            key=lambda path: path.casefold(),
        )
        if not paths:
            return

        worker = _BatchSubmitWorker(slurm, paths)
        worker.succeeded = []
        worker.failed = []
        progress = QProgressDialog(
            _tr("dirs.batch_submit_progress", "Submitting scripts..."),
            "",
            0,
            len(paths),
            self,
        )
        progress.setWindowTitle(_tr("dirs.submit_sbatch_batch", "Submit all with sbatch"))
        progress.setAutoClose(False)
        progress.show()
        worker.progress_dialog = progress
        self._batch_submit_workers.add(worker)
        worker.signals.progress.connect(self._on_batch_submit_progress)
        worker.signals.file_finished.connect(self._on_batch_submit_file_finished)
        worker.signals.file_failed.connect(self._on_batch_submit_file_failed)
        worker.signals.finished.connect(self._on_batch_submit_finished)
        QThreadPool.globalInstance().start(worker)
    @Slot(object, str, str)
    def _on_batch_submit_file_finished(
        self,
        worker: _BatchSubmitWorker,
        script_path: str,
        output: str,
    ) -> None:
        job_id = self._extract_job_id(output)
        if not job_id:
            worker.failed.append((script_path, "no valid job ID"))
            append_event(
                {
                    "type": "directories_batch_submit",
                    "path": script_path,
                    "status": "failed",
                    "result": output,
                    "error": "no valid job ID",
                }
            )
            return
        worker.succeeded.append((script_path, job_id))
        append_event(
            {
                "type": "directories_batch_submit",
                "path": script_path,
                "status": "success",
                "jobid": job_id,
                "result": output,
            }
        )
        self.script_submitted.emit(job_id, script_path)
    @Slot(object, str, str)
    def _on_batch_submit_file_failed(
        self,
        worker: _BatchSubmitWorker,
        script_path: str,
        error: str,
    ) -> None:
        worker.failed.append((script_path, str(error)))
        append_event(
            {
                "type": "directories_batch_submit",
                "path": script_path,
                "status": "failed",
                "error": str(error),
            }
        )
    @Slot(object)
    def _on_batch_submit_finished(self, worker: _BatchSubmitWorker) -> None:
        self._batch_submit_workers.discard(worker)
        progress = getattr(worker, "progress_dialog", None)
        if progress is not None:
            progress.setValue(progress.maximum())
            progress.close()
            progress.deleteLater()
        succeeded = list(getattr(worker, "succeeded", []) or [])
        failed = list(getattr(worker, "failed", []) or [])
        total = len(succeeded) + len(failed)
        if not total:
            return
        ok_count = len(succeeded)
        bad_count = len(failed)
        details = [f"{path}: {job_id}" for path, job_id in succeeded]
        details += [f"{path}: {error}" for path, error in failed]
        detail_text = "\n" + "\n".join(details) if details else ""
        if bad_count:
            QMessageBox.warning(
                self,
                t("common.error"),
                _tr(
                    "dirs.batch_submit_summary_failed",
                    "Batch submit finished: {ok} submitted, {bad} failed.",
                ).format(ok=ok_count, bad=bad_count) + detail_text,
            )
            return
        QMessageBox.information(
            self,
            t("common.info"),
            _tr(
                "dirs.batch_submit_summary_success",
                "Batch submit finished: {ok} scripts submitted.",
            ).format(ok=ok_count) + detail_text,
        )
    def run_shell_script(self, script_path: str) -> None:
        ssh = (self.session or {}).get("ssh")
        if not ssh:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            append_event(
                {
                    "type": "directories_run_shell",
                    "path": script_path,
                    "status": "failed",
                    "error": "no SSH session",
                }
            )
            return

        worker = _ShellRunWorker(ssh, script_path)
        self._shell_run_workers.add(worker)
        worker.signals.finished.connect(self._on_shell_run_finished)
        worker.signals.failed.connect(self._on_shell_run_failed)
        QThreadPool.globalInstance().start(worker)
    @Slot(object, int, int, str)
    def _on_batch_submit_progress(
        self,
        worker: _BatchSubmitWorker,
        completed: int,
        total: int,
        script_path: str,
    ) -> None:
        progress = getattr(worker, "progress_dialog", None)
        if progress is not None:
            progress.setRange(0, total)
            progress.setValue(completed)
            progress.setLabelText(script_path)
    @Slot(object, str, str)
    def _on_submit_finished(self, worker: _SubmitWorker, script_path: str, output: str) -> None:
        self._submit_workers.discard(worker)
        job_id = self._extract_job_id(output)
        if not job_id:
            append_event(
                {
                    "type": "directories_submit",
                    "path": script_path,
                    "status": "failed",
                    "result": output,
                    "error": "no valid job ID",
                }
            )
            message = t("dirs.submit_failed_no_job_id")
            if message == "[dirs.submit_failed_no_job_id]":
                message = "Submission returned no valid job ID. Check the script and Slurm response."
            if output:
                message += f"\n\n{output}"
            QMessageBox.critical(self, t("common.error"), message)
            return

        append_event(
            {
                "type": "directories_submit",
                "path": script_path,
                "status": "success",
                "jobid": job_id,
                "result": output,
            }
        )
        self.script_submitted.emit(job_id, script_path)
        message = t("dirs.submit_success")
        if message == "[dirs.submit_success]":
            message = "Submitted with sbatch. Job ID: {jobid}"
        QMessageBox.information(
            self,
            t("common.info"),
            message.format(jobid=job_id) + (f"\n\n{output}" if output else ""),
        )
    @Slot(object, str, str)
    def _on_submit_failed(self, worker: _SubmitWorker, script_path: str, error: str) -> None:
        self._submit_workers.discard(worker)
        append_event(
            {
                "type": "directories_submit",
                "path": script_path,
                "status": "failed",
                "error": error,
            }
        )
        message = t("dirs.submit_failed")
        if message == "[dirs.submit_failed]":
            message = "sbatch submission failed: {err}\nCheck the connection and Slurm script directives."
        QMessageBox.critical(self, t("common.error"), message.format(err=error))
    def _create_shell_run_result_dialog(
        self,
        script_path: str,
        message: str,
        output: str,
    ) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(t("common.info"))
        layout = QVBoxLayout(dialog)
        summary = QLabel(message)
        summary.setWordWrap(True)
        path_label = QLabel(script_path)
        path_label.setWordWrap(True)
        output_view = QPlainTextEdit()
        output_view.setObjectName("shellRunOutput")
        output_view.setReadOnly(True)
        output_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        output_view.setPlainText(output or "")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(summary)
        layout.addWidget(path_label)
        layout.addWidget(output_view, 1)
        layout.addWidget(buttons)

        available = self.screen().availableGeometry()
        max_width = max(320, int(available.width() * 0.90))
        max_height = max(240, int(available.height() * 0.85))
        dialog.setMaximumSize(max_width, max_height)
        dialog.resize(min(800, max_width), min(520, max_height))
        return dialog
    @Slot(object, str, str)
    def _on_shell_run_finished(self, worker: _ShellRunWorker, script_path: str, output: str) -> None:

        self._shell_run_workers.discard(worker)
        append_event(
            {
                "type": "directories_run_shell",
                "path": script_path,
                "status": "success",
                "result": output,
            }
        )
        message = t("dirs.run_shell_success")
        if message == "[dirs.run_shell_success]":
            message = "Script completed in terminal."
        self._create_shell_run_result_dialog(script_path, message, output).exec()
    @Slot(object, str, str)
    def _on_shell_run_failed(self, worker: _ShellRunWorker, script_path: str, error: str) -> None:
        self._shell_run_workers.discard(worker)
        append_event(
            {
                "type": "directories_run_shell",
                "path": script_path,
                "status": "failed",
                "error": error,
            }
        )
        message = t("dirs.run_shell_failed")
        if message == "[dirs.run_shell_failed]":
            message = "Script run failed: {err}"
        QMessageBox.critical(self, t("common.error"), message.format(err=error))
    @staticmethod
    def _extract_job_id(sbatch_output: str) -> str:
        match = re.search(
            r"Submitted batch job\s+(\d+)",
            sbatch_output or "",
            flags=re.IGNORECASE,
        )
        return match.group(1) if match else ""
