"""Widget-only composition for the Jobs workspace pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.core.i18n import t


@dataclass
class JobsPage:
    page: Any
    sizer: Any
    table: Any
    columns: tuple[str, ...]
    column_labels: tuple[str, ...]
    refresh: Any
    filter_label: Any
    filter_field: Any
    auto_refresh: Any
    hide_finished: Any
    refresh_label: Any
    cancel: Any
    empty_label: Any


@dataclass
class ClusterPage:
    page: Any
    sizer: Any
    heading: Any
    refresh: Any
    raw_status: Any
    servers_box: Any
    status_text: Any
    servers_text: Any
    servers_table: Any


@dataclass
class DetailsPage:
    page: Any
    sizer: Any
    no_selection_panel: Any
    no_selection_label: Any
    no_selection_hint: Any
    go_to_jobs: Any
    content_panel: Any
    content_sizer: Any
    summary: Any
    values: dict[str, Any]
    labels: dict[str, Any]
    detail_label_keys: dict[str, str]
    accounting_column_keys: tuple[str, ...]
    accounting_column_labels: dict[str, str]
    warning: Any
    raw_details: Any
    accounting_box: Any
    accounting_sizer: Any
    accounting_table: Any
    refresh_accounting: Any
    raw_accounting: Any
    accounting_warning: Any
    advanced_box: Any
    advanced_sizer: Any
    toggle_accounting: Any
    toggle_advanced: Any


@dataclass
class FilesPage:
    page: Any
    sizer: Any
    model: Any
    browser: Any
    header: Any
    no_selection_panel: Any
    no_selection_label: Any
    no_selection_hint: Any
    go_to_jobs: Any
    job_header: Any
    workdir_label: Any
    open_main_files: Any


@dataclass
class OutputsPage:
    page: Any
    sizer: Any
    toolbar_panel: Any
    search_panel: Any
    no_selection_panel: Any
    no_selection_label: Any
    no_selection_hint: Any
    go_to_jobs: Any
    refresh: Any
    follow: Any
    pause: Any
    search_field: Any
    search_label: Any
    find_next: Any
    jump_latest: Any
    open_window: Any
    show_files: Any
    channel_notebook: Any
    no_channels_label: Any
    channels: dict[str, Any]
    channel_paths: dict[str, Any]
    channel_paused: dict[str, bool]
    channel_follow: dict[str, bool]
    channel_pause_buttons: dict[str, Any]
    channel_status: dict[str, Any]
    channel_status_keys: dict[str, str]
    channel_path_labels: dict[str, Any]
    channel_offsets: dict[str, int]
    channel_in_flight: dict[str, bool]
    channel_waiting: dict[str, int]


@dataclass
class JobsWorkspaceViews:
    notebook: Any
    jobs: JobsPage
    cluster: ClusterPage
    details: DetailsPage
    files: FilesPage
    outputs: OutputsPage


def _jobs_page(wx, notebook, hide_finished: bool) -> JobsPage:
    page = wx.Panel(notebook)
    toolbar = wx.BoxSizer(wx.HORIZONTAL)
    refresh = wx.Button(page, label=t("jobs.refresh"))
    filter_label = wx.StaticText(page, label=f"{t('common.filter')}:")
    filter_field = wx.TextCtrl(page, style=wx.TE_PROCESS_ENTER)
    try:
        filter_field.SetHint(t("jobs.filter_hint"))
    except Exception:
        pass
    auto_refresh = wx.CheckBox(page, label=t("jobs.auto_refresh"))
    auto_refresh.SetValue(True)
    hide = wx.CheckBox(page, label=t("jobs.hide_finished"))
    hide.SetValue(hide_finished)
    refresh_label = wx.StaticText(page, label="")
    for control, proportion, flags, border in (
        (refresh, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6),
        (filter_label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4),
        (filter_field, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6),
        (auto_refresh, 0, wx.ALIGN_CENTER_VERTICAL, 0),
        (hide, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 8),
        (refresh_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 6),
    ):
        toolbar.Add(control, proportion, flags, border)

    table = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_HRULES)
    columns = (
        ("job_id", "jobs.job_id", 100), ("name", "jobs.name", 140),
        ("state", "jobs.state", 90), ("partition", "jobs.partition", 90),
        ("elapsed", "jobs.elapsed", 90), ("nodes", "jobs.nodes", 60),
        ("cpus", "jobs.cpus", 60), ("reason", "jobs.node_or_reason", 120),
    )
    for index, (_key, label_key, width) in enumerate(columns):
        table.InsertColumn(index, t(label_key))
        table.SetColumnWidth(index, width)
    cancel_row = wx.BoxSizer(wx.HORIZONTAL)
    cancel = wx.Button(page, label=t("jobs.cancel"))
    cancel.Enable(False)
    cancel_row.AddStretchSpacer(1)
    cancel_row.Add(cancel, 0, wx.ALIGN_CENTER_VERTICAL)
    empty = wx.StaticText(page, label=t("jobs_outputs.no_active_jobs"))
    empty.Hide()
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(toolbar, 0, wx.EXPAND | wx.ALL, 4)
    sizer.Add(table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    sizer.Add(empty, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    sizer.Add(cancel_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    page.SetSizer(sizer)
    return JobsPage(
        page, sizer, table, tuple(column[0] for column in columns),
        tuple(column[1] for column in columns), refresh, filter_label, filter_field,
        auto_refresh, hide, refresh_label, cancel, empty,
    )


def _cluster_page(wx, notebook) -> ClusterPage:
    page = wx.Panel(notebook)
    heading = wx.StaticText(page, label=t("jobs_outputs.cluster_status"))
    heading.SetFont(wx.Font(wx.FontInfo(11).Bold()))
    status_text = wx.StaticText(page, label="")
    status_text.Wrap(900)
    servers_box = wx.StaticBox(page, label=t("jobs.cluster_servers"))
    servers_sizer = wx.StaticBoxSizer(servers_box, wx.VERTICAL)
    toolbar = wx.BoxSizer(wx.HORIZONTAL)
    refresh = wx.Button(servers_box, label=t("jobs.refresh"))
    raw_status = wx.Button(servers_box, label=t("raw_viewer.raw_server_status"))
    toolbar.Add(refresh, 0, wx.RIGHT, 6)
    toolbar.Add(raw_status, 0)
    servers_text = wx.StaticText(servers_box, label="")
    servers_table = wx.ListCtrl(servers_box, style=wx.LC_REPORT | wx.LC_HRULES)
    for index, key in enumerate(("partition", "free_cpus", "total_cpus", "memory_per_core")):
        servers_table.InsertColumn(index, t(f"jobs.{key}"))
    for index, width in enumerate((150, 120, 80, 100)):
        servers_table.SetColumnWidth(index, width)
    toolbar.AddStretchSpacer(1)
    servers_sizer.Add(toolbar, 0, wx.EXPAND | wx.ALL, 4)
    servers_sizer.Add(servers_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    servers_sizer.Add(servers_table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(heading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Add(status_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Add(servers_sizer, 1, wx.EXPAND | wx.ALL, 8)
    page.SetSizer(sizer)
    return ClusterPage(page, sizer, heading, refresh, raw_status, servers_box, status_text, servers_text, servers_table)


def _details_page(wx, notebook, state: dict[str, Any]) -> DetailsPage:
    page = wx.Panel(notebook)
    sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection = wx.Panel(page)
    no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection_label = wx.StaticText(no_selection, label=t("jobs.no_job_selected"))
    no_selection_hint = wx.StaticText(no_selection, label=t("jobs.no_job_selected_hint"))
    no_selection_sizer.Add(no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    no_selection_sizer.Add(no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    go_to_jobs = wx.Button(no_selection, label=t("jobs.go_to_jobs"))
    no_selection_sizer.Add(go_to_jobs, 0, wx.ALIGN_CENTER)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection.SetSizer(no_selection_sizer)

    content = wx.Panel(page)
    content_sizer = wx.BoxSizer(wx.VERTICAL)
    summary = wx.StaticText(content, label=f"{t('jobs.details_header')} —")
    summary.SetFont(wx.Font(wx.FontInfo(11).Bold()))
    content_sizer.Add(summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    keys = (
        ("job_id", "jobs.job_id"), ("state", "jobs.state"), ("name", "jobs.name"),
        ("partition", "jobs.partition"), ("elapsed", "jobs.elapsed"), ("resources", "jobs.resources"),
        ("workdir", "jobs.workdir"), ("stdout_path", "jobs.stdout"), ("stderr_path", "jobs.stderr"),
    )
    values: dict[str, Any] = {}
    labels: dict[str, Any] = {}
    grid = wx.FlexGridSizer(0, 4, 6, 10)
    grid.AddGrowableCol(1, 1)
    grid.AddGrowableCol(3, 1)
    for key, label_key in keys[:6]:
        label = wx.StaticText(content, label=t(label_key))
        label.SetMinSize(wx.Size(78, -1))
        value = wx.TextCtrl(content, style=wx.TE_READONLY | wx.HSCROLL)
        value.SetValue("—")
        labels[key], values[key] = label, value
        grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(value, 1, wx.EXPAND)
    content_sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    for key, label_key in keys[6:]:
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(content, label=t(label_key))
        label.SetMinSize(wx.Size(78, -1))
        value = wx.TextCtrl(content, style=wx.TE_READONLY | wx.HSCROLL)
        value.SetValue("—")
        labels[key], values[key] = label, value
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(value, 1, wx.EXPAND)
        content_sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    warning = wx.StaticText(content, label="")
    warning.Wrap(900)
    warning.Hide()
    content_sizer.Add(warning, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    content_sizer.Add(wx.StaticLine(content), 0, wx.EXPAND | wx.ALL, 8)
    raw_details = wx.Button(content, label=t("raw_viewer.raw_job_details"))
    content_sizer.Add(raw_details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    accounting_box = wx.StaticBox(content, label=f"▸ {t('jobs_outputs.accounting_details')}")
    accounting_sizer = wx.StaticBoxSizer(accounting_box, wx.VERTICAL)
    refresh_accounting = wx.Button(accounting_box, label=t("jobs_outputs.refresh_sacct"))
    accounting_table = wx.ListCtrl(accounting_box, style=wx.LC_REPORT | wx.LC_HRULES)
    accounting_column_keys = ("job_id", "state", "elapsed", "max_rss", "alloc_tres", "exit_code")
    accounting_column_labels = {
        "job_id": "jobs.job_id", "state": "jobs.state", "elapsed": "jobs.elapsed",
        "max_rss": "jobs.max_rss", "alloc_tres": "jobs.alloc_tres", "exit_code": "jobs.exit_code",
    }
    for index, key in enumerate(accounting_column_keys):
        accounting_table.InsertColumn(index, t(accounting_column_labels[key]))
    for index, width in enumerate((80, 90, 90, 80, 120, 80)):
        accounting_table.SetColumnWidth(index, width)
    raw_accounting = wx.Button(accounting_box, label=t("raw_viewer.raw_accounting"))
    accounting_row = wx.BoxSizer(wx.HORIZONTAL)
    accounting_row.Add(refresh_accounting, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.Add(raw_accounting, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.AddStretchSpacer(1)
    accounting_warning = wx.StaticText(accounting_box, label="")
    accounting_warning.Wrap(900)
    accounting_warning.Hide()
    accounting_sizer.Add(accounting_row, 0, wx.EXPAND | wx.ALL, 4)
    accounting_sizer.Add(accounting_warning, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    accounting_sizer.Add(accounting_table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    accounting_sizer.SetMinSize(wx.Size(-1, 90))
    content_sizer.Add(accounting_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
    accounting_sizer.ShowItems(False)

    def toggle_accounting(_event=None):
        state["accounting_collapsed"] = not state["accounting_collapsed"]
        collapsed = state["accounting_collapsed"]
        accounting_sizer.ShowItems(not collapsed)
        marker = "▸" if collapsed else "▾"
        accounting_box.SetLabel(f"{marker} {t('jobs_outputs.accounting_details')}")
        content_sizer.Layout()

    accounting_box.Bind(wx.EVT_LEFT_DOWN, toggle_accounting)
    advanced_box = wx.StaticBox(content, label=f"▸ {t('jobs.advanced')}")
    advanced_sizer = wx.StaticBoxSizer(advanced_box, wx.VERTICAL)
    advanced_keys = (
        ("reason", "jobs.reason"), ("script_path", "jobs.script"), ("nodelist", "jobs.nodelist"),
        ("exit_code", "jobs.exit_code"), ("nodes", "jobs.nodes"), ("cpus", "jobs.cpus"),
    )
    for key, label_key in advanced_keys:
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(advanced_box, label=t(label_key))
        label.SetMinSize(wx.Size(90, -1))
        value = wx.TextCtrl(advanced_box, style=wx.TE_READONLY | wx.HSCROLL)
        value.SetValue("—")
        labels[key], values[key] = label, value
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(value, 1, wx.EXPAND)
        advanced_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 4)
    advanced_sizer.ShowItems(False)
    content_sizer.Add(advanced_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

    def toggle_advanced(_event=None):
        state["advanced_collapsed"] = not state["advanced_collapsed"]
        collapsed = state["advanced_collapsed"]
        advanced_sizer.ShowItems(not collapsed)
        marker = "▸" if collapsed else "▾"
        advanced_box.SetLabel(f"{marker} {t('jobs.advanced')}")
        content_sizer.Layout()

    advanced_box.Bind(wx.EVT_LEFT_DOWN, toggle_advanced)
    content.SetSizer(content_sizer)
    content.Hide()
    sizer.Add(no_selection, 1, wx.EXPAND)
    sizer.Add(content, 1, wx.EXPAND)
    page.SetSizer(sizer)
    detail_label_keys = dict(keys)
    detail_label_keys.update(dict(advanced_keys))
    return DetailsPage(
        page, sizer, no_selection, no_selection_label, no_selection_hint, go_to_jobs,
        content, content_sizer, summary, values, labels, detail_label_keys,
        accounting_column_keys, accounting_column_labels, warning, raw_details,
        accounting_box, accounting_sizer, accounting_table, refresh_accounting,
        raw_accounting, accounting_warning, advanced_box, advanced_sizer,
        toggle_accounting, toggle_advanced,
    )


def _files_page(wx, notebook, *, open_main_files, kwargs) -> FilesPage:
    from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
    from hpc_gui.wx_remote_files_view import build_remote_files_panel

    page = wx.Panel(notebook)
    model = WxRemoteDirectoryModel("/")
    sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection = wx.Panel(page)
    no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection_label = wx.StaticText(no_selection, label=t("jobs_outputs.no_selected_job"))
    no_selection_hint = wx.StaticText(no_selection, label=t("jobs_outputs.no_selected_job_files_hint"))
    go_to_jobs = wx.Button(no_selection, label=t("jobs.go_to_jobs"))
    no_selection_sizer.Add(no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    no_selection_sizer.Add(no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    no_selection_sizer.Add(go_to_jobs, 0, wx.ALIGN_CENTER)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection.SetSizer(no_selection_sizer)
    sizer.Add(no_selection, 1, wx.EXPAND)
    header = wx.Panel(page)
    header_sizer = wx.BoxSizer(wx.VERTICAL)
    job_header = wx.StaticText(header, label="")
    workdir_label = wx.StaticText(header, label="")
    header_sizer.Add(job_header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
    header_sizer.Add(workdir_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    open_button = None
    if callable(open_main_files):
        open_button = wx.Button(header, label=t("jobs_outputs.open_main_files"))
        header_sizer.Add(open_button, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    header.SetSizer(header_sizer)
    header.Hide()
    sizer.Add(header, 0, wx.EXPAND)
    remote = kwargs.get("remote_files_callbacks") or {}
    session_state = kwargs.get("session_state")
    session = (session_state or {}).get("session") or {} if isinstance(session_state, dict) else {}
    profile = session.get("profile") or {}
    profile_id = str(profile.get("id", profile.get("profile_id", "")))
    try:
        from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
        navigation_store = navigation_store_for_profile(profile_id) if profile_id else None
    except Exception:
        navigation_store = None
    browser = build_remote_files_panel(
        page, model=model, loader=remote.get("loader"), operation=remote.get("operation"),
        read_text=remote.get("read_text"), open_editor=remote.get("open_editor"),
        open_editor_new_window=remote.get("open_editor_new_window"), run_shell=remote.get("run_shell"),
        chmod=remote.get("chmod"), submit_slurm=kwargs.get("submit_slurm") or remote.get("submit_slurm"),
        operation_supported=remote.get("operation_supported"), chmod_supported=remote.get("chmod_supported"),
        submit_slurm_supported=remote.get("submit_slurm_supported"),
        navigation_store=remote.get("navigation_store") or navigation_store,
        provider_filters=kwargs.get("provider_filters") or remote.get("provider_filters"),
        plugin_filters=remote.get("plugin_filters"),
    )
    sizer.Add(browser, 1, wx.EXPAND)
    browser.Hide()
    page.SetSizer(sizer)
    return FilesPage(page, sizer, model, browser, header, no_selection, no_selection_label,
                     no_selection_hint, go_to_jobs, job_header, workdir_label, open_button)


def _outputs_page(wx, notebook) -> OutputsPage:
    page = wx.Panel(notebook)
    sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection = wx.Panel(page)
    no_selection_sizer = wx.BoxSizer(wx.VERTICAL)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection_label = wx.StaticText(no_selection, label=t("jobs_outputs.no_selected_job"))
    no_selection_hint = wx.StaticText(no_selection, label=t("jobs_outputs.no_selected_job_outputs_hint"))
    go_to_jobs = wx.Button(no_selection, label=t("jobs.go_to_jobs"))
    no_selection_sizer.Add(no_selection_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)
    no_selection_sizer.Add(no_selection_hint, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)
    no_selection_sizer.Add(go_to_jobs, 0, wx.ALIGN_CENTER)
    no_selection_sizer.AddStretchSpacer(1)
    no_selection.SetSizer(no_selection_sizer)
    sizer.Add(no_selection, 1, wx.EXPAND)
    toolbar_panel = wx.Panel(page)
    toolbar = wx.BoxSizer(wx.HORIZONTAL)
    refresh = wx.Button(toolbar_panel, label=t("jobs_outputs.refresh_all"))
    pause = wx.Button(toolbar_panel, label=t("jobs_outputs.pause_all"))
    follow = wx.CheckBox(toolbar_panel, label=t("jobs_outputs.auto_scroll_all"))
    follow.SetValue(True)
    toolbar.Add(refresh, 0, wx.RIGHT, 6)
    toolbar.Add(pause, 0, wx.RIGHT, 6)
    toolbar.Add(follow, 0, wx.ALIGN_CENTER_VERTICAL)
    toolbar.AddStretchSpacer(1)
    toolbar_panel.SetSizer(toolbar)
    sizer.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 4)
    search_panel = wx.Panel(page)
    search_row = wx.BoxSizer(wx.HORIZONTAL)
    search_label = wx.StaticText(search_panel, label=f"{t('jobs_outputs.search')}:")
    search_field = wx.TextCtrl(search_panel, style=wx.TE_PROCESS_ENTER)
    try:
        search_field.SetHint(t("jobs_outputs.search_hint"))
    except Exception:
        pass
    find_next = wx.Button(search_panel, label=t("jobs_outputs.find_next"))
    jump_latest = wx.Button(search_panel, label=t("jobs_outputs.jump_to_latest"))
    open_window = wx.Button(search_panel, label=t("jobs_outputs.open_in_window"))
    show_files = wx.Button(search_panel, label=t("jobs_outputs.show_in_files"))
    for control in (search_label, search_field, find_next, jump_latest, open_window, show_files):
        search_row.Add(control, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
    search_row.AddStretchSpacer(1)
    search_panel.SetSizer(search_row)
    sizer.Add(search_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    channel_notebook = wx.Notebook(page)
    channel_notebook.SetMinSize(wx.Size(-1, 200))
    no_channels = wx.StaticText(channel_notebook, label=t("jobs_outputs.no_channels"))
    sizer.Add(channel_notebook, 1, wx.EXPAND | wx.ALL, 4)
    page.SetSizer(sizer)
    return OutputsPage(
        page, sizer, toolbar_panel, search_panel, no_selection, no_selection_label,
        no_selection_hint, go_to_jobs, refresh, follow, pause, search_field,
        search_label, find_next, jump_latest, open_window, show_files, channel_notebook,
        no_channels, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {},
    )


def build_workspace_views(wx, panel, *, hide_finished, open_main_files, kwargs, state) -> JobsWorkspaceViews:
    """Build and return the widget contracts consumed by Jobs controllers."""
    notebook = wx.Notebook(panel)
    jobs = _jobs_page(wx, notebook, hide_finished)
    cluster = _cluster_page(wx, notebook)
    details = _details_page(wx, notebook, state)
    files = _files_page(wx, notebook, open_main_files=open_main_files, kwargs=kwargs)
    outputs = _outputs_page(wx, notebook)
    for page, key in (
        (jobs.page, "jobs.title"), (cluster.page, "jobs.cluster"),
        (details.page, "jobs.details"), (files.page, "jobs_outputs.files_title"),
        (outputs.page, "jobs_outputs.outputs_title"),
    ):
        notebook.AddPage(page, t(key))
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(notebook, 1, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(root)
    return JobsWorkspaceViews(notebook, jobs, cluster, details, files, outputs)