"""Required GUI surfaces in the packaged runtime smoke contract."""

_PACKAGED_SMOKE_SURFACES = {
    "files_surface": ("hpc_gui.wx_local_files", "hpc_gui.wx_remote_files_view", "hpc_gui.wx_transfer_workspace"),
    "editor_surface": ("hpc_gui.wx_editor_view",),
    "jobs_surface": ("hpc_gui.wx_jobs",),
    "plugin_ansys_surface": ("hpc_gui.wx_plugins_view", "hpc_gui.wx_ansys_view"),
    "diagnostics_updater_surface": ("hpc_gui.core.diagnostics", "hpc_gui.services.app_updater", "hpc_gui.wx_updater_view"),
}

_PACKAGED_SMOKE_CONTROL_SURFACES = {
    "files_controls": (
        ("_embedded_local_files_panel", "_wx_local_controls", ("listing", "path", "refresh_btn")),
        ("_embedded_remote_files_panel", "_wx_remote_controls", ("listing", "path", "btn_refresh")),
        ("embedded_transfers_panel", "_wx_transfer_controls", ("queue", "failed", "completed", "cancel")),
    ),
    "editor_controls": (
        ("_embedded_editor_panel", "_wx_editor_controls", ("editor", "save", "doc_tabs")),
    ),
    "jobs_controls": (
        ("_embedded_jobs_panel", "_wx_jobs_controls", ("jobs", "refresh", "output_search", "output_find_next")),
    ),
}
