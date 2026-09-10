"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Lock, Thread
from types import SimpleNamespace
from typing import Any, Callable
from uuid import uuid4

from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController
from hpc_gui.services.selected_job_context import SelectedJobStore
from hpc_gui.services.slurm_models import parse_scontrol
from hpc_gui.services.output_channel_resolver import (
    OutputResolver, ResolvedOutputChannel, TrackedOutput,
)
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState, retain_last_lines
from hpc_gui.wx_host import make_host

from hpc_gui.services.parser_registry import parse as parse_with_registry
from hpc_gui.services.provider_contract import extract_contract


_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")

_JOB_TABLE_COLUMNS = ("job_id", "name", "state", "partition", "elapsed", "nodes", "cpus", "reason")

_COLUMN_LABEL_KEYS = {
    "job_id": "jobs.job_id",
    "name": "jobs.name",
    "state": "jobs.state",
    "partition": "jobs.partition",
    "elapsed": "jobs.elapsed",
    "nodes": "jobs.nodes",
    "cpus": "jobs.cpus",
    "reason": "jobs.reason",
}

JOBS_PAGE = 0
CLUSTER_PAGE = 1
DETAILS_PAGE = 2
FILES_PAGE = 3
OUTPUTS_PAGE = 4


def _format_size(n: int | str) -> str:
    try:
        n = int(n)
    except Exception:
        return ""
    if n <= 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.1f} {units[i]}" if i else f"{int(v)} {units[i]}"


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


def _output_at_bottom(ctrl) -> bool:
    try:
        import wx
        maximum = ctrl.GetScrollRange(wx.VERTICAL)
        return maximum <= 0 or ctrl.GetScrollPos(wx.VERTICAL) >= maximum - 1
    except (AttributeError, RuntimeError, ImportError):
        return True


