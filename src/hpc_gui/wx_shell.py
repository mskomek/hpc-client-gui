"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os as os
import inspect as inspect
import json as json
import shlex as shlex
from pathlib import Path as Path
from pathlib import PurePosixPath as PurePosixPath
from threading import Event as Event, Thread as Thread

from hpc_gui import __version__ as __version__
from hpc_gui.core.i18n import (
    current_language as current_language,
    load_saved_language as load_saved_language,
    set_language as set_language,
    subscribe_language_change as subscribe_language_change,
    system_default_language as system_default_language,
    t as t,
    unsubscribe_language_change as unsubscribe_language_change,
)
from hpc_gui.core.wx_errors import report_wx_action_error as report_wx_action_error
from hpc_gui.services.directory_comparison import (
    ComparableEntry as ComparableEntry,
    compare_directory_entries as compare_directory_entries,
)
from hpc_gui.services.synchronized_browsing import (
    SyncRoots as SyncRoots,
    local_to_remote as local_to_remote,
    normalize_local_root as normalize_local_root,
    normalize_remote_root as normalize_remote_root,
    remote_to_local as remote_to_local,
)
from hpc_gui.services.transfer_controller import TransferItem as TransferItem
from hpc_gui.services.transfer_session_controller import (
    TransferSessionController as TransferSessionController,
)
from hpc_gui.wx_lifecycle import WxLifecycleController as WxLifecycleController
from hpc_gui.wx_runtime import environment_without_qt_graphics as environment_without_qt_graphics
from hpc_gui.wx_application import run_wx_application as run_wx_application


from hpc_gui.wx_shell_window_support import _flag_bitmap as _flag_bitmap
from hpc_gui.wx_shell_window_support import _WxTrayAdapter as _WxTrayAdapter
from hpc_gui.wx_shell_window_support import _make_tray as _make_tray
from hpc_gui.wx_shell_window_support import _window_work_areas as _window_work_areas
from hpc_gui.wx_shell_window_support import _restore_main_window_state as _restore_main_window_state
from hpc_gui.wx_shell_window_support import _save_main_window_state as _save_main_window_state
from hpc_gui.wx_shell_window_support import _update_shell_status_text as _update_shell_status_text
from hpc_gui.wx_shell_frame import create_shell_frame as create_shell_frame
from hpc_gui.wx_shell_smoke_contract import _PACKAGED_SMOKE_SURFACES as _PACKAGED_SMOKE_SURFACES
from hpc_gui.wx_shell_smoke_contract import (
    _PACKAGED_SMOKE_CONTROL_SURFACES as _PACKAGED_SMOKE_CONTROL_SURFACES,
)
from hpc_gui.wx_shell_smoke_session import (
    _connect_packaged_smoke_session as _connect_packaged_smoke_session,
)
from hpc_gui.wx_shell_fresh_smoke import (
    _run_fresh_user_acceptance as _run_fresh_user_acceptance,
    _fresh_src_leakage as _fresh_src_leakage,
    _fresh_find_button as _fresh_find_button,
    _fresh_click as _fresh_click,
    _fresh_drive_add_dialog as _fresh_drive_add_dialog,
    _fresh_run1_visible_flow as _fresh_run1_visible_flow,
)
from hpc_gui.wx_shell_packaged_smoke import _run_packaged_smoke as _run_packaged_smoke
from hpc_gui.wx_shell_files import _editor_session_key as _editor_session_key
from hpc_gui.wx_shell_files import _editor_action_factory as _editor_action_factory
from hpc_gui.wx_shell_terminal import _run_shell_in_terminal as _run_shell_in_terminal
from hpc_gui.wx_shell_files import _get_editor_manager as _get_editor_manager
from hpc_gui.wx_shell_file_transfer import _destination_exists as _destination_exists
from hpc_gui.wx_shell_file_transfer import _run_file_view_item as _run_file_view_item
from hpc_gui.wx_shell_file_transfer import (
    _call_transfer_with_progress as _call_transfer_with_progress,
)
from hpc_gui.wx_shell_file_transfer import _cancel_transfer_sessions as _cancel_transfer_sessions
from hpc_gui.wx_shell_file_transfer import _verify_transfer_item as _verify_transfer_item
from hpc_gui.wx_shell_file_transfer import (
    _transfer_checksum_requested as _transfer_checksum_requested,
)
from hpc_gui.wx_shell_file_transfer import _start_file_transfers as _start_file_transfers
from hpc_gui.wx_shell_files import _local_files_callbacks as _local_files_callbacks
from hpc_gui.wx_shell_files import _remote_files_callbacks as _remote_files_callbacks
from hpc_gui.wx_shell_jobs import _jobs_callbacks as _jobs_callbacks
from hpc_gui.wx_shell_connections import _connection_callbacks as _connection_callbacks
from hpc_gui.wx_shell_events import _logs_callbacks as _logs_callbacks
from hpc_gui.wx_shell_events import _directories_callbacks as _directories_callbacks
from hpc_gui.wx_shell_events import _select_embedded_page as _select_embedded_page
from hpc_gui.wx_shell_settings import run_wx_update_check as run_wx_update_check
from hpc_gui.wx_shell_dispatch import _dispatch as _dispatch


def main() -> int:
    return run_wx_application(create_shell_frame, _run_packaged_smoke)


__all__ = ["main"]
