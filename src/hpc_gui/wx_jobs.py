"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Lock, Thread
from types import SimpleNamespace
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController
from hpc_gui.services.selected_job_context import SelectedJobStore
from hpc_gui.services.slurm_models import parse_scontrol
from hpc_gui.services.output_channel_resolver import (
    OutputResolver, ResolvedOutputChannel, TrackedOutput,
)
from hpc_gui.wx_host import make_host


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


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, interval_ms: int = 1000, lifecycle=None) -> int:
    """Show a bounded detached output view; polling stays in the callback."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next(item for item in model.detached if item.id == str(view_id))
    frame = wx.Frame(parent, title=f"{t('jobs.open_output')} {view.id}", size=(800, 500))
    output = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    timer = wx.Timer(frame)
    state = {"closed": False, "in_flight": False}
    state_lock = Lock()

    def refresh(_event=None):
        if not read_output:
            return
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True

        def fetch() -> None:
            try:
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
                output.ShowPosition(output.GetLastPosition())

        Thread(target=fetch, daemon=True).start()

    def resized(_event):
        model.resize_detached(view.id, max(1, output.GetClientSize().width // 8), max(1, output.GetClientSize().height // 16))
        _event.Skip()

    def closed(_event=None):
        with state_lock:
            state["closed"] = True
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        frame.Destroy()

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('jobs.open_output')} {view.id}")

    frame.Bind(wx.EVT_TIMER, refresh, timer)
    frame.Bind(wx.EVT_SIZE, resized)
    frame.Bind(wx.EVT_CLOSE, closed)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(closed)
    if read_output:
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
    parts = [p.strip() for p in s.split("|")] if "|" in s else s.split()
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


def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, cancel, lifecycle, final_state, generation, embedded, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, list_job_files=None, has_status_capability=None, **kwargs):
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    # Alias tolerance for caller naming
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct") or kwargs.get("sacct_callback") or kwargs.get("refresh_accounting")
    if show_job_details is None:
        show_job_details = kwargs.get("show_details") or kwargs.get("scontrol") or kwargs.get("scontrol_show_job") or kwargs.get("show_details_callback")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("lssrv") or kwargs.get("lssrv_refresh") or kwargs.get("lssrv_callback") or kwargs.get("refresh_lssrv_callback")
    if list_job_files is None:
        list_job_files = kwargs.get("list_job_files") or kwargs.get("job_files") or kwargs.get("files_callback")
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

    # --- Filter bar --------------------------------------------------------
    filter_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_refresh = wx.Button(panel, label=t("jobs.refresh"))
    lbl_filter = wx.StaticText(panel, label=f"{t('common.filter')}:")
    filter_field = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    try:
        filter_field.SetHint(t("jobs.filter_hint"))
    except Exception:
        pass
    cb_auto_refresh = wx.CheckBox(panel, label=t("jobs.auto_refresh"))
    cb_auto_refresh.SetValue(True)
    filter_row.Add(btn_refresh, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    filter_row.Add(lbl_filter, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    filter_row.Add(filter_field, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    filter_row.Add(cb_auto_refresh, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(filter_row, 0, wx.EXPAND | wx.ALL, 6)

    # --- Sub-tab notebook ---------------------------------------------------
    notebook = wx.Notebook(panel)
    details_page = wx.Panel(notebook)
    files_page = wx.Panel(notebook)
    outputs_page = wx.Panel(notebook)
    notebook.AddPage(details_page, f"{t('jobs.title')} / {t('common.details')}")
    notebook.AddPage(files_page, t("jobs_outputs.files_title"))
    notebook.AddPage(outputs_page, t("jobs_outputs.outputs_title"))

    # --- Details page: 3 vertically stacked collapsible sections -----------
    details_sizer = wx.BoxSizer(wx.VERTICAL)

    # ---- Section 1: Jobs list -----------------------------------------------
    jobs_box = wx.StaticBox(details_page, label=f"▾ {t('jobs.title')}")
    jobs_sizer = wx.StaticBoxSizer(jobs_box, wx.VERTICAL)
    jobs = wx.ListCtrl(jobs_box, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
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
    jobs_sizer.Add(jobs, 1, wx.EXPAND | wx.ALL, 4)
    details_sizer.Add(jobs_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    # Collapse state for Jobs section
    _jobs_collapsed = {"collapsed": False}
    _jobs_content_items = [jobs]
    _jobs_original_proportions = {}

    # ---- Section 2: Job Details ---------------------------------------------
    details_box = wx.StaticBox(details_page, label=f"▾ {t('jobs_outputs.job_details')}")
    details_group_sizer = wx.StaticBoxSizer(details_box, wx.VERTICAL)
    details_text = wx.TextCtrl(details_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    try:
        details_text.SetHint(t("jobs.select_job_hint"))
    except Exception:
        pass
    btn_raw_scontrol = wx.Button(details_box, label=t("jobs_outputs.show_raw_scontrol"))
    raw_scontrol_text = wx.TextCtrl(details_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    raw_scontrol_text.Show(False)
    try:
        raw_scontrol_text.SetHint(t("jobs_outputs.raw_scontrol_hint"))
    except Exception:
        pass
    details_group_sizer.Add(details_text, 1, wx.EXPAND | wx.ALL, 4)
    details_group_sizer.Add(btn_raw_scontrol, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    details_group_sizer.Add(raw_scontrol_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    raw_scontrol_text.Show(False)
    details_sizer.Add(details_group_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    _details_collapsed = {"collapsed": False}
    _details_content_items = [details_text, btn_raw_scontrol, raw_scontrol_text]

    # ---- Section 3: Accounting ----------------------------------------------
    accounting_box = wx.StaticBox(details_page, label=f"▾ {t('jobs_outputs.accounting_details')}")
    accounting_sizer = wx.StaticBoxSizer(accounting_box, wx.VERTICAL)
    btn_sacct = wx.Button(accounting_box, label=t("jobs_outputs.refresh_sacct"))
    accounting_text = wx.TextCtrl(accounting_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    try:
        accounting_text.SetHint(t("jobs_outputs.accounting_placeholder"))
    except Exception:
        pass
    accounting_row = wx.BoxSizer(wx.HORIZONTAL)
    accounting_row.Add(btn_sacct, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.AddStretchSpacer(1)
    accounting_sizer.Add(accounting_row, 0, wx.EXPAND | wx.ALL, 4)
    accounting_sizer.Add(accounting_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    accounting_sizer.SetMinSize(wx.Size(-1, 90))
    details_sizer.Add(accounting_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    _accounting_collapsed = {"collapsed": False}
    _accounting_content_items = [btn_sacct, accounting_text]

    # ---- Cancel button row -------------------------------------------------
    cancel_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_cancel = wx.Button(details_page, label=t("jobs.cancel"))
    btn_cancel.Enable(False)
    cancel_row.AddStretchSpacer(1)
    cancel_row.Add(btn_cancel, 0, wx.ALIGN_CENTER_VERTICAL)
    details_sizer.Add(cancel_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    details_page.SetSizer(details_sizer)

    # --- Collapse/expand helpers for all three sections ----------------------
    def _toggle_section(box, sizer, collapsed_state, content_items, _event=None):
        collapsed_state["collapsed"] = not collapsed_state["collapsed"]
        is_collapsed = collapsed_state["collapsed"]
        for item in content_items:
            try:
                item.Show(not is_collapsed)
            except Exception:
                pass
        if is_collapsed:
            box.SetLabel(box.GetLabel().replace("▾", "▸"))
        else:
            box.SetLabel(box.GetLabel().replace("▸", "▾"))
        details_sizer.Layout()

    def _toggle_jobs(_event=None):
        _toggle_section(jobs_box, jobs_sizer, _jobs_collapsed, _jobs_content_items)

    def _toggle_details(_event=None):
        _toggle_section(details_box, details_group_sizer, _details_collapsed, _details_content_items)

    def _toggle_accounting(_event=None):
        _toggle_section(accounting_box, accounting_sizer, _accounting_collapsed, _accounting_content_items)

    jobs_box.Bind(wx.EVT_LEFT_DOWN, _toggle_jobs)
    details_box.Bind(wx.EVT_LEFT_DOWN, _toggle_details)
    accounting_box.Bind(wx.EVT_LEFT_DOWN, _toggle_accounting)

    # --- Files sub-tab: shared remote browser integrated with SelectedJobContext -
    from hpc_gui.wx_remote_files_view import build_remote_files_panel
    from hpc_gui.wx_remote_files import WxRemoteDirectoryModel

    files_model = WxRemoteDirectoryModel("/")
    files_sizer = wx.BoxSizer(wx.VERTICAL)

    # Job workdir label
    files_workdir_label = wx.StaticText(files_page, label=t("jobs.select_job_hint"))
    files_sizer.Add(files_workdir_label, 0, wx.EXPAND | wx.ALL, 4)

    # Resolve navigation store for favorites/history
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

    # Shared remote browser panel
    files_browser = build_remote_files_panel(
        files_page,
        model=files_model,
        navigation_store=_nav_store,
    )

    # Wire follow callback from the Jobs workspace
    def _on_follow_file(remote_path, mode="new_tab", follower_id=None):
        """Handle Follow/Track from the Files context menu."""
        ctx = model.selected_job_store.context
        if not ctx.job_id:
            return
        if mode == "existing" and follower_id:
            tracked_outputs = state.get("tracked_outputs", [])
            for tracked_item in tracked_outputs:
                if tracked_item.tracking_id == follower_id:
                    tracked_outputs.remove(tracked_item)
                    break
            new_tracked = TrackedOutput(
                tracking_id=follower_id,
                channel_id=None,
                label=remote_path.rsplit("/", 1)[-1],
                path=remote_path,
                origin="manual",
            )
            tracked_outputs.append(new_tracked)
            pathCtrl = output_channel_paths.get(follower_id)
            if pathCtrl:
                pathCtrl.SetValue(remote_path)
            textCtrl = output_channels.get(follower_id)
            if textCtrl:
                textCtrl.SetValue("")
            refresh_outputs_tab(force=True)
            return
        tracking_id = f"manual_{ctx.job_id}_{remote_path.rsplit('/', 1)[-1]}"
        tracked = TrackedOutput(
            tracking_id=tracking_id,
            channel_id=None,
            label=remote_path.rsplit("/", 1)[-1],
            path=remote_path,
            origin="manual",
        )
        state.setdefault("tracked_outputs", []).append(tracked)
        refresh_outputs_tab(force=True)

    files_browser._follow_callback = _on_follow_file
    files_sizer.Add(files_browser, 1, wx.EXPAND)
    files_page.SetSizer(files_sizer)

    # --- Outputs sub-tab: dynamic 0..N output channels ----------------------
    outputs_sizer = wx.BoxSizer(wx.VERTICAL)
    outputs_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    outputs_refresh_btn = wx.Button(outputs_page, label=t("jobs.refresh"))
    outputs_follow = wx.CheckBox(outputs_page, label=t("files.auto_scroll"))
    outputs_follow.SetValue(True)
    outputs_pause_btn = wx.Button(outputs_page, label=t("jobs.pause_output"))
    outputs_toolbar.Add(outputs_refresh_btn, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_pause_btn, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_follow, 0, wx.ALIGN_CENTER_VERTICAL)
    outputs_toolbar.AddStretchSpacer(1)
    outputs_sizer.Add(outputs_toolbar, 0, wx.EXPAND | wx.ALL, 4)

    # Per-channel search bar
    search_row = wx.BoxSizer(wx.HORIZONTAL)
    search_label = wx.StaticText(outputs_page, label=f"{t('common.filter')}:")
    search_field = wx.TextCtrl(outputs_page, style=wx.TE_PROCESS_ENTER)
    try:
        search_field.SetHint(t("jobs_outputs.search_hint"))
    except Exception:
        pass
    btn_find_next = wx.Button(outputs_page, label=t("jobs_outputs.find_next"))
    btn_jump_latest = wx.Button(outputs_page, label=t("jobs_outputs.jump_to_latest"))
    btn_open_window = wx.Button(outputs_page, label=t("jobs_outputs.open_in_window"))
    btn_show_files = wx.Button(outputs_page, label=t("jobs_outputs.show_in_files"))
    search_row.Add(search_label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    search_row.Add(search_field, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    search_row.Add(btn_find_next, 0, wx.RIGHT, 4)
    search_row.Add(btn_jump_latest, 0, wx.RIGHT, 4)
    search_row.Add(btn_open_window, 0, wx.RIGHT, 4)
    search_row.Add(btn_show_files, 0, wx.RIGHT, 4)
    search_row.AddStretchSpacer(1)
    outputs_sizer.Add(search_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    # Dynamic output channel tabs
    output_channel_notebook = wx.Notebook(outputs_page)
    output_channel_notebook.SetMinSize(wx.Size(-1, 200))
    output_no_channels_label = wx.StaticText(
        output_channel_notebook,
        label=t("jobs_outputs.no_channels"),
    )
    output_channels: dict[str, wx.TextCtrl] = {}
    output_channel_paths: dict[str, wx.TextCtrl] = {}
    output_channel_paused: dict[str, bool] = {}
    output_resolver = OutputResolver()
    outputs_sizer.Add(output_channel_notebook, 1, wx.EXPAND | wx.ALL, 4)
    outputs_page.SetSizer(outputs_sizer)

    root.Add(notebook, 1, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(root)

    # --- State management --------------------------------------------------
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
        "outputs_in_flight": False,
        "outputs_generation": 0,
        "outputs_paused": False,
        "_timer_paused": False,
        "raw_scontrol_visible": False,
        "filter_query": "",
        "resolved_channels": [],
        "output_channel_defs": [],
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
            # Show parsed details
            _show_parsed_details(row, item)
            failure = model.explain_failure(SimpleNamespace(**item))
            if failure:
                details_text.SetValue(details_text.GetValue() + "\n" + "\n".join(failure.as_lines()))
        # Trigger accounting refresh for selected job
        _refresh_sacct()
        # Show details (scontrol)
        _show_job_details()
        # Navigate shared browser to WorkDir
        _navigate_files_to_workdir()
        # Refresh outputs tab
        refresh_outputs_tab()

    def _show_parsed_details(row: dict[str, str], item: dict[str, Any]):
        """Show labeled detail fields for the selected job."""
        fields = []
        fields.append(f"Job ID:      {row['job_id']}")
        fields.append(f"Name:        {row['name']}")
        fields.append(f"State:       {row['state']}")
        fields.append(f"Partition:   {row['partition']}")
        fields.append(f"Elapsed:     {row['elapsed']}")
        if row["nodes"]:
            fields.append(f"Nodes:       {row['nodes']}")
        if row["cpus"]:
            fields.append(f"CPUs:        {row['cpus']}")
        if row["reason"]:
            fields.append(f"Reason:      {row['reason']}")
        workdir = str(item.get("workdir", "")).strip() if isinstance(item, dict) else ""
        if workdir:
            fields.append(f"WorkDir:     {workdir}")
        stdout_p = str(item.get("stdout_path", "")).strip() if isinstance(item, dict) else ""
        if stdout_p:
            fields.append(f"StdOut:      {stdout_p}")
        stderr_p = str(item.get("stderr_path", "")).strip() if isinstance(item, dict) else ""
        if stderr_p:
            fields.append(f"StdErr:      {stderr_p}")
        script_p = str(item.get("script_path", "")).strip() if isinstance(item, dict) else ""
        if script_p:
            fields.append(f"Script:      {script_p}")
        details_text.SetValue("\n".join(fields))
        # Update selected job store with scheduler metadata
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
                    details_text.SetValue(str(error))
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

    # --- Toggle raw scontrol ------------------------------------------------
    def _toggle_raw_scontrol(_event=None):
        state["raw_scontrol_visible"] = not state["raw_scontrol_visible"]
        raw_scontrol_text.Show(state["raw_scontrol_visible"])
        btn_raw_scontrol.SetLabel(
            t("jobs_outputs.hide_raw_scontrol") if state["raw_scontrol_visible"]
            else t("jobs_outputs.show_raw_scontrol")
        )
        details_sizer.Layout()

    # --- Accounting (sacct) for selected job ---------------------------------
    def _refresh_sacct(_event=None):
        if not refresh_sacct:
            return
        job_id = state["selected_job"] or model.tracking.selected_job_id
        if not job_id:
            return
        with state_lock:
            if state["closed"] or state["sacct_in_flight"]:
                return
            state["sacct_in_flight"] = True
        req_job_id = job_id
        req_gen = model.selected_job_store.generation
        btn_sacct.Enable(False)

        def worker():
            try:
                result = refresh_sacct(req_job_id)
                post(_done_sacct, result, None)
            except Exception as error:
                post(_done_sacct, "", error)

        def _done_sacct(result, error):
            with state_lock:
                state["sacct_in_flight"] = False
            if state["closed"]:
                return
            if (model.selected_job_store.job_id != req_job_id
                    or model.selected_job_store.generation != req_gen):
                btn_sacct.Enable(bool(refresh_sacct))
                return
            btn_sacct.Enable(bool(refresh_sacct))
            if error:
                accounting_text.SetValue(str(error))
            else:
                text = clean_output(result) if result is not None else ""
                accounting_text.SetValue(text)

        Thread(target=worker, daemon=True).start()

    # --- Show job details (scontrol) for selected job -----------------------
    def _show_job_details(_event=None):
        if not show_job_details:
            return
        job_id = state["selected_job"] or model.tracking.selected_job_id
        if not job_id:
            return
        with state_lock:
            if state["closed"] or state["details_in_flight"]:
                return
            state["details_in_flight"] = True
        req_job_id = job_id
        req_gen = model.selected_job_store.generation

        def worker():
            try:
                try:
                    result = show_job_details(req_job_id)
                except TypeError:
                    result = show_job_details()
                post(_done_details, result, None)
            except Exception as error:
                post(_done_details, "", error)

        def _done_details(result, error):
            with state_lock:
                state["details_in_flight"] = False
            if state["closed"]:
                return
            if (model.selected_job_store.job_id != req_job_id
                    or model.selected_job_store.generation != req_gen):
                return
            if error:
                raw_scontrol_text.SetValue(str(error))
                return
            text = str(result or "").strip()
            raw_scontrol_text.SetValue(text)
            if text and req_job_id:
                detail = parse_scontrol(text, req_job_id)
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
                if update_kwargs:
                    model.selected_job_store.update(**update_kwargs)
                    model.set_output(
                        model.selected_job_store.context.stdout_path,
                        model.selected_job_store.context.stderr_path,
                    )

        Thread(target=worker, daemon=True).start()

    # --- Job files ----------------------------------------------------------
    def _navigate_files_to_workdir(_event=None):
        """Navigate the shared browser to the selected job's WorkDir."""
        workdir = model.selected_job_store.workdir
        if not workdir:
            files_workdir_label.SetLabel(t("jobs.select_job_hint"))
            return
        files_workdir_label.SetLabel(f"{t('jobs_outputs.workdir')}: {workdir}")
        try:
            files_model.navigate(workdir)
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
            try:
                idx = output_channel_notebook.GetPageIndex(tabCtrl.GetParent() if tabCtrl else None)
                if idx >= 0:
                    output_channel_notebook.DeletePage(idx)
            except Exception:
                pass
        for ch in channels:
            if ch.id not in output_channels:
                tab_panel = wx.Panel(output_channel_notebook)
                tab_sizer = wx.BoxSizer(wx.VERTICAL)
                path_field = wx.TextCtrl(tab_panel, style=wx.TE_READONLY)
                path_field.SetValue(ch.path)
                text_ctrl = wx.TextCtrl(
                    tab_panel,
                    style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
                )
                text_ctrl.SetMinSize(wx.Size(-1, 150))
                tab_sizer.Add(path_field, 0, wx.EXPAND | wx.ALL, 4)
                tab_sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 4)
                tab_panel.SetSizer(tab_sizer)
                output_channel_notebook.AddPage(tab_panel, ch.label)
                output_channels[ch.id] = text_ctrl
                output_channel_paths[ch.id] = path_field
                output_channel_paused[ch.id] = False
            else:
                pathCtrl = output_channel_paths.get(ch.id)
                if pathCtrl:
                    pathCtrl.SetValue(ch.path)
        if not channels:
            if output_channel_notebook.GetPageCount() == 0:
                output_channel_notebook.AddPage(
                    output_no_channels_label,
                    t("jobs_outputs.outputs_title"),
                )
        else:
            try:
                idx = output_channel_notebook.GetPageIndex(output_no_channels_label)
                if idx >= 0:
                    output_channel_notebook.DeletePage(idx)
            except Exception:
                pass

    def _resolve_output_channels():
        """Resolve output channels for the currently selected job."""
        ctx = model.selected_job_store.context
        if not ctx.job_id:
            return []
        # Check for provider-defined channels
        channel_defs = state.get("output_channel_defs", [])
        if channel_defs:
            auto = output_resolver.resolve(
                channel_defs,
                job_id=ctx.job_id,
                workdir=ctx.workdir,
                scontrol_stdout=ctx.stdout_path,
                scontrol_stderr=ctx.stderr_path,
            )
        else:
            # Legacy: use generic Slurm semantics
            auto = output_resolver.resolve_legacy(
                job_id=ctx.job_id,
                workdir=ctx.workdir,
                scontrol_stdout=ctx.stdout_path,
                scontrol_stderr=ctx.stderr_path,
            )
        # Append manually tracked outputs as additional channels
        tracked = state.get("tracked_outputs", [])
        for tracked_item in tracked:
            if ctx.job_id and ctx.job_id not in tracked_item.tracking_id:
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
            if state["closed"] or not job_id:
                return
            if state.get("_timer_paused") and not force:
                return
            if state["outputs_in_flight"] and state.get("_outputs_job_id") == job_id:
                return
            state["outputs_in_flight"] = True
            state["_outputs_job_id"] = job_id
            state["outputs_generation"] += 1
            gen = state["outputs_generation"]
            request_id = job_id
        outputs_refresh_btn.Enable(False)
        # Resolve channels for current selection
        resolved = _resolve_output_channels()
        state["resolved_channels"] = resolved
        # Ensure tabs match resolved channels
        try:
            wx.CallAfter(_ensure_output_tabs, resolved)
        except Exception:
            pass
        # Read output for each resolved channel
        if not read_output:
            outputs_refresh_btn.Enable(True)
            return

        def worker(req_id=request_id, g=gen, channels=resolved):
            results = {}
            # Read automatic channels via read_output callback
            if read_output:
                try:
                    result = read_output(req_id)
                    if isinstance(result, dict):
                        results["stdout"] = result.get("stdout", "")
                        results["stderr"] = result.get("stderr", "")
                except Exception:
                    pass
            # Read manually tracked files directly
            for ch in channels:
                if ch.source == "manual" and ch.path:
                    try:
                        session = None
                        try:
                            from hpc_gui.wx_shell import _get_session_files
                            session = _get_session_files()
                        except Exception:
                            pass
                        if session and hasattr(session, "read_text"):
                            results[ch.id] = session.read_text(ch.path)
                    except Exception:
                        results[ch.id] = ""
            post(lambda: _done_outputs(results, None, req_id, g, channels))

        def _done_outputs(result, err, req_id, g, channels=None):
            with state_lock:
                state["outputs_in_flight"] = False
                if state["closed"] or g != state["outputs_generation"] or req_id != state["selected_job"]:
                    outputs_refresh_btn.Enable(True)
                    return
            outputs_refresh_btn.Enable(True)
            if err:
                # Show error in first available channel tab
                for textCtrl in output_channels.values():
                    textCtrl.SetValue(str(err))
                    break
                return
            if channels and isinstance(result, dict):
                # Map results to resolved channels
                for ch in channels:
                    textCtrl = output_channels.get(ch.id)
                    if not textCtrl:
                        continue
                    # Check if result has a direct key for this channel
                    if ch.id in result:
                        textCtrl.SetValue(clean_output(result[ch.id]))
                    elif "stdout" in ch.roles:
                        textCtrl.SetValue(clean_output(result.get("stdout", "")))
                    elif "stderr" in ch.roles:
                        textCtrl.SetValue(clean_output(result.get("stderr", "")))
                    elif ch.source == "manual":
                        textCtrl.SetValue(clean_output(result.get(ch.id, "")))
                    else:
                        textCtrl.SetValue(clean_output(str(result)))
            elif isinstance(result, dict):
                # Fallback: legacy dict with stdout/stderr
                for ch_id, textCtrl in output_channels.items():
                    if "stdout" in ch_id:
                        textCtrl.SetValue(clean_output(result.get("stdout", "")))
                    elif "stderr" in ch_id:
                        textCtrl.SetValue(clean_output(result.get("stderr", "")))
            elif isinstance(result, (tuple, list)):
                vals = list(result)
                for i, textCtrl in enumerate(output_channels.values()):
                    textCtrl.SetValue(clean_output(vals[i] if i < len(vals) else ""))
            else:
                for textCtrl in output_channels.values():
                    textCtrl.SetValue(clean_output(result))
            if outputs_follow.GetValue() and not state["outputs_paused"] and not state["minimized"]:
                state["follow_calls"] += 1
                for textCtrl in output_channels.values():
                    try:
                        textCtrl.ShowPosition(textCtrl.GetLastPosition())
                    except Exception:
                        pass

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
            if error:
                details_text.SetValue(str(error))

        Thread(target=worker, daemon=True).start()

    # --- Pause/Resume -------------------------------------------------------
    def toggle_outputs_pause(_event=None):
        state["outputs_paused"] = not state["outputs_paused"]
        state["user_paused"] = state["outputs_paused"]
        state["_timer_paused"] = state["outputs_paused"]
        outputs_pause_btn.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))

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
        for col_idx, col_key in enumerate(_JOB_TABLE_COLUMNS):
            jobs.SetColumn(col_idx, t(_COLUMN_LABEL_KEYS.get(col_key, col_key)))
        try:
            notebook.SetPageText(0, f"{t('jobs.title')} / {t('common.details')}")
            notebook.SetPageText(1, t("jobs_outputs.files_title"))
            notebook.SetPageText(2, t("jobs_outputs.outputs_title"))
        except Exception:
            pass
        details_box.SetLabel(t("jobs_outputs.job_details"))
        accounting_box.SetLabel(t("jobs_outputs.accounting_details"))
        btn_sacct.SetLabel(t("jobs_outputs.refresh_sacct"))
        try:
            accounting_text.SetHint(t("jobs_outputs.accounting_placeholder"))
        except Exception:
            pass
        btn_raw_scontrol.SetLabel(
            t("jobs_outputs.hide_raw_scontrol") if state["raw_scontrol_visible"]
            else t("jobs_outputs.show_raw_scontrol")
        )
        try:
            files_workdir_label.SetLabel(t("jobs.select_job_hint"))
        except Exception:
            pass
        outputs_refresh_btn.SetLabel(t("jobs.refresh"))
        outputs_follow.SetLabel(t("files.auto_scroll"))
        outputs_pause_btn.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))
        try:
            output_no_channels_label.SetLabel(t("jobs_outputs.no_channels"))
        except Exception:
            pass
        outputs_refresh_btn.SetLabel(t("jobs.refresh"))
        outputs_follow.SetLabel(t("files.auto_scroll"))
        outputs_pause_btn.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))

    # --- Bind events --------------------------------------------------------
    jobs.Bind(wx.EVT_LIST_ITEM_SELECTED, select_job)
    btn_refresh.Bind(wx.EVT_BUTTON, refresh_jobs)
    btn_cancel.Bind(wx.EVT_BUTTON, cancel_job)
    btn_sacct.Bind(wx.EVT_BUTTON, _refresh_sacct)
    btn_raw_scontrol.Bind(wx.EVT_BUTTON, _toggle_raw_scontrol)
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
        if sel < 0:
            return None
        for cid, tc in output_channels.items():
            try:
                if tc.GetParent() and output_channel_notebook.GetPage(output_channel_notebook.GetPageIndex(tc.GetParent())) is not None:
                    idx = output_channel_notebook.GetPageIndex(tc.GetParent())
                    if idx == sel:
                        return tc
            except Exception:
                pass
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
        text = tc.GetValue()
        frame = wx.Frame(host, title=f"{t('jobs_outputs.output')} — {state['selected_job']}", size=(800, 500))
        out = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        out.SetValue(text)
        out.ShowPosition(out.GetLastPosition())
        frame.Show()

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
            files_model.navigate(parent_dir)
        except Exception:
            pass
        notebook.SetSelection(1)

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
            sel = notebook.GetSelection()
            if sel == 1:
                _navigate_files_to_workdir()
            elif sel == 2:
                refresh_outputs_tab()
        except Exception:
            pass
        evt.Skip()

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_notebook_page_changed)

    # --- Timer tick ---------------------------------------------------------
    def tick(event):
        refresh_jobs(event)
        try:
            if notebook.GetSelection() == 2:
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

    # Expose internal state for tests
    host._wx_jobs_state = state
    host._wx_jobs_model = model
    host._wx_jobs_controls = {
        "jobs": jobs,
        "follow": outputs_follow, "pause": outputs_pause_btn,
        "refresh": btn_refresh, "cancel": btn_cancel,
        "notebook": notebook,
        "details_page": details_page, "files_page": files_page, "outputs_page": outputs_page,
        "accounting_text": accounting_text,
        "details_text": details_text,
        "raw_scontrol_text": raw_scontrol_text,
        "btn_raw_scontrol": btn_raw_scontrol,
        "btn_sacct": btn_sacct,
        "accounting_box": accounting_box,
        "details_box": details_box,
        "files_browser": files_browser,
        "files_model": files_model,
        "files_workdir_label": files_workdir_label,
        "output_channel_notebook": output_channel_notebook,
        "output_channels": output_channels,
        "output_channel_paths": output_channel_paths,
        "outputs_refresh": outputs_refresh_btn,
        "outputs_follow": outputs_follow,
        "outputs_pause": outputs_pause_btn,
        "filter_field": filter_field,
        "cb_auto_refresh": cb_auto_refresh,
        "btn_cancel": btn_cancel,
    }
    host._wx_jobs_model = model
    host._wx_jobs_refresh_jobs = refresh_jobs
    host._wx_jobs_refresh_outputs = lambda: refresh_outputs_tab(force=True)
    host._wx_jobs_refresh_sacct = _refresh_sacct
    host._wx_jobs_show_details = _show_job_details
    host._wx_jobs_notebook = notebook
    host._wx_jobs_navigate_files = _navigate_files_to_workdir
    host._wx_jobs_refresh_outputs_tab = refresh_outputs_tab
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
