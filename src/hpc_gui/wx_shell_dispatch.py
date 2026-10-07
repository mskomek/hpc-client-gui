"""wx shell dispatch workflows."""
from __future__ import annotations

from hpc_gui.core.wx_errors import report_wx_action_error
from hpc_gui.wx_shell_connections import _connection_callbacks
from hpc_gui.wx_shell_events import _directories_callbacks
from hpc_gui.wx_shell_files import _get_editor_manager
from hpc_gui.wx_shell_jobs import _jobs_callbacks
from hpc_gui.wx_shell_files import _local_files_callbacks
from hpc_gui.wx_shell_events import _logs_callbacks
from hpc_gui.wx_shell_events import _select_embedded_page
from hpc_gui.wx_shell_settings import run_wx_update_check


def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id == "APP-HELP":
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-SETTINGS":
        from hpc_gui.wx_settings_view import show_settings
        try:
            # W37 SETTINGS-PERSIST-001: inject the real settings/profile
            # state plus a real persistence callback. Apply without
            # persistence is forbidden.
            from hpc_gui.wx_settings import build_model_from_storage, persist_model_snapshot
            _model = build_model_from_storage(
                apply=lambda snapshot: persist_model_snapshot(snapshot),
            )
            show_settings(parent=parent, model=_model)
        except Exception as exc:
            # W02 ERROR-GOV: a settings failure must be visible, never silent.
            report_wx_action_error(parent, area="SETTINGS", message_key="settings.open_failed", exc=exc)
    elif command_id == "APP-UPDATE-CHECK":
        # W41 UPDATER-ROUTE-001/002: the visible menu action shares the single
        # authoritative update-check controller so CHECKING always reaches
        # UP_TO_DATE / UPDATE_AVAILABLE / FAILED via the real service.
        # WxUpdateDialog is the canonical owner for this branch (W02 TRACE).
        try:
            from hpc_gui.wx_updater_view import WxUpdateDialog as _WxUpdateDialogOwner

            _ = _WxUpdateDialogOwner
            run_wx_update_check(parent)
        except Exception as exc:
            # W02 ERROR-GOV: an updater failure must be visible, never silent.
            report_wx_action_error(parent, area="UPDATE", message_key="updates.open_failed", exc=exc)
    elif command_id == "APP-SEND-LOGS":
        from hpc_gui.wx_send_logs_view import show_send_logs
        try:
            show_send_logs(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: a diagnostics failure must be visible, never silent.
            report_wx_action_error(parent, area="LOGS", message_key="logs.send_open_failed", exc=exc)
    elif command_id == "APP-ABOUT":
        from hpc_gui.wx_about import show_about
        try:
            show_about(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: an about-dialog failure must be visible, never silent.
            # NOTE: the success path still uses the real wx.Dialog (see W01
            # FIX-W01-002); only the failure path reports through the helper.
            report_wx_action_error(parent, area="ABOUT", message_key="about.open_failed", exc=exc)
    elif command_id in {"PLUGIN-BROWSE", "PLUGIN-MANAGE", "PLUGIN-UPDATES"}:
        try:
            from hpc_gui.wx_plugins_view import show_plugins
            # Map to initial tab
            tab_map = {"PLUGIN-BROWSE": "discover", "PLUGIN-MANAGE": "installed", "PLUGIN-UPDATES": "updates"}
            initial = tab_map.get(command_id, "discover")
            # Try to pass initial_tab if supported
            try:
                show_plugins(parent=parent, initial_tab=initial)
            except TypeError:
                show_plugins(parent=parent)
        except Exception as exc:
            # W02 ERROR-GOV: a plugin-manager failure must be visible, never silent.
            report_wx_action_error(parent, area="PLUGIN", message_key="plugins.open_failed", exc=exc)
    elif command_id == "PLUGIN-REQUEST":
        try:
            from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
            import webbrowser
            request_error = None
            try:
                opened = bool(webbrowser.open(PLUGIN_REQUEST_URL))
            except Exception as exc:
                opened = False
                request_error = exc
        except Exception as exc:
            opened = False
            request_error = exc
        if not opened:
            # W02 ERROR-GOV (DEF-W02-002): webbrowser.open() returning False
            # opens no browser and raises nothing; that silent no-op must
            # still produce a visible, diagnosable error like the Qt surface.
            report_wx_action_error(
                parent, area="PLUGIN", message_key="plugins.request_plugin_failed", exc=request_error
            )
    elif command_id == "APP-CONNECT":
        if _select_embedded_page(session_state, parent, "APP-CONNECT"):
            return
        from hpc_gui.wx_connection import show_connection

        _conn = _connection_callbacks(session_state, parent, lifecycle)
        show_connection(parent, **_conn)
    elif command_id == "NAV-FILES":
        if _select_embedded_page(session_state, parent, "NAV-FILES"):
            return
        from hpc_gui.wx_local_files import show_local_files

        _kwargs = _local_files_callbacks(session_state, parent, lifecycle)
        show_local_files(parent, **_kwargs)
    elif command_id == "NAV-DIRECTORIES":
        if _select_embedded_page(session_state, parent, "NAV-DIRECTORIES"):
            return
        from hpc_gui.wx_directories_view import show_directories

        show_directories(parent, **_directories_callbacks(session_state, parent, lifecycle))
    elif command_id == "NAV-LOGS":
        if _select_embedded_page(session_state, parent, "NAV-LOGS"):
            return
        from hpc_gui.wx_logs_view import show_logs

        _kwargs = _logs_callbacks(session_state, parent, lifecycle)
        show_logs(parent, **_kwargs)
    elif command_id == "NAV-EDITOR":
        if _select_embedded_page(session_state, parent, "NAV-EDITOR"):
            return
        _get_editor_manager(session_state, parent, lifecycle).open_primary("", "", is_local=False)
    elif command_id == "NAV-TERMINAL":
        if _select_embedded_page(session_state, parent, "NAV-TERMINAL"):
            return
        from hpc_gui.wx_terminal import show_terminal

        session = (session_state or {}).get("session") or {}
        show_terminal(parent, ssh=session.get("ssh"), lifecycle=lifecycle)
    elif command_id == "NAV-JOBS":
        if _select_embedded_page(session_state, parent, "NAV-JOBS"):
            return
        from hpc_gui.wx_jobs import show_jobs

        _kwargs = _jobs_callbacks(session_state, parent, lifecycle)
        # show_jobs expects lifecycle, list_jobs, read_output, cancel, final_state, generation
        show_jobs(parent, **_kwargs)
    elif command_id in {"PLUGIN-ANSYS-LINTER", "APP-ANSYS"}:
        from hpc_gui.wx_ansys_view import show_ansys_lint

        show_ansys_lint(parent, lifecycle=lifecycle)
