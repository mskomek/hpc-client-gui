"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

from functools import partial
from threading import Lock

from hpc_gui.core.i18n import subscribe_language_change, t
from hpc_gui.jobs.output_workspace import (
    DetachedOutput, WxJobsModel, clean_output, show_job_output,
)
from hpc_gui.jobs.workspace_state import create_workspace_state
from hpc_gui.jobs.workspace_views import build_workspace_views
from hpc_gui.jobs.job_rows import parse_job_row as _parse_job_row  # noqa: F401
from hpc_gui.jobs.files_controller import JobFilesBindings, JobFilesController
from hpc_gui.jobs.details_presenter import JobDetailsPresenter, JobDetailsViewBindings
from hpc_gui.jobs.details_controller import JobDetailsBindings, JobDetailsController
from hpc_gui.jobs.job_list_controller import JobListBindings, JobListController
from hpc_gui.jobs.jobs_refresh_controller import JobsRefreshBindings, JobsRefreshController
from hpc_gui.jobs.job_selection_controller import JobSelectionBindings, JobSelectionController
from hpc_gui.jobs.cancel_job_controller import CancelJobBindings, CancelJobController
from hpc_gui.jobs.provider_status_controller import (
    ProviderStatusBindings, ProviderStatusController,
)
from hpc_gui.jobs.workspace_localization import (
    JobsLocalizationBindings, JobsLocalizationController,
)
from hpc_gui.jobs.output_panel_interactions import (
    OutputPanelInteractionBindings, OutputPanelInteractions,
)
from hpc_gui.jobs.manual_output_followers import (
    ManualFollowerBindings, ManualOutputFollowers,
)
from hpc_gui.jobs.output_request_coordinator import OutputRequestBindings, OutputRequestCoordinator
from hpc_gui.jobs.output_channels_controller import OutputChannelBindings, OutputChannelController
from hpc_gui.jobs.output_refresh_controller import OutputRefreshBindings, OutputRefreshController
from hpc_gui.jobs.workspace_lifecycle import (
    JobsWorkspaceLifecycle, WorkspaceLifecycleActions, WorkspaceLifecycleBindings,
)
from hpc_gui.jobs.workspace_callbacks import normalize_provider_callbacks
from hpc_gui.jobs.workspace_navigation import go_to_jobs, select_workspace_page
from hpc_gui.jobs.workspace_test_access import expose_workspace_access
from hpc_gui.config import storage
from hpc_gui.services.output_channel_resolver import OutputResolver
from hpc_gui.wx_host import make_host



_JOB_TABLE_COLUMNS = ("job_id", "name", "state", "partition", "elapsed", "nodes", "cpus", "reason")

