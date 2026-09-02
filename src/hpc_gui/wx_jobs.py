"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController


_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


@dataclass(frozen=True)
class DetachedOutput:
    id: str
    stdout_path: str = ""
    stderr_path: str = ""
    mode: str = "combined"
    cols: int = 80
    rows: int = 24


def clean_output(text: str, max_lines: int = 5000) -> str:
    lines = str(text or "").splitlines()[-max(1, int(max_lines)):]
    return _ANSI.sub("", "".join(f"{line}\n" for line in lines))


class WxJobsModel:
    def __init__(self, *, notify: Callable[[str], None] | None = None, provenance: JobProvenanceCapture | None = None) -> None:
        self.tracking = JobTrackingController()
        self.notify = notify
        self.provenance = provenance
        self.detached: list[DetachedOutput] = []
        self.failure = None
        self.tail_failures = 0

    def poll_allowed(self, details_visible: bool = True, auto_refresh: bool = True) -> bool:
        return self.tracking.should_poll_jobs(details_visible, auto_refresh)

    def set_output(self, stdout_path: str = "", stderr_path: str = "") -> None:
        self.tracking.set_output_metadata(stdout_path=stdout_path, stderr_path=stderr_path)

    def open_detached(self, stdout_path: str = "", stderr_path: str = "", mode: str = "combined") -> DetachedOutput:
        view = DetachedOutput(str(len(self.detached) + 1), stdout_path, stderr_path, mode)
        self.detached.append(view)
        return view

    def update_detached(self, view_id: str, text: str, max_lines: int = 5000) -> str:
        if not any(view.id == str(view_id) for view in self.detached):
            raise KeyError(view_id)
        return clean_output(text, max_lines)

    def resize_detached(self, view_id: str, cols: int, rows: int) -> DetachedOutput:
        for index, view in enumerate(self.detached):
            if view.id == str(view_id):
                resized = DetachedOutput(view.id, view.stdout_path, view.stderr_path, view.mode, max(1, int(cols)), max(1, int(rows)))
                self.detached[index] = resized
                return resized
        raise KeyError(view_id)

    def record_tail_failure(self) -> int:
        self.tail_failures += 1
        return self.tail_failures

    def record_tail_success(self) -> None:
        self.tail_failures = 0

    def cancel_job(self, cancel: Callable[[str], Any], job_id: str) -> Any:
        return cancel(str(job_id)) if str(job_id).strip() else None

    def explain_failure(self, job: Any):
        self.failure = explain_job_failure(job)
        return self.failure

    def submitted(self, job_id: str, script_text: str, **kwargs: Any) -> None:
        if self.provenance:
            self.provenance.submitted(job_id, script_text, **kwargs)
        if self.notify:
            self.notify(str(job_id))


__all__ = ["DetachedOutput", "WxJobsModel", "clean_output"]
