"""Shared patchable dependencies for the main-window behavior mixins."""

from hpc_gui.config.storage import (
    get_last_seen_changelog_version,
    get_sbatch_follow_mode,
    set_last_seen_changelog_version,
)
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.services.changelog import chronological_changelog, load_changelog_text

__all__ = [
    "chronological_changelog",
    "get_last_seen_changelog_version",
    "get_sbatch_follow_mode",
    "load_changelog_text",
    "set_last_seen_changelog_version",
    "show_exception",
]