def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, cancel, lifecycle, final_state, generation, embedded, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, list_job_files=None, output_channel_defs=None, **kwargs):
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    from hpc_gui.wx_raw_viewer import show_raw_viewer

    callbacks = normalize_provider_callbacks(
        refresh_accounting=refresh_sacct, show_job_details=show_job_details,
        refresh_cluster_status=refresh_lssrv, list_job_files=list_job_files,
        kwargs=kwargs,
    )
    refresh_job_metadata = kwargs.get("refresh_job_metadata")
    open_main_files = kwargs.get("open_main_files")
    has_status_capability = kwargs.get("has_status_capability")
    model = model or WxJobsModel()
    if lifecycle is not None and model.completion_notify is None:
        model.completion_notify = lambda job_id, message: lifecycle.notify_job(message, job_id=job_id)
    host, finish = make_host(parent, title=t("jobs.title"), size=(1000, 700), embedded=embedded)
    panel = wx.Panel(host)
    state = create_workspace_state(output_channel_defs, kwargs)
    views = build_workspace_views(
        wx, panel, hide_finished=storage.get_hide_finished_jobs_enabled(),
        open_main_files=open_main_files, kwargs=kwargs, state=state,
    )
    notebook = views.notebook
    output_resolver = OutputResolver()
    _remote_cbs = kwargs.get("remote_files_callbacks") or {}
    _remote_reader = kwargs.get("read_remote_path") or _remote_cbs.get("read_text")
    _remote_statter = kwargs.get("stat_remote_path")
    detail_keys = tuple(views.details.detail_label_keys.items())
    _select_inner_page = partial(select_workspace_page, notebook)
    _go_to_jobs = partial(go_to_jobs, notebook, views.jobs.page)

    views.details.go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)

    views.files.go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)
    views.outputs.go_to_jobs.Bind(wx.EVT_BUTTON, _go_to_jobs)

    output_channel_controller = OutputChannelController(OutputChannelBindings(
        wx=wx, state=state, model=model, resolver=output_resolver,
        notebook=views.outputs.channel_notebook, no_channels_label=views.outputs.no_channels_label,
        channels=views.outputs.channels, paths=views.outputs.channel_paths, paused=views.outputs.channel_paused,
        follow=views.outputs.channel_follow, pause_buttons=views.outputs.channel_pause_buttons,
        status=views.outputs.channel_status, status_keys=views.outputs.channel_status_keys,
        path_labels=views.outputs.channel_path_labels, offsets=views.outputs.channel_offsets,
        in_flight=views.outputs.channel_in_flight, waiting=views.outputs.channel_waiting,
    ))
    _ensure_output_tabs = output_channel_controller.ensure_tabs
    _resolve_output_channels = output_channel_controller.resolve_channels
    _set_output_channel_status = output_channel_controller.set_status

    def _update_outputs_visibility():
        has_job = bool(state.get("selected_job"))
        views.outputs.no_selection_panel.Show(not has_job)
        views.outputs.toolbar_panel.Show(has_job)
        views.outputs.search_panel.Show(has_job)
        views.outputs.channel_notebook.Show(has_job)
        views.outputs.sizer.Layout()

    state_lock = Lock()
    files_controller = JobFilesController(JobFilesBindings(
        wx=wx, model=model, state=state, browser=views.files.browser, directory_model=views.files.model,
        no_selection_panel=views.files.no_selection_panel, header=views.files.header, browser_sizer=views.files.sizer,
        job_header=views.files.job_header, workdir_label=views.files.workdir_label,
        open_main_files=open_main_files,
    ))
    _files_directory = files_controller.directory
    _update_files_header = files_controller.update_header
    _show_files_selected_state = files_controller.show_selected_state
    _open_in_main_files = files_controller.open_main_files
    _reset_files_browser = files_controller.reset_browser
    _navigate_files_to_workdir = files_controller.navigate_to_workdir
    if views.files.open_main_files is not None:
        views.files.open_main_files.Bind(wx.EVT_BUTTON, _open_in_main_files)
    timer = wx.Timer(host)

    def post(callback, *args):
        try:
            if wx.GetApp() is not None:
                wx.CallAfter(callback, *args)
        except BaseException:
            pass

    provider_status_controller = ProviderStatusController(ProviderStatusBindings(
        state=state, state_lock=state_lock, kwargs=kwargs,
        refresh_status=callbacks.refresh_cluster_status,
        has_status_capability=has_status_capability, generation=generation,
        post=post, table=views.cluster.servers_table, servers_text=views.cluster.servers_text,
        servers_box=views.cluster.servers_box, status_text=views.cluster.status_text,
        refresh_button=views.cluster.refresh, raw_button=views.cluster.raw_status,
        page_sizer=views.cluster.sizer, host=host, show_raw_viewer=show_raw_viewer,
    ))
    _refresh_raw_server_status = provider_status_controller.refresh_raw_status
    _open_raw_server_status = provider_status_controller.open_raw_status
    _provider_connected = provider_status_controller.provider_connected
    _provider_status_supported = provider_status_controller.provider_status_supported
    _render_cluster_servers = provider_status_controller.render_servers
    _refresh_provider_status = provider_status_controller.refresh_provider_status
    _toggle_cluster_servers = provider_status_controller.toggle_cluster_servers

    output_requests = OutputRequestCoordinator(OutputRequestBindings(
        state=state, selected_job_store=model.selected_job_store,
        lock=state_lock, session_generation=generation,
    ))
    _output_owner = output_requests.owner
    _output_owner_is_current = output_requests.is_current
    _begin_output_request = output_requests.begin
    _finish_output_request = output_requests.finish

    output_refresh_controller = OutputRefreshController(OutputRefreshBindings(
        state=state, state_lock=state_lock, model=model,
        begin_request=_begin_output_request, finish_request=_finish_output_request,
        output_owner=_output_owner, set_status=_set_output_channel_status,
        ensure_tabs=_ensure_output_tabs, resolve_channels=_resolve_output_channels,
        update_visibility=_update_outputs_visibility, post=post,
        read_output=read_output, remote_reader=_remote_reader, remote_statter=_remote_statter,
        kwargs=kwargs, channels=views.outputs.channels, paused=views.outputs.channel_paused,
        follow=views.outputs.channel_follow, offsets=views.outputs.channel_offsets,
        waiting=views.outputs.channel_waiting, status=views.outputs.channel_status,
        pause_buttons=views.outputs.channel_pause_buttons, auto_scroll=views.outputs.follow,
        refresh_button=views.outputs.refresh, pause_all_button=views.outputs.pause,
    ))
    _refresh_single_channel = output_refresh_controller.refresh_single_channel
    refresh_outputs_tab = output_refresh_controller.refresh_outputs_tab
    toggle_outputs_pause = output_refresh_controller.toggle_pause
    output_channel_controller.bindings.refresh_single = _refresh_single_channel
    manual_followers = ManualOutputFollowers(ManualFollowerBindings(
        state=state, model=model, host=host, lifecycle=lifecycle,
        files_browser=views.files.browser, remote_reader=_remote_reader,
        remote_statter=_remote_statter, channel_paths=views.outputs.channel_paths,
        channels=views.outputs.channels, resolve_channels=_resolve_output_channels,
        ensure_tabs=_ensure_output_tabs, refresh_single=_refresh_single_channel,
        refresh_outputs=refresh_outputs_tab, select_page=_select_inner_page,
        outputs_page=views.outputs.page,
    ))
    _on_follow_file = manual_followers.follow_file
    _remove_manual_follower = manual_followers.remove
    views.files.browser._follow_callback = _on_follow_file

    # Table filtering and row rendering are owned by a framework boundary.
    job_list_controller = JobListController(JobListBindings(
        state=state, table=views.jobs.table, page_sizer=views.jobs.sizer,
        empty_label=views.jobs.empty_label, cancel_button=views.jobs.cancel,
        hide_finished=views.jobs.hide_finished, filter_field=views.jobs.filter_field,
        column_keys=_JOB_TABLE_COLUMNS, wx=wx,
    ))
    render_items = job_list_controller.render_items
    _apply_filter = job_list_controller.apply_filter
    _refresh_job_table = job_list_controller.refresh_rows
    _on_column_click = job_list_controller.on_column_click
    _on_filter_changed = job_list_controller.on_filter_changed
    _toggle_hide_finished = job_list_controller.toggle_hide_finished

    jobs_refresh_controller = JobsRefreshController(JobsRefreshBindings(
        list_jobs=list_jobs, state=state, state_lock=state_lock, model=model,
        post=post, generation=generation, refresh_label=views.jobs.refresh_label,
        render_items=render_items, cancel_button=views.jobs.cancel, cancel=cancel,
        final_state=final_state,
    ))
    refresh_jobs = jobs_refresh_controller.refresh_jobs

    details_presenter = JobDetailsPresenter(JobDetailsViewBindings(
        state=state, model=model, no_selection_panel=views.details.no_selection_panel,
        content_panel=views.details.content_panel, page_sizer=views.details.sizer,
        content_sizer=views.details.content_sizer, summary=views.details.summary,
        values=views.details.values, warning=views.details.warning,
        accounting_table=views.details.accounting_table, accounting_warning=views.details.accounting_warning,
    ))
    _show_details_content = details_presenter.show_content
    _clear_detail_values = details_presenter.clear_values
    _update_summary_header = details_presenter.update_summary_header
    _set_detail = details_presenter.set_field
    _show_parsed_details = details_presenter.show_parsed_details

    details_controller = JobDetailsController(JobDetailsBindings(
        wx=wx, state=state, state_lock=state_lock, model=model, post=post,
        refresh_metadata=refresh_job_metadata, refresh_accounting_callback=callbacks.refresh_accounting,
        show_details_callback=callbacks.show_job_details, generation=generation, kwargs=kwargs,
        host=host, show_raw_viewer=show_raw_viewer, presenter=details_presenter,
        refresh_outputs=refresh_outputs_tab, update_files_header=_update_files_header,
        navigate_files=_navigate_files_to_workdir, accounting_button=views.details.refresh_accounting,
        accounting_sizer=views.details.accounting_sizer, accounting_table=views.details.accounting_table,
        accounting_warning=views.details.accounting_warning, details_sizer=views.details.sizer,
        details_warning=views.details.warning,
    ))
    _refresh_job_metadata = details_controller.refresh_job_metadata
    _refresh_raw_job_details = details_controller.refresh_raw_job_details
    _open_raw_job_details = details_controller.open_raw_job_details
    _refresh_raw_accounting = details_controller.refresh_raw_accounting
    _open_raw_accounting = details_controller.open_raw_accounting
    _refresh_sacct = details_controller.refresh_accounting
    _show_job_details = details_controller.show_job_details

    # Selection and bulk-record actions are composed after cancel is bound.

    # --- Refresh jobs -------------------------------------------------------
    # The scheduler refresh lifecycle lives in JobsRefreshController.

    # Provider status loading is owned by ProviderStatusController.

    cancel_controller = CancelJobController(CancelJobBindings(
        wx=wx, state=state, model=model, kwargs=kwargs, cancel=cancel,
        final_state=final_state, post=post, refresh_jobs=refresh_jobs,
        cancel_button=views.jobs.cancel,
    ))
    cancel_job = cancel_controller.cancel_job

    selection_controller = JobSelectionController(JobSelectionBindings(
        wx=wx, state=state, model=model, table=views.jobs.table, kwargs=kwargs,
        cancel=cancel, cancel_job=cancel_job, refresh_jobs=refresh_jobs,
        ensure_output_tabs=_ensure_output_tabs,
        update_outputs_visibility=_update_outputs_visibility,
        clear_detail_values=_clear_detail_values,
        show_details_content=_show_details_content,
        reset_files_browser=_reset_files_browser,
        show_files_selected_state=_show_files_selected_state,
        update_files_header=_update_files_header,
        show_parsed_details=_show_parsed_details,
        update_summary_header=_update_summary_header, detail_values=views.details.values,
        refresh_accounting=_refresh_sacct, show_job_details=_show_job_details,
        refresh_metadata=_refresh_job_metadata,
        navigate_files=_navigate_files_to_workdir,
        refresh_outputs=refresh_outputs_tab, cancel_button=views.jobs.cancel,
    ))
    _clear_job_selection = selection_controller.clear_job_selection
    _clear_job_row_selection = selection_controller.clear_job_row_selection
    _on_jobs_left_down = selection_controller.on_jobs_left_down
    _on_job_item_deselected = selection_controller.on_job_item_deselected
    select_job = selection_controller.select_job
    _on_jobs_right_click = selection_controller.on_jobs_right_click
    _delete_selected_details = selection_controller.delete_selected_details

    localization_controller = JobsLocalizationController(JobsLocalizationBindings(
        host=host, state=state, jobs=views.jobs.table, notebook=notebook,
        filter_label=views.jobs.filter_label, filter_field=views.jobs.filter_field,
        refresh_button=views.jobs.refresh, auto_refresh=views.jobs.auto_refresh,
        hide_finished=views.jobs.hide_finished, cancel_button=views.jobs.cancel,
        jobs_empty_label=views.jobs.empty_label, no_selection_label=views.details.no_selection_label,
        no_selection_hint=views.details.no_selection_hint, go_to_jobs=views.details.go_to_jobs,
        files_no_selection_label=views.files.no_selection_label,
        files_no_selection_hint=views.files.no_selection_hint,
        files_go_to_jobs=views.files.go_to_jobs,
        files_open_main_button=views.files.open_main_files,
        outputs_no_selection_label=views.outputs.no_selection_label,
        outputs_no_selection_hint=views.outputs.no_selection_hint,
        outputs_go_to_jobs=views.outputs.go_to_jobs, detail_keys=detail_keys,
        detail_labels=views.details.labels, details_warning=views.details.warning,
        raw_details_button=views.details.raw_details, accounting_box=views.details.accounting_box,
        accounting_button=views.details.refresh_accounting, accounting_table=views.details.accounting_table,
        accounting_column_keys=views.details.accounting_column_keys,
        accounting_column_labels=views.details.accounting_column_labels,
        accounting_warning=views.details.accounting_warning,
        raw_accounting_button=views.details.raw_accounting,
        cluster_heading=views.cluster.heading, cluster_status_text=views.cluster.status_text,
        cluster_servers_box=views.cluster.servers_box,
        cluster_refresh_button=views.cluster.refresh,
        cluster_raw_button=views.cluster.raw_status,
        cluster_servers_table=views.cluster.servers_table, advanced_box=views.details.advanced_box,
        update_summary_header=_update_summary_header,
        update_files_header=_update_files_header, files_header=views.files.header,
        files_no_selection_panel=views.files.no_selection_panel,
        outputs_refresh_button=views.outputs.refresh, outputs_follow=views.outputs.follow,
        outputs_pause_button=views.outputs.pause, output_channels=views.outputs.channels,
        output_channel_notebook=views.outputs.channel_notebook,
        output_channel_path_labels=views.outputs.channel_path_labels,
        output_channel_pause_buttons=views.outputs.channel_pause_buttons,
        output_channel_paused=views.outputs.channel_paused,
        output_channel_status=views.outputs.channel_status,
        output_channel_status_keys=views.outputs.channel_status_keys,
        output_no_channels_label=views.outputs.no_channels_label,
    ))
    refresh_labels = localization_controller.refresh_labels

    lifecycle_actions = WorkspaceLifecycleActions(
        ensure_output_tabs=_ensure_output_tabs,
        update_outputs_visibility=_update_outputs_visibility,
        set_output_channel_status=_set_output_channel_status,
        clear_detail_values=_clear_detail_values,
        show_details_content=_show_details_content,
        reset_files_browser=_reset_files_browser,
        show_files_selected_state=_show_files_selected_state,
        update_files_header=_update_files_header,
        refresh_provider_status=_refresh_provider_status,
        refresh_jobs=refresh_jobs,
        show_job_details=_show_job_details,
        refresh_job_metadata=_refresh_job_metadata,
        navigate_files_to_workdir=_navigate_files_to_workdir,
        refresh_outputs_tab=refresh_outputs_tab,
        show_parsed_details=_show_parsed_details,
        update_summary_header=_update_summary_header,
        refresh_accounting=_refresh_sacct,
    )
    lifecycle_controller = JobsWorkspaceLifecycle(WorkspaceLifecycleBindings(
        wx=wx, host=host, state=state, state_lock=state_lock, timer=timer,
        notebook=notebook, outputs_page=views.outputs.page, auto_refresh=views.jobs.auto_refresh,
        model=model, embedded=embedded, refresh_labels=refresh_labels,
        filter_field=views.jobs.filter_field, search_field=views.outputs.search_field, cancel_button=views.jobs.cancel,
        outputs_pause_button=views.outputs.pause, outputs_no_selection_panel=views.outputs.no_selection_panel,
        files_browser=views.files.browser, output_channel_pause_buttons=views.outputs.channel_pause_buttons,
        output_channel_paused=views.outputs.channel_paused, output_channel_status=views.outputs.channel_status,
        remote_callbacks=_remote_cbs, kwargs=kwargs, actions=lifecycle_actions,
    ))
    _on_notebook_page_changed = lifecycle_controller.on_page_changed
    tick = lifecycle_controller.tick

    output_panel_interactions = OutputPanelInteractions(OutputPanelInteractionBindings(
        wx=wx, state=state, model=model, search_field=views.outputs.search_field,
        channel_notebook=views.outputs.channel_notebook, output_channels=views.outputs.channels,
        output_channel_paths=views.outputs.channel_paths, host=host, lifecycle=lifecycle,
        read_output=read_output, remote_reader=_remote_reader,
        remote_statter=_remote_statter, files_workdir_label=views.files.workdir_label,
        files_browser=views.files.browser,
        show_files_selected_state=_show_files_selected_state,
        files_page=views.files.page, select_inner_page=_select_inner_page,
    ))
    output_panel_interactions.bind({
        "find_next": views.outputs.find_next, "jump_latest": views.outputs.jump_latest,
        "open_window": views.outputs.open_window, "show_files": views.outputs.show_files,
    })
    _get_active_channel_textctrl = output_panel_interactions.active_channel_text
    _on_search = output_panel_interactions.search
    _on_find_next = output_panel_interactions.find_next
    _on_jump_latest = output_panel_interactions.jump_latest
    _on_open_in_window = output_panel_interactions.open_in_window
    open_detached = output_panel_interactions.open_detached
    _on_show_in_files = output_panel_interactions.show_in_files

    # --- Bind events --------------------------------------------------------
    views.jobs.table.Bind(wx.EVT_LEFT_DOWN, _on_jobs_left_down)
    views.jobs.table.Bind(wx.EVT_LIST_ITEM_SELECTED, select_job)
    views.jobs.table.Bind(wx.EVT_LIST_ITEM_DESELECTED, _on_job_item_deselected)
    views.jobs.table.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, _on_jobs_right_click)
    try:
        views.jobs.table.Bind(wx.EVT_LIST_COL_CLICK, _on_column_click)
    except Exception:
        pass
    views.jobs.refresh.Bind(wx.EVT_BUTTON, refresh_jobs)
    views.jobs.hide_finished.Bind(wx.EVT_CHECKBOX, _toggle_hide_finished)
    views.jobs.cancel.Bind(wx.EVT_BUTTON, cancel_job)
    views.details.refresh_accounting.Bind(wx.EVT_BUTTON, _refresh_sacct)
    views.details.raw_accounting.Bind(wx.EVT_BUTTON, _open_raw_accounting)
    views.details.raw_details.Bind(wx.EVT_BUTTON, _open_raw_job_details)
    views.cluster.raw_status.Bind(wx.EVT_BUTTON, _open_raw_server_status)
    views.cluster.refresh.Bind(wx.EVT_BUTTON, _refresh_provider_status)
    views.jobs.filter_field.Bind(wx.EVT_TEXT, _on_filter_changed)
    try:
        views.jobs.filter_field.Bind(wx.EVT_TEXT_ENTER, _on_filter_changed)
    except Exception:
        pass
    views.outputs.refresh.Bind(wx.EVT_BUTTON, lambda e: refresh_outputs_tab(force=True))
    views.outputs.pause.Bind(wx.EVT_BUTTON, toggle_outputs_pause)

    # Output search and secondary actions are owned by OutputPanelInteractions.

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_notebook_page_changed)

    timer.Start(1000)
    host.Bind(wx.EVT_TIMER, tick, timer)
    host.Bind(wx.EVT_ICONIZE, lifecycle_controller.iconized)
    host.bind_host_close(lifecycle_controller.close)
    if lifecycle is not None:
        # close() is the single owner of this embedded page's teardown.
        # A second bound host.Hide cleanup runs after Destroy() and raises
        # RuntimeError on the deleted wx Panel (W55 packaged shutdown).
        lifecycle.register_cleanup(lifecycle_controller.close)
    subscribe_language_change(refresh_labels)

    expose_workspace_access(
        host, model=model, state=state, views=views,
        callbacks={
            "open_detached_output": open_detached,
            "refresh_jobs": refresh_jobs,
            "cancel_job": cancel_job,
            "refresh_outputs": lambda: refresh_outputs_tab(force=True),
            "refresh_accounting": _refresh_sacct,
            "refresh_raw_job_details": _refresh_raw_job_details,
            "refresh_raw_accounting": _refresh_raw_accounting,
            "refresh_raw_server_status": _refresh_raw_server_status,
            "show_job_details": _show_job_details,
            "navigate_files": _navigate_files_to_workdir,
            "refresh_outputs_tab": refresh_outputs_tab,
            "set_session": lifecycle_controller.set_session,
            "toggle_cluster_servers": _toggle_cluster_servers,
            "delete_details": _delete_selected_details,
            "sort_jobs": _on_column_click,
            "open_output_window": _on_open_in_window,
            "go_to_jobs": _go_to_jobs,
            "show_details_content": _show_details_content,
        },
    )
    host.Bind(wx.EVT_WINDOW_DESTROY, lifecycle_controller.on_destroy)
    _update_outputs_visibility()
    _show_files_selected_state(False)
    _refresh_provider_status()
    refresh_jobs()
    finish()
    return host


def build_jobs_panel(
    parent, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None,
    cancel=None, lifecycle=None, final_state=None, generation=None,
    refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs,
):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_jobs(
        parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel,
        lifecycle=lifecycle, final_state=final_state, generation=generation,
        embedded=True, refresh_sacct=refresh_sacct,
        show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs,
    )


def show_jobs(
    parent=None, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None,
    cancel=None, lifecycle=None, final_state=None, generation=None,
    refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs,
) -> int:
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as error:
        raise RuntimeError("wxPython is not installed") from error
    _build_jobs(
        parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel,
        lifecycle=lifecycle, final_state=final_state, generation=generation,
        embedded=False, refresh_sacct=refresh_sacct,
        show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs,
    )
    return wx.ID_OK


__all__ = ["DetachedOutput", "WxJobsModel", "clean_output", "show_job_output", "show_jobs", "build_jobs_panel"]
