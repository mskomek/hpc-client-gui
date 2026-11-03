"""Selected-job Details, Accounting, and raw Slurm refresh workflows."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.jobs.job_rows import parse_job_row
from hpc_gui.services.parser_registry import parse as parse_with_registry
from hpc_gui.services.provider_contract import extract_contract
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.services.slurm_models import parse_scontrol


def normalize_raw_result(value, *, source_id: str, command: str, error=None) -> RawCommandResult:
    if isinstance(value, RawCommandResult):
        return value
    return RawCommandResult.from_response(
        source_id=source_id, command=command,
        stdout="" if error else str(value or ""),
        stderr=str(error) if error else "", exit_code=1 if error else -1,
    )


def detail_response_has_fields(text: str) -> bool:
    fields = (
        "JobId", "JobName", "JobState", "UserId", "Partition", "Elapsed", "RunTime",
        "NumNodes", "NumCPUs", "NodeList", "Reason", "ExitCode", "Command",
        "WorkDir", "StdOut", "StdErr",
    )
    import re
    pattern = r"\b(?:" + "|".join(fields) + r")\s*="
    return bool(re.search(pattern, str(text or ""), re.IGNORECASE))


@dataclass
class JobDetailsBindings:
    wx: Any
    state: dict[str, Any]
    state_lock: Any
    model: Any
    post: Callable
    refresh_metadata: Callable | None
    refresh_accounting_callback: Callable | None
    show_details_callback: Callable | None
    generation: Callable | None
    kwargs: dict[str, Any]
    host: Any
    show_raw_viewer: Callable
    presenter: Any
    refresh_outputs: Callable
    update_files_header: Callable
    navigate_files: Callable
    accounting_button: Any
    accounting_sizer: Any
    accounting_table: Any
    accounting_warning: Any
    details_sizer: Any
    details_warning: Any


class JobDetailsController:
    """Fetch and present details while binding each response to the selection."""

    def __init__(self, bindings: JobDetailsBindings) -> None:
        self.bindings = bindings

    def refresh_job_metadata(self) -> None:
        b = self.bindings
        if not callable(b.refresh_metadata):
            return
        job_id = b.state["selected_job"]
        if not job_id:
            return
        generation = b.model.selected_job_store.generation

        def worker():
            try:
                result = b.refresh_metadata(job_id)
                b.post(done, result, None, job_id, generation)
            except Exception as error:
                b.post(done, None, error, job_id, generation)

        def done(result, error, response_job_id, response_generation):
            state = b.state
            if (
                state["closed"] or state["selected_job"] != response_job_id
                or b.model.selected_job_store.generation != response_generation
            ):
                return
            if error or not isinstance(result, dict):
                return
            metadata = {key: str(value).strip() for key, value in result.items() if value not in (None, "")}
            if not metadata:
                return
            current = next((
                item for item in state.get("raw_items", ())
                if parse_job_row(item)["job_id"] == response_job_id
            ), {})
            merged = dict(current) if isinstance(current, dict) else {}
            merged.update(metadata)
            merged.setdefault("id", response_job_id)
            row = parse_job_row(merged)
            base_row = parse_job_row(current) if current else {}
            for key in ("name", "state", "partition", "elapsed", "nodes", "cpus", "reason"):
                if not row.get(key) and base_row.get(key):
                    row[key] = base_row[key]
            b.presenter.show_parsed_details(row, merged)
            b.presenter.update_summary_header()
            b.navigate_files()
            b.refresh_outputs(force=True)

        Thread(target=worker, daemon=True).start()

    def refresh_raw_job_details(self):
        b = self.bindings
        job_id = b.state["selected_job"]
        callback = b.show_details_callback
        if not job_id or not callback:
            return b.state.get("raw_details_result")
        generation = b.model.selected_job_store.generation
        try:
            try:
                result = callback(job_id)
            except TypeError:
                result = callback()
            raw = normalize_raw_result(result, source_id="scontrol", command=f"scontrol show job {job_id}")
            if self._stale(job_id, generation):
                return b.state.get("raw_details_result")
            b.state["raw_details_result"] = raw
            save = b.kwargs.get("save_job_raw_snapshot")
            if raw.ok and raw.stdout and callable(save):
                save(job_id, "raw_details", raw.stdout)
            return raw
        except Exception as error:
            raw = RawCommandResult.from_response(
                source_id="scontrol", command=f"scontrol show job {job_id}",
                stdout="", stderr=str(error), exit_code=1,
            )
            if self._stale(job_id, generation):
                return b.state.get("raw_details_result")
            b.state["raw_details_result"] = raw
            return raw

    def open_raw_job_details(self, _event=None) -> None:
        b = self.bindings
        result = b.state.get("raw_details_result") or RawCommandResult(
            source_id="scontrol", command=f"scontrol show job {b.state['selected_job']}",
            stdout="", stderr=t("jobs_outputs.raw_not_available"), exit_code=-1,
        )
        b.show_raw_viewer(
            b.host, result, title=t("raw_viewer.raw_job_details"),
            refresh_callback=self.refresh_raw_job_details,
        )

    def refresh_raw_accounting(self):
        b = self.bindings
        job_id = b.state["selected_job"]
        callback = b.refresh_accounting_callback
        if not job_id or not callback:
            return b.state.get("raw_accounting_result")
        generation = b.model.selected_job_store.generation
        try:
            result = callback(job_id)
            raw = normalize_raw_result(
                result, source_id="sacct",
                command=f"sacct -n -P -j {job_id} --format=JobIDRaw,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
            )
            if self._stale(job_id, generation):
                return b.state.get("raw_accounting_result")
            b.state["raw_accounting_result"] = raw
            save = b.kwargs.get("save_job_raw_snapshot")
            if raw.ok and raw.stdout and callable(save):
                save(job_id, "raw_accounting", raw.stdout)
            return raw
        except Exception as error:
            raw = RawCommandResult.from_response(
                source_id="sacct", command=f"sacct -n -P -j {job_id}",
                stdout="", stderr=str(error), exit_code=1,
            )
            if self._stale(job_id, generation):
                return b.state.get("raw_accounting_result")
            b.state["raw_accounting_result"] = raw
            return raw

    def open_raw_accounting(self, _event=None) -> None:
        b = self.bindings
        result = b.state.get("raw_accounting_result") or RawCommandResult(
            source_id="sacct", command=f"sacct -j {b.state['selected_job']}",
            stdout="", stderr=t("jobs_outputs.raw_not_available"), exit_code=-1,
        )
        b.show_raw_viewer(
            b.host, result, title=t("raw_viewer.raw_accounting"),
            refresh_callback=self.refresh_raw_accounting,
        )

    def refresh_accounting(self, _event=None) -> None:
        b = self.bindings
        callback = b.refresh_accounting_callback
        if not callback:
            return
        job_id = b.state["selected_job"] or b.model.tracking.selected_job_id
        if not job_id:
            return
        with b.state_lock:
            if b.state["closed"]:
                return
            b.state["sacct_request_id"] += 1
            request_id = b.state["sacct_request_id"]
            b.state["sacct_requests"] += 1
            b.state["sacct_in_flight"] = True
        generation = b.model.selected_job_store.generation
        b.accounting_button.Enable(False)

        def worker():
            try:
                result = callback(job_id)
                b.post(done, result, None, request_id)
            except Exception as error:
                b.post(done, "", error, request_id)

        def done(result, error, response_id):
            state = b.state
            with b.state_lock:
                state["sacct_requests"] = max(0, state["sacct_requests"] - 1)
                state["sacct_in_flight"] = state["sacct_requests"] > 0
            if state["closed"]:
                return
            if (
                b.model.selected_job_store.job_id != job_id
                or b.model.selected_job_store.generation != generation
                or response_id != state["sacct_request_id"]
            ):
                b.accounting_button.Enable(state["sacct_requests"] == 0 and bool(callback))
                return
            b.accounting_button.Enable(state["sacct_requests"] == 0 and bool(callback))
            raw = normalize_raw_result(
                result, source_id="sacct",
                command=f"sacct -j {job_id} --format=JobID,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
                error=error,
            )
            state["raw_accounting_result"] = raw
            state["accounting_parse_error"] = ""
            b.accounting_warning.Hide()
            raw_text = raw.stdout.strip()
            raw_error = raw.stderr.strip() if raw.has_error else ""
            if raw.has_error and not raw_error:
                raw_error = f"exit code {raw.exit_code}"
            if raw_error:
                b.accounting_table.DeleteAllItems()
                index = b.accounting_table.InsertItem(0, t("jobs_outputs.accounting_error"))
                b.accounting_table.SetItem(index, 1, raw_error)
            else:
                self._render_accounting(raw_text)
            b.accounting_sizer.Layout()

        Thread(target=worker, daemon=True).start()

    def _render_accounting(self, text: str) -> None:
        b = self.bindings
        table, state = b.accounting_table, b.state
        table.DeleteAllItems()
        if not text:
            table.InsertItem(0, t("jobs_outputs.accounting_empty"))
            return
        parsed_rows = None
        try:
            session = state.get("session") or {}
            profile = session.get("profile") or {}
            template = profile.get("provider_template") if isinstance(profile, dict) else None
            contract = extract_contract(template)
            if contract.accounting_parser:
                result = parse_with_registry(contract.accounting_parser, text, raw_source_id="sacct")
                if result.ok and hasattr(result.data, "rows"):
                    parsed_rows = list(result.data.rows)
                elif result.error:
                    state["accounting_parse_error"] = result.error.message
        except Exception:
            pass
        if parsed_rows is not None:
            if not parsed_rows:
                table.InsertItem(0, t("jobs_outputs.accounting_empty"))
            for row in parsed_rows:
                index = table.InsertItem(table.GetItemCount(), row.job_id)
                for column, value in enumerate(
                    (row.state, row.elapsed, row.max_rss, row.alloc_tres, row.exit_code), start=1
                ):
                    table.SetItem(index, column, value)
        else:
            valid_rows = 0
            for line in text.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("jobid"):
                    continue
                parts = [part.strip() for part in line.split("|")]
                if len(parts) < 2:
                    continue
                valid_rows += 1
                index = table.InsertItem(table.GetItemCount(), parts[0])
                for column, value in enumerate(parts[1:6], start=1):
                    table.SetItem(index, column, value)
            if valid_rows == 0:
                state["accounting_parse_error"] = "invalid accounting rows"
        if state["accounting_parse_error"]:
            b.accounting_warning.SetLabel(t("jobs_outputs.parse_error_accounting"))
            b.accounting_warning.Show()
        else:
            b.accounting_warning.Hide()

    def show_job_details(self, _event=None) -> None:
        b = self.bindings
        callback = b.show_details_callback
        if not callback:
            return
        job_id = b.state["selected_job"] or b.model.tracking.selected_job_id
        if not job_id:
            return
        with b.state_lock:
            if b.state["closed"]:
                return
            b.state["details_request_id"] += 1
            request_id = b.state["details_request_id"]
            b.state["details_requests"] += 1
            b.state["details_in_flight"] = True
        generation = b.model.selected_job_store.generation

        def worker():
            try:
                try:
                    result = callback(job_id)
                except TypeError:
                    result = callback()
                b.post(done, result, None, request_id)
            except Exception as error:
                b.post(done, "", error, request_id)

        def done(result, error, response_id):
            state = b.state
            with b.state_lock:
                state["details_requests"] = max(0, state["details_requests"] - 1)
                state["details_in_flight"] = state["details_requests"] > 0
            if state["closed"] or (
                b.model.selected_job_store.job_id != job_id
                or b.model.selected_job_store.generation != generation
                or response_id != state["details_request_id"]
            ):
                return
            raw = normalize_raw_result(
                result, source_id="scontrol", command=f"scontrol show job {job_id}", error=error,
            )
            state["raw_details_result"] = raw
            if raw.has_error:
                state["details_parse_error"] = raw.stderr or f"exit code {raw.exit_code}"
                b.details_warning.SetLabel(t("jobs_outputs.parse_error_details"))
                b.details_warning.Show()
                b.details_sizer.Layout()
                return
            text = raw.stdout.strip()
            if not text or not job_id:
                return
            state["details_parse_error"] = ""
            if not detail_response_has_fields(text):
                state["details_parse_error"] = "unrecognized job details"
                self._show_detail_error()
                return
            detail = self._parse_provider_details(text)
            if detail is None:
                try:
                    detail = parse_scontrol(text, job_id)
                except Exception as parse_error:
                    state["details_parse_error"] = str(parse_error)
                    self._show_detail_error()
                    return
            returned_id = str(getattr(detail, "job_id", "") or "").strip()
            if returned_id and returned_id != job_id:
                state["details_parse_error"] = "job details returned a different job ID"
                self._show_detail_error()
                return
            state["details_parse_error"] = ""
            updates = {}
            for context_key, detail_key in (
                ("name", "name"), ("state", "state"), ("partition", "partition"),
                ("elapsed", "elapsed"), ("nodes", "nodes"), ("cpus", "cpus"),
                ("reason", "reason"), ("workdir", "workdir"),
                ("stdout_path", "stdout_path"), ("stderr_path", "stderr_path"),
                ("script_path", "script_path"), ("nodelist", "nodelist"),
                ("exit_code", "exit_code"), ("failure_reason", "failure_reason"),
            ):
                value = str(getattr(detail, detail_key, "") or "").strip()
                if value:
                    updates[context_key] = value
                    b.presenter.set_field(detail_key, value)
            if updates:
                b.model.selected_job_store.update(**updates)
                context = b.model.selected_job_store.context
                b.model.set_output(context.stdout_path, context.stderr_path)
                b.update_files_header()
                b.navigate_files()
                b.refresh_outputs(force=True)
            if state["details_parse_error"]:
                self._show_detail_error()
            else:
                b.details_warning.Hide()
            b.details_sizer.Layout()

        Thread(target=worker, daemon=True).start()

    def _parse_provider_details(self, text: str):
        state = self.bindings.state
        try:
            session = state.get("session") or {}
            profile = session.get("profile") or {}
            template = profile.get("provider_template") if isinstance(profile, dict) else None
            contract = extract_contract(template)
            if not contract.job_details_parser:
                return None
            result = parse_with_registry(contract.job_details_parser, text, raw_source_id="scontrol")
            if result.ok and hasattr(result.data, "workdir"):
                return result.data
            if result.error:
                state["details_parse_error"] = result.error.message
        except Exception:
            pass
        return None

    def _show_detail_error(self) -> None:
        b = self.bindings
        b.details_warning.SetLabel(t("jobs_outputs.parse_error_details"))
        b.details_warning.Show()
        b.details_sizer.Layout()

    def _stale(self, job_id: str, generation: int) -> bool:
        b = self.bindings
        return (
            b.state["selected_job"] != job_id
            or b.model.selected_job_store.generation != generation
        )
