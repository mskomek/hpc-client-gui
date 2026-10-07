"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os
import inspect
import json
import shlex
from pathlib import Path
from pathlib import PurePosixPath
from threading import Event, Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.core.wx_errors import report_wx_action_error
from hpc_gui.services.directory_comparison import ComparableEntry, compare_directory_entries
from hpc_gui.services.synchronized_browsing import SyncRoots, local_to_remote, normalize_local_root, normalize_remote_root, remote_to_local
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui.wx_runtime import environment_without_qt_graphics
from hpc_gui.wx_application import run_wx_application


from hpc_gui.wx_shell_window_support import _flag_bitmap


from hpc_gui.wx_shell_window_support import _WxTrayAdapter


from hpc_gui.wx_shell_window_support import _make_tray


from hpc_gui.wx_shell_window_support import _window_work_areas


from hpc_gui.wx_shell_window_support import _restore_main_window_state


from hpc_gui.wx_shell_window_support import _save_main_window_state


from hpc_gui.wx_shell_window_support import _update_shell_status_text


from hpc_gui.wx_shell_frame import create_shell_frame


from hpc_gui.wx_shell_smoke_contract import _PACKAGED_SMOKE_SURFACES

from hpc_gui.wx_shell_smoke_contract import _PACKAGED_SMOKE_CONTROL_SURFACES


from hpc_gui.wx_shell_smoke_session import _connect_packaged_smoke_session




from hpc_gui.wx_shell_fresh_smoke import _run_fresh_user_acceptance


from hpc_gui.wx_shell_fresh_smoke import _fresh_src_leakage


from hpc_gui.wx_shell_fresh_smoke import _fresh_find_button


from hpc_gui.wx_shell_fresh_smoke import _fresh_click


from hpc_gui.wx_shell_fresh_smoke import _fresh_drive_add_dialog


from hpc_gui.wx_shell_fresh_smoke import _fresh_run1_visible_flow


from hpc_gui.wx_shell_packaged_smoke import _run_packaged_smoke


def main() -> int:
    return run_wx_application(create_shell_frame, _run_packaged_smoke)


from hpc_gui.wx_shell_files import _editor_session_key


from hpc_gui.wx_shell_files import _editor_action_factory


from hpc_gui.wx_shell_terminal import _run_shell_in_terminal


from hpc_gui.wx_shell_files import _get_editor_manager


from hpc_gui.wx_shell_file_transfer import _destination_exists


from hpc_gui.wx_shell_file_transfer import _run_file_view_item


from hpc_gui.wx_shell_file_transfer import _call_transfer_with_progress


from hpc_gui.wx_shell_file_transfer import _cancel_transfer_sessions


from hpc_gui.wx_shell_file_transfer import _verify_transfer_item


from hpc_gui.wx_shell_file_transfer import _transfer_checksum_requested


from hpc_gui.wx_shell_file_transfer import _start_file_transfers


from hpc_gui.wx_shell_files import _local_files_callbacks


from hpc_gui.wx_shell_files import _remote_files_callbacks


from hpc_gui.wx_shell_jobs import _jobs_callbacks


from hpc_gui.wx_shell_connections import _connection_callbacks


from hpc_gui.wx_shell_events import _logs_callbacks


from hpc_gui.wx_shell_events import _directories_callbacks


from hpc_gui.wx_shell_events import _select_embedded_page


from hpc_gui.wx_shell_settings import run_wx_update_check


from hpc_gui.wx_shell_dispatch import _dispatch


__all__ = ["main"]
