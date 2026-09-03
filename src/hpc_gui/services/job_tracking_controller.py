"""Framework-neutral job polling and output-follow state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputMetadata:
    stdout_path: str = ""
    stderr_path: str = ""
    script_path: str = ""
    workdir: str = ""


class JobTrackingController:
    """Own state and polling decisions; UI adapters own timers and rendering."""

    def __init__(self) -> None:
        self.connected = False
        self.page_active = True
        self.minimized = False
        self.selected_job_id = ""
        self.output = OutputMetadata()

    def set_session(self, session) -> None:
        self.connected = bool(session and session.get("connected"))
        self.selected_job_id = ""
        self.output = OutputMetadata()

    def set_page_active(self, active: bool) -> None:
        self.page_active = bool(active)

    def set_minimized(self, minimized: bool) -> None:
        self.minimized = bool(minimized)

    def select_job(self, job_id: str) -> None:
        self.selected_job_id = str(job_id or "").strip()

    def set_output_metadata(self, **values: str) -> None:
        self.output = OutputMetadata(
            **{field: str(values.get(field, getattr(self.output, field)) or "") for field in OutputMetadata.__dataclass_fields__}
        )

    def should_poll_jobs(self, details_visible: bool, auto_refresh: bool) -> bool:
        return self.connected and self.page_active and not self.minimized and bool(details_visible and auto_refresh)

    def should_follow_output(self, outputs_visible: bool) -> bool:
        return self.connected and self.page_active and not self.minimized and bool(outputs_visible and (self.output.stdout_path or self.output.stderr_path))