class WxJobsModel:
    def __init__(self, *, notify: Callable[[str], None] | None = None, provenance: JobProvenanceCapture | None = None, completion_notify: Callable[[str, str], None] | None = None) -> None:
        self.tracking = JobTrackingController()
        self.selected_job_store = SelectedJobStore()
        self.notify = notify
        self.provenance = provenance
        self.detached: list[DetachedOutput] = []
        self.failure = None
        self.tail_failures = 0
        self.completion_notify = completion_notify
        self._job_states: dict[str, str] = {}
        self._active_job_ids: set[str] = set()
        self._monitor_initialized = False
        self._monitor_generation = 0

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

    def update_job_state(self, job_id: str, state: str, message: str = "") -> bool:
        """Publish one completion event per observed terminal state transition."""
        job_id, state = str(job_id).strip(), str(state).strip().upper()
        if not job_id:
            return False
        previous = self._job_states.get(job_id)
        self._job_states[job_id] = state
        if state not in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
            return False
        if previous == state or not self.completion_notify:
            return False
        if message:
            notification = message
        elif state == "COMPLETED":
            notification = t("login.job_completed").format(jobid=job_id)
        else:
            notification = t("login.job_failed").format(jobid=job_id, state=state)
        self.completion_notify(job_id, notification)
        return True

    def set_monitor_generation(self, generation: int) -> None:
        generation = int(generation)
        if generation == self._monitor_generation:
            return
        self._monitor_generation = generation
        self._active_job_ids.clear()
        self._monitor_initialized = False

    def poll_active_jobs(self, items, final_state=None, *, generation: int | None = None) -> bool:
        """Track squeue membership and query final states for disappeared jobs."""
        if generation is not None and int(generation) != self._monitor_generation:
            return False
        rows = tuple(items or ())
        current = {
            str(item.get("id", item.get("job_id", ""))).strip()
            for item in rows
            if isinstance(item, dict) and str(item.get("id", item.get("job_id", ""))).strip()
        }
        if not self._monitor_initialized:
            self._active_job_ids = current
            self._monitor_initialized = True
            for item in rows:
                if isinstance(item, dict):
                    self._job_states[str(item.get("id", item.get("job_id", "")))] = str(item.get("state", "")).strip().upper()
            return True
        for job_id in sorted(self._active_job_ids - current):
            state = str(final_state(job_id) if final_state else "").strip().upper()
            if state in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
                self.update_job_state(job_id, state)
            elif self.completion_notify:
                self.completion_notify(job_id, t("login.job_finished").format(jobid=job_id))
        for item in rows:
            if isinstance(item, dict):
                self.update_job_state(item.get("id", item.get("job_id", "")), item.get("state", ""), "")
        self._active_job_ids = current
        return True


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, read_path=None, stat_path=None, follower=None, interval_ms: int = 1000, lifecycle=None, on_closed=None) -> int:
    """Show a live detached follower; late callbacks are ignored after close."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next((item for item in model.detached if item.id == str(view_id)), None)
    frame = wx.Frame(parent, title=f"{t('jobs.open_output')} {view.id if view else view_id}", size=(800, 500))
    root = wx.BoxSizer(wx.VERTICAL)
    if follower is not None:
        root.Add(wx.StaticText(frame, label=follower.state.path), 0, wx.EXPAND | wx.ALL, 6)
    output = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    root.Add(output, 1, wx.EXPAND | wx.ALL, 6)
    controls = wx.BoxSizer(wx.HORIZONTAL)
    pause = wx.Button(frame, label=t("jobs.pause_output"))
    auto_scroll = wx.CheckBox(frame, label=t("files.auto_scroll"))
    auto_scroll.SetValue(True)
    controls.Add(pause, 0, wx.RIGHT, 6)
    controls.Add(auto_scroll, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    frame.SetSizer(root)
    frame._wx_output_controls = {"output": output, "pause": pause, "auto_scroll": auto_scroll, "follower": follower}
    timer = wx.Timer(frame)
    state = {"closed": False, "in_flight": False, "at_bottom": True}
    state_lock = Lock()

    def toggle_pause(_event=None):
        paused = follower is not None and follower.state.paused
        if follower is not None:
            follower.state.paused = not paused
        pause.SetLabel(
            t("jobs.resume_output") if follower is not None and follower.state.paused
            else t("jobs.pause_output")
        )

    def refresh(_event=None):
        if follower is None and not read_output:
            return
        state["at_bottom"] = _output_at_bottom(output)
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True
            if follower is not None:
                follower.state.paused = pause.GetLabel() == t("jobs.resume_output")
                follower.state.auto_scroll = auto_scroll.GetValue()

        def fetch() -> None:
            try:
                if follower is not None:
                    if not callable(read_path):
                        raise RuntimeError(t("jobs_outputs.remote_reader_unavailable"))
                    _chunk, text, _waiting = follower.poll(read_path, stat_path)
                else:
                    text = model.update_detached(view.id, read_output())
                wx.CallAfter(apply, text, None)
            except Exception as error:
                wx.CallAfter(apply, "", error)

        def apply(text, error) -> None:
            with state_lock:
                state["in_flight"] = False
                if state["closed"]:
                    return
            if error:
                output.SetValue(str(error))
            else:
                output.SetValue(text)
                if auto_scroll.GetValue() and state["at_bottom"]:
                    output.ShowPosition(output.GetLastPosition())

        Thread(target=fetch, daemon=True).start()

    pause.Bind(wx.EVT_BUTTON, toggle_pause)

    def resized(_event):
        if view is not None:
            model.resize_detached(view.id, max(1, output.GetClientSize().width // 8), max(1, output.GetClientSize().height // 16))
        _event.Skip()

    def closed(_event=None):
        with state_lock:
            if state["closed"]:
                return
            state["closed"] = True
        if follower is not None:
            follower.close()
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        if callable(on_closed):
            on_closed()
        frame.Destroy()

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('jobs.open_output')} {view.id if view else view_id}")

    frame._wx_output_refresh = refresh
    frame.Bind(wx.EVT_TIMER, refresh, timer)
    frame.Bind(wx.EVT_SIZE, resized)
    frame.Bind(wx.EVT_CLOSE, closed)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(closed)
    if follower is not None or read_output:
        timer.Start(max(100, int(interval_ms)))
        refresh()
    frame.Show()
    return wx.ID_OK


def _parse_job_row(item: dict[str, Any] | str) -> dict[str, str]:
    """Extract a normalised row dict from a raw job item (dict or string)."""
    if isinstance(item, dict):
        return {
            "job_id": str(item.get("id", item.get("job_id", ""))).strip(),
            "name": str(item.get("name", "")).strip(),
            "state": str(item.get("state", "")).strip(),
            "partition": str(item.get("partition", "")).strip(),
            "elapsed": str(item.get("elapsed", "")).strip(),
            "nodes": str(item.get("nodes", "")).strip(),
            "cpus": str(item.get("cpus", "")).strip(),
            "reason": str(item.get("reason", item.get("failure_reason", ""))).strip(),
        }
    s = str(item).strip()
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
    else:
        parts = s.split(None, 8)
    return {
        "job_id": parts[0] if parts else s,
        "name": parts[2] if len(parts) > 2 else "",
        "state": parts[4] if len(parts) > 4 else "",
        "partition": parts[1] if len(parts) > 1 else "",
        "elapsed": parts[5] if len(parts) > 5 else "",
        "nodes": parts[6] if len(parts) > 6 else "",
        "cpus": parts[7] if len(parts) > 7 else "",
        "reason": parts[8] if len(parts) > 8 else "",
    }


def _matches_filter(row: dict[str, str], query: str) -> bool:
    """Case-insensitive match across job_id, name, and state."""
    if not query:
        return True
    q = query.lower()
    for field in ("job_id", "name", "state"):
        if q in row.get(field, "").lower():
            return True
    return False


def _parse_cluster_server_rows(text: str) -> list[tuple[str, str, str, str]]:
    """Parse the allowlisted lssrv table shape for the Jobs page."""
    rows: list[tuple[str, str, str, str]] = []
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return rows
    first = lines[0].replace("|", " ").split()
    has_header = bool(first and first[0].lower() in {"server", "servers", "node", "hostname"})
    if not has_header:
        return rows
    for line in lines[1:]:
        fields = [part.strip() for part in line.split("|")] if "|" in line else line.split()
        if len(fields) < (2 if has_header else 3):
            continue
        if fields[0].lower() in {"server", "servers", "node", "hostname"}:
            continue
        rows.append(tuple((fields + [""] * 4)[:4]))
    return rows


def _detail_response_has_fields(text: str) -> bool:
    return bool(re.search(r"(?:NodeList|Reason|ExitCode|Command|WorkDir|StdOut|StdErr)=", str(text or "")))


def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, cancel, lifecycle, final_state, generation, embedded, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, list_job_files=None, output_channel_defs=None, **kwargs):
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    from hpc_gui.services.raw_command_result import RawCommandResult
    from hpc_gui.wx_raw_viewer import show_raw_viewer

    def _raw_result(value, *, source_id: str, command: str, error=None):
        if isinstance(value, RawCommandResult):
            return value
        return RawCommandResult.from_response(
            source_id=source_id,
            command=command,
            stdout="" if error else str(value or ""),
            stderr=str(error) if error else "",
            exit_code=1 if error else 0,
        )
    # Alias tolerance for caller naming
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct") or kwargs.get("sacct_callback") or kwargs.get("refresh_accounting")
    if show_job_details is None:
        show_job_details = kwargs.get("show_details") or kwargs.get("scontrol") or kwargs.get("scontrol_show_job") or kwargs.get("show_details_callback")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("lssrv") or kwargs.get("lssrv_refresh") or kwargs.get("lssrv_callback") or kwargs.get("refresh_lssrv_callback")
    if list_job_files is None:
        list_job_files = kwargs.get("list_job_files") or kwargs.get("job_files") or kwargs.get("files_callback")
    open_main_files = kwargs.get("open_main_files")
    has_status_capability = kwargs.get("has_status_capability")
    if refresh_sacct is None and "refresh_sacct" in kwargs:
        refresh_sacct = kwargs["refresh_sacct"]
    if show_job_details is None and "show_job_details" in kwargs:
        show_job_details = kwargs["show_job_details"]
    if refresh_lssrv is None and "refresh_lssrv" in kwargs:
        refresh_lssrv = kwargs["refresh_lssrv"]
    if list_job_files is None and "list_job_files" in kwargs:
        list_job_files = kwargs["list_job_files"]
    model = model or WxJobsModel()
    if lifecycle is not None and model.completion_notify is None:
        model.completion_notify = lambda job_id, message: lifecycle.notify_job(message, job_id=job_id)
    host, finish = make_host(parent, title=t("jobs.title"), size=(1000, 700), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)

    # --- Sub-tab notebook: Jobs | Cluster | Details | Files | Outputs ------
    notebook = wx.Notebook(panel)
    jobs_page = wx.Panel(notebook)
    cluster_page = wx.Panel(notebook)
    details_page = wx.Panel(notebook)
    files_page = wx.Panel(notebook)
    outputs_page = wx.Panel(notebook)
    notebook.AddPage(jobs_page, t("jobs.title"))
    notebook.AddPage(cluster_page, t("jobs.cluster"))
    notebook.AddPage(details_page, t("jobs.details"))
    notebook.AddPage(files_page, t("jobs_outputs.files_title"))
    notebook.AddPage(outputs_page, t("jobs_outputs.outputs_title"))

    # ======================================================================
    # JOBS PAGE — table, filter, auto-refresh, cancel
    # ======================================================================
    jobs_page_sizer = wx.BoxSizer(wx.VERTICAL)

    # -- Toolbar row --------------------------------------------------------
    jobs_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    btn_refresh = wx.Button(jobs_page, label=t("jobs.refresh"))
    lbl_filter = wx.StaticText(jobs_page, label=f"{t('common.filter')}:")
    filter_field = wx.TextCtrl(jobs_page, style=wx.TE_PROCESS_ENTER)
    try:
        filter_field.SetHint(t("jobs.filter_hint"))
    except Exception:
        pass
    cb_auto_refresh = wx.CheckBox(jobs_page, label=t("jobs.auto_refresh"))
    cb_auto_refresh.SetValue(True)
    jobs_toolbar.Add(btn_refresh, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    jobs_toolbar.Add(lbl_filter, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    jobs_toolbar.Add(filter_field, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    jobs_toolbar.Add(cb_auto_refresh, 0, wx.ALIGN_CENTER_VERTICAL)

    # -- Jobs table ---------------------------------------------------------
    jobs = wx.ListCtrl(jobs_page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
    for col_idx, col_key in enumerate(_JOB_TABLE_COLUMNS):
        label = t(_COLUMN_LABEL_KEYS.get(col_key, col_key))
        jobs.InsertColumn(col_idx, label)
    jobs.SetColumnWidth(0, 100)
    jobs.SetColumnWidth(1, 140)
    jobs.SetColumnWidth(2, 90)
    jobs.SetColumnWidth(3, 90)
    jobs.SetColumnWidth(4, 90)
    jobs.SetColumnWidth(5, 60)
    jobs.SetColumnWidth(6, 60)
    jobs.SetColumnWidth(7, 120)

    # -- Cancel button row --------------------------------------------------
    cancel_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_cancel = wx.Button(jobs_page, label=t("jobs.cancel"))
    btn_cancel.Enable(False)
    cancel_row.AddStretchSpacer(1)
    cancel_row.Add(btn_cancel, 0, wx.ALIGN_CENTER_VERTICAL)

    jobs_page_sizer.Add(jobs_toolbar, 0, wx.EXPAND | wx.ALL, 4)
    jobs_page_sizer.Add(jobs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    jobs_empty_label = wx.StaticText(jobs_page, label=t("jobs_outputs.no_active_jobs"))
    jobs_empty_label.Hide()
    jobs_page_sizer.Add(jobs_empty_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)

    jobs_page_sizer.Add(cancel_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    jobs_page.SetSizer(jobs_page_sizer)

    # ======================================================================
    # CLUSTER PAGE — provider/session-scoped status
    # ======================================================================
    cluster_page_sizer = wx.BoxSizer(wx.VERTICAL)
    cluster_heading = wx.StaticText(cluster_page, label=t("jobs_outputs.cluster_status"))
    cluster_heading.SetFont(wx.Font(wx.FontInfo(11).Bold()))
    cluster_status_text = wx.StaticText(cluster_page, label="")
    cluster_status_text.Wrap(900)
    cluster_servers_box = wx.StaticBox(cluster_page, label=t("jobs.cluster_servers"))
    cluster_servers_sizer = wx.StaticBoxSizer(cluster_servers_box, wx.VERTICAL)
    cluster_servers_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    btn_refresh_lssrv = wx.Button(cluster_servers_box, label=t("jobs.refresh"))
    btn_raw_server_status = wx.Button(cluster_servers_box, label=t("raw_viewer.raw_server_status"))
    cluster_servers_toolbar.Add(btn_refresh_lssrv, 0, wx.RIGHT, 6)
    cluster_servers_toolbar.Add(btn_raw_server_status, 0)
    cluster_servers_text = wx.StaticText(cluster_servers_box, label="")
    cluster_servers_table = wx.ListCtrl(
        cluster_servers_box,
        style=wx.LC_REPORT | wx.LC_HRULES,
    )
    for index, key in enumerate(("server", "state", "cpus", "memory")):
        cluster_servers_table.InsertColumn(index, t(f"jobs.{key}"))
    for index, width in enumerate((150, 120, 80, 100)):
        cluster_servers_table.SetColumnWidth(index, width)
    cluster_servers_toolbar.AddStretchSpacer(1)
    cluster_servers_sizer.Add(cluster_servers_toolbar, 0, wx.EXPAND | wx.ALL, 4)
    cluster_servers_sizer.Add(cluster_servers_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    cluster_servers_sizer.Add(cluster_servers_table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    cluster_page_sizer.Add(cluster_heading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    cluster_page_sizer.Add(cluster_status_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    cluster_page_sizer.Add(cluster_servers_sizer, 1, wx.EXPAND | wx.ALL, 8)
    cluster_page.SetSizer(cluster_page_sizer)

    def _toggle_cluster_servers(_event=None):
        return None

    # ======================================================================
    # DETAILS PAGE — compact summary, raw, accounting, cluster servers, advanced
    # ======================================================================
    details_sizer = wx.BoxSizer(wx.VERTICAL)

    # -- No-selection state --------------------------------------------------
    no_selection_panel = wx.Panel(details_page)
    no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection_label = wx.StaticText(no_selection_panel, label=t("jobs.no_job_selected"))
    no_selection_hint = wx.StaticText(no_selection_panel, label=t("jobs.no_job_selected_hint"))
    btn_go_to_jobs = wx.Button(no_selection_panel, label=t("jobs.go_to_jobs"))
    no_selection_sizer.AddStretchSpacer(1)
    no_selection_sizer.Add(no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    no_selection_sizer.Add(no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    no_selection_sizer.Add(btn_go_to_jobs, 0, wx.ALIGN_CENTER)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection_panel.SetSizer(no_selection_sizer)

    # -- Selected-job content panel -----------------------------------------
    details_content_panel = wx.Panel(details_page)
    details_content_sizer = wx.BoxSizer(wx.VERTICAL)

    # -- Job summary header -------------------------------------------------
    details_summary_label = wx.StaticText(details_content_panel, label=f"{t('jobs.details_header')} —")
    details_summary_label.SetFont(wx.Font(wx.FontInfo(11).Bold()))
    details_content_sizer.Add(details_summary_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    # -- Primary detail fields ----------------------------------------------
    detail_keys = (
        ("job_id", "jobs.job_id"), ("state", "jobs.state"),
        ("name", "jobs.name"), ("partition", "jobs.partition"),
        ("elapsed", "jobs.elapsed"), ("resources", "jobs.resources"),
        ("workdir", "jobs.workdir"), ("stdout_path", "jobs.stdout"),
        ("stderr_path", "jobs.stderr"),
    )
    detail_values: dict[str, wx.TextCtrl] = {}
    detail_labels: dict[str, wx.StaticText] = {}
    short_keys = detail_keys[:6]
    short_grid = wx.FlexGridSizer(0, 4, 6, 10)
    short_grid.AddGrowableCol(1, 1)
    short_grid.AddGrowableCol(3, 1)
    for index, (field_key, label_key) in enumerate(short_keys):
        lbl = wx.StaticText(details_content_panel, label=t(label_key))
        lbl.SetMinSize(wx.Size(78, -1))
        val = wx.TextCtrl(details_content_panel, style=wx.TE_READONLY | wx.HSCROLL)
        val.SetValue("—")
        detail_labels[field_key] = lbl
        detail_values[field_key] = val
        short_grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        short_grid.Add(val, 1, wx.EXPAND)
    details_content_sizer.Add(short_grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    for field_key, label_key in detail_keys[6:]:
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(details_content_panel, label=t(label_key))
        lbl.SetMinSize(wx.Size(78, -1))
        detail_labels[field_key] = lbl
        val = wx.TextCtrl(details_content_panel, style=wx.TE_READONLY | wx.HSCROLL)
        val.SetValue("—")
        detail_values[field_key] = val
        row_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row_sizer.Add(val, 1, wx.EXPAND)
        details_content_sizer.Add(row_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    details_warning_label = wx.StaticText(details_content_panel, label="")
    details_warning_label.Wrap(900)
    details_warning_label.Hide()
    details_content_sizer.Add(details_warning_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    # -- Separator ----------------------------------------------------------
    details_content_sizer.Add(wx.StaticLine(details_content_panel), 0, wx.EXPAND | wx.ALL, 8)

    # -- Raw Job Details button ---------------------------------------------
    btn_raw_job_details = wx.Button(details_content_panel, label=t("raw_viewer.raw_job_details"))
    details_content_sizer.Add(btn_raw_job_details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- Accounting collapsible section -------------------------------------
    accounting_box = wx.StaticBox(details_content_panel, label=f"▸ {t('jobs_outputs.accounting_details')}")
    accounting_sizer = wx.StaticBoxSizer(accounting_box, wx.VERTICAL)
    btn_sacct = wx.Button(accounting_box, label=t("jobs_outputs.refresh_sacct"))
    accounting_table = wx.ListCtrl(accounting_box, style=wx.LC_REPORT | wx.LC_HRULES)
    accounting_column_keys = ("job_id", "state", "elapsed", "max_rss", "alloc_tres", "exit_code")
    accounting_column_labels = {
        "job_id": "jobs.job_id", "state": "jobs.state", "elapsed": "jobs.elapsed",
        "max_rss": "jobs.max_rss", "alloc_tres": "jobs.alloc_tres", "exit_code": "jobs.exit_code",
    }
    for index, key in enumerate(accounting_column_keys):
        accounting_table.InsertColumn(index, t(accounting_column_labels[key]))
    accounting_table.SetColumnWidth(0, 80)
    accounting_table.SetColumnWidth(1, 90)
    accounting_table.SetColumnWidth(2, 90)
    accounting_table.SetColumnWidth(3, 80)
    accounting_table.SetColumnWidth(4, 120)
    accounting_table.SetColumnWidth(5, 80)
    btn_toggle_raw_acct = wx.Button(accounting_box, label=t("raw_viewer.raw_accounting"))
    accounting_row = wx.BoxSizer(wx.HORIZONTAL)
    accounting_row.Add(btn_sacct, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.Add(btn_toggle_raw_acct, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.AddStretchSpacer(1)
    accounting_warning_label = wx.StaticText(accounting_box, label="")
    accounting_warning_label.Wrap(900)
    accounting_warning_label.Hide()
    accounting_sizer.Add(accounting_row, 0, wx.EXPAND | wx.ALL, 4)
    accounting_sizer.Add(accounting_warning_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    accounting_sizer.Add(accounting_table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    accounting_sizer.SetMinSize(wx.Size(-1, 90))
    details_content_sizer.Add(accounting_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    _accounting_collapsed = {"collapsed": True}
    accounting_sizer.ShowItems(False)

    def _toggle_accounting(_event=None):
        _accounting_collapsed["collapsed"] = not _accounting_collapsed["collapsed"]
        is_collapsed = _accounting_collapsed["collapsed"]
        state["accounting_collapsed"] = is_collapsed
        accounting_sizer.ShowItems(not is_collapsed)
        if is_collapsed:
            accounting_box.SetLabel(accounting_box.GetLabel().replace("▾", "▸"))
        else:
            accounting_box.SetLabel(accounting_box.GetLabel().replace("▸", "▾"))
        details_content_sizer.Layout()

    accounting_box.Bind(wx.EVT_LEFT_DOWN, _toggle_accounting)

    # -- Advanced collapsible section ---------------------------------------
    advanced_box = wx.StaticBox(details_content_panel, label=f"▸ {t('jobs.advanced')}")
    advanced_sizer = wx.StaticBoxSizer(advanced_box, wx.VERTICAL)
    advanced_keys = (
        ("reason", "jobs.reason"), ("script_path", "jobs.script"),
        ("nodelist", "jobs.nodelist"), ("exit_code", "jobs.exit_code"),
        ("nodes", "jobs.nodes"), ("cpus", "jobs.cpus"),
    )
    for field_key, label_key in advanced_keys:
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(advanced_box, label=t(label_key))
        lbl.SetMinSize(wx.Size(90, -1))
        detail_labels[field_key] = lbl
        val = wx.TextCtrl(advanced_box, style=wx.TE_READONLY | wx.HSCROLL)
        val.SetValue("—")
        detail_values[field_key] = val
        row_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row_sizer.Add(val, 1, wx.EXPAND)
        advanced_sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 4)
    advanced_sizer.ShowItems(False)
    details_content_sizer.Add(advanced_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    _advanced_collapsed = {"collapsed": True}

    def _toggle_advanced(_event=None):
        _advanced_collapsed["collapsed"] = not _advanced_collapsed["collapsed"]
        is_collapsed = _advanced_collapsed["collapsed"]
        state["advanced_collapsed"] = is_collapsed
        advanced_sizer.ShowItems(not is_collapsed)
        if is_collapsed:
            advanced_box.SetLabel(advanced_box.GetLabel().replace("▾", "▸"))
        else:
            advanced_box.SetLabel(advanced_box.GetLabel().replace("▸", "▾"))
        details_content_sizer.Layout()

    advanced_box.Bind(wx.EVT_LEFT_DOWN, _toggle_advanced)

    # -- Assemble details page with no-selection / content toggle ------------
    details_content_panel.SetSizer(details_content_sizer)
    details_content_panel.Hide()

    details_sizer.Add(no_selection_panel, 1, wx.EXPAND)
    details_sizer.Add(details_content_panel, 1, wx.EXPAND)
    details_page.SetSizer(details_sizer)

    # -- Go to Jobs button handler ------------------------------------------
    def _select_inner_page(page):
        for index in range(notebook.GetPageCount()):
            if notebook.GetPage(index) is page:
                notebook.SetSelection(index)
                return

    def _go_to_jobs(_event=None):
        _select_inner_page(jobs_page)

    btn_go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)

    # ======================================================================
    # FILES SUB-TAB — shared remote browser
    # ======================================================================
    from hpc_gui.wx_remote_files_view import build_remote_files_panel
    from hpc_gui.wx_remote_files import WxRemoteDirectoryModel

    files_model = WxRemoteDirectoryModel("/")
    files_sizer = wx.BoxSizer(wx.VERTICAL)

    files_no_selection_panel = wx.Panel(files_page)
    files_no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    files_no_selection_label = wx.StaticText(files_no_selection_panel, label=t("jobs_outputs.no_selected_job"))
    files_no_selection_hint = wx.StaticText(files_no_selection_panel, label=t("jobs_outputs.no_selected_job_files_hint"))
    files_go_to_jobs = wx.Button(files_no_selection_panel, label=t("jobs.go_to_jobs"))
    files_no_selection_sizer.AddStretchSpacer(1)
    files_no_selection_sizer.Add(files_no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    files_no_selection_sizer.Add(files_no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    files_no_selection_sizer.Add(files_go_to_jobs, 0, wx.ALIGN_CENTER)
    files_no_selection_sizer.AddStretchSpacer(1)
    files_no_selection_panel.SetSizer(files_no_selection_sizer)
    files_sizer.Add(files_no_selection_panel, 1, wx.EXPAND)

    files_header = wx.Panel(files_page)
    files_header_sizer = wx.BoxSizer(wx.VERTICAL)
    files_job_header = wx.StaticText(files_header, label="")
    files_workdir_label = wx.StaticText(files_header, label="")
    files_header_sizer.Add(files_job_header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
    files_header_sizer.Add(files_workdir_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    files_open_main_button = None
    if callable(open_main_files):
        files_open_main_button = wx.Button(files_header, label=t("jobs_outputs.open_main_files"))
        files_header_sizer.Add(files_open_main_button, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    files_header.SetSizer(files_header_sizer)
    files_header.Hide()
    files_sizer.Add(files_header, 0, wx.EXPAND)

    _nav_store = None
    try:
        from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
        _session = None
        if kwargs.get("session_state") and isinstance(kwargs["session_state"], dict):
            _session = kwargs["session_state"].get("session") or {}
        if not _session:
            _session = {}
        _profile = _session.get("profile") or {}
        _profile_id = str(_profile.get("id", _profile.get("profile_id", "")))
        if _profile_id:
            _nav_store = navigation_store_for_profile(_profile_id)
    except Exception:
        pass

    _remote_cbs = kwargs.get("remote_files_callbacks") or {}
    _remote_reader = kwargs.get("read_remote_path") or _remote_cbs.get("read_text")
    _remote_statter = kwargs.get("stat_remote_path")

    files_browser = build_remote_files_panel(
        files_page,
        model=files_model,
        loader=_remote_cbs.get("loader"),
        operation=_remote_cbs.get("operation"),
        read_text=_remote_cbs.get("read_text"),
        open_editor=_remote_cbs.get("open_editor"),
        open_editor_new_window=_remote_cbs.get("open_editor_new_window"),
        run_shell=_remote_cbs.get("run_shell"),
        chmod=_remote_cbs.get("chmod"),
        submit_slurm=kwargs.get("submit_slurm") or _remote_cbs.get("submit_slurm"),
        operation_supported=_remote_cbs.get("operation_supported"),
        chmod_supported=_remote_cbs.get("chmod_supported"),
        submit_slurm_supported=_remote_cbs.get("submit_slurm_supported"),
        navigation_store=_remote_cbs.get("navigation_store") or _nav_store,
        provider_filters=kwargs.get("provider_filters") or _remote_cbs.get("provider_filters"),
        plugin_filters=_remote_cbs.get("plugin_filters"),
    )

    def _on_follow_file(remote_path, mode="new_tab", follower_id=None):
        ctx = model.selected_job_store.context
        if not ctx.job_id:
            return
        remote_path = str(remote_path)
        def _new_follower(tracking_id):
            follower = OutputFollower(OutputFollowerState(
                tracking_id=tracking_id, channel_id=None, job_id=ctx.job_id,
                generation=ctx.generation, label=PurePosixPath(remote_path).name or remote_path,
                path=remote_path, origin="manual", roles=("manual",),
            ))
            state.setdefault("followers", {})[tracking_id] = follower
            return follower
        if mode == "existing" and follower_id:
            tracked_outputs = state.get("tracked_outputs", [])
            old = next((item for item in tracked_outputs if item.tracking_id == follower_id), None)
            if old is None:
                return
            tracked_outputs[tracked_outputs.index(old)] = TrackedOutput(
                tracking_id=follower_id, channel_id=None,
                label=PurePosixPath(remote_path).name or remote_path,
                path=remote_path, origin="manual", job_id=ctx.job_id,
            )
            follower = state.setdefault("followers", {}).get(follower_id) or _new_follower(follower_id)
            follower.assign(channel_id=None, job_id=ctx.job_id, generation=ctx.generation,
                            label=PurePosixPath(remote_path).name or remote_path,
                            path=remote_path, origin="manual", roles=("manual",))
            pathCtrl = output_channel_paths.get(follower_id)
            if pathCtrl:
                pathCtrl.SetValue(remote_path)
            textCtrl = output_channels.get(follower_id)
            if textCtrl:
                textCtrl.SetValue("")
            refresh_outputs_tab(force=True)
            _select_inner_page(outputs_page)
            return
        tracking_id = f"follower-{uuid4().hex}"
        tracked = TrackedOutput(
            tracking_id=tracking_id, channel_id=None,
            label=PurePosixPath(remote_path).name or remote_path,
            path=remote_path, origin="manual", job_id=ctx.job_id,
        )
        state.setdefault("tracked_outputs", []).append(tracked)
        follower = _new_follower(tracking_id)
        if mode == "new_window":
            show_job_output(host, model, tracking_id, follower=follower,
                            read_path=_remote_reader, stat_path=_remote_statter,
                            lifecycle=lifecycle,
                            on_closed=lambda fid=tracking_id: _remove_manual_follower(fid))
        else:
            refresh_outputs_tab(force=True)
            _select_inner_page(outputs_page)

    def _remove_manual_follower(tracking_id):
        state["tracked_outputs"][:] = [
            item for item in state.get("tracked_outputs", ()) if item.tracking_id != tracking_id
        ]
        state.get("followers", {}).pop(tracking_id, None)
        refresh_outputs_tab(force=True)

    files_browser._follow_callback = _on_follow_file
    files_sizer.Add(files_browser, 1, wx.EXPAND)
    files_browser.Hide()
    files_page.SetSizer(files_sizer)

    def _show_files_selected_state(show: bool):
        if show:
            files_no_selection_panel.Hide()
            files_header.Show()
            files_browser.Show()
        else:
            files_header.Hide()
            files_browser.Hide()
            files_no_selection_panel.Show()
        files_sizer.Layout()

    def _open_in_main_files(_event=None):
        ctx = model.selected_job_store.context
        if ctx.job_id and callable(open_main_files):
            open_main_files(ctx.workdir or "/")

    def _reset_files_browser():
        reset = getattr(files_browser, "_wx_remote_reset", None)
        if callable(reset):
            reset()
        else:
            try:
                files_model.invalidate()
                files_browser._wx_remote_controls["listing"].DeleteAllItems()
            except Exception:
                pass

    files_go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)
    if files_open_main_button is not None:
        files_open_main_button.Bind(wx.EVT_BUTTON, _open_in_main_files)

    # ======================================================================
    # OUTPUTS SUB-TAB — dynamic 0..N output channels
    # ======================================================================
    outputs_sizer = wx.BoxSizer(wx.VERTICAL)
    outputs_no_selection_panel = wx.Panel(outputs_page)
    outputs_no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    outputs_no_selection_label = wx.StaticText(outputs_no_selection_panel, label=t("jobs_outputs.no_selected_job"))
    outputs_no_selection_hint = wx.StaticText(outputs_no_selection_panel, label=t("jobs_outputs.no_selected_job_outputs_hint"))
    outputs_go_to_jobs = wx.Button(outputs_no_selection_panel, label=t("jobs.go_to_jobs"))
    outputs_no_selection_sizer.AddStretchSpacer(1)
    outputs_no_selection_sizer.Add(outputs_no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    outputs_no_selection_sizer.Add(outputs_no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    outputs_no_selection_sizer.Add(outputs_go_to_jobs, 0, wx.ALIGN_CENTER)
    outputs_no_selection_sizer.AddStretchSpacer(1)
    outputs_no_selection_panel.SetSizer(outputs_no_selection_sizer)
    outputs_sizer.Add(outputs_no_selection_panel, 1, wx.EXPAND)

    outputs_toolbar_panel = wx.Panel(outputs_page)
    outputs_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    outputs_refresh_btn = wx.Button(outputs_toolbar_panel, label=t("jobs_outputs.refresh_all"))
    outputs_follow = wx.CheckBox(outputs_toolbar_panel, label=t("jobs_outputs.auto_scroll_all"))
    outputs_follow.SetValue(True)
    outputs_pause_btn = wx.Button(outputs_toolbar_panel, label=t("jobs_outputs.pause_all"))
    outputs_toolbar.Add(outputs_refresh_btn, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_pause_btn, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_follow, 0, wx.ALIGN_CENTER_VERTICAL)
    outputs_toolbar.AddStretchSpacer(1)
    outputs_toolbar_panel.SetSizer(outputs_toolbar)
    outputs_sizer.Add(outputs_toolbar_panel, 0, wx.EXPAND | wx.ALL, 4)

    search_panel = wx.Panel(outputs_page)
    search_row = wx.BoxSizer(wx.HORIZONTAL)
    search_label = wx.StaticText(search_panel, label=f"{t('jobs_outputs.search')}:")
    search_field = wx.TextCtrl(search_panel, style=wx.TE_PROCESS_ENTER)
    try:
        search_field.SetHint(t("jobs_outputs.search_hint"))
    except Exception:
        pass
    btn_find_next = wx.Button(search_panel, label=t("jobs_outputs.find_next"))
    btn_jump_latest = wx.Button(search_panel, label=t("jobs_outputs.jump_to_latest"))
    btn_open_window = wx.Button(search_panel, label=t("jobs_outputs.open_in_window"))
    btn_show_files = wx.Button(search_panel, label=t("jobs_outputs.show_in_files"))
    search_row.Add(search_label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    search_row.Add(search_field, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    search_row.Add(btn_find_next, 0, wx.RIGHT, 4)
    search_row.Add(btn_jump_latest, 0, wx.RIGHT, 4)
    search_row.Add(btn_open_window, 0, wx.RIGHT, 4)
    search_row.Add(btn_show_files, 0, wx.RIGHT, 4)
    search_row.AddStretchSpacer(1)
    search_panel.SetSizer(search_row)
    outputs_sizer.Add(search_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    output_channel_notebook = wx.Notebook(outputs_page)
    output_channel_notebook.SetMinSize(wx.Size(-1, 200))
    output_no_channels_label = wx.StaticText(
        output_channel_notebook, label=t("jobs_outputs.no_channels"),
    )
    output_channels: dict[str, wx.TextCtrl] = {}
    output_channel_paths: dict[str, wx.TextCtrl] = {}
    output_channel_paused: dict[str, bool] = {}
    output_channel_follow: dict[str, bool] = {}
    output_channel_pause_buttons: dict[str, wx.Button] = {}
    output_channel_status: dict[str, wx.StaticText] = {}
    output_channel_status_keys: dict[str, str] = {}
    output_channel_path_labels: dict[str, wx.StaticText] = {}
    output_channel_offsets: dict[str, int] = {}
    output_channel_in_flight: dict[str, bool] = {}
    output_channel_waiting: dict[str, int] = {}
    output_resolver = OutputResolver()
    outputs_sizer.Add(output_channel_notebook, 1, wx.EXPAND | wx.ALL, 4)
    outputs_page.SetSizer(outputs_sizer)

    def _set_output_channel_status(channel_id: str, key: str):
        label = output_channel_status.get(channel_id)
        if label is not None:
            output_channel_status_keys[channel_id] = key
            label.SetLabel(f"{t('jobs_outputs.status')}: {t(key)}")

    def _update_outputs_visibility():
        has_job = bool(state.get("selected_job"))
        outputs_no_selection_panel.Show(not has_job)
        outputs_toolbar_panel.Show(has_job)
        search_panel.Show(has_job)
        output_channel_notebook.Show(has_job)
        outputs_sizer.Layout()

    outputs_go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)

    root.Add(notebook, 1, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(root)

    # ======================================================================
    # STATE MANAGEMENT
    # ======================================================================
    state: dict[str, Any] = {
        "items": [],
        "raw_items": [],
        "selected_job": "",
        "selected_generation": 0,
        "closed": False,
        "in_flight": False,
        "output_in_flight": False,
        "cancel_in_flight": False,
        "user_paused": False,
        "minimized": False,
        "follow_calls": 0,
        "sacct_in_flight": False,
        "details_in_flight": False,
        "sacct_requests": 0,
        "details_requests": 0,
        "sacct_request_id": 0,
        "details_request_id": 0,
        "status_request_id": 0,
        "status_in_flight": False,
        "provider_generation": 0,
        "outputs_in_flight": False,
        "outputs_requests": 0,
        "outputs_request_id": 0,
        "outputs_generation": 0,
        "outputs_paused": False,
        "_timer_paused": False,
        "raw_scontrol_visible": False,
        "filter_query": "",
        "resolved_channels": [],
        "output_channel_defs": list(output_channel_defs) if output_channel_defs is not None else None,
        "output_channel_defs_provider": kwargs.get("output_channel_defs_provider"),
        "tracked_outputs": [],
        "followers": {},
        "detached_followers": [],
        "session": (kwargs.get("session_state") or {}).get("session") if isinstance(kwargs.get("session_state"), dict) else None,
        "raw_details_result": None,
        "raw_accounting_result": None,
        "raw_status_result": None,
        "details_parse_error": "",
        "accounting_parse_error": "",
        "status_parse_error": "",
        "cluster_status_key": "jobs_outputs.no_cluster_connection",
        "accounting_collapsed": True,
        "advanced_collapsed": True,
        "session_state_supplied": isinstance(kwargs.get("session_state"), dict),
    }
    state_lock = Lock()
    timer = wx.Timer(host)

    def post(callback, *args):
        try:
            if wx.GetApp() is not None:
                wx.CallAfter(callback, *args)
        except BaseException:
            pass

    # --- Jobs table rendering with filtering --------------------------------
    def render_items(items):
        state["raw_items"] = list(items or [])
        _apply_filter()

    def _apply_filter():
        query = state["filter_query"]
        filtered = []
        for item in state["raw_items"]:
            row = _parse_job_row(item)
            if _matches_filter(row, query):
                filtered.append((row, item))
        state["items"] = [item for _, item in filtered]
        _refresh_job_table(filtered)

    def _refresh_job_table(filtered):
        jobs.DeleteAllItems()
        selected_still_visible = False
        jobs_empty_label.Show(not filtered)
        for row, _item in filtered:
            index = jobs.InsertItem(jobs.GetItemCount(), row["job_id"])
            jobs.SetItem(index, 1, row["name"])
            jobs.SetItem(index, 2, row["state"])
            jobs.SetItem(index, 3, row["partition"])
            jobs.SetItem(index, 4, row["elapsed"])
            jobs.SetItem(index, 5, row["nodes"])
            jobs.SetItem(index, 6, row["cpus"])
            jobs.SetItem(index, 7, row["reason"])
            if row["job_id"] == state["selected_job"]:
                selected_still_visible = True
                jobs.Select(index)
                jobs.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        if not selected_still_visible and state["selected_job"]:
            btn_cancel.Enable(False)
        if not filtered:
            btn_cancel.Enable(False)
            if state["selected_job"]:
                _clear_job_selection()
        jobs_page_sizer.Layout()

    # --- Show/hide details page content vs no-selection state ----------------
    def _show_details_content(show: bool):
        if show:
            no_selection_panel.Hide()
            details_content_panel.Show()
        else:
            details_content_panel.Hide()
            no_selection_panel.Show()
        details_sizer.Layout()

    def _clear_detail_values():
        for control in detail_values.values():
            control.SetValue("—")
        details_summary_label.SetLabel(t("jobs.details_header"))
        state["details_parse_error"] = ""
        details_warning_label.Hide()
        accounting_table.DeleteAllItems()
        accounting_warning_label.Hide()

    def _clear_job_selection():
        state["selected_job"] = ""
        state["selected_generation"] += 1
        state["sacct_request_id"] += 1
        state["details_request_id"] += 1
        state["outputs_request_id"] += 1
        state["outputs_generation"] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["details_parse_error"] = ""
        state["accounting_parse_error"] = ""
        model.tracking.select_job("")
        model.selected_job_store.clear()
        btn_cancel.Enable(False)
        _clear_detail_values()
        _show_details_content(False)
        _reset_files_browser()
        _show_files_selected_state(False)
        _ensure_output_tabs([])
        _update_outputs_visibility()

    # --- Job selection handler -----------------------------------------------
    def select_job(event):
        idx = event.GetIndex()
        if idx < 0 or idx >= len(state["items"]):
            return
        item = state["items"][idx]
        row = _parse_job_row(item)
        job_id = row["job_id"]
        if not job_id:
            return
        state["selected_job"] = job_id
        state["selected_generation"] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["details_parse_error"] = ""
        state["accounting_parse_error"] = ""
        model.tracking.select_job(job_id)
        btn_cancel.Enable(True)
        # Publish to the shared selected-job context
        model.selected_job_store.select(
            job_id=job_id,
            name=row["name"],
            state=row["state"],
            partition=row["partition"],
            elapsed=row["elapsed"],
            nodes=row["nodes"],
            cpus=row["cpus"],
            reason=row["reason"],
        )
        # Also set stdout/stderr from raw item if available
        if isinstance(item, dict):
            stdout_p = str(item.get("stdout_path", "")).strip()
            stderr_p = str(item.get("stderr_path", "")).strip()
            if stdout_p or stderr_p:
                model.selected_job_store.update(stdout_path=stdout_p, stderr_path=stderr_p)
                model.set_output(stdout_p, stderr_p)
            _show_parsed_details(row, item)
            failure = model.explain_failure(SimpleNamespace(**item))
            if failure:
                current_reason = detail_values["reason"].GetValue()
                detail_values["reason"].SetValue(
                    f"{current_reason}\n{'; '.join(failure.as_lines())}".strip("—\n")
                )
        # Show details content (hide no-selection state)
        _show_details_content(True)
        _update_outputs_visibility()
        # Update summary header
        _update_summary_header()
        # Trigger accounting refresh for selected job
        _refresh_sacct()
        # Show details (scontrol)
        _show_job_details()
        # Navigate shared browser to WorkDir
        _navigate_files_to_workdir()
        # Refresh outputs tab
        refresh_outputs_tab()
        # NOTE: Do NOT auto-switch to Details tab.
        # User stays on Jobs; details content is updated in background.

    def _update_summary_header():
        ctx = model.selected_job_store.context
        parts = []
        if ctx.job_id:
            parts.append(ctx.job_id)
        if ctx.name:
            parts.append(ctx.name)
        summary = " · ".join(parts) if parts else ""
        details_summary_label.SetLabel(f"{t('jobs.details_header')} — {summary}" if summary else t('jobs.details_header'))

    def _set_detail(field_key, value):
        control = detail_values.get(field_key)
        if control is not None:
            control.SetValue(str(value or "—"))

    def _show_parsed_details(row: dict[str, str], item: dict[str, Any]):
        details_warning_label.Hide()
        for field_key in ("job_id", "name", "state", "partition", "elapsed", "nodes", "cpus"):
            _set_detail(field_key, row.get(field_key, ""))
        workdir = str(item.get("workdir", "")).strip() if isinstance(item, dict) else ""
        stdout_p = str(item.get("stdout_path", "")).strip() if isinstance(item, dict) else ""
        stderr_p = str(item.get("stderr_path", "")).strip() if isinstance(item, dict) else ""
        script_p = str(item.get("script_path", "")).strip() if isinstance(item, dict) else ""
        nodelist = str(item.get("nodelist", "")).strip() if isinstance(item, dict) else ""
        exit_code = str(item.get("exit_code", "")).strip() if isinstance(item, dict) else ""
        _set_detail("workdir", workdir)
        _set_detail("stdout_path", stdout_p)
        _set_detail("stderr_path", stderr_p)
        _set_detail("script_path", script_p)
        _set_detail("nodelist", nodelist)
        _set_detail("exit_code", exit_code)
        # Compute resources value
        nodes = row.get("nodes", "")
        cpus = row.get("cpus", "")
        if nodes or cpus:
            res_str = t("jobs.resources_value").format(nodes=nodes or "?", cpus=cpus or "?")
        else:
            res_str = "—"
        _set_detail("resources", res_str)
        if isinstance(item, dict):
            update_kwargs: dict[str, str] = {}
            if workdir:
                update_kwargs["workdir"] = workdir
            if stdout_p:
                update_kwargs["stdout_path"] = stdout_p
            if stderr_p:
                update_kwargs["stderr_path"] = stderr_p
            if script_p:
                update_kwargs["script_path"] = script_p
            if update_kwargs:
                model.selected_job_store.update(**update_kwargs)

    # --- Refresh jobs -------------------------------------------------------
    def refresh_jobs(_event=None):
        if not list_jobs or state["minimized"]:
            return
        request_generation = generation() if generation else None
        if request_generation is not None:
            model.set_monitor_generation(request_generation)
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True

        def fetch():
            try:
                result = list_jobs()
                post(done, result, None, request_generation)
            except Exception as error:
                post(done, (), error, request_generation)

        def done(result, error, req_gen=None):
            with state_lock:
                state["in_flight"] = False
            if not state["closed"] and (generation is None or req_gen == generation()):
                if error:
                    pass  # Job listing errors are logged, not shown in accounting
                else:
                    items = tuple(result or ())
                    render_items(items)
                    for item in items:
                        if isinstance(item, dict):
                            job_id = str(item.get("id", item.get("job_id", ""))).strip()
                            model._job_states.setdefault(job_id, str(item.get("state", "")).strip().upper())
                    model.poll_active_jobs(items, final_state, generation=req_gen)

        Thread(target=fetch, daemon=True).start()

    # --- Filter handling ----------------------------------------------------
    def _on_filter_changed(_event=None):
        state["filter_query"] = filter_field.GetValue().strip()
        _apply_filter()

    # --- Open Raw Job Details viewer ----------------------------------------
    def _refresh_raw_job_details():
        job_id = state["selected_job"]
        if not job_id or not show_job_details:
            return state.get("raw_details_result")
        request_generation = model.selected_job_store.generation
        try:
            try:
                result = show_job_details(job_id)
            except TypeError:
                result = show_job_details()
            raw = _raw_result(
                result,
                source_id="scontrol",
                command=f"scontrol show job {job_id}",
            )
            if (state["selected_job"] != job_id
                    or model.selected_job_store.generation != request_generation):
                return state.get("raw_details_result")
            state["raw_details_result"] = raw
            return raw
        except Exception as exc:
            raw = RawCommandResult.from_response(
                source_id="scontrol",
                command=f"scontrol show job {job_id}",
                stdout="", stderr=str(exc), exit_code=1,
            )
            if (state["selected_job"] != job_id
                    or model.selected_job_store.generation != request_generation):
                return state.get("raw_details_result")
            state["raw_details_result"] = raw
            return raw

    def _open_raw_job_details(_event=None):
        result = state.get("raw_details_result")
        if result is None:
            result = RawCommandResult(
                source_id="scontrol",
                command=f"scontrol show job {state['selected_job']}",
                stdout="",
                stderr=t("jobs_outputs.raw_not_available"),
                exit_code=-1,
            )
        show_raw_viewer(host, result, title=t("raw_viewer.raw_job_details"),
                        refresh_callback=_refresh_raw_job_details)

    def _refresh_raw_accounting():
        job_id = state["selected_job"]
        if not job_id or not refresh_sacct:
            return state.get("raw_accounting_result")
        request_generation = model.selected_job_store.generation
        try:
            result = refresh_sacct(job_id)
            raw = _raw_result(
                result,
                source_id="sacct",
                command=f"sacct -n -P -j {job_id} --format=JobIDRaw,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
            )
            if (state["selected_job"] != job_id
                    or model.selected_job_store.generation != request_generation):
                return state.get("raw_accounting_result")
            state["raw_accounting_result"] = raw
            return raw
        except Exception as exc:
            raw = RawCommandResult.from_response(
                source_id="sacct",
                command=f"sacct -n -P -j {job_id}",
                stdout="", stderr=str(exc), exit_code=1,
            )
            if (state["selected_job"] != job_id
                    or model.selected_job_store.generation != request_generation):
                return state.get("raw_accounting_result")
            state["raw_accounting_result"] = raw
            return raw

    def _open_raw_accounting(_event=None):
        result = state.get("raw_accounting_result")
        if result is None:
            result = RawCommandResult(
                source_id="sacct",
                command=f"sacct -j {state['selected_job']}",
                stdout="",
                stderr=t("jobs_outputs.raw_not_available"),
                exit_code=-1,
            )
        show_raw_viewer(host, result, title=t("raw_viewer.raw_accounting"),
                        refresh_callback=_refresh_raw_accounting)

    def _refresh_raw_server_status():
        if not _provider_status_supported():
            return state.get("raw_status_result")
        request_generation = generation() if callable(generation) else None
        provider_generation = state["provider_generation"]
        try:
            try:
                result = refresh_lssrv()
            except TypeError:
                result = refresh_lssrv("")
            raw = _raw_result(result, source_id="lssrv", command="lssrv")
            if (provider_generation != state["provider_generation"]
                    or callable(generation) and generation() != request_generation):
                return state.get("raw_status_result")
            state["raw_status_result"] = raw
            return raw
        except Exception as exc:
            raw = RawCommandResult.from_response(
                source_id="lssrv",
                command="lssrv",
                stdout="", stderr=str(exc), exit_code=1,
            )
            if (provider_generation != state["provider_generation"]
                    or callable(generation) and generation() != request_generation):
                return state.get("raw_status_result")
            state["raw_status_result"] = raw
            return raw

    def _open_raw_server_status(_event=None):
        result = state.get("raw_status_result")
        if result is None:
            result = RawCommandResult(
                source_id="lssrv",
                command="lssrv",
                stdout="",
                stderr=t("jobs_outputs.raw_not_available"),
                exit_code=-1,
            )
        show_raw_viewer(host, result, title=t("raw_viewer.raw_server_status"),
                        refresh_callback=_refresh_raw_server_status)

    # --- Accounting (sacct) for selected job ---------------------------------
    def _refresh_sacct(_event=None):
        if not refresh_sacct:
            return
        job_id = state["selected_job"] or model.tracking.selected_job_id
        if not job_id:
            return
        with state_lock:
            if state["closed"]:
                return
            state["sacct_request_id"] += 1
            request_id = state["sacct_request_id"]
            state["sacct_requests"] += 1
            state["sacct_in_flight"] = True
        req_job_id = job_id
        req_gen = model.selected_job_store.generation
        btn_sacct.Enable(False)

        def worker():
            try:
                result = refresh_sacct(req_job_id)
                post(_done_sacct, result, None, request_id)
            except Exception as error:
                post(_done_sacct, "", error, request_id)

        def _done_sacct(result, error, req_id):
            with state_lock:
                state["sacct_requests"] = max(0, state["sacct_requests"] - 1)
                state["sacct_in_flight"] = state["sacct_requests"] > 0
            if state["closed"]:
                return
            if (model.selected_job_store.job_id != req_job_id
                    or model.selected_job_store.generation != req_gen
                    or req_id != state["sacct_request_id"]):
                btn_sacct.Enable(state["sacct_requests"] == 0 and bool(refresh_sacct))
                return
            btn_sacct.Enable(state["sacct_requests"] == 0 and bool(refresh_sacct))
            # Store raw result for Raw Accounting viewer
            raw = _raw_result(
                result,
                source_id="sacct",
                command=f"sacct -j {req_job_id} --format=JobID,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
                error=error,
            )
            state["raw_accounting_result"] = raw
            state["accounting_parse_error"] = ""
            accounting_warning_label.Hide()
            raw_text = raw.stdout.strip()
            raw_error = raw.stderr.strip() if raw.has_error else ""
            if raw.has_error and not raw_error:
                raw_error = f"exit code {raw.exit_code}"
            if raw_error:
                accounting_table.DeleteAllItems()
                idx = accounting_table.InsertItem(0, t("jobs_outputs.accounting_error"))
                accounting_table.SetItem(idx, 1, raw_error)
            else:
                text = raw_text
                accounting_table.DeleteAllItems()
                if not text:
                    idx = accounting_table.InsertItem(0, t("jobs_outputs.accounting_empty"))
                    return
                # Try provider-defined parser first, fall back to inline parsing
                parsed_rows = None
                try:
                    session = state.get("session") or {}
                    profile = session.get("profile") or {}
                    provider_tpl = profile.get("provider_template") if isinstance(profile, dict) else None
                    contract = extract_contract(provider_tpl)
                    if contract.accounting_parser:
                        pr = parse_with_registry(contract.accounting_parser, text, raw_source_id="sacct")
                        if pr.ok and hasattr(pr.data, "rows"):
                            parsed_rows = list(pr.data.rows)
                        elif pr.error:
                            state["accounting_parse_error"] = pr.error.message
                except Exception:
                    pass
                if parsed_rows is not None:
                    if not parsed_rows:
                        accounting_table.InsertItem(0, t("jobs_outputs.accounting_empty"))
                    for row in parsed_rows:
                        idx = accounting_table.InsertItem(accounting_table.GetItemCount(), row.job_id)
                        accounting_table.SetItem(idx, 1, row.state)
                        accounting_table.SetItem(idx, 2, row.elapsed)
                        accounting_table.SetItem(idx, 3, row.max_rss)
                        accounting_table.SetItem(idx, 4, row.alloc_tres)
                        accounting_table.SetItem(idx, 5, row.exit_code)
                else:
                    # Fallback: inline pipe-delimited parsing
                    valid_rows = 0
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.lower().startswith("jobid"):
                            continue
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) < 2:
                            continue
                        valid_rows += 1
                        idx = accounting_table.InsertItem(accounting_table.GetItemCount(), parts[0])
                        for ci, val in enumerate(parts[1:], 1):
                            if ci <= 5:
                                accounting_table.SetItem(idx, ci, val)
                    if valid_rows == 0:
                        state["accounting_parse_error"] = "invalid accounting rows"
                if state["accounting_parse_error"]:
                    accounting_warning_label.SetLabel(t("jobs_outputs.parse_error_accounting"))
                    accounting_warning_label.Show()
                else:
                    accounting_warning_label.Hide()
            accounting_sizer.Layout()

        Thread(target=worker, daemon=True).start()

    # --- Show job details (scontrol) for selected job -----------------------
    def _show_job_details(_event=None):
        if not show_job_details:
            return
        job_id = state["selected_job"] or model.tracking.selected_job_id
        if not job_id:
            return
        with state_lock:
            if state["closed"]:
                return
            state["details_request_id"] += 1
            request_id = state["details_request_id"]
            state["details_requests"] += 1
            state["details_in_flight"] = True
        req_job_id = job_id
        req_gen = model.selected_job_store.generation

        def worker():
            try:
                try:
                    result = show_job_details(req_job_id)
                except TypeError:
                    result = show_job_details()
                post(_done_details, result, None, request_id)
            except Exception as error:
                post(_done_details, "", error, request_id)

        def _done_details(result, error, req_id):
            with state_lock:
                state["details_requests"] = max(0, state["details_requests"] - 1)
                state["details_in_flight"] = state["details_requests"] > 0
            if state["closed"]:
                return
            if (model.selected_job_store.job_id != req_job_id
                    or model.selected_job_store.generation != req_gen
                    or req_id != state["details_request_id"]):
                return
            # Store raw result for Raw Job Details viewer
            raw = _raw_result(
                result,
                source_id="scontrol",
                command=f"scontrol show job {req_job_id}",
                error=error,
            )
            state["raw_details_result"] = raw
            if raw.has_error:
                state["details_parse_error"] = raw.stderr or f"exit code {raw.exit_code}"
                details_warning_label.SetLabel(t("jobs_outputs.parse_error_details"))
                details_warning_label.Show()
                details_content_sizer.Layout()
                return
            text = raw.stdout.strip()
            if text and req_job_id:
                state["details_parse_error"] = ""
                if not _detail_response_has_fields(text):
                    state["details_parse_error"] = "unrecognized job details"
                    details_warning_label.SetLabel(t("jobs_outputs.parse_error_details"))
                    details_warning_label.Show()
                    details_content_sizer.Layout()
                    return
                # Try provider-defined parser first, fall back to hardcoded
                detail = None
                try:
                    session = state.get("session") or {}
                    profile = session.get("profile") or {}
                    provider_tpl = profile.get("provider_template") if isinstance(profile, dict) else None
                    contract = extract_contract(provider_tpl)
                    if contract.job_details_parser:
                        pr = parse_with_registry(contract.job_details_parser, text, raw_source_id="scontrol")
                        if pr.ok and hasattr(pr.data, "workdir"):
                            detail = pr.data
                        elif pr.error:
                            state["details_parse_error"] = pr.error.message
                except Exception:
                    pass
                if detail is None:
                    try:
                        detail = parse_scontrol(text, req_job_id)
                    except Exception as parse_error:
                        state["details_parse_error"] = str(parse_error)
                        details_warning_label.SetLabel(t("jobs_outputs.parse_error_details"))
                        details_warning_label.Show()
                        details_content_sizer.Layout()
                        return
                update_kwargs: dict[str, str] = {}
                if detail.workdir:
                    update_kwargs["workdir"] = detail.workdir
                if detail.stdout_path:
                    update_kwargs["stdout_path"] = detail.stdout_path
                if detail.stderr_path:
                    update_kwargs["stderr_path"] = detail.stderr_path
                if detail.script_path:
                    update_kwargs["script_path"] = detail.script_path
                if detail.nodelist:
                    update_kwargs["nodelist"] = detail.nodelist
                if detail.exit_code:
                    update_kwargs["exit_code"] = detail.exit_code
                if detail.failure_reason:
                    update_kwargs["failure_reason"] = detail.failure_reason
                _set_detail("workdir", detail.workdir)
                _set_detail("stdout_path", detail.stdout_path)
                _set_detail("stderr_path", detail.stderr_path)
                _set_detail("script_path", detail.script_path)
                _set_detail("nodelist", detail.nodelist)
                _set_detail("exit_code", detail.exit_code)
                if update_kwargs:
                    model.selected_job_store.update(**update_kwargs)
                    model.set_output(
                        model.selected_job_store.context.stdout_path,
                        model.selected_job_store.context.stderr_path,
                    )
                    _update_files_header()
                    _navigate_files_to_workdir()
                    refresh_outputs_tab(force=True)
                if state["details_parse_error"]:
                    details_warning_label.SetLabel(t("jobs_outputs.parse_error_details"))
                    details_warning_label.Show()
                else:
                    details_warning_label.Hide()
                details_content_sizer.Layout()

        Thread(target=worker, daemon=True).start()

    def _provider_connected():
        if state.get("session_state_supplied"):
            return state.get("session") is not None
        return bool(kwargs.get("provider_connected") or callable(has_status_capability) or callable(refresh_lssrv))

    def _provider_status_supported():
        if not _provider_connected() or not callable(refresh_lssrv):
            return False
        try:
            return bool(has_status_capability()) if callable(has_status_capability) else True
        except Exception:
            return False

    def _render_cluster_servers(raw_text: str, parsed_rows=None):
        rows = (
            [(item.name, item.state, item.total_cpus, item.free_cpus) for item in parsed_rows]
            if parsed_rows is not None
            else _parse_cluster_server_rows(raw_text)
        )
        cluster_servers_table.DeleteAllItems()
        for server, server_state, cpus, memory in rows:
            index = cluster_servers_table.InsertItem(cluster_servers_table.GetItemCount(), server)
            cluster_servers_table.SetItem(index, 1, server_state)
            cluster_servers_table.SetItem(index, 2, cpus)
            cluster_servers_table.SetItem(index, 3, memory)
        cluster_servers_text.SetLabel("")
        if rows:
            state["cluster_status_key"] = "jobs_outputs.cluster_status_loaded"
            cluster_status_text.SetLabel(t("jobs_outputs.cluster_status_loaded"))
        elif str(raw_text or "").strip():
            state["status_parse_error"] = "invalid cluster status"
            state["cluster_status_key"] = "jobs_outputs.parse_error_cluster"
            cluster_status_text.SetLabel(t("jobs_outputs.parse_error_cluster"))
        else:
            state["cluster_status_key"] = "jobs_outputs.no_cluster_status"
            cluster_status_text.SetLabel(t("jobs_outputs.no_cluster_status"))
        cluster_servers_table.Show(bool(rows))

    def _refresh_provider_status(_event=None):
        if not _provider_connected():
            state["raw_status_result"] = None
            state["status_parse_error"] = ""
            state["cluster_status_key"] = "jobs_outputs.no_cluster_connection"
            cluster_servers_table.DeleteAllItems()
            cluster_servers_box.Hide()
            cluster_status_text.SetLabel(t("jobs_outputs.no_cluster_connection"))
            btn_refresh_lssrv.Enable(False)
            btn_raw_server_status.Enable(False)
            cluster_page_sizer.Layout()
            return
        if not _provider_status_supported():
            state["raw_status_result"] = None
            state["status_parse_error"] = ""
            state["cluster_status_key"] = "jobs_outputs.cluster_unsupported"
            cluster_servers_table.DeleteAllItems()
            cluster_servers_box.Hide()
            cluster_status_text.SetLabel(t("jobs_outputs.cluster_unsupported"))
            btn_refresh_lssrv.Enable(False)
            btn_raw_server_status.Enable(False)
            cluster_page_sizer.Layout()
            return
        cluster_servers_box.Show()
        btn_refresh_lssrv.Enable(True)
        btn_raw_server_status.Enable(True)
        state["cluster_status_key"] = "jobs_outputs.refreshing_cluster_status"
        cluster_status_text.SetLabel(t("jobs_outputs.refreshing_cluster_status"))
        cluster_servers_table.Hide()
        with state_lock:
            state["status_request_id"] += 1
            request_id = state["status_request_id"]
            state["status_in_flight"] = True
            provider_generation = state["provider_generation"]
        session_generation = generation() if callable(generation) else None
        def worker():
            try:
                try:
                    result = refresh_lssrv()
                except TypeError:
                    result = refresh_lssrv("")
                post(done, result, None, request_id, provider_generation, session_generation)
            except Exception as error:
                post(done, "", error, request_id, provider_generation, session_generation)
        def done(result, error, req_id, req_provider_generation, req_session_generation):
            state["status_in_flight"] = False
            if (state["closed"]
                    or req_id != state["status_request_id"]
                    or req_provider_generation != state["provider_generation"]
                    or callable(generation) and req_session_generation != generation()):
                return
            raw = _raw_result(
                result,
                source_id="lssrv",
                command="lssrv",
                error=error,
            )
            state["raw_status_result"] = raw
            if raw.has_error:
                cluster_servers_table.DeleteAllItems()
                cluster_servers_table.Hide()
                state["cluster_status_key"] = "jobs_outputs.cluster_status_failed"
                cluster_status_text.SetLabel(t("jobs_outputs.cluster_status_failed"))
            else:
                state["status_parse_error"] = ""
                parsed_rows = None
                try:
                    session = state.get("session") or {}
                    profile = session.get("profile") or {}
                    provider_tpl = profile.get("provider_template") if isinstance(profile, dict) else None
                    contract = extract_contract(provider_tpl)
                    if contract.cluster_status_parser:
                        parsed = parse_with_registry(
                            contract.cluster_status_parser,
                            raw.stdout,
                            raw_source_id="lssrv",
                        )
                        if parsed.ok and isinstance(parsed.data, list):
                            parsed_rows = parsed.data
                        elif parsed.error:
                            state["status_parse_error"] = parsed.error.message
                except Exception:
                    pass
                _render_cluster_servers(raw.stdout, parsed_rows)
            cluster_page_sizer.Layout()
        Thread(target=worker, daemon=True).start()

    # --- Job files ----------------------------------------------------------
    def _update_files_header(ctx=None):
        ctx = ctx or model.selected_job_store.context
        if not ctx.job_id:
            files_job_header.SetLabel("")
            files_workdir_label.SetLabel("")
            return
        files_job_header.SetLabel(
            f"{t('jobs_outputs.job_label')} {ctx.job_id}"
            + (f" · {ctx.name}" if ctx.name else "")
        )
        files_workdir_label.SetLabel(
            f"{t('jobs_outputs.workdir')}: {ctx.workdir or '—'}"
        )

    def _navigate_files_to_workdir(_event=None):
        """Navigate the shared browser to the selected job's WorkDir."""
        ctx = model.selected_job_store.context
        _update_files_header(ctx)
        if not ctx.job_id:
            _show_files_selected_state(False)
            return
        _show_files_selected_state(bool(ctx.workdir))
        workdir = ctx.workdir
        if not workdir:
            return
        try:
            files_browser._wx_remote_controls["navigate"](workdir)
            files_browser._wx_remote_controls["load"]()
        except Exception:
            pass

    # --- Outputs tab --------------------------------------------------------
    def _ensure_output_tabs(channels: list[ResolvedOutputChannel]):
        """Create or update output channel tabs to match resolved channels."""
        current_ids = set(output_channels.keys())
        new_ids = {c.id for c in channels}
        for cid in current_ids - new_ids:
            tabCtrl = output_channels.pop(cid, None)
            output_channel_paths.pop(cid, None)
            output_channel_paused.pop(cid, None)
            output_channel_follow.pop(cid, None)
            output_channel_pause_buttons.pop(cid, None)
            output_channel_status.pop(cid, None)
            output_channel_status_keys.pop(cid, None)
            output_channel_path_labels.pop(cid, None)
            output_channel_offsets.pop(cid, None)
            output_channel_in_flight.pop(cid, None)
            output_channel_waiting.pop(cid, None)
            old_follower = state.get("followers", {}).pop(cid, None)
            if old_follower is not None:
                old_follower.close()
            try:
                page = tabCtrl.GetParent() if tabCtrl else None
                for idx in range(output_channel_notebook.GetPageCount()):
                    if output_channel_notebook.GetPage(idx) is page:
                        output_channel_notebook.DeletePage(idx)
                        break
            except Exception:
                pass
        for ch in channels:
            if ch.id not in output_channels:
                tab_panel = wx.Panel(output_channel_notebook)
                tab_sizer = wx.BoxSizer(wx.VERTICAL)
                # Per-channel toolbar
                ch_toolbar = wx.BoxSizer(wx.HORIZONTAL)
                path_label = wx.StaticText(tab_panel, label=f"{t('jobs_outputs.path')}:")
                path_field = wx.TextCtrl(tab_panel, style=wx.TE_READONLY)
                path_field.SetValue(ch.path)
                ch_pause_btn = wx.Button(tab_panel, label=t("jobs.pause_output"), size=(80, -1))
                ch_refresh_btn = wx.Button(tab_panel, label=t("jobs.refresh"), size=(70, -1))
                ch_follow_cb = wx.CheckBox(tab_panel, label=t("files.auto_scroll"))
                ch_follow_cb.SetValue(True)
                ch_status_label = wx.StaticText(tab_panel, label=f"{t('jobs_outputs.status')}: {t('jobs_outputs.status_following')}")
                ch_toolbar.Add(path_field, 1, wx.EXPAND | wx.RIGHT, 4)
                ch_toolbar.Insert(0, path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                ch_toolbar.Add(ch_pause_btn, 0, wx.RIGHT, 4)
                ch_toolbar.Add(ch_refresh_btn, 0, wx.RIGHT, 4)
                ch_toolbar.Add(ch_follow_cb, 0, wx.ALIGN_CENTER_VERTICAL)
                ch_toolbar.AddStretchSpacer(1)
                ch_toolbar.Add(ch_status_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
                text_ctrl = wx.TextCtrl(
                    tab_panel,
                    style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
                )
                text_ctrl.SetMinSize(wx.Size(-1, 150))
                tab_sizer.Add(ch_toolbar, 0, wx.EXPAND | wx.ALL, 4)
                tab_sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 4)
                tab_panel.SetSizer(tab_sizer)
                output_channel_notebook.AddPage(tab_panel, ch.label)
                output_channels[ch.id] = text_ctrl
                output_channel_paths[ch.id] = path_field
                output_channel_paused[ch.id] = False
                output_channel_follow[ch.id] = True
                output_channel_pause_buttons[ch.id] = ch_pause_btn
                output_channel_status[ch.id] = ch_status_label
                output_channel_status_keys[ch.id] = "jobs_outputs.status_following"
                output_channel_path_labels[ch.id] = path_label
                output_channel_offsets[ch.id] = 0
                output_channel_in_flight[ch.id] = False
                output_channel_waiting[ch.id] = 0
                state.setdefault("followers", {})[ch.id] = OutputFollower(OutputFollowerState(
                    tracking_id=f"follower-{uuid4().hex}",
                    channel_id=ch.id,
                    job_id=model.selected_job_store.job_id,
                    generation=model.selected_job_store.generation,
                    label=ch.label,
                    path=ch.path,
                    origin="provider" if ch.definition is not None else "legacy_slurm",
                    roles=ch.roles,
                ))

                def _on_ch_pause(evt, cid=ch.id, pause_button=ch_pause_btn):
                    output_channel_paused[cid] = not output_channel_paused[cid]
                    pause_button.SetLabel(
                        t("jobs.resume_output") if output_channel_paused[cid]
                        else t("jobs.pause_output")
                    )
                    _set_output_channel_status(
                        cid,
                        "jobs_outputs.status_paused" if output_channel_paused[cid]
                        else "jobs_outputs.status_following",
                    )

                def _on_ch_refresh(evt, cid=ch.id):
                    _refresh_single_channel(cid)

                def _on_ch_follow(evt, cid=ch.id, follow_checkbox=ch_follow_cb):
                    output_channel_follow[cid] = follow_checkbox.GetValue()

                ch_pause_btn.Bind(wx.EVT_BUTTON, _on_ch_pause)
                ch_refresh_btn.Bind(wx.EVT_BUTTON, _on_ch_refresh)
                ch_follow_cb.Bind(wx.EVT_CHECKBOX, _on_ch_follow)
            else:
                pathCtrl = output_channel_paths.get(ch.id)
                if pathCtrl:
                    pathCtrl.SetValue(ch.path)
                follower = state.setdefault("followers", {}).get(ch.id)
                if follower is not None:
                    follower.assign(
                        channel_id=ch.id,
                        job_id=model.selected_job_store.job_id,
                        generation=model.selected_job_store.generation,
                        label=ch.label,
                        path=ch.path,
                        origin="provider" if ch.definition is not None else "legacy_slurm",
                        roles=ch.roles,
                    )
        if not channels:
            output_no_channels_label.Show()
            if output_channel_notebook.GetPageCount() == 0:
                output_channel_notebook.AddPage(
                    output_no_channels_label,
                    t("jobs_outputs.outputs_title"),
                )
        else:
            output_no_channels_label.Hide()
            try:
                idx = output_channel_notebook.GetPageIndex(output_no_channels_label)
                if idx >= 0:
                    output_channel_notebook.DeletePage(idx)
            except Exception:
                pass

    def _refresh_single_channel(channel_id):
        """Refresh output for a single channel (per-channel refresh button)."""
        ctx = model.selected_job_store.context
        if not ctx.job_id:
            return
        textCtrl = output_channels.get(channel_id)
        follower = state.get("followers", {}).get(channel_id)
        if not textCtrl or follower is None:
            return

        def worker():
            try:
                follower.state.paused = output_channel_paused.get(channel_id, False)
                if callable(_remote_reader):
                    _chunk, content, waiting = follower.poll(_remote_reader, _remote_statter, force=True)
                elif callable(read_output) and set(follower.state.roles) & {"stdout", "stderr"}:
                    result = read_output(ctx.job_id)
                    content = result.get("stdout" if "stdout" in follower.state.roles else "stderr", "") if isinstance(result, dict) else result
                    content = follower.replace_snapshot(content)
                    waiting = False
                else:
                    raise RuntimeError(t("jobs_outputs.remote_reader_unavailable"))
                post(lambda c=content, w=waiting: (textCtrl.SetValue(retain_last_lines(c)), _set_output_channel_status(
                    channel_id,
                    "jobs_outputs.status_waiting" if w else "jobs_outputs.status_following",
                )))
            except Exception as error:
                post(lambda e=error: _set_output_channel_status(channel_id, "jobs_outputs.status_error"))

        Thread(target=worker, daemon=True).start()

    def _resolve_output_channels():
        """Resolve output channels for the currently selected job."""
        ctx = model.selected_job_store.context
        if not ctx.job_id:
            return []
        defs_provider = state.get("output_channel_defs_provider")
        channel_defs = defs_provider() if callable(defs_provider) else state.get("output_channel_defs")
        state["output_channel_defs"] = channel_defs
        if channel_defs is not None:
            auto = output_resolver.resolve(
                channel_defs,
                job_id=ctx.job_id,
                workdir=ctx.workdir,
                scontrol_stdout=ctx.stdout_path,
                scontrol_stderr=ctx.stderr_path,
                job_name=ctx.name,
                language=current_language(),
            )
        else:
            auto = output_resolver.resolve_legacy(
                job_id=ctx.job_id,
                workdir=ctx.workdir,
                scontrol_stdout=ctx.stdout_path,
                scontrol_stderr=ctx.stderr_path,
                job_name=ctx.name,
                language=current_language(),
            )
        # Append manually tracked outputs as additional channels
        tracked = state.get("tracked_outputs", [])
        for tracked_item in tracked:
            if tracked_item.job_id and tracked_item.job_id != ctx.job_id:
                continue
            auto.append(ResolvedOutputChannel(
                id=tracked_item.tracking_id,
                role="manual",
                label=tracked_item.label,
                path=tracked_item.path,
                source="manual",
                roles=("manual",),
            ))
        return auto

    def refresh_outputs_tab(_event=None, *, force=False):
        with state_lock:
            job_id = state["selected_job"]
            if state["closed"]:
                return
            if not job_id:
                _ensure_output_tabs([])
                _update_outputs_visibility()
                return
            if state.get("_timer_paused") and not force:
                return
            if state["outputs_in_flight"] and state.get("_outputs_job_id") == job_id and not force:
                return
            state["outputs_in_flight"] = True
            state["outputs_requests"] += 1
            state["outputs_request_id"] += 1
            output_request_id = state["outputs_request_id"]
            state["_outputs_job_id"] = job_id
            state["outputs_generation"] += 1
            gen = state["outputs_generation"]
            request_id = uuid4().hex
        resolved = _resolve_output_channels()
        state["resolved_channels"] = resolved
        _ensure_output_tabs(resolved)
        readers = _remote_reader

        def worker(req_id=request_id, output_req_id=output_request_id, g=gen, channels=resolved):
            results = {}
            for channel in channels:
                follower = state.get("followers", {}).get(channel.id)
                if follower is None:
                    continue
                if callable(readers) and channel.path:
                    _chunk, retained, waiting = follower.poll(readers, _remote_statter)
                    results[channel.id] = (retained, waiting)
                    continue
                # Legacy test/adaptor compatibility is restricted to semantic
                # stdout/stderr channels; arbitrary paths always use readers.
                content = ""
                if callable(read_output) and set(channel.roles) & {"stdout", "stderr"}:
                    try:
                        legacy = read_output(job_id)
                        if isinstance(legacy, dict):
                            content = legacy.get("stdout" if "stdout" in channel.roles else "stderr", "")
                        elif isinstance(legacy, (tuple, list)):
                            content = legacy[0 if "stdout" in channel.roles else 1] if legacy else ""
                        else:
                            content = legacy
                        results[channel.id] = (follower.replace_snapshot(content), False)
                    except (FileNotFoundError, OSError):
                        follower.state.waiting_state = min(follower.state.waiting_state + 1, 5)
                        results[channel.id] = (follower.text, True)
                else:
                    results[channel.id] = (follower.text, True)
            post(_done_outputs, results, None, req_id, output_req_id, g, channels)

        def _done_outputs(result, err, req_id, output_req_id, g, channels):
            with state_lock:
                state["outputs_requests"] = max(0, state["outputs_requests"] - 1)
                state["outputs_in_flight"] = state["outputs_requests"] > 0
                current = (
                    not state["closed"]
                    and g == state["outputs_generation"]
                    and job_id == state["selected_job"]
                    and output_req_id == state["outputs_request_id"]
                )
            if not current:
                return
            if err:
                for text_ctrl in output_channels.values():
                    text_ctrl.SetValue(str(err))
                    break
                for channel in channels:
                    _set_output_channel_status(channel.id, "jobs_outputs.status_error")
                return
            for channel in channels:
                text_ctrl = output_channels.get(channel.id)
                if not text_ctrl:
                    continue
                retained, waiting = result.get(channel.id, ("", False))
                follower = state.get("followers", {}).get(channel.id)
                if output_channel_paused.get(channel.id, False):
                    _set_output_channel_status(channel.id, "jobs_outputs.status_paused")
                    continue
                at_bottom = _output_at_bottom(text_ctrl)
                text_ctrl.SetValue(retain_last_lines(retained))
                output_channel_offsets[channel.id] = follower.state.offset if follower else 0
                output_channel_waiting[channel.id] = follower.state.waiting_state if follower else 0
                status_key = "jobs_outputs.status_waiting" if waiting else (
                    "jobs_outputs.status_completed"
                    if str(model.selected_job_store.context.state).upper() in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}
                    else "jobs_outputs.status_following"
                )
                _set_output_channel_status(channel.id, status_key)
                if outputs_follow.GetValue() and output_channel_follow.get(channel.id, True) and at_bottom and not state["minimized"]:
                    state["follow_calls"] += 1
                    text_ctrl.ShowPosition(text_ctrl.GetLastPosition())
            outputs_refresh_btn.Enable(True)

        Thread(target=worker, daemon=True).start()

    # --- Cancel with confirmation -------------------------------------------
    def cancel_job(_event):
        job_id = model.tracking.selected_job_id
        if not cancel or not job_id or state["cancel_in_flight"]:
            return
        ctx = model.selected_job_store.context
        name_part = f" ({ctx.name})" if ctx.name else ""
        msg = t("jobs.cancel_confirm").format(job_id=job_id + name_part)
        if wx.MessageBox(msg, t("jobs.cancel"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
            return
        state["cancel_in_flight"] = True
        btn_cancel.Enable(False)

        def worker():
            try:
                cancel(job_id)
                post(cancel_done, None)
            except Exception as error:
                post(cancel_done, error)

        def cancel_done(error):
            state["cancel_in_flight"] = False
            if state["closed"]:
                return
            btn_cancel.Enable(True)

        Thread(target=worker, daemon=True).start()

    # --- Pause/Resume -------------------------------------------------------
    def toggle_outputs_pause(_event=None):
        state["outputs_paused"] = not state["outputs_paused"]
        state["user_paused"] = state["outputs_paused"]
        state["_timer_paused"] = state["outputs_paused"]
        outputs_pause_btn.SetLabel(t("jobs_outputs.resume_all" if state["outputs_paused"] else "jobs_outputs.pause_all"))
        for cid, button in output_channel_pause_buttons.items():
            output_channel_paused[cid] = state["outputs_paused"]
            button.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))
            _set_output_channel_status(
                cid,
                "jobs_outputs.status_paused" if state["outputs_paused"] else "jobs_outputs.status_following",
            )

    def open_detached(_event):
        job_id = state["selected_job"]
        if not read_output or not job_id:
            return
        view = model.open_detached()

        def read_stdout():
            result = read_output(job_id)
            if isinstance(result, dict):
                return result.get("stdout", "")
            if isinstance(result, (tuple, list)):
                return result[0] if result else ""
            return result

        show_job_output(host, model, view.id, read_output=read_stdout, lifecycle=lifecycle)

    # --- Shutdown -----------------------------------------------------------
    def close(_event=None):
        if state["closed"]:
            return
        state["closed"] = True
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        host.Hide()
        host.Destroy()

    def on_destroy(event):
        # Embedded hosts can be destroyed directly by their parent without
        # going through the synthetic close callback.
        if event.GetEventObject() is not host:
            event.Skip()
            return
        state["closed"] = True
        timer.Stop()
        for follower in state.get("followers", {}).values():
            follower.close()
        unsubscribe_language_change(refresh_labels)
        event.Skip()

    def set_session(session):
        state["session"] = session
        state["provider_generation"] += 1
        state["selected_job"] = ""
        state["selected_generation"] += 1
        state["outputs_generation"] += 1
        state["outputs_request_id"] += 1
        state["sacct_request_id"] += 1
        state["details_request_id"] += 1
        state["status_request_id"] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["raw_status_result"] = None
        state["details_parse_error"] = ""
        state["accounting_parse_error"] = ""
        state["status_parse_error"] = ""
        state["outputs_paused"] = False
        state["user_paused"] = False
        state["_timer_paused"] = False
        state["outputs_in_flight"] = False
        filter_field.SetValue("")
        search_field.SetValue("")
        model.tracking.set_session(session)
        btn_cancel.Enable(False)
        for follower in state.get("followers", {}).values():
            follower.close()
        state["followers"].clear()
        state["tracked_outputs"].clear()
        for follower in state.get("detached_followers", ()):
            follower.close()
        state["detached_followers"].clear()
        model.selected_job_store.clear()
        _ensure_output_tabs([])
        _update_outputs_visibility()
        for button in output_channel_pause_buttons.values():
            button.SetLabel(t("jobs.pause_output"))
        for cid in output_channel_status:
            _set_output_channel_status(cid, "jobs_outputs.status_disconnected")
        _clear_detail_values()
        _show_details_content(False)
        _reset_files_browser()
        _show_files_selected_state(False)
        _update_files_header()
        set_navigation_store = getattr(files_browser, "_wx_remote_set_navigation_store", None)
        if callable(set_navigation_store):
            set_navigation_store(_remote_cbs.get("navigation_store"))
        refresh_provider_filters = getattr(files_browser, "_wx_remote_set_provider_filters", None)
        if callable(refresh_provider_filters):
            try:
                refresh_provider_filters(_remote_cbs.get("provider_filters") or kwargs.get("provider_filters"), _remote_cbs.get("plugin_filters") or kwargs.get("plugin_filters"))
            except Exception:
                pass
        _refresh_provider_status()
        refresh_jobs()

    # --- Minimize -----------------------------------------------------------
    def iconized(event):
        state["minimized"] = bool(event.IsIconized())
        if not state["minimized"]:
            refresh_jobs()
        event.Skip()

    # --- i18n refresh -------------------------------------------------------
    def refresh_labels(_language=None):
        host.set_host_title(t("jobs.title"))
        lbl_filter.SetLabel(f"{t('common.filter')}:")
        try:
            filter_field.SetHint(t("jobs.filter_hint"))
        except Exception:
            pass
        btn_refresh.SetLabel(t("jobs.refresh"))
        cb_auto_refresh.SetLabel(t("jobs.auto_refresh"))
        btn_cancel.SetLabel(t("jobs.cancel"))
        jobs_empty_label.SetLabel(t("jobs_outputs.no_active_jobs"))
        for col_idx, col_key in enumerate(_JOB_TABLE_COLUMNS):
            info = jobs.GetColumn(col_idx)
            info.Text = t(_COLUMN_LABEL_KEYS.get(col_key, col_key))
            jobs.SetColumn(col_idx, info)
        try:
            notebook.SetPageText(JOBS_PAGE, t("jobs.title"))
            notebook.SetPageText(CLUSTER_PAGE, t("jobs.cluster"))
            notebook.SetPageText(DETAILS_PAGE, t("jobs.details"))
            notebook.SetPageText(FILES_PAGE, t("jobs_outputs.files_title"))
            notebook.SetPageText(OUTPUTS_PAGE, t("jobs_outputs.outputs_title"))
        except Exception:
            pass
        no_selection_label.SetLabel(t("jobs.no_job_selected"))
        no_selection_hint.SetLabel(t("jobs.no_job_selected_hint"))
        btn_go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        files_no_selection_label.SetLabel(t("jobs_outputs.no_selected_job"))
        files_no_selection_hint.SetLabel(t("jobs_outputs.no_selected_job_files_hint"))
        files_go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        if files_open_main_button is not None:
            files_open_main_button.SetLabel(t("jobs_outputs.open_main_files"))
        outputs_no_selection_label.SetLabel(t("jobs_outputs.no_selected_job"))
        outputs_no_selection_hint.SetLabel(t("jobs_outputs.no_selected_job_outputs_hint"))
        outputs_go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        _update_summary_header()
        for field_key, label_key in detail_keys:
            if field_key in detail_labels:
                detail_labels[field_key].SetLabel(t(label_key))
        for field_key in ("nodes", "cpus"):
            if field_key in detail_labels:
                detail_labels[field_key].SetLabel(t(f"jobs.{field_key}"))
        if "resources" in detail_labels:
            detail_labels["resources"].SetLabel(t("jobs.resources"))
        if details_warning_label.IsShown():
            details_warning_label.SetLabel(t("jobs_outputs.parse_error_details"))
        if accounting_warning_label.IsShown():
            accounting_warning_label.SetLabel(t("jobs_outputs.parse_error_accounting"))
        btn_raw_job_details.SetLabel(t("raw_viewer.raw_job_details"))
        accounting_prefix = "▸" if _accounting_collapsed["collapsed"] else "▾"
        accounting_box.SetLabel(f"{accounting_prefix} {t('jobs_outputs.accounting_details')}")
        btn_sacct.SetLabel(t("jobs_outputs.refresh_sacct"))
        for index, key in enumerate(accounting_column_keys):
            info = accounting_table.GetColumn(index)
            info.Text = t(accounting_column_labels[key])
            accounting_table.SetColumn(index, info)
        btn_toggle_raw_acct.SetLabel(t("raw_viewer.raw_accounting"))
        cluster_heading.SetLabel(t("jobs_outputs.cluster_status"))
        cluster_status_text.SetLabel(t(state.get("cluster_status_key", "jobs_outputs.no_cluster_connection")))
        cluster_servers_box.SetLabel(t("jobs.cluster_servers"))
        btn_refresh_lssrv.SetLabel(t("jobs.refresh"))
        btn_raw_server_status.SetLabel(t("raw_viewer.raw_server_status"))
        for index, key in enumerate(("server", "state", "cpus", "memory")):
            info = cluster_servers_table.GetColumn(index)
            info.Text = t(f"jobs.{key}")
            cluster_servers_table.SetColumn(index, info)
        advanced_prefix = "▸" if _advanced_collapsed["collapsed"] else "▾"
        advanced_box.SetLabel(f"{advanced_prefix} {t('jobs.advanced')}")
        _update_files_header()
        files_header.Layout()
        files_no_selection_panel.Layout()
        outputs_refresh_btn.SetLabel(t("jobs_outputs.refresh_all"))
        outputs_follow.SetLabel(t("jobs_outputs.auto_scroll_all"))
        outputs_pause_btn.SetLabel(t("jobs_outputs.resume_all" if state["outputs_paused"] else "jobs_outputs.pause_all"))
        for cid, text_ctrl in output_channels.items():
            page = text_ctrl.GetParent()
            try:
                output_channel_notebook.SetPageText(output_channel_notebook.GetPageIndex(page), next((ch.label for ch in state.get("resolved_channels", ()) if ch.id == cid), cid))
            except Exception:
                pass
            if cid in output_channel_path_labels:
                output_channel_path_labels[cid].SetLabel(f"{t('jobs_outputs.path')}:")
            if cid in output_channel_status:
                output_channel_status[cid].SetLabel(
                    f"{t('jobs_outputs.status')}: {t(output_channel_status_keys.get(cid, 'jobs_outputs.status_following'))}"
                )
        try:
            output_no_channels_label.SetLabel(t("jobs_outputs.no_channels"))
        except Exception:
            pass
    # --- Bind events --------------------------------------------------------
    jobs.Bind(wx.EVT_LIST_ITEM_SELECTED, select_job)
    btn_refresh.Bind(wx.EVT_BUTTON, refresh_jobs)
    btn_cancel.Bind(wx.EVT_BUTTON, cancel_job)
    btn_sacct.Bind(wx.EVT_BUTTON, _refresh_sacct)
    btn_toggle_raw_acct.Bind(wx.EVT_BUTTON, _open_raw_accounting)
    btn_raw_job_details.Bind(wx.EVT_BUTTON, _open_raw_job_details)
    btn_raw_server_status.Bind(wx.EVT_BUTTON, _open_raw_server_status)
    btn_refresh_lssrv.Bind(wx.EVT_BUTTON, _refresh_provider_status)
    filter_field.Bind(wx.EVT_TEXT, _on_filter_changed)
    try:
        filter_field.Bind(wx.EVT_TEXT_ENTER, _on_filter_changed)
    except Exception:
        pass
    outputs_refresh_btn.Bind(wx.EVT_BUTTON, lambda e: refresh_outputs_tab(force=True))
    outputs_pause_btn.Bind(wx.EVT_BUTTON, toggle_outputs_pause)

    # --- Per-channel search / find / jump / open / show ---------------------
    def _get_active_channel_textctrl():
        sel = output_channel_notebook.GetSelection()
        if sel < 0 or sel >= output_channel_notebook.GetPageCount():
            return None
        page = output_channel_notebook.GetPage(sel)
        for cid, tc in output_channels.items():
            if tc.GetParent() is page:
                return tc
        return None

    def _on_search(_event=None):
        query = search_field.GetValue().strip()
        if not query:
            return
        tc = _get_active_channel_textctrl()
        if not tc:
            return
        text = tc.GetValue()
        pos = text.find(query)
        if pos >= 0:
            tc.SetStyle(pos, pos + len(query), wx.TextAttr(wx.RED, wx.YELLOW))

    def _on_find_next(_event=None):
        query = search_field.GetValue().strip()
        if not query:
            return
        tc = _get_active_channel_textctrl()
        if not tc:
            return
        text = tc.GetValue()
        pos = tc.GetInsertionPoint() + 1
        found = text.find(query, pos)
        if found < 0:
            found = text.find(query)
        if found >= 0:
            tc.SetInsertionPoint(found)
            tc.SetSelection(found, found + len(query))

    def _on_jump_latest(_event=None):
        tc = _get_active_channel_textctrl()
        if tc:
            tc.ShowPosition(tc.GetLastPosition())

    def _on_open_in_window(_event=None):
        tc = _get_active_channel_textctrl()
        if not tc or not state["selected_job"]:
            return
        channel = next((ch for ch in state.get("resolved_channels", ()) if output_channels.get(ch.id) is tc), None)
        if channel is None:
            return
        detached = OutputFollower(OutputFollowerState(
            tracking_id=f"window-{uuid4().hex}", channel_id=channel.id,
            job_id=state["selected_job"], generation=model.selected_job_store.generation,
            label=channel.label, path=channel.path, origin="provider" if channel.definition else "legacy_slurm",
            roles=channel.roles,
        ))
        state.setdefault("detached_followers", []).append(detached)
        reader = _remote_reader
        if not callable(reader) and callable(read_output) and set(channel.roles) & {"stdout", "stderr"}:
            def reader(_path, job_id=state["selected_job"], roles=channel.roles):
                result = read_output(job_id)
                return result.get("stdout" if "stdout" in roles else "stderr", "") if isinstance(result, dict) else result
        if callable(reader):
            show_job_output(host, model, detached.state.tracking_id, follower=detached,
                            read_path=reader, stat_path=_remote_statter, lifecycle=lifecycle,
                            on_closed=lambda item=detached: state["detached_followers"].remove(item) if item in state["detached_followers"] else None)

    def _on_show_in_files(_event=None):
        tc = _get_active_channel_textctrl()
        if not tc:
            return
        path_val = ""
        for cid, ctrl in output_channels.items():
            if ctrl is tc and cid in output_channel_paths:
                path_val = output_channel_paths[cid].GetValue()
                break
        if not path_val:
            return
        parent_dir = str(PurePosixPath(path_val).parent) or "/"
        files_workdir_label.SetLabel(f"{t('jobs_outputs.workdir')}: {parent_dir}")
        try:
            active_file_tab = files_browser._wx_remote_tabs[files_browser._wx_remote_notebook.GetSelection()]
            active_file_tab["highlight_path"] = path_val
            files_browser._wx_remote_controls["navigate"](parent_dir)
            files_browser._wx_remote_controls["load"]()
        except Exception:
            pass
        _show_files_selected_state(True)
        _select_inner_page(files_page)

    btn_find_next.Bind(wx.EVT_BUTTON, _on_find_next)
    btn_jump_latest.Bind(wx.EVT_BUTTON, _on_jump_latest)
    btn_open_window.Bind(wx.EVT_BUTTON, _on_open_in_window)
    btn_show_files.Bind(wx.EVT_BUTTON, _on_show_in_files)
    try:
        search_field.Bind(wx.EVT_TEXT_ENTER, _on_search)
    except Exception:
        pass

    def _on_notebook_page_changed(evt):
        try:
            page = notebook.GetCurrentPage()
            if page is files_page:
                _navigate_files_to_workdir()
            elif page is outputs_page:
                refresh_outputs_tab()
        except Exception:
            pass
        evt.Skip()

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_notebook_page_changed)

    # --- Timer tick ---------------------------------------------------------
    def tick(event):
        refresh_jobs(event)
        try:
            if notebook.GetCurrentPage() is outputs_page:
                ctx = model.selected_job_store.context
                terminal_states = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}
                is_terminal = ctx.state.upper() in terminal_states if ctx.state else False
                if is_terminal:
                    grace = state.get("_terminal_grace", 0)
                    if grace < 3:
                        state["_terminal_grace"] = grace + 1
                        refresh_outputs_tab(event)
                    elif grace == 3:
                        state["_terminal_grace"] = grace + 1
                        refresh_outputs_tab(event, force=True)
                else:
                    state["_terminal_grace"] = 0
                    refresh_outputs_tab(event)
        except Exception:
            pass

    timer.Start(1000)
    host.Bind(wx.EVT_TIMER, tick, timer)
    host.Bind(wx.EVT_ICONIZE, iconized)
    host.bind_host_close(close)
    if lifecycle is not None:
        lifecycle.register_cleanup(host.Hide)
        lifecycle.register_cleanup(close)
    subscribe_language_change(refresh_labels)

    # --- Expose internal state for tests -----------------------------------
    host._wx_jobs_state = state
    host._wx_jobs_model = model
    host._wx_jobs_controls = {
        "jobs": jobs,
        "follow": outputs_follow, "pause": outputs_pause_btn,
        "refresh": btn_refresh, "cancel": btn_cancel,
            "notebook": notebook,
            "jobs_page": jobs_page, "cluster_page": cluster_page, "details_page": details_page,
            "files_page": files_page, "outputs_page": outputs_page,
        "accounting_table": accounting_table,
        "detail_values": detail_values,
        "detail_labels": detail_labels,
        "details_content_panel": details_content_panel,
            "no_selection_panel": no_selection_panel,
            "details_warning": details_warning_label,
        "collapse_accounting": _toggle_accounting,
        "collapse_cluster_servers": _toggle_cluster_servers,
        "collapse_advanced": _toggle_advanced,
        "btn_raw_job_details": btn_raw_job_details,
        "btn_raw_accounting": btn_toggle_raw_acct,
        "btn_sacct": btn_sacct,
        "btn_raw_server_status": btn_raw_server_status,
            "accounting_box": accounting_box,
            "accounting_warning": accounting_warning_label,
            "cluster_servers_box": cluster_servers_box,
            "cluster_status_text": cluster_status_text,
        "advanced_box": advanced_box,
            "files_browser": files_browser,
            "files_model": files_model,
            "files_no_selection_panel": files_no_selection_panel,
            "files_job_header": files_job_header,
        "files_workdir_label": files_workdir_label,
        "open_main_files": files_open_main_button,
        "output_channel_notebook": output_channel_notebook,
        "output_no_channels_label": output_no_channels_label,
        "output_channels": output_channels,
            "output_channel_paths": output_channel_paths,
            "output_channel_status": output_channel_status,
        "outputs_no_selection_panel": outputs_no_selection_panel,
        "details_go_to_jobs": btn_go_to_jobs,
        "files_go_to_jobs": files_go_to_jobs,
        "outputs_go_to_jobs": outputs_go_to_jobs,
        "outputs_refresh": outputs_refresh_btn,
        "outputs_follow": outputs_follow,
        "outputs_pause": outputs_pause_btn,
        "output_search": search_field,
        "output_find_next": btn_find_next,
        "output_jump_latest": btn_jump_latest,
        "output_open_window": btn_open_window,
        "output_show_files": btn_show_files,
        "filter_field": filter_field,
        "cb_auto_refresh": cb_auto_refresh,
        "btn_cancel": btn_cancel,
        "cluster_servers_text": cluster_servers_text,
        "cluster_servers_table": cluster_servers_table,
        "btn_refresh_lssrv": btn_refresh_lssrv,
        "open_output_window": _on_open_in_window,
        "go_to_jobs": _go_to_jobs,
        "show_details_content": _show_details_content,
    }
    host._wx_jobs_model = model
    host._wx_jobs_refresh_jobs = refresh_jobs
    host._wx_jobs_refresh_outputs = lambda: refresh_outputs_tab(force=True)
    host._wx_jobs_refresh_sacct = _refresh_sacct
    host._wx_jobs_refresh_raw_job_details = _refresh_raw_job_details
    host._wx_jobs_refresh_raw_accounting = _refresh_raw_accounting
    host._wx_jobs_refresh_raw_server_status = _refresh_raw_server_status
    host._wx_jobs_show_details = _show_job_details
    host._wx_jobs_notebook = notebook
    host._wx_jobs_navigate_files = _navigate_files_to_workdir
    host._wx_jobs_refresh_outputs_tab = refresh_outputs_tab
    host._wx_jobs_set_session = set_session
    host.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    _update_outputs_visibility()
    _show_files_selected_state(False)
    _refresh_provider_status()
    refresh_jobs()
    finish()
    return host


def build_jobs_panel(parent, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None, cancel=None, lifecycle=None, final_state=None, generation=None, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs):
    """Embedded panel factory. Returns the wx.Panel host."""
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct")
    if show_job_details is None:
        show_job_details = kwargs.get("show_job_details") or kwargs.get("show_details") or kwargs.get("scontrol")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("refresh_lssrv") or kwargs.get("lssrv")
    return _build_jobs(parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel, lifecycle=lifecycle, final_state=final_state, generation=generation, embedded=True, refresh_sacct=refresh_sacct, show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs)


def show_jobs(parent=None, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None, cancel=None, lifecycle=None, final_state=None, generation=None, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs) -> int:
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct")
    if show_job_details is None:
        show_job_details = kwargs.get("show_job_details") or kwargs.get("show_details") or kwargs.get("scontrol")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("refresh_lssrv") or kwargs.get("lssrv")
    _build_jobs(parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel, lifecycle=lifecycle, final_state=final_state, generation=generation, embedded=False, refresh_sacct=refresh_sacct, show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs)
    return wx.ID_OK


__all__ = ["DetachedOutput", "WxJobsModel", "clean_output", "show_job_output", "show_jobs", "build_jobs_panel"]
