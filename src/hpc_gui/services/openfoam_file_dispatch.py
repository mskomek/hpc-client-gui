"""Active API 3 OpenFOAM linter routing for local and SFTP file menus."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from hpc_gui.openfoam_core.local_paths import require_local_path_without_links
from hpc_gui.openfoam_core.limits import MAX_CASE_FILES


def active_linter():
    """Return the exact active Linter plugin after the normal host loader."""
    from hpc_gui.plugins.loader import load_installed_plugins
    from hpc_gui.plugins.trusted_api3 import API3_LINTER_ID

    result = load_installed_plugins()
    return next(
        (plugin for plugin in result.plugins if plugin.manifest.id == API3_LINTER_ID),
        None,
    )


def _supported_name(name: str) -> bool:
    from hpc_gui.plugin_engines.openfoam_lint.api import supports_filename

    return supports_filename(name)


def supports_local_targets(paths) -> bool:
    """Accept bounded dictionary selections or a conventional case folder."""
    selected = tuple(Path(item).expanduser() for item in paths or ())
    if not selected or len(selected) > MAX_CASE_FILES:
        return False
    if len(selected) == 1:
        try:
            safe = require_local_path_without_links(selected[0])
            if safe.is_dir():
                return any(
                    (safe / name).is_dir() and not (safe / name).is_symlink()
                    for name in ("system", "constant", "0", "0.orig")
                )
        except (OSError, ValueError):
            return False
    for path in selected:
        try:
            safe = require_local_path_without_links(path)
            if not safe.is_file() or not _supported_name(safe.name):
                return False
        except (OSError, ValueError):
            return False
    return True


def supports_remote_target(path: str, *, is_directory: bool) -> bool:
    """Accept one SFTP dictionary or a selected remote directory."""
    if (
        not isinstance(path, str)
        or len(path) > 4096
        or not path.startswith("/")
        or path.startswith("//")
        or "\\" in path
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in path)
    ):
        return False
    components = path[1:].split("/")
    if not components or any(part in {"", ".", ".."} for part in components):
        return False
    if is_directory:
        return True
    return _supported_name(PurePosixPath(path).name)


def dispatch_linter(paths, *, host_window=None, session_state=None) -> bool:
    """Re-discover and revalidate the exact plugin at the action boundary."""
    from hpc_gui.services.plugin_menu_actions import dispatch_plugin_menu_action
    from hpc_gui.ui.plugin_menu_qt_host import QtPluginMenuHost

    plugin = active_linter()
    if plugin is None:
        return False
    host = QtPluginMenuHost(
        host_window=host_window,
        initial_paths=tuple(str(path) for path in (paths or ())),
        session_state=session_state,
    )
    return dispatch_plugin_menu_action("openfoam.validate", plugin, host)
