from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from hpc_gui.config.storage import SBATCH_FOLLOW_MODE_OUTPUTS_TAB

from hpc_gui.core.i18n import t

from hpc_gui.core.ui_errors import show_exception

from hpc_gui.core.history import append_event

from hpc_gui.services.slurm_models import parse_scontrol

from hpc_gui.services.slurm_script_parser import storage_area_for_path

from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings

from ._jobs_output_text import _ansi_to_html, _bounded_output_text



class _JobsOutputsJobsMixin:
        def refresh_jobs(self):
            if not self.session or not self.session.get("slurm"):
                return
            user = self.session["cfg"].username
            slurm = self.session["slurm"]

            def success(txt) -> None:
                if not self.is_details_polling_visible():
                    return
                self.jobs_text.setPlainText(txt)
                append_event({"type": "squeue", "user": user})

            def failed(e) -> None:
                show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="JOBS")

            self._start_async(
                "squeue",
                lambda: slurm.squeue(user),
                success,
                on_error=failed,
            )
        def cancel_job(self):
            if not self.session or not self.session.get("slurm"):
                return
            jobid = self.cancel_id.text().strip()
            if not jobid:
                return
            slurm = self.session["slurm"]

            def success(res) -> None:
                self.jobs_text.append("\n" + res)
                append_event({"type": "scancel", "jobid": jobid})

            def failed(e) -> None:
                show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="JOBS")

            self._start_async(
                "scancel",
                lambda: slurm.scancel(jobid),
                success,
                on_error=failed,
            )
        def refresh_sacct(self):
            if not self.session or not self.session.get("slurm"):
                return
            user = self.session["cfg"].username
            slurm = self.session["slurm"]

            def success(txt) -> None:
                if not self.is_details_polling_visible():
                    return
                self.meta_text.setPlainText(txt)
                append_event({"type": "sacct", "user": user})

            def failed(e) -> None:
                show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="JOBS")

            self._start_async(
                "sacct",
                lambda: slurm.sacct(user),
                success,
                on_error=failed,
            )
        def _open_detail_script(self, _link: str) -> None:
            path = str(getattr(self, "_detail_script_path", "")).strip()
            if path:
                self._activate_slurm_script(path)
                stdout, stderr = self._detail_scheduler_paths
                if stdout:
                    self.active_out = stdout
                    self.path_out.setText(stdout)
                if stderr:
                    self.active_err = stderr
                    self.path_err.setText(stderr)
        def _show_workdir(self, path: str) -> None:
            cfg = (self.session or {}).get("cfg")
            system = normalize_system_settings(getattr(cfg, "system_settings", None))
            user = getattr(cfg, "username", "")
            area = storage_area_for_path(
                path,
                {
                    "home": format_remote_path(system["home_dir"], user),
                    "scratch": format_remote_path(system["scratch_dir"], user),
                },
            )
            suffix = f" ({area})" if area else ""
            self.meta_job_workdir.setText(
                f"<b>{t('jobs_outputs.workdir')}:</b> {path}{suffix}"
            )
        def show_job_details(self):
            if not self.session or not self.session.get("slurm"):
                return
            jobid = (self.meta_job_id.text() or "").strip() or (self.cancel_id.text() or "").strip()
            if not jobid:
                QMessageBox.information(
                    self, t("common.info"), t("jobs_outputs.job_id_required")
                )
                return
            slurm = self.session["slurm"]

            def success(txt) -> None:
                self.meta_text.setPlainText(txt)
                detail = parse_scontrol(txt, jobid)
                self._detail_script_path = detail.script_path
                self._detail_scheduler_paths = (detail.stdout_path, detail.stderr_path)
                self._tracking.set_output_metadata(
                    stdout_path=detail.stdout_path, stderr_path=detail.stderr_path,
                    script_path=detail.script_path, workdir=detail.workdir,
                )
                if detail.workdir:
                    self._show_workdir(detail.workdir)
                if detail.stdout_path:
                    self.active_out = detail.stdout_path
                    self.path_out.setText(detail.stdout_path)
                if detail.stderr_path:
                    self.active_err = detail.stderr_path
                    self.path_err.setText(detail.stderr_path)
                if detail.script_path:
                    self.meta_job_script.setText(f"<b>{t('jobs_outputs.script_path')}:</b> <a href=\"script\">{detail.script_path}</a>")
                else:
                    self.meta_job_script.clear()
                append_event({"type": "scontrol_show_job", "jobid": jobid})

            def failed(e) -> None:
                show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="JOBS")

            self._start_async(
                "scontrol",
                lambda: slurm.scontrol_show_job(jobid),
                success,
                on_error=failed,
            )
        def refresh_lssrv(self):
            if (
                not self.session
                or not self.session.get("connected")
                or not self.session.get("slurm")
            ):
                return
            slurm = self.session["slurm"]

            def success(txt) -> None:
                if not self.is_details_polling_visible():
                    return
                if txt:
                    self.lssrv_text.setHtml(_ansi_to_html(_bounded_output_text(txt)))
                else:
                    self.lssrv_text.setPlainText(t("jobs_outputs.lssrv_empty"))
                append_event({"type": "lssrv", "status": "success"})

            def failed(e) -> None:
                append_event({"type": "lssrv", "status": "failed", "error": str(e)})
                self.lssrv_text.setPlainText(t("jobs_outputs.lssrv_failed"))
                show_exception(
                    self,
                    title=t("common.error"),
                    user_message=str(e),
                    exc=e,
                    area="JOBS",
                )

            if self._start_async(
                "lssrv",
                slurm.lssrv,
                success,
                on_error=failed,
            ):
                append_event({"type": "lssrv", "status": "attempt"})
        def focus_job(
            self,
            jobid: str,
            script_path: str = "",
            *,
            switch_to_outputs: bool = True,
            follow_mode: str = SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
        ):
            """Focus a submitted job in the jobs UI and optionally bind outputs from script."""
            if not jobid:
                return
            self.cancel_id.setText(jobid)
            self.meta_job_id.setText(jobid)
            self._tracking.select_job(jobid)
            self.refresh_jobs()
            self.refresh_sacct()
            if script_path:
                self._activate_slurm_script(
                    script_path,
                    switch_to_outputs=switch_to_outputs,
                    follow_mode=follow_mode,
                )
                if switch_to_outputs and follow_mode == SBATCH_FOLLOW_MODE_OUTPUTS_TAB:
                    self.section_tabs.setCurrentWidget(self.outputs_tab)
