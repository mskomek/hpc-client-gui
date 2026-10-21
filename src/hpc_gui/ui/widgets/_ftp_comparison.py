"""FTP directory-comparison leaf for the file-manager FTP widget.

Owns ``FtpComparisonMixin``: comparison visibility/waiting state, settings
persistence, toggle handling, debounced recompute scheduling, and snapshot
comparison across the local and active remote panels. Uses the 150 ms debounce
timer created in the facade ``__init__``. Everything else is reached via
``self``.

Imports lower-level config/services/i18n only — never panels, FTP internals of
other leaves, controllers, or other branches.
"""

from __future__ import annotations

from hpc_gui.config.file_manager_profile import (
    normalize_file_manager_settings,
    update_profile_file_manager_settings,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.directory_comparison import compare_directory_entries


class FtpComparisonMixin:
    """Directory-comparison ownership (mixed into ``FtpWidget``)."""

    session: object

    def _session_file_manager(self) -> dict:
        cfg = (self.session or {}).get("cfg")
        return normalize_file_manager_settings(
            getattr(cfg, "file_manager_settings", None)
        )

    def _set_compare_checked(self, checked: bool) -> None:
        if self.btn_compare_directories.isChecked() == checked:
            return
        self.btn_compare_directories.blockSignals(True)
        try:
            self.btn_compare_directories.setChecked(checked)
        finally:
            self.btn_compare_directories.blockSignals(False)

    def _apply_comparison_state(self, file_manager: dict) -> None:
        """Reset comparison UI from the current profile's stored setting."""
        connected = bool(self.session and self.session.get("connected"))
        self._comparison_waiting_reason = ""
        self._comparison_recompute_timer.stop()
        self._set_comparison_waiting("")
        self.btn_compare_directories.setEnabled(connected)
        wanted = bool(file_manager.get("comparison_enabled")) if connected else False
        self._set_compare_checked(wanted)
        self._apply_comparison_visibility(wanted)
        if wanted:
            self._schedule_comparison_recompute()

    def _apply_comparison_visibility(self, visible: bool) -> None:
        self.local_panel.set_comparison_visible(visible)
        self.panel_scratch.set_comparison_visible(visible)
        self.panel_home.set_comparison_visible(visible)

    def _set_comparison_waiting(self, reason: str) -> None:
        self._comparison_waiting_reason = reason
        base = t("ftp.compare_directories")
        self.btn_compare_directories.setToolTip(
            f"{base}\n{reason}" if reason else base
        )

    def _persist_comparison_setting(self, value: bool) -> bool:
        profile_name = str((self.session or {}).get("profile_name") or "").strip()
        if not profile_name:
            return False
        update_profile_file_manager_settings(
            profile_name,
            {"comparison_enabled": value},
        )
        return True

    def _on_compare_directories_toggled(self, checked: bool) -> None:
        self._apply_comparison_visibility(checked)
        if not (self.session and self.session.get("connected")):
            return
        if checked:
            self._schedule_comparison_recompute()
        else:
            self._comparison_recompute_timer.stop()
            self._set_comparison_waiting("")
        saved = self._session_file_manager()
        if bool(saved.get("comparison_enabled")) == bool(checked):
            return
        try:
            self._persist_comparison_setting(bool(checked))
        except Exception as exc:
            self.btn_compare_directories.setChecked(not checked)
            self._set_comparison_waiting(str(exc))

    def _schedule_comparison_recompute(self) -> None:
        if not self.btn_compare_directories.isChecked():
            return
        if not (self.session and self.session.get("connected")):
            return
        self._comparison_recompute_timer.start()

    def _recompute_directory_comparison(self) -> None:
        if not self.btn_compare_directories.isChecked():
            return
        if not (self.session and self.session.get("connected")):
            return
        local_panel = self.local_panel
        remote_panel = self.active_remote_panel()
        other_remote = (
            self.panel_home if remote_panel is self.panel_scratch else self.panel_scratch
        )
        local_identity, local_entries = local_panel.current_entries_snapshot()
        remote_identity, remote_entries = remote_panel.current_entries_snapshot()
        local_current = str(local_panel.current_dir or "")
        remote_current = str(remote_panel.current_dir or "").rstrip("/") or "/"
        missing = []
        if not local_identity or local_identity != local_current:
            missing.append(t("ftp.waiting_local_folder"))
        if not remote_identity or remote_identity != remote_current:
            missing.append(t("ftp.waiting_remote_folder"))
        if missing:
            local_panel.clear_comparison_statuses()
            remote_panel.clear_comparison_statuses()
            self._set_comparison_waiting("; ".join(missing))
            return
        try:
            result = compare_directory_entries(local_entries, remote_entries)
        except Exception as exc:
            local_panel.clear_comparison_statuses()
            remote_panel.clear_comparison_statuses()
            self._set_comparison_waiting(str(exc))
            return
        if (
            str(local_panel.current_dir or "") != local_identity
            or (str(remote_panel.current_dir or "").rstrip("/") or "/") != remote_identity
            or self.active_remote_panel() is not remote_panel
        ):
            return
        other_remote.clear_comparison_statuses()
        local_panel.apply_comparison_statuses(result.local)
        remote_panel.apply_comparison_statuses(result.remote)
        self._set_comparison_waiting("")


__all__ = [
    "FtpComparisonMixin",
]
